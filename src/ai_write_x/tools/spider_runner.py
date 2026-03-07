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

# 并发配置 - V17 超大规模抓取优化 (千兆带宽建议值)
# 根据生成需求动态调整抓取策略:
# - 生成1篇 → 抓取100篇候选
# - 生成5篇 → 抓取150篇候选  
# - 生成10篇 → 抓取200篇候选
MAX_CONCURRENT_SPIDERS = 16  # 同时运行的爬虫数量 (翻倍)
MAX_CONCURRENT_ARTICLES = 30  # 每个爬虫并发获取文章数 (翻倍)
MAX_CONCURRENT_REQUESTS = 100  # 全局最大并发请求数 (翻倍)

# 动态抓取策略配置
DYNAMIC_FETCH_CONFIG = {
    1: {"target": 100, "spider_limit": 50},    # 生成1篇,每个爬虫抓50条
    5: {"target": 150, "spider_limit": 40},    # 生成5篇,每个爬虫抓40条
    10: {"target": 200, "spider_limit": 35},   # 生成10篇,每个爬虫抓35条
}

# 全局信号量控制并发
_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


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

    def __init__(self, sync_load: bool = False):
        self.spiders: Dict = {}
        self.running = False
        self._loading_done = threading.Event()
        
        # V18 Fix: 支持同步加载，避免后台线程加载延迟问题
        if sync_load:
            self._load_spiders(silent=False)
        else:
            # V13.0 Optimization: 将爬虫模块加载移至后台线程，防止阻塞 Web 服务器启动
            threading.Thread(target=self._load_spiders_with_event, daemon=True).start()
    
    def _load_spiders_with_event(self):
        """加载爬虫并设置完成事件"""
        try:
            self._load_spiders(silent=True)
        finally:
            self._loading_done.set()
    
    def wait_for_loading(self, timeout: float = 10.0) -> bool:
        """等待爬虫加载完成"""
        if self._loading_done.is_set():
            return True
        return self._loading_done.wait(timeout)
    
    def calculate_fetch_limit(self, article_count: int = 1) -> int:
        """
        V17: 根据文章生成数量计算需要抓取的新闻数量
        
        策略:
        - 生成1篇 → 抓取100篇候选 (10:1比例)
        - 生成5篇 → 抓取150篇候选 (30:1比例)  
        - 生成10篇 → 抓取200篇候选 (20:1比例)
        - 生成N篇 → 动态计算 (最少100,最多300)
        """
        if article_count <= 1:
            return 100
        elif article_count <= 5:
            return 150
        elif article_count <= 10:
            return 200
        else:
            # 超过10篇,每多1篇增加10个候选,上限300
            return min(200 + (article_count - 10) * 10, 300)
    
    def calculate_spider_limit(self, article_count: int = 1, spider_count: int = 1) -> int:
        """
        V17: 计算每个爬虫应该抓取的数量
        """
        total_target = self.calculate_fetch_limit(article_count)
        # 每个爬虫至少抓20条,确保有足够候选
        per_spider = max(20, total_target // max(1, spider_count))
        return per_spider

    def _load_spiders(self, silent=True):
        """加载爬虫模块"""
        # V16.0 Fix: 改进爬虫加载逻辑，增加错误追踪
        import os
        
        if not silent:
            log.print_log(f"[SpiderRunner] 开始加载爬虫，目录: {SPIDER_DIR}", "info")
        
        # 验证爬虫目录存在
        if not os.path.exists(SPIDER_DIR):
            log.print_log(f"[SpiderRunner] 爬虫目录不存在: {SPIDER_DIR}", "error")
            return
        
        # V18: 终极扩展，打造全网最强抓取能力
        spider_files = [
            # ========== V18新增：多平台热榜 ==========
            ("multimedia_hot", "MultiMediaHot", "热榜", "多平台热榜"),
            
            # ========== V18新增：RSS聚合 (100+源) ==========
            ("rss_aggregator", "RSSAggregator", "综合", "RSS新闻聚合"),
            
            # ========== V17新增：全网热榜聚合 ==========
            ("hotrank_api", "HotRankAggregator", "热榜", "全网热榜聚合"),
            ("google_news", "GoogleNewsRSS", "国际", "Google News"),
            ("newsapi_org", "NewsAPIOrg", "国际", "NewsAPI.org"),
            
            # ========== V17新增：国际权威媒体 ==========
            ("international_media", "CNN", "国际", "CNN"),
            ("international_media", "TheGuardian", "国际", "The Guardian"),
            ("international_media", "FinancialTimes", "财经", "Financial Times"),
            ("international_media", "AlJazeera", "国际", "Al Jazeera"),
            ("international_media", "ArsTechnica", "科技", "Ars Technica"),
            
            # ========== 原有爬虫 ==========
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
            # 热点排行
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

        loaded_count = 0
        failed_count = 0
        
        for filename, class_name, category, source in spider_files:
            spider_file = SPIDER_DIR / f"{filename}.py"
            
            # V16.0 Fix: 检查文件是否存在
            if not os.path.exists(spider_file):
                if not silent:
                    log.print_log(f"[SpiderRunner] 爬虫文件不存在: {spider_file}", "warning")
                failed_count += 1
                continue
            
            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(
                    filename, spider_file
                )
                if spec is None or spec.loader is None:
                    if not silent:
                        log.print_log(f"[SpiderRunner] 无法创建模块规格: {filename}", "error")
                    failed_count += 1
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 检查类是否存在
                if not hasattr(module, class_name):
                    if not silent:
                        log.print_log(f"[SpiderRunner] 类不存在: {class_name} in {filename}", "error")
                    failed_count += 1
                    continue
                
                spider_class = getattr(module, class_name)
                self.spiders[filename] = {
                    "name": class_name,
                    "class": spider_class,
                    "category": category,
                    "source": source,
                    "enabled": True
                }
                loaded_count += 1
                if not silent:
                    log.print_log(f"[SpiderRunner] 加载爬虫: {filename}", "info")
            except Exception as e:
                failed_count += 1
                if not silent:
                    log.print_log(f"[SpiderRunner] 加载爬虫失败 {filename}: {e}", "error")
        
        # V16.0 Fix: 记录加载统计
        if not silent:
            log.print_log(
                f"[SpiderRunner] 爬虫加载完成: {loaded_count} 成功, {failed_count} 失败, "
                f"总计 {len(self.spiders)} 个爬虫可用",
                "success" if loaded_count > 0 else "warning"
            )

    async def run_spider(self, spider_name: str, limit: int = 10) -> Dict:
        """运行单个爬虫"""
        # V18 Fix: 等待爬虫加载完成
        if not self.spiders:
            log.print_log("[SpiderRunner] 等待爬虫加载完成...", "info")
            self.wait_for_loading(timeout=10.0)
        
        if spider_name not in self.spiders:
            log.print_log(f"[SpiderRunner] 爬虫 {spider_name} 不存在，可用爬虫: {list(self.spiders.keys())}", "warning")
            return {"success": False, "message": f"爬虫 {spider_name} 不存在"}

        spider_info = self.spiders[spider_name]
        spider_class = spider_info["class"]

        try:
            spider = spider_class()
            log.print_log(f"开始爬取: {spider_name}", "info")

            # V18: 根据不同爬虫类型传递正确参数
            news_list = []
            
            # ===== V18新增爬虫 =====
            if spider_name == "multimedia_hot":
                # 多平台热榜 (B站、贴吧、虎扑等)
                news_list = await spider.get_news_list()
            elif spider_name == "rss_aggregator":
                # RSS新闻聚合 (100+源)
                news_list = await spider.get_news_list()
            
            # ===== V17新增爬虫 =====
            elif spider_name == "hotrank_api":
                # 全网热榜聚合
                news_list = await spider.get_news_list()
            elif spider_name == "google_news":
                # Google News RSS
                news_list = await spider.get_news_list()
            elif spider_name == "newsapi_org":
                # NewsAPI.org
                news_list = await spider.get_news_list()
            elif spider_name in ["cnn", "guardian", "ft", "aljazeera", "arstechnica"]:
                # 国际媒体爬虫
                news_list = await spider.get_news_list()
            
            # ===== 原有爬虫 =====
            elif spider_name == "pengpai":
                news_list = await spider.get_news_list({"code": "25462", "classify": "1"})
            elif spider_name == "wangyi":
                news_list = await spider.get_news_list({
                    "code": "https://news.163.com/special/cm_yaowen20200213/?callback=data_callback",
                    "classify": "16"
                })
            elif spider_name == "souhu":
                news_list = await spider.get_news_list({"code": "438647_15", "classify": "16"})
            elif spider_name == "tengxunxinwen":
                news_list = await spider.get_news_list({"code": "news_news_finance", "classify": "2"})
            elif spider_name == "xinlang":
                news_list = await spider.get_news_list("https://news.sina.com.cn/world/")
            elif spider_name == "zhongguoribao":
                news_list = await spider.get_news_list({
                    "code": "https://china.chinadaily.com.cn/5bd5639ca3101a87ca8ff636",
                    "classify": "1"
                })
            elif spider_name == "hellogithub":
                news_list = await spider.get_hot_items(page=1, category="all")
            elif spider_name == "aipapers":
                news_list = await spider.get_news_list({"code": "huggingface"})
            elif spider_name in ["zaobao", "nytimes", "wsj", "bbc", "xinhua", "voa", "8world"]:
                news_list = await spider.get_news_list()
            elif spider_name in ["wangyi_domestic", "wangyi_fujian", "wangyi_world", "wangyi_tech", "wangyi_money", "wangyi_war"]:
                news_list = await spider.get_news_list()
            else:
                news_list = await spider.get_news_list()
            
            # 标准化URL字段
            for item in news_list:
                if isinstance(item, dict):
                    if "url" in item and "article_url" not in item:
                        item["article_url"] = item["url"]
                
            log.print_log(f"{spider_name} 获取到 {len(news_list)} 条列表", "info")

            # 使用信号量控制并发数
            article_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ARTICLES)
            
            async def process_article(item: Dict, idx: int) -> bool:
                """并发处理单篇文章"""
                async with article_semaphore:
                    try:
                        # 获取详情
                        article = await spider.get_news_info(item, spider_info["category"])
                        if not article:
                            url = item.get('article_url') or item.get('url', '')
                            spider_data_manager.add_failed(url, "获取文章详情失败", spider_name)
                            return False
                        
                        # 标准化URL字段
                        if "url" in article and "article_url" not in article:
                            article["article_url"] = article["url"]
                        
                        url = article.get('article_url') or article.get('url', '')
                        log.print_log(f"[{idx+1}/{limit}] 处理: {article.get('title', '无标题')[:25]}...", "debug")
                        
                        # V18: 移除每篇文章的自动翻译，改为只保存原文
                        # 翻译只针对最终选择的文章进行，提高性能
                        
                        # 保存文章
                        article['spider'] = spider_name
                        if 'source' not in article or not article['source']:
                            article['source'] = spider_info.get("name", spider_name)
                        
                        # V18 Fix: 将 article_info 映射为 content (spider_data_manager 期望的字段)
                        if 'article_info' in article and 'content' not in article:
                            article['content'] = article['article_info']
                        
                        # 确保必要字段存在
                        if 'content' not in article or not article['content']:
                            log.print_log(f"文章缺少内容字段，跳过保存: {article.get('title', '无标题')}", "warning")
                            return False
                        
                        return spider_data_manager.save_article(article)
                        
                    except Exception as e:
                        url = item.get('article_url') or item.get('url', '')
                        spider_data_manager.add_failed(url, str(e), spider_name)
                        log.print_log(f"处理失败: {e}", "error")
                        return False
            
            # 并发处理所有文章
            tasks = [process_article(item, i) for i, item in enumerate(news_list[:limit])]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            saved_count = sum(1 for r in results if r is True)
            failed_count = sum(1 for r in results if r is False or isinstance(r, Exception))
            
            log.print_log(f"{spider_name} 完成: {saved_count} 成功, {failed_count} 失败, 共 {len(tasks)} 篇", "success")
            return {"success": True, "saved": saved_count, "total": len(news_list[:limit]), "failed": failed_count}

        except Exception as e:
            log.print_log(f"爬虫 {spider_name} 运行失败: {e}", "error")
            return {"success": False, "message": str(e)}

    async def run_all_spiders(self, limit: int = 10, article_count: int = 1) -> Dict:
        """
        并发运行所有爬虫
        
        Args:
            limit: 每个爬虫的基础限制(已废弃,使用动态计算)
            article_count: 用户需要生成的文章数量,用于动态计算抓取量
        """
        enabled_spiders = [name for name, info in self.spiders.items() if info["enabled"]]
        
        # V17: 动态计算抓取策略
        total_target = self.calculate_fetch_limit(article_count)
        per_spider_limit = self.calculate_spider_limit(article_count, len(enabled_spiders))
        
        log.print_log(f"[V17大规模抓取] 目标: {total_target}篇候选 | 爬虫: {len(enabled_spiders)}个 | 每爬虫: {per_spider_limit}篇", "info")
        log.print_log(f"开始并发运行 {len(enabled_spiders)} 个爬虫 (最大并发: {MAX_CONCURRENT_SPIDERS})", "info")
        
        # 使用信号量控制爬虫并发数
        spider_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SPIDERS)
        
        async def run_with_limit(spider_name: str) -> Dict:
            async with spider_semaphore:
                result = await self.run_spider(spider_name, per_spider_limit)
                return {"spider": spider_name, **result}
        
        # 并发执行所有爬虫
        tasks = [run_with_limit(name) for name in enabled_spiders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                log.print_log(f"爬虫异常: {r}", "error")
            else:
                valid_results.append(r)
        
        total_saved = sum(r.get("saved", 0) for r in valid_results)
        total_failed = sum(r.get("failed", 0) for r in valid_results)
        save_path = spider_data_manager.get_save_path()
        
        log.print_log(f"[V17大规模抓取] 完成: {total_saved} 成功, {total_failed} 失败 | 目标达成率: {total_saved/max(1,total_target)*100:.1f}%", "success")
        
        return {
            "success": True,
            "results": valid_results,
            "total_saved": total_saved,
            "total_failed": total_failed,
            "target": total_target,
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

    def run_in_background(self, limit: int = 10, article_count: int = 1):
        """在后台线程中运行所有爬虫"""
        if task_status.running:
            return {"success": False, "message": "爬虫正在运行中"}
        
        def run_task():
            asyncio.run(self._run_all_spiders_async(limit, article_count))
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        return {"success": True, "message": "爬虫已在后台启动"}

    async def _run_all_spiders_async(self, limit: int = 10, article_count: int = 1):
        """异步并发运行所有爬虫"""
        global task_status
        task_status.reset()
        task_status.running = True
        
        enabled_spiders = [name for name, info in self.spiders.items() if info["enabled"]]
        task_status.total_spiders = len(enabled_spiders)
        
        # V17: 动态计算抓取策略
        total_target = self.calculate_fetch_limit(article_count)
        per_spider_limit = self.calculate_spider_limit(article_count, len(enabled_spiders))
        
        task_status.add_log(f"[V17大规模抓取] 目标: {total_target}篇 | 爬虫: {len(enabled_spiders)}个 | 每爬虫: {per_spider_limit}篇", "info")
        task_status.add_log(f"开始并发运行 {len(enabled_spiders)} 个爬虫...", "info")
        
        # 使用信号量控制爬虫并发数
        spider_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SPIDERS)
        completed = 0
        
        async def run_spider_with_status(spider_name: str) -> Dict:
            nonlocal completed
            async with spider_semaphore:
                task_status.current_spider = spider_name
                task_status.add_log(f"[{spider_name}] 启动...", "info")
                
                result = await self.run_spider(spider_name, per_spider_limit)
                
                completed += 1
                task_status.completed_spiders = completed
                task_status.total_saved += result.get("saved", 0)
                task_status.progress = int(completed / task_status.total_spiders * 100)
                task_status.add_log(f"[{spider_name}] 完成: {result.get('saved', 0)} 篇", "success")
                
                return {"spider": spider_name, **result}
        
        # 并发执行所有爬虫
        tasks = [run_spider_with_status(name) for name in enabled_spiders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                task_status.add_log(f"爬虫异常: {r}", "error")
            else:
                valid_results.append(r)
        
        task_status.results = valid_results
        task_status.running = False
        task_status.progress = 100
        actual_saved = task_status.total_saved
        task_status.add_log(f"[V17大规模抓取] 全部完成! 共保存 {actual_saved}/{total_target} 篇文章 | 达成率: {actual_saved/max(1,total_target)*100:.1f}%", "success")


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
