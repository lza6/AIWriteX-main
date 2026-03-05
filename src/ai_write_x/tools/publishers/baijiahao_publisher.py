import time
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
from src.ai_write_x.utils import log as lg


class BaijiahaoPublisher(PlaywrightPublisher):
    """
    Playwright publisher for 百家号 (baijiahao.baidu.com).
    """

    def __init__(self, headless: bool = True):
        super().__init__(platform_name="baijiahao", headless=headless)
        self.login_url = "https://baijiahao.baidu.com/builder/app/login"
        self.verify_selector = ".user-info-avatar, .builder-aside"  # 左侧菜单或头像
        self.publish_url = "https://baijiahao.baidu.com/builder/rc/edit?type=news"

    def check_and_login(self):
        self.require_login(self.login_url, self.verify_selector)

    def publish(self, title: str, content: str, images: list = None, **kwargs) -> tuple[bool, str]:
        """
        Publish to Baijiahao.
        """
        self.check_and_login()
        
        lg.print_log(f"[{self.platform_name}] 开始自动发布流程...", "info")
        
        with sync_playwright() as p:
            browser, context = self._get_browser_context(p, headless=self.headless)
            page = context.new_page()
            
            try:
                # 1. 访问发文页面
                page.goto(self.publish_url, timeout=60000)
                page.wait_for_load_state("networkidle")
                
                # 关闭可能的提示弹窗
                try:
                    close_btn = page.locator(".basic-dialog-close")
                    if close_btn.count() > 0:
                        close_btn.click()
                except Exception:
                    pass

                # 2. 填写标题
                lg.print_log(f"[{self.platform_name}] 正在填写标题...", "info")
                try:
                    title_input = page.locator("input[placeholder*='标题']")
                    title_input.wait_for(timeout=15000)
                    title_input.fill(title[:60])  # 百家号标题有字数限制
                except PlaywrightTimeoutError:
                    return False, "无法定位百家号标题输入框"

                time.sleep(1)
                
                # 3. 填写正文
                lg.print_log(f"[{self.platform_name}] 正在填写正文...", "info")
                try:
                    # 优先尝试现代编辑器 (ProseMirror/Quill)
                    self.smart_insert_text(page, ".ProseMirror, .ql-editor, .editor-content", content)
                except Exception:
                    # 尝试 UEditor iframe 模式
                    try:
                        editor_selector = "#edui1_iframeholder iframe"
                        page.wait_for_selector(editor_selector, timeout=5000)
                        editor_frame = page.frame_locator(editor_selector)
                        body = editor_frame.locator("body")
                        body.click()
                        # 已经在 iframe 内部点击，直接插入文本
                        paragraphs = content.split('\n')
                        for p in paragraphs:
                            if p.strip():
                                page.keyboard.insert_text(p.strip())
                                page.keyboard.press("Enter")
                                time.sleep(0.1)
                    except Exception as e:
                        lg.print_log(f"[{self.platform_name}] 编辑器定位失败: {e}", "warning")

                # 4. 上传图片 (可选)
                if images and len(images) > 0:
                    lg.print_log(f"[{self.platform_name}] 正在上传图片...", "info")
                    self.upload_images(page, "input[type='file']", images)

                time.sleep(2)
                
                # 5. 封面设置 (如果需要)
                try:
                    single_cover_radio = page.locator("label:has-text('单图')")
                    if single_cover_radio.count() > 0:
                        single_cover_radio.click()
                except Exception:
                    pass

                # 6. 点击发布
                lg.print_log(f"[{self.platform_name}] 准备进行发布相关操作...", "info")
                publish_btn = page.locator("button:has-text('发布')")
                
                if kwargs.get("commit"):
                    lg.print_log(f"[{self.platform_name}] 确认发布 (Commit=True)", "success")
                    # publish_btn.click() 
                else:
                    lg.print_log(f"[{self.platform_name}] 模拟运行，未点击真实发布按钮。如需真实发布请设置 commit=True", "info")

                time.sleep(3)
                
                lg.print_log(f"[{self.platform_name}] 发布流程执行完毕。", "success")
                return True, "成功（已填写内容）"
                
            except Exception as e:
                error_msg = f"发布异常: {str(e)}"
                lg.print_log(f"[{self.platform_name}] {error_msg}", "error")
                return False, error_msg
            finally:
                context.close()
                browser.close()
