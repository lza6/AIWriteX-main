import requests
import random
import time
from typing import Any, Optional, List, Dict
from bs4 import BeautifulSoup

from src.ai_write_x.utils import log

# 平台名称映射
PLATFORMS = [
    {"name": "微博", "zhiwei_id": "weibo", "tophub_id": "s.weibo.com"},
    {"name": "抖音", "zhiwei_id": "douyin", "tophub_id": "douyin.com"},
    {"name": "哔哩哔哩", "zhiwei_id": "bilibili", "tophub_id": "bilibili.com"},
    {"name": "今日头条", "zhiwei_id": "toutiao", "tophub_id": "toutiao.com"},
    {"name": "百度热点", "zhiwei_id": "baidu", "tophub_id": "baidu.com"},
    {"name": "小红书", "zhiwei_id": "little-red-book", "tophub_id": None},
    {"name": "快手", "zhiwei_id": "kuaishou", "tophub_id": None},
    {"name": "虎扑", "zhiwei_id": None, "tophub_id": "hupu.com"},
    {"name": "豆瓣小组", "zhiwei_id": None, "tophub_id": "douban.com"},
    {"name": "澎湃新闻", "zhiwei_id": None, "tophub_id": "thepaper.cn"},
    {"name": "知乎热榜", "zhiwei_id": "zhihu", "tophub_id": "zhihu.com"},
]

# 知微数据支持的平台
ZHIWEI_PLATFORMS = [p["zhiwei_id"] for p in PLATFORMS if p["zhiwei_id"]]

# tophub 支持的平台
TOPHUB_PLATFORMS = [p["tophub_id"] for p in PLATFORMS if p["tophub_id"]]


def get_zhiwei_hotnews(platform: str) -> Optional[List[Dict]]:
    """
    获取知微数据的热点数据
    参数 platform: 平台标识 (weibo, douyin, bilibili, toutiao, baidu, little-red-book, kuaishou, zhihu)
    返回格式: 列表数据，每个元素为热点条目字典，仅包含 name, rank, lastCount, url
    """
    api_url = f"https://trends.zhiweidata.com/hotSearchTrend/search/longTimeInListSearch?type={platform}&sortType=realTime"  # noqa 501
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa 501
            "Referer": "https://trends.zhiweidata.com/",
        }
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("state") and isinstance(data.get("data"), list):
            return [
                {
                    "name": item.get("name", ""),
                    "rank": item.get("rank", 0),
                    "lastCount": item.get("lastCount", 0),
                    "url": item.get("url", ""),
                }
                for item in data["data"]
            ]
        return None
    except Exception as e:  # noqa 841
        return None


def get_tophub_hotnews(platform: str, cnt: int = 10) -> Optional[List[Dict]]:
    """
    获取 tophub.today 的热点数据
    参数 platform: 平台名称（中文，如“微博”）
    参数 tophub_id: tophub.today 的平台标识（如 s.weibo.com, zhihu.com）
    参数 cnt: 返回的新闻数量
    返回格式: 列表数据，每个元素为热点条目字典，包含 name, rank, lastCount
    """
    api_url = "https://tophub.today/"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa 501
        }
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        platform_divs = soup.find_all("div", class_="cc-cd")

        for div in platform_divs:
            platform_span = div.find("div", class_="cc-cd-lb").find("span")  # type: ignore
            if platform_span and platform_span.text.strip() == platform:  # type: ignore
                news_items = div.find_all("div", class_="cc-cd-cb-ll")[:cnt]  # type: ignore
                hotnews = []
                for item in news_items:
                    rank = item.find("span", class_="s").text.strip()  # type: ignore
                    title = item.find("span", class_="t").text.strip()  # type: ignore
                    engagement = item.find("span", class_="e")  # type: ignore
                    last_count = engagement.text.strip() if engagement else "0"
                    hotnews.append(
                        {
                            "name": title,
                            "rank": int(rank),
                            "lastCount": last_count,
                            "url": item.find("a")["href"] if item.find("a") else "",  # type: ignore
                        }
                    )
                return hotnews
        return None
    except Exception as e:  # noqa 841
        return None


def get_vvhan_hotnews() -> Optional[List[Dict]]:
    """
    获取 vvhan 的热点数据（作为备用）
    返回格式: [{"name": platform_name, "data": [...]}, ...]
    """
    api_url = "https://api.vvhan.com/api/hotlist/all"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("success") and isinstance(data.get("data"), list):
            return data["data"]
        return None
    except Exception as e:  # noqa 841
        return None


