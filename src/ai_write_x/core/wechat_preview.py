import os
import re
import time
import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from src.ai_write_x.utils import utils
from src.ai_write_x.utils.path_manager import PathManager
import src.ai_write_x.utils.log as lg

class WeChatPreviewEngine:
    """微信公众号文章预览引擎 - 1:1 还原手机版效果"""
    
    # 微信官方支持的 CSS 属性白名单
    WECHAT_SUPPORTED_CSS = {
        'color', 'background-color', 'font-size', 'font-weight', 'font-style',
        'font-family', 'text-align', 'line-height', 'margin', 'padding',
        'border', 'border-radius', 'box-shadow', 'width', 'height',
        'display', 'position', 'top', 'left', 'right', 'bottom',
        'flex', 'flex-direction', 'justify-content', 'align-items',
        'text-decoration', 'letter-spacing', 'word-spacing',
        'vertical-align', 'overflow', 'visibility', 'opacity',
        'transform', 'transition', 'animation'
    }
    
    # 微信不支持的 CSS 属性（会被过滤）
    WECHAT_BLOCKED_CSS = {
        'position: fixed', 'float',
        'z-index', 'clip', 'mask', 'filter',
        'backdrop-filter', 'mix-blend-mode'
    }
    
    # 微信安全字体列表
    SAFE_FONTS = [
        '-apple-system', 'BlinkMacSystemFont', 'Helvetica Neue',
        'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei',
        'Arial', 'sans-serif'
    ]
    
    def __init__(self):
        self.preview_dir = PathManager.get_root_dir() / "previews"
        self.preview_dir.mkdir(exist_ok=True)
    
    def generate_preview_html(self, content: str, title: str = "文章预览") -> str:
        """生成微信预览 HTML（1:1 还原手机版）"""
        
        # 清理和规范化 HTML
        cleaned_content = self._clean_html_for_wechat(content)
        
        # 生成完整的预览页面
        preview_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{title}</title>
    <style>
        /* 微信文章基础样式还原 */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
            font-size: 17px;
            line-height: 1.6;
            color: #333;
            background-color: #ededed;
            max-width: 677px;
            margin: 0 auto;
            padding: 0;
        }}
        
        /* 微信文章容器 */
        .wechat-article {{
            background-color: #fff;
            padding: 20px 16px;
            min-height: 100vh;
        }}
        
        /* 图片样式 */
        img {{
            max-width: 100% !important;
            height: auto !important;
            display: block;
            margin: 16px 0;
            border-radius: 8px;
        }}
        
        /* 顶部状态栏模拟 */
        .status-bar {{
            background-color: #ededed;
            padding: 8px 16px;
            font-size: 12px;
            color: #000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 9999;
        }}
        
        /* 内容区域 */
        .content-wrapper {{
            padding-bottom: 20px;
        }}
    </style>
</head>
<body>
    <!-- 顶部状态栏模拟 -->
    <div class="status-bar">
        <span>📶 5G</span>
        <span id="current-time">12:00</span>
        <span>🔋 100%</span>
    </div>
    
    <!-- 文章内容 -->
    <div class="wechat-article content-wrapper">
        <h1 style="font-size: 22px; line-height: 1.4; margin-bottom: 20px;">{title}</h1>
        {cleaned_content}
    </div>
    
    <script>
        // 更新时间
        function updateTime() {{
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            document.getElementById('current-time').textContent = hours + ":" + minutes;
        }}
        updateTime();
        setInterval(updateTime, 1000);
    </script>
