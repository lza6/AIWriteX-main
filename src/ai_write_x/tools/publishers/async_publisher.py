"""
AIWriteX 异步发布器基类
基于Playwright的异步API，提供更好的并发性能
"""
import asyncio
import json
import os
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Optional, List

from playwright.async_api import async_playwright, Page, BrowserContext
from src.ai_write_x.utils import log as lg
from src.ai_write_x.utils.performance_optimizer import browser_pool


class AsyncPlaywrightPublisher(ABC):
    """
    异步Playwright发布器基类
    
    特性:
    - 使用浏览器实例池复用浏览器
    - 异步操作提高并发性能
    - 自动Cookie管理
    """
    
    def __init__(self, platform_name: str, headless: bool = True):
        self.platform_name = platform_name
        self.headless = headless
        
        # 确定Cookie保存路径
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        self.cookies_dir = os.path.join(base_dir, "data", "cookies")
        os.makedirs(self.cookies_dir, exist_ok=True)
        self.cookie_file = os.path.join(self.cookies_dir, f"{self.platform_name}_cookies.json")
    
    async def _get_context(self):
        """获取浏览器上下文（从池或新建）"""
        # 使用同步的池获取上下文，然后包装为异步
        loop = asyncio.get_event_loop()
        context = await loop.run_in_executor(
            None, 
            browser_pool.get_context, 
            self.cookie_file
        )
        return context
    
    async def _release_context(self, context):
        """释放浏览器上下文回池"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            browser_pool.release_context,
            context,
            self.cookie_file
        )
    
    @asynccontextmanager
    async def _managed_context(self):
        """上下文管理器，自动释放资源"""
        context = None
        try:
            context = await self._get_context()
            yield context
        finally:
            if context:
                await self._release_context(context)
    
    async def check_and_login(self):
        """异步检查登录状态"""
        # 登录操作仍需同步（用户交互）
        from playwright.sync_api import sync_playwright
        
        lg.print_log(f"[{self.platform_name}] 检查登录状态...", "info")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_login_check)
    
    def _sync_login_check(self):
        """同步登录检查（内部使用）"""
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
            context = browser.new_context()
            
            # 加载Cookie
            if os.path.exists(self.cookie_file):
                try:
                    with open(self.cookie_file, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)
                        context.add_cookies(cookies)
                except Exception:
                    pass
            
            page = context.new_page()
            page.goto(self.login_url)
            
            try:
                page.wait_for_selector(self.verify_selector, timeout=120000)
                lg.print_log(f"[{self.platform_name}] 登录验证成功！", "success")
                
                # 保存Cookie
                cookies = context.cookies()
                with open(self.cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=4)
            except Exception as e:
                lg.print_log(f"[{self.platform_name}] 登录验证失败: {e}", "error")
            finally:
                context.close()
                browser.close()
    
    async def upload_images(self, page: Page, input_selector: str, images: List[str]):
        """异步图片上传"""
        if not images:
            return
        
        try:
            await page.wait_for_selector(input_selector, timeout=10000)
            valid_images = [img for img in images if os.path.exists(img)]
            if valid_images:
                await page.set_input_files(input_selector, valid_images)
                lg.print_log(f"[{self.platform_name}] 已上传 {len(valid_images)} 张图片。", "info")
                await asyncio.sleep(2)
        except Exception as e:
            lg.print_log(f"[{self.platform_name}] 图片上传失败: {e}", "warning")
    
    async def smart_insert_text(self, page: Page, selector: str, content: str):
        """异步智能文本插入"""
        try:
            await page.wait_for_selector(selector, timeout=10000)
            await page.click(selector)
            
            paragraphs = content.split('\n')
            for p in paragraphs:
                if p.strip():
                    await page.keyboard.insert_text(p.strip())
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(0.1)
            
            lg.print_log(f"[{self.platform_name}] 正文内容填写完毕。", "info")
        except Exception as e:
            lg.print_log(f"[{self.platform_name}] 正文填写失败: {e}", "warning")
    
    @abstractmethod
    async def publish(self, title: str, content: str, images: List[str] = None, **kwargs) -> tuple[bool, str]:
        """
        异步发布内容
        
        Returns:
            (成功状态, 消息)
        """
        pass
    
    @property
    @abstractmethod
    def login_url(self) -> str:
        """登录页面URL"""
        pass
    
    @property
    @abstractmethod
    def verify_selector(self) -> str:
        """登录成功验证选择器"""
        pass
