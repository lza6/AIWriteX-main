import os
import time
import json
from abc import ABC, abstractmethod
from typing import Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext
from src.ai_write_x.utils import log as lg


class PlaywrightPublisher(ABC):
    """
    Playwright-based abstract base class for multi-platform publishing.
    Handles browser launch, context creation, and cookie state management.
    """

    def __init__(self, platform_name: str, headless: bool = True):
        self.platform_name = platform_name
        self.headless = headless
        
        # Determine the base directory for saving cookies
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        self.cookies_dir = os.path.join(base_dir, "data", "cookies")
        os.makedirs(self.cookies_dir, exist_ok=True)
        self.cookie_file = os.path.join(self.cookies_dir, f"{self.platform_name}_cookies.json")

    def _get_browser_context(self, p, headless: bool):
        """Launch browser and get context"""
        browser = p.chromium.launch(headless=headless, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        # Load local cookies if exists
        self._load_cookies(context)
        return browser, context

    def _load_cookies(self, context: BrowserContext):
        """Load cookies from local file"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)
                lg.print_log(f"[{self.platform_name}] 已加载本地 Cookie。", "info")
            except Exception as e:
                lg.print_log(f"[{self.platform_name}] 加载 Cookie 失败: {e}", "warning")

    def _save_cookies(self, context: BrowserContext):
        """Save cookies to local file"""
        try:
            cookies = context.cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=4)
            lg.print_log(f"[{self.platform_name}] Cookie 已保存至 {self.cookie_file}。", "success")
        except Exception as e:
            lg.print_log(f"[{self.platform_name}] 保存 Cookie 失败: {e}", "error")

    def require_login(self, login_url: str, verify_selector: str, timeout: int = 120000):
        """
        Open a visible browser to allow the user to scan a QR code or login manually if not logged in.
        
        :param login_url: The URL to navigate to for login.
        :param verify_selector: A CSS selector that indicates a successful login (e.g. avatar or writer center element).
        :param timeout: How long to wait for the user to login (default 120s).
        """
        lg.print_log(f"[{self.platform_name}] 正在检查登录状态，如需登录将弹出浏览器窗口请您扫码或手动登录...", "info")
        
        with sync_playwright() as p:
            # For login, we ALWAYS show the browser so the user can interact
            browser, context = self._get_browser_context(p, headless=False)
            page = context.new_page()
            page.goto(login_url)
            
            try:
                # Wait for the verify selector to appear, implying login is successful or already logged in
                page.wait_for_selector(verify_selector, timeout=timeout)
                lg.print_log(f"[{self.platform_name}] 登录验证成功！", "success")
                self._save_cookies(context)
            except Exception as e:
                lg.print_log(f"[{self.platform_name}] 登录验证超时或失败，请检查是否成功登录（{e}）。", "error")
            finally:
                context.close()
                browser.close()

    def upload_images(self, page: Page, input_selector: str, images: list):
        """Standard image upload helper"""
        if not images:
            return
        
        try:
            page.wait_for_selector(input_selector, timeout=10000)
            # Filter only existing files
            valid_images = [img for img in images if os.path.exists(img)]
            if valid_images:
                page.set_input_files(input_selector, valid_images)
                lg.print_log(f"[{self.platform_name}] 已上传 {len(valid_images)} 张图片。", "info")
                time.sleep(2)  # Wait for upload to process
        except Exception as e:
            lg.print_log(f"[{self.platform_name}] 图片上传失败: {e}", "warning")

    def smart_insert_text(self, page: Page, selector: str, content: str):
        """Smart text insertion for rich-text editors"""
        try:
            page.wait_for_selector(selector, timeout=10000)
            page.click(selector)
            
            # Split by paragraphs to simulate more natural typing/pasting
            paragraphs = content.split('\n')
            for p in paragraphs:
                if p.strip():
                    page.keyboard.insert_text(p.strip())
                    page.keyboard.press("Enter")
                    time.sleep(0.1)
            lg.print_log(f"[{self.platform_name}] 正文内容填写完毕。", "info")
        except Exception as e:
            lg.print_log(f"[{self.platform_name}] 正文填写失败: {e}", "warning")

    @abstractmethod
    def publish(self, title: str, content: str, images: list = None, **kwargs) -> tuple[bool, str]:
        """
        Abstract method to publish content.
        Needs to be implemented by subclass.
        
        :return: (True, "Publish Success URL") OR (False, "Error Message")
        """
        pass
