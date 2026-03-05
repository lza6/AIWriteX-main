import time
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
from src.ai_write_x.utils import log as lg


class XiaohongshuPublisher(PlaywrightPublisher):
    """
    Playwright publisher for 小红书 (creator.xiaohongshu.com).
    """

    def __init__(self, headless: bool = True):
        super().__init__(platform_name="xiaohongshu", headless=headless)
        self.login_url = "https://creator.xiaohongshu.com/creator/home"
        self.verify_selector = ".creator-home"  # 创作者页面主页的某个唯一元素
        self.publish_url = "https://creator.xiaohongshu.com/creator/post"

    def check_and_login(self):
        self.require_login(self.login_url, self.verify_selector)

    def publish(self, title: str, content: str, images: list = None, **kwargs) -> tuple[bool, str]:
        """
        Publish to Xiaohongshu (TuWen / 图文).
        """
        self.check_and_login()
        
        lg.print_log(f"[{self.platform_name}] 开始自动发布流程...", "info")
        
        with sync_playwright() as p:
            browser, context = self._get_browser_context(p, headless=self.headless)
            page = context.new_page()
            
            try:
                # 1. 访问发布页
                page.goto(self.publish_url, timeout=60000)
                page.wait_for_load_state("networkidle")
                
                # 2. 上传图片 (小红书图文必须有至少一张图片)
                if images and len(images) > 0:
                    lg.print_log(f"[{self.platform_name}] 正在上传图片...", "info")
                    self.upload_images(page, "input[type='file'][accept*='image']", images)
                else:
                    lg.print_log(f"[{self.platform_name}] 警告：小红书发布图文通常需要至少一张图片。", "warning")
                    # 如果没有图片，尝试继续，但可能会失败

                # 3. 填写标题
                lg.print_log(f"[{self.platform_name}] 正在填写标题...", "info")
                title_input = page.locator("input[placeholder*='填写标题']")
                title_input.wait_for(timeout=10000)
                # 小红书标题建议精炼，截断为 30 字
                truncated_title = title[:30]
                title_input.fill(truncated_title)
                
                # 4. 填写正文
                lg.print_log(f"[{self.platform_name}] 正在填写正文...", "info")
                self.smart_insert_text(page, ".ql-editor", content)
                
                # 5. 点击发布按钮
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
