# -*- coding: UTF-8 -*-
"""
视觉处理库 - Vision Processor
用于在抓取到热搜/借鉴文章时，自动将文章中的配图提取出并使用 Vision LLM 进行看图说话理解。
最后将理解的文本拼接回文章，实现真正的图文并茂上下文。
"""
import re
from typing import Dict, List
from src.ai_write_x.core.llm_client import LLMClient
from src.ai_write_x.utils import log

class VisionProcessor:
    def __init__(self):
        self.llm_client = LLMClient()
    
    def process_article_images(self, article: Dict) -> Dict:
        """
        处理文章字典，找出图片并请求 VL（Vision LLM）打标理解，追加到上下文中。
        """
        if not article:
            return article
            
        # 根据爬虫不同的数据结构提取文本和图片
        content = article.get('content') or article.get('article_info') or ""
        img_urls = article.get('img_list', [])
        
        # 如果 img_list 为空，我们再尝试从 content 里正则提取 <img src="...">
        if not img_urls and content:
            found_imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
            # 有些 markdown 格式的
            found_md_imgs = re.findall(r'!\[.*?\]\((.*?)\)', content)
            img_urls.extend(found_imgs)
            img_urls.extend(found_md_imgs)
            
        # 过滤空链接并去重
        img_urls = list(set([u for u in img_urls if u and u.startswith('http')]))
        
        if not img_urls:
            return article

        # 为了避免过多请求，最多挑选前2张图像进行理解
        max_images = 2
        selected_imgs = img_urls[:max_images]
        
        log.print_log(f"[VisionProcessor] 检测到 {len(img_urls)} 张图，准备对前 {len(selected_imgs)} 张执行 Vision LLM 深度视觉理解...", "info")
        
        vision_understandings = []
        for idx, img_url in enumerate(selected_imgs):
            try:
                log.print_log(f"  [视觉扫描] 正在分析图 {idx + 1} ({img_url[:40]}...)", "info")
                prompt = "你是一个专业的信息提取助手。请简明扼要地描述这张图片里的核心内容、发生场景、以及任何明显的信息（人物、环境、文字等）。只输出描述，不要废话。"
                
                # 开始调用 Vision
                # 注意：chat_with_vision 需要模型支持，如 gpt-4o, qwen-vl 等
                # 根据 llm_client.py 逻辑，它会自动 fallback 为 vision 模型
                understanding = self.llm_client.chat_with_vision(text=prompt, image_data=img_url)
                if understanding:
                    vision_understandings.append(f"[图{idx+1} 视觉理解: {understanding}]")
                    log.print_log(f"  [识别成功] 图 {idx+1} 分析完成。", "success")
            except Exception as e:
                log.print_log(f"  [识别失败] 图 {idx+1} Vision LLM 返回错误: {e}", "warning")
                
        # 将视觉理解拼接到原文末尾
        if vision_understandings:
            vision_text = "\n\n【附加视觉解析信息(由VL提供)】：\n" + "\n".join(vision_understandings)
            
            if 'article_info' in article:
                article['article_info'] += vision_text
            if 'content' in article:
                article['content'] += vision_text
                
            log.print_log(f"[VisionProcessor] 已将 {len(vision_understandings)} 段视觉解析合并至正文上下文。", "success")
            
        return article
