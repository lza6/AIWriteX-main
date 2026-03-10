"""
AIWriteX 抖音发布器
支持抖音视频发布和图文发布功能
"""
import time
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from src.ai_write_x.tools.publishers.base_publisher import PlaywrightPublisher
from src.ai_write_x.utils import log as lg


class DouyinPublisher(PlaywrightPublisher):
    """
    Playwright publisher for 抖音 (creator.douyin.com)
    支持视频发布和图文发布
    """

    def __init__(self, headless: bool = True):
        super().__init__(platform_name="douyin", headless=headless)
        # 抖音创作者平台
        self.login_url = "https://creator.douyin.com/"
        # 登录成功的标志：创作中心元素
        self.verify_selector = ".creator-layout, .user-info"
        # 视频发布页面
        self.video_publish_url = "https://creator.douyin.com/creator-micro/content/upload"
        # 图文发布页面
        self.image_publish_url = "https://creator.douyin.com/creator-micro/content/upload?type=image"

    def check_and_login(self):
        """检查登录状态，如未登录则引导登录"""
        self.require_login(self.login_url, self.verify_selector)

    def publish_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        cover_path: str = None,
        **kwargs
    ) -> tuple[bool, str]:
        """
        发布视频到抖音
        
        Args:
            video_path: 视频文件路径
            title: 视频标题
            description: 视频描述
            tags: 话题标签列表
            cover_path: 封面图片路径
            
        Returns:
            (成功状态, 消息)
        """
        if not os.path.exists(video_path):
            return False, f"视频文件不存在: {video_path}"

        self.check_and_login()
        lg.print_log(f"[{self.platform_name}] 开始视频发布流程...", "info")

        with sync_playwright() as p:
            browser, context = self._get_browser_context(p, headless=self.headless)
            page = context.new_page()

            try:
                # 1. 访问视频发布页面
                page.goto(self.video_publish_url, timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                # 2. 上传视频
                lg.print_log(f"[{self.platform_name}] 正在上传视频...", "info")
                video_input = page.locator("input[type='file'][accept='video/*']")
                video_input.wait_for(timeout=20000)
                video_input.set_input_files(video_path)

                # 等待上传完成
                lg.print_log(f"[{self.platform_name}] 等待视频上传处理...", "info")
                time.sleep(10)  # 给足时间上传和处理

                # 3. 上传封面（如果提供）
                if cover_path and os.path.exists(cover_path):
                    lg.print_log(f"[{self.platform_name}] 正在上传封面...", "info")
                    try:
                        # 点击上传封面按钮
                        cover_btn = page.locator("text=上传封面").first
                        if cover_btn.count() > 0:
                            cover_btn.click()
                            time.sleep(1)
                            cover_input = page.locator("input[type='file']").last
                            cover_input.set_input_files(cover_path)
                            time.sleep(2)
                    except Exception as e:
                        lg.print_log(f"[{self.platform_name}] 封面上传失败: {e}", "warning")

                # 4. 填写标题和描述
                lg.print_log(f"[{self.platform_name}] 正在填写标题...", "info")
                title_input = page.locator("textarea[placeholder*='标题']").first
                title_input.wait_for(timeout=10000)
                # 抖音标题限制55字
                truncated_title = title[:55]
                title_input.fill(truncated_title)

                # 5. 添加话题标签
                if tags and len(tags) > 0:
                    lg.print_log(f"[{self.platform_name}] 正在添加话题标签...", "info")
                    for tag in tags[:5]:  # 限制5个标签
                        tag_input = page.locator("input[placeholder*='添加话题']").first
                        if tag_input.count() > 0:
                            tag_input.click()
                            tag_input.fill(f"#{tag}")
                            time.sleep(0.5)
                            # 选择第一个建议
                            suggestion = page.locator(".tag-suggestion-item").first
                            if suggestion.count() > 0:
                                suggestion.click()
                                time.sleep(0.3)

                # 6. 发布设置
                lg.print_log(f"[{self.platform_name}] 准备发布...", "info")
                
                if kwargs.get("commit"):
                    lg.print_log(f"[{self.platform_name}] 确认发布 (Commit=True)", "success")
                    publish_btn = page.locator("button:has-text('发布'):not(:has-text('定时'))").first
                    if publish_btn.count() > 0:
                        publish_btn.click()
                        time.sleep(5)
                        return True, "视频发布成功"
                else:
                    lg.print_log(f"[{self.platform_name}] 模拟运行，未点击真实发布按钮", "info")

                return True, "成功（已填写内容）"

            except Exception as e:
                error_msg = f"视频发布异常: {str(e)}"
                lg.print_log(f"[{self.platform_name}] {error_msg}", "error")
                return False, error_msg
            finally:
                context.close()
                browser.close()

    def publish_images(
        self,
        title: str,
        content: str,
        images: list,
        tags: list = None,
        **kwargs
    ) -> tuple[bool, str]:
        """
        发布图文到抖音
        
        Args:
            title: 图文标题
            content: 图文内容
            images: 图片路径列表
            tags: 话题标签列表
            
        Returns:
            (成功状态, 消息)
        """
        if not images or len(images) == 0:
            return False, "抖音图文发布需要至少一张图片"

        self.check_and_login()
        lg.print_log(f"[{self.platform_name}] 开始图文发布流程...", "info")

        with sync_playwright() as p:
            browser, context = self._get_browser_context(p, headless=self.headless)
            page = context.new_page()

            try:
                # 1. 访问图文发布页面
                page.goto(self.image_publish_url, timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                # 2. 上传图片
                lg.print_log(f"[{self.platform_name}] 正在上传图片...", "info")
                valid_images = [img for img in images if os.path.exists(img)]
                if not valid_images:
                    return False, "没有有效的图片文件"

                # 抖音图文支持多张图片
                image_input = page.locator("input[type='file'][accept='image/*']").first
                image_input.wait_for(timeout=10000)
                
                # 逐个上传图片
                for img_path in valid_images[:9]:  # 最多9张
                    image_input.set_input_files(img_path)
                    time.sleep(1)

                time.sleep(3)  # 等待图片处理

                # 3. 填写标题
                lg.print_log(f"[{self.platform_name}] 正在填写标题...", "info")
                title_input = page.locator("textarea[placeholder*='标题']").first
                title_input.wait_for(timeout=10000)
                truncated_title = title[:55]
                title_input.fill(truncated_title)

                # 4. 填写正文
                if content:
                    lg.print_log(f"[{self.platform_name}] 正在填写正文...", "info")
                    content_input = page.locator(".editor-content[contenteditable='true']").first
                    if content_input.count() > 0:
                        content_input.click()
                        # 分段输入内容
                        paragraphs = content.split('\n')
                        for para in paragraphs:
                            if para.strip():
                                content_input.type(para.strip())
                                page.keyboard.press("Enter")
                                time.sleep(0.1)

                # 5. 添加话题标签
                if tags and len(tags) > 0:
                    lg.print_log(f"[{self.platform_name}] 正在添加话题标签...", "info")
                    for tag in tags[:5]:
                        tag_input = page.locator("input[placeholder*='话题']").first
                        if tag_input.count() > 0:
                            tag_input.click()
                            tag_input.type(f"#{tag}")
                            time.sleep(0.5)
                            # 选择建议
                            suggestion = page.locator(".tag-suggestion-item").first
                            if suggestion.count() > 0:
                                suggestion.click()
                                time.sleep(0.3)

                # 6. 发布
                lg.print_log(f"[{self.platform_name}] 准备发布...", "info")
                
                if kwargs.get("commit"):
                    lg.print_log(f"[{self.platform_name}] 确认发布 (Commit=True)", "success")
                    publish_btn = page.locator("button:has-text('发布')").first
                    if publish_btn.count() > 0:
                        publish_btn.click()
                        time.sleep(5)
                        return True, "图文发布成功"
                else:
                    lg.print_log(f"[{self.platform_name}] 模拟运行，未点击真实发布按钮", "info")

                return True, "成功（已填写内容）"

            except Exception as e:
                error_msg = f"图文发布异常: {str(e)}"
                lg.print_log(f"[{self.platform_name}] {error_msg}", "error")
                return False, error_msg
            finally:
                context.close()
                browser.close()

    def publish(self, title: str, content: str, images: list = None, **kwargs) -> tuple[bool, str]:
        """
        通用发布接口
        如果提供视频路径则发布视频，否则发布图文
        """
        video_path = kwargs.get("video_path")
        
        if video_path and os.path.exists(video_path):
            return self.publish_video(
                video_path=video_path,
                title=title,
                description=content,
                tags=kwargs.get("tags"),
                cover_path=kwargs.get("cover_path"),
                **kwargs
            )
        else:
            return self.publish_images(
                title=title,
                content=content,
                images=images or [],
                tags=kwargs.get("tags"),
                **kwargs
            )