</body>
</html>"""
        
        return preview_html
    
    def _clean_html_for_wechat(self, html_content: str) -> str:
        """清理 HTML 以符合微信规范"""
        
        # 移除不支持的 CSS 属性 (鲁棒性加强)
        for blocked in self.WECHAT_BLOCKED_CSS:
            # 匹配 属性名: 属性值 结构，处理空格和分号
            # 例如: position: fixed; 或 filter: blur(5px);
            prop_name = blocked.split(':')[0].strip() if ':' in blocked else blocked
            if ':' in blocked:
                # 匹配特定属性值对
                pattern = rf'{re.escape(prop_name)}\s*:\s*{re.escape(blocked.split(":")[1].strip())}[^;]*;?'
            else:
                # 匹配属性及其所有值
                pattern = rf'{re.escape(prop_name)}\s*:[^;]*;?'
                
            html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE)
        
        # 移除<script>标签
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        
        # 移除外部 CSS 引用
        html_content = re.sub(r'<link[^>]*rel=["\']stylesheet["\'][^>]*>', '', html_content, flags=re.IGNORECASE)
        
        # 确保图片有 alt 属性且 src 安全
        html_content = re.sub(
            r'<img([^>]*)src=["\']([^"\']+)["\']([^>]*)>',
            lambda m: f'<img{m.group(1)}src="{m.group(2)}"{m.group(3)} alt="图片">' if 'alt=' not in m.group(0) else m.group(0),
            html_content,
            flags=re.IGNORECASE
        )
        
        return html_content
    
    def check_compatibility(self, html_content: str) -> Dict[str, Any]:
        """检查 HTML 兼容性，返回可能被微信过滤的内容"""
        
        issues = []
        warnings = []
        
        # 检查不支持的 CSS
        for blocked in self.WECHAT_BLOCKED_CSS:
            if blocked.lower() in html_content.lower():
                issues.append(f"检测到不支持的 CSS: {blocked}")
        
        # 检查<script>标签
        if '<script' in html_content.lower():
            issues.append("检测到<script>标签（微信会过滤）")
        
        # 检查图片是否缺少 alt
        img_tags = re.findall(r'<img[^>]*>', html_content, re.IGNORECASE)
        for img in img_tags:
            if 'alt=' not in img.lower():
                warnings.append("图片缺少 alt 属性")
        
        # 计算得分
        score = max(0, 100 - len(issues) * 15 - len(warnings) * 5)
        
        return {
            'compatible': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'score': score
        }
    
    def save_preview(self, html_content: str, title: str) -> str:
        """保存预览 HTML 并返回路径"""
        preview_html = self.generate_preview_html(html_content, title)
        
        # 使用日期文件夹
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        safe_title = utils.sanitize_filename(title)
        
        # 预览存放在 output/previews/YYYY-MM-DD/SafeTitle/
        preview_dir = os.path.join(PathManager.get_output_dir(), "previews", date_str, safe_title)
        os.makedirs(preview_dir, exist_ok=True)
        
        preview_path = os.path.join(preview_dir, "preview.html")
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(preview_html)
            
        return preview_path

    async def capture_screenshots(self, preview_path: str, title: str) -> List[str]:
        """V20.1: 使用 Playwright 捕获 3 张手机端截图 (V-AUDIT)"""
        screenshots = []
        try:
            from playwright.async_api import async_playwright
            
            # 自动检测并安装浏览器内核 (V20.1)
            await self._ensure_playwright_installed()
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # 模拟 iPhone 13 宽度
                context = await browser.new_context(
                    viewport={'width': 390, 'height': 844},
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
                )
                page = await context.new_page()
                # 转换绝对路径为 file:// 协议
                abs_path = os.path.abspath(preview_path)
                await page.goto(f"file:///{abs_path}")
                await page.wait_for_timeout(2000) # 等待动画
                
                preview_dir = os.path.dirname(preview_path)
                safe_title = utils.sanitize_filename(title)
                
                # 截图 1: 顶部 Hook 区
                s1_path = os.path.join(preview_dir, f"{safe_title}_Screen1.png")
                await page.screenshot(path=s1_path)
                screenshots.append(s1_path)
                
                # 截图 2: 中部段落/图片区
                await page.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(500)
                s2_path = os.path.join(preview_dir, f"{safe_title}_Screen2.png")
                await page.screenshot(path=s2_path)
                screenshots.append(s2_path)
                
                # 截图 3: 底部尾页/CTA
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(500)
                s3_path = os.path.join(preview_dir, f"{safe_title}_Screen3.png")
                await page.screenshot(path=s3_path)
                screenshots.append(s3_path)
                
                await browser.close()
        except Exception as e:
            lg.print_log(f"📸 截图捕获失败: {str(e)}", "warning")
            
        return screenshots

    def audit_visuals(self, html_content: str) -> Dict[str, Any]:
        """V20.1: AI 视觉自审逻辑
        检测关键组件是否成功渲染，段落密度是否合理。
        """
        issues = []
        success_flags = {
            "has_h2": "<h2>" in html_content,
            "has_images": "<img" in html_content,
            "has_quotes": "quote" in html_content.lower(),
            "spacing_ok": 'height: 20px' in html_content or 'margin' in html_content
        }
        
        if not success_flags["has_h2"]:
            issues.append("未检测到副标题，阅读节奏感较差")
        if not success_flags["spacing_ok"]:
            issues.append("段落间距可能不足，建议增加空行组件")
            
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "flags": success_flags
        }

    def generate_compatibility_report(self, html_content: str) -> str:
        """生成兼容性报告"""
        report = []
        
        # 检查是否包含 script 标签
        if "<script" in html_content:
            report.append("❌ 包含有害的 <script> 标签")
            
        # 检查是否有外部 CSS
        if "<link" in html_content or "<style" in html_content:
            report.append("⚠️ 包含外部样式或 <style> 块，微信可能不完全支持")
            
        # 检查图片占位符
        if "img-placeholder" in html_content:
            report.append("⚠️ 仍包含图片占位符，未完成生图渲染")
            
        if not report:
            return "✅ 微信预览兼容性良好"
            
        return " | ".join(report)

    async def _ensure_playwright_installed(self):
        """确保 Playwright 浏览器内核已安装"""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                try:
                    # 尝试启动以检查是否存在
                    browser = await p.chromium.launch(headless=True)
                    await browser.close()
                except Exception:
                    # 如果启动失败，说明可能没安装内核
                    lg.print_log("🌐 检测到缺少浏览器内核，正在后台自动补全 (仅执行一次)...", "info")
                    import subprocess
                    import sys
                    # 运行安装命令
                    subprocess.run(
                        [sys.executable, "-m", "playwright", "install", "chromium"],
                        check=True,
                        capture_output=True
                    )
                    lg.print_log("✅ 浏览器内核补全成功！", "success")
        except Exception as e:
            lg.print_log(f"⚠️ 自动补全内核失败: {str(e)}", "warning")