def get_platform_news(platform: str, cnt: int = 10, exclude_topics: List[str] = None) -> List[str]:
    """
    获取指定平台的新闻标题，深度支持到 200 条
    """
    if exclude_topics is None:
        exclude_topics = []
    
    # 查找平台对应的标识
    platform_info = next((p for p in PLATFORMS if p["name"] == platform), None)
    if not platform_info:
        return []

    topics = []
    # 1. 优先尝试知微数据
    if platform_info["zhiwei_id"] in ZHIWEI_PLATFORMS:
        hotnews = get_zhiwei_hotnews(platform_info["zhiwei_id"])
        if hotnews:
            # 增加抓取深度到 200
            topics = [item.get("name", "") for item in hotnews[:200] if item.get("name")]

    # 2. 回退到 tophub.today
    if not topics and platform_info["tophub_id"] in TOPHUB_PLATFORMS:
        hotnews = get_tophub_hotnews(platform, 200)
        if hotnews:
            topics = [item.get("name", "") for item in hotnews[:200] if item.get("name")]

    # 3. 回退到 vvhan API
    if not topics:
        hotnews = get_vvhan_hotnews()
        if hotnews:
            platform_data = next((pf["data"] for pf in hotnews if pf["name"] == platform), [])
            topics = [item["title"] for item in platform_data[:200]]

    # 过滤掉已存在的话题
    filtered_topics = [t for t in topics if t not in exclude_topics]
    return filtered_topics


def get_authority_topics(limit: int = 50, exclude_topics: List[str] = None) -> List[str]:
    """
    从高权重源（BBC, NYTimes, WSJ等）抓取优质话题
    """
    if exclude_topics is None:
        exclude_topics = []
        
    try:
        from src.ai_write_x.tools.spider_runner import spider_runner
        import asyncio
        
        authority_spiders = ["bbc", "nytimes", "wsj", "zaobao", "xinhua"]
        all_authority_news = []
        
        # 为了避免异步嵌套复杂性，优先从 spider_data_manager 获取最近抓取的
        from src.ai_write_x.tools.spider_manager import spider_data_manager
        
        for s in authority_spiders:
            # 获取最近抓取的文章标题作为话题
            articles = spider_data_manager.get_articles(limit=limit, source=spider_runner.spiders.get(s, {}).get("source", s))
            all_authority_news.extend([a['title'] for a in articles])

        if not all_authority_news:
             # 如果数据库没有，尝试实时跑一下（仅在必要时）
             log.print_log("数据库中无权威源数据，尝试实时采集...", "info")
             try:
                 # 同步环境下运行异步
                 async def run_sync():
                     tasks = [spider_runner.run_spider(s, limit=10) for s in authority_spiders]
                     await asyncio.gather(*tasks)
                 asyncio.run(run_sync())
                 
                 for s in authority_spiders:
                    articles = spider_data_manager.get_articles(limit=limit, source=spider_runner.spiders.get(s, {}).get("source", s))
                    all_authority_news.extend([a['title'] for a in articles])
             except:
                 pass

        filtered = [t for t in all_authority_news if t not in exclude_topics]
        # 去重
        seen = set()
        unique_filtered = [x for x in filtered if not (x in seen or seen.add(x))]
        return unique_filtered[:limit]
    except Exception as e:
        log.print_log(f"获取权威源话题失败: {e}", "warning")
        return []


def select_platform_topic(platform: Any, cnt: int = 10, exclude_topics: List[str] = None, authority_priority: bool = False) -> str:
    """
    获取话题，支持权威源优先
    """
    topics = []
    if authority_priority:
        topics = get_authority_topics(limit=cnt, exclude_topics=exclude_topics)
        if topics:
            log.print_log(f"已从中外权威媒体（BBC/新华社等）选取高质量话题", "success")
    
    if not topics:
        topics = get_platform_news(platform, cnt, exclude_topics)
        
    if not topics:
        if exclude_topics:
            topics = get_platform_news(platform, cnt)
        if not topics:
            topics = ["历史上的今天"]
            log.print_log(f"所有源均不可用，将使用默认话题。")

    # 加权随机选择
    weights = [1 / (i + 1) ** 1.5 for i in range(len(topics))]
    selected_topic = random.choices(topics, weights=weights, k=1)[0]
    selected_topic = selected_topic.replace("|", "——")

    return selected_topic
