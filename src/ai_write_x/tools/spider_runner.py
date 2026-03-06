# -*- coding: UTF-8 -*-
"""
爬虫运行器 - 集成 article-spider 到主程序
"""
import asyncio
import os
import sys
import importlib.util
import threading
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# 添加 src/ai_write_x/scrapers 到路径
SPIDER_DIR = Path(__file__).parent.parent / "scrapers"
sys.path.insert(0, str(SPIDER_DIR))

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.ai_write_x.tools.spider_manager import spider_data_manager
from src.ai_write_x.utils import log


# 后台任务状态
class SpiderTaskStatus:
    """爬虫任务状态"""
    def __init__(self):
        self.running = False
        self.current_spider = ""
        self.progress = 0  # 0-100
        self.total_spiders = 0
        self.completed_spiders = 0
        self.results = []
        self.logs = []
        self.total_saved = 0
        
    def reset(self):
        self.running = False
        self.current_spider = ""
        self.progress = 0
        self.total_spiders = 0
        self.completed_spiders = 0
        self.results = []
        self.logs = []
        self.total_saved = 0
    
    def add_log(self, message: str, level: str = "info"):
        self.logs.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "level": level
        })
        # 保留最近100条日志
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]

# 全局任务状态
task_status = SpiderTaskStatus()


