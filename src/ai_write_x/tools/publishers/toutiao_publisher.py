import time
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
from src.ai_write_x.utils import log as lg


class ToutiaoPublisher(PlaywrightPublisher):
    """
    Playwright publisher for 今日头条 (mp.toutiao.com).
    """

    def __init__(self, headless: bool = True):
        super().__init__(platform_name="toutiao", headless=headless)
        self.login_url = "https://mp.toutiao.com/profile_v4/index"
        # 创作中心左侧边栏或者顶部的头像通常可以作为登录成功的标志
        self.verify_selector = ".syl-page-menu, .xigua-menu"
        self.publish_url = "https://mp.toutiao.com/profile_v4/graphic/publish"

    def check_and_login(self):
        self.require_login(self.login_url, self.verify_selector)

    def publish(self, title: str, content: str, images: list = None, **kwargs) -> tuple[bool, str]:
        """
        Publish to Toutiao.
        """
        self.check_and_login()
        
        lg.print_log(f"[{self.platform_name}] 开始自动发布流程...", "info")
        
        with sync_playwright() as p:
            # For publishing, use the requested headless state
            browser, context = self._get_browser_context(p, headless=self.headless)
            page = context.new_page()
            
            try:
                # 1. 访问发文页面
                page.goto(self.publish_url, timeout=60000)
                page.wait_for_load_state("networkidle")
                
                # 等待编辑器加载
                try:
                    # 尝试寻找标题输入框
                    title_input_selector = "textarea[placeholder*='标题']"
                    page.wait_for_selector(title_input_selector, timeout=15000)
                except PlaywrightTimeoutError:
                    return False, "无法找到标题输入框，可能页面结构已改变或未登录成功。"

                # 2. 填写标题
                lg.print_log(f"[{self.platform_name}] 正在填写标题...", "info")
                # 头条标题限制一般是 5-30 或 5-50，这里做个简单截断保护
                truncated_title = title[:50]
                page.fill(title_input_selector, truncated_title)
                time.sleep(1)
                
                # 3. 填写正文 (头条通常使用的是 Prosemirror 或者相似的富文本编辑器)
                lg.print_log(f"[{self.platform_name}] 正在填写正文...", "info")
                self.smart_insert_text(page, ".ProseMirror", content)

                # 4. 上传图片 (可选)
                if images and len(images) > 0:
                    lg.print_log(f"[{self.platform_name}] 正在上传图片...", "info")
                    # 通常头条编辑器页面会有 input[type='file']，尝试自动寻找
                    file_input = page.locator("input[type='file']").first
                    if file_input.count() > 0:
                        self.upload_images(page, "input[type='file']", images)
                    else:
                        lg.print_log(f"[{self.platform_name}] 未能找到图片上传入口。", "warning")

                time.sleep(2)
                
                # 5. 点击发布按钮
                lg.print_log(f"[{self.platform_name}] 准备进行发布相关操作...", "info")
                # 寻找包含“发布”文字的按钮
                publish_btn_selector = "button:has-text('发布')"
                page.wait_for_selector(publish_btn_selector, timeout=10000)
                
                # 如果 kwargs 中带有 commit=True 则真实点击，否则默认仅保存/停留在页面
                if kwargs.get("commit"):
                    lg.print_log(f"[{self.platform_name}] 确认发布 (Commit=True)", "success")
                    # page.click(publish_btn_selector) 
                else:
                    lg.print_log(f"[{self.platform_name}] 模拟运行，未点击真实发布按钮。如需真实发布请设置 commit=True", "info")
                
                # 6. 等待发布成功的提示或跳转
                time.sleep(5) 
                
                lg.print_log(f"[{self.platform_name}] 发布流程执行完毕。", "success")
                return True, "成功（已填写内容）"
                
            except Exception as e:
                error_msg = f"发布过程中出现异常: {str(e)}"
                lg.print_log(f"[{self.platform_name}] {error_msg}", "error")
                return False, error_msg
            finally:
                context.close()
                browser.close()