class SpiderRunner:
    """爬虫运行器"""

    def __init__(self):
        self.spiders: Dict = {}
        self.running = False
        # V13.0 Optimization: 将爬虫模块加载移至后台线程，防止阻塞 Web 服务器启动
        threading.Thread(target=self._load_spiders, daemon=True).start()

    def _load_spiders(self, silent=True):
        """加载爬虫模块"""
        # V13.0 Optimization: 默认静默加载，减少启动阶段的日志压力
        spider_files = [
            # 新闻爬虫
            ("pengpai", "PengPai", "综合", "澎湃新闻"),
            ("wangyi", "WangYi", "综合", "网易新闻"),
            ("souhu", "SouHu", "综合", "搜狐新闻"),
            ("tengxunxinwen", "TenXuNews", "新闻", "腾讯新闻"),
            ("xinlang", "XinLangGuoJi", "国际", "新浪国际"),
            ("zhongguoribao", "ChineseDayNews", "日报", "中国日报"),
            # GitHub/AI爬虫
            ("hellogithub", "HelloGithub", "GitHubTrending", "HelloGitHub"),
            # AI论文工具爬虫
            ("aipapers", "AIPapers", "AI推荐", "HuggingFace"),
            # 国际新闻爬虫
            ("zaobao", "ZaoBao", "国际", "联合早报"),
            ("nytimes", "NYTimes", "国际", "纽约时报"),
            ("wsj", "WSJ", "财经", "华尔街日报"),
            ("bbc", "BBCChinese", "国际", "BBC中文"),
            ("xinhua", "XinhuaNews", "国际", "新华社"),
            ("voa", "VOAChinese", "国际", "VOA中文"),
            ("8world", "World8", "国际", "8视界"),
            # 科技/体育
            ("ithome", "ITHome", "科技", "IT之家"),
            ("tengxuntiyu", "TenXun", "体育", "腾讯体育"),
            # 热点排行 (New)
            ("douyin", "DouyinSpider", "热搜", "抖音"),
            ("weibo", "WeiboSpider", "热搜", "微博"),
            # 网易新闻分类爬虫
            ("wangyi_domestic", "WangYiDomestic", "国内", "网易国内"),
            ("wangyi_fujian", "WangYiFujian", "地方", "网易福建"),
            ("wangyi_world", "WangYiWorld", "国际", "网易国际"),
            ("wangyi_tech", "WangYiTech", "科技", "网易科技"),
            ("wangyi_money", "WangYiMoney", "财经", "网易财经"),
            ("wangyi_war", "WangYiWar", "军事", "网易军事"),
        ]

        for filename, class_name, category, source in spider_files:
            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(
                    filename, SPIDER_DIR / f"{filename}.py"
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                spider_class = getattr(module, class_name)
                self.spiders[filename] = {
                    "name": class_name,
                    "class": spider_class,
                    "category": category,
                    "source": source,
                    "enabled": True
                }
                if not silent:
                    log.print_log(f"加载爬虫: {filename}", "info")
            except Exception as e:
                if not silent:
                    log.print_log(f"加载爬虫失败 {filename}: {e}", "error")

    async def run_spider(self, spider_name: str, limit: int = 10) -> Dict:
        """运行单个爬虫"""
        if spider_name not in self.spiders:
            return {"success": False, "message": f"爬虫 {spider_name} 不存在"}

        spider_info = self.spiders[spider_name]
        spider_class = spider_info["class"]

        try:
            spider = spider_class()
            log.print_log(f"开始爬取: {spider_name}", "info")

            # 根据不同爬虫类型传递正确参数
            news_list = []
            if spider_name == "pengpai":
                # 澎湃新闻需要dict with code and classify
                news_list = await spider.get_news_list({"code": "25462", "classify": "1"})
            elif spider_name == "wangyi":
                # 网易新闻需要dict with code (URL) and classify
                news_list = await spider.get_news_list({
                    "code": "https://news.163.com/special/cm_yaowen20200213/?callback=data_callback",
                    "classify": "16"
                })
            elif spider_name == "souhu":
                # 搜狐新闻需要dict with code (like "438647_15") and classify
                news_list = await spider.get_news_list({"code": "438647_15", "classify": "16"})
            elif spider_name == "tengxunxinwen":
                # 腾讯新闻需要dict with code and classify
                news_list = await spider.get_news_list({"code": "news_news_finance", "classify": "2"})
            elif spider_name == "xinlang":
                # 新浪国际需要URL
                news_list = await spider.get_news_list("https://news.sina.com.cn/world/")
            elif spider_name == "zhongguoribao":
                # 中国日报需要dict with code (URL) and classify
                news_list = await spider.get_news_list({
                    "code": "https://china.chinadaily.com.cn/5bd5639ca3101a87ca8ff636",
                    "classify": "1"
                })
            elif spider_name == "hellogithub":
                # HelloGithub GitHubTrending爬虫
                news_list = await spider.get_hot_items(page=1, category="all")
            elif spider_name == "aipapers":
                # AI论文工具爬虫
                news_list = await spider.get_news_list({"code": "huggingface"})
                # 处理AIPapers返回的数据，标准化URL字段
                for item in news_list:
                    if "url" in item and "article_url" not in item:
                        item["article_url"] = item["url"]
            elif spider_name in ["zaobao", "nytimes", "wsj", "bbc", "xinhua", "voa", "8world"]:
                # 国际新闻爬虫 - 无需特殊参数
                news_list = await spider.get_news_list()
                # 标准化URL字段
                for item in news_list:
                    if "url" in item and "article_url" not in item:
                        item["article_url"] = item["url"]
            elif spider_name in ["wangyi_domestic", "wangyi_fujian", "wangyi_world", "wangyi_tech", "wangyi_money", "wangyi_war"]:
                # 网易新闻分类爬虫 - 无需特殊参数
                news_list = await spider.get_news_list()
                # 标准化URL字段
                for item in news_list:
                    if "url" in item and "article_url" not in item:
                        item["article_url"] = item["url"]
            else:
                # 默认调用
                news_list = await spider.get_news_list()
                
            log.print_log(f"{spider_name} 获取到 {len(news_list)} 条列表", "info")

            saved_count = 0
            for i, item in enumerate(news_list[:limit]):
                try:
                    # 获取详情
                    article = await spider.get_news_info(item, spider_info["category"])
                    if article:
                        # 标准化URL字段 - AIPapers使用url而非article_url
                        if "url" in article and "article_url" not in article:
                            article["article_url"] = article["url"]
                        # 检查URL字段
                        url = article.get('article_url') or article.get('url', '')
                        log.print_log(f"处理文章: {article.get('title', '无标题')[:30]}... URL: {url[:50]}", "debug")
                        
                        # 检测并使用大模型翻译繁体字/英文到简体中文
                        try:
                            title_text = article.get('title', '')
                            content_text = article.get('content', '')
                            check_text = (title_text + " " + content_text)[:500]
                            
                            trad_chars = set("這為與國學發會機後過對當實經網進們點還無體說業動聲從來樣麼將門開關車書報電線華視")
                            is_traditional = bool(set(check_text) & trad_chars)
                            
                            eng_chars = sum(1 for c in check_text if c.isascii() and c.isalpha())
                            is_english = (eng_chars / max(len(check_text), 1)) > 0.4
                            
                            if is_traditional or is_english:
                                log.print_log(f"检测到繁体字或外语，正在使用大模型翻译为简体中文...", "info")
                                from src.ai_write_x.core.llm_client import get_llm_client
                                import json
                                
                                def _translate():
                                    client = get_llm_client()
                                    sys_msg = "你是一流的翻译专家。请将输入的新闻标题和内容翻译为地道流畅的简体中文。必须且仅输出非Markdown包裹的严格JSON格式，格式为: {\"title\": \"标题\", \"content\": \"内容\"}"
                                    usr_msg = f"Title: {title_text}\n\nContent: {content_text}"
                                    return client.chat(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": usr_msg}], temperature=0.2)
                                
                                response_text = await asyncio.to_thread(_translate)
                                
                                import re
                                json_match = re.search(r'\{[\s\S]*\}', response_text)
                                if json_match:
                                    translated_data = json.loads(json_match.group(0))
                                    if "title" in translated_data and "content" in translated_data:
                                        article['title'] = translated_data['title']
                                        article['content'] = translated_data['content']
                                        log.print_log(f"成功将文章翻译为简体中文", "success")
                        except Exception as e:
                            log.print_log(f"文章翻译为简体中文时出错: {e}", "warn")
                        
                        # 视觉解析已移动到用户真正选用该文章时才执行 (generate.py)
                            
                        # 保存到 JSON 文件
                        article['spider'] = spider_name
                        if 'source' not in article or not article['source']:
                            article['source'] = spider_info.get("name", spider_name)
                            
                        if spider_data_manager.save_article(article):
                            saved_count += 1
                        else:
                            log.print_log(f"文章已存在或保存失败: {url[:30]}", "debug")
                    else:
                        # 保存失败记录
                        url = item.get('article_url') or item.get('url', '')
                        spider_data_manager.add_failed(url, "获取文章详情失败", spider_name)
                        log.print_log(f"文章详情获取失败: {url[:30]}", "warn")
                except Exception as e:
                    # 保存失败记录
                    url = item.get('article_url') or item.get('url', '')
                    spider_data_manager.add_failed(url, str(e), spider_name)
                    log.print_log(f"处理文章失败: {e}", "error")

            log.print_log(f"{spider_name} 爬取完成，保存 {saved_count} 篇", "success")
            return {"success": True, "saved": saved_count, "total": len(news_list[:limit])}

        except Exception as e:
            log.print_log(f"爬虫 {spider_name} 运行失败: {e}", "error")
            return {"success": False, "message": str(e)}

    async def run_all_spiders(self, limit: int = 10) -> Dict:
        """运行所有爬虫"""
        results = []
        for spider_name in self.spiders:
            if self.spiders[spider_name]["enabled"]:
                result = await self.run_spider(spider_name, limit)
                results.append({
                    "spider": spider_name,
                    **result
                })
        
        total_saved = sum(r.get("saved", 0) for r in results)
        save_path = spider_data_manager.get_save_path()
        
        return {
            "success": True,
            "results": results,
            "total_saved": total_saved,
            "save_path": save_path,
            "total_count": spider_data_manager.get_total_count()
        }

    def get_spider_list(self) -> List[Dict]:
        """获取爬虫列表"""
        return [
            {
                "name": name,
                "display_name": info["name"],
                "category": info["category"],
                "enabled": info["enabled"]
            }
            for name, info in self.spiders.items()
        ]

    def get_articles(self, limit: int = 100, source: str = None, category: str = None) -> List[Dict]:
        """获取爬取的文章"""
        return spider_data_manager.get_articles(limit, source, category)

    def get_stats(self) -> Dict:
        """获取爬虫统计"""
        articles = spider_data_manager.get_articles(limit=10000)
        return {
            "total": len(articles),
            "sources": spider_data_manager.get_sources(),
            "categories": spider_data_manager.get_categories(),
            "spiders": self.get_spider_list()
        }

    def run_in_background(self, limit: int = 10):
        """在后台线程中运行所有爬虫"""
        if task_status.running:
            return {"success": False, "message": "爬虫正在运行中"}
        
        def run_task():
            asyncio.run(self._run_all_spiders_async(limit))
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        return {"success": True, "message": "爬虫已在后台启动"}

    async def _run_all_spiders_async(self, limit: int = 10):
        """异步运行所有爬虫"""
        global task_status
        task_status.reset()
        task_status.running = True
        task_status.total_spiders = len([s for s in self.spiders.values() if s["enabled"]])
        task_status.add_log("开始运行所有爬虫...", "info")
        
        results = []
        for spider_name in self.spiders:
            if self.spiders[spider_name]["enabled"]:
                task_status.current_spider = spider_name
                task_status.add_log(f"正在运行: {spider_name}...", "info")
                
                result = await self.run_spider(spider_name, limit)
                results.append({"spider": spider_name, **result})
                
                task_status.completed_spiders += 1
                task_status.total_saved += result.get("saved", 0)
                task_status.progress = int(task_status.completed_spiders / task_status.total_spiders * 100)
                task_status.add_log(f"{spider_name} 完成: 保存 {result.get('saved', 0)} 篇", "success")
        
        task_status.results = results
        task_status.running = False
        task_status.progress = 100
        task_status.add_log(f"全部完成! 共保存 {task_status.total_saved} 篇文章", "success")


def get_task_status() -> Dict:
    """获取任务状态"""
    save_path = spider_data_manager.get_save_path()
    total_count = spider_data_manager.get_total_count()
    
    return {
        "running": task_status.running,
        "current_spider": task_status.current_spider,
        "progress": task_status.progress,
        "total_spiders": task_status.total_spiders,
        "completed_spiders": task_status.completed_spiders,
        "total_saved": task_status.total_saved,
        "save_path": save_path,
        "total_count": total_count,
        "logs": task_status.logs[-20:]  # 返回最近20条日志
    }


# 全局实例
spider_runner = SpiderRunner()
