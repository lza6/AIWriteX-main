import asyncio
import json
import time
from urllib.parse import quote

from lxml import etree

from base import BaseSpider
from logger_utils import logger

pengpai_failed_urls = set()


class PengPai(BaseSpider):
    source_name = "澎湃新闻"
    category = "新闻"

    category_list = [
        {"name": "中国政库", "code": "25462", "classify": "1"},
        {"name": "中南海", "code": "25488", "classify": "1"},
        {"name": "舆论场", "code": "25489", "classify": "3"},
        {"name": "打虎记", "code": "25490", "classify": "1"},
        {"name": "人事风向", "code": "25423", "classify": "1"},
        {"name": "法治中国", "code": "25426", "classify": "3"},
        {"name": "一号专案", "code": "25424", "classify": "1"},
        {"name": "港台来信", "code": "25463", "classify": "7"},
        {"name": "长三角政商", "code": "25491", "classify": "2"},
        {"name": "直击现场", "code": "25428", "classify": "3"},
        {"name": "公益湃", "code": "68750", "classify": "3"},
        {"name": "暖闻", "code": "27604", "classify": "3"},
        {"name": "澎湃质量观", "code": "25464", "classify": "3"},
        {"name": "绿政公署", "code": "25425", "classify": "13"},
        {"name": "国防聚焦", "code": "137534", "classify": "8"},
        {"name": "澎湃人物", "code": "25427", "classify": "3"},
        {"name": "画外", "code": "143036", "classify": "6"},
        {"name": "浦江头条", "code": "25422", "classify": "3"},
        {"name": "上海大调研", "code": "127425", "classify": "3"},
        {"name": "教育家", "code": "25487", "classify": "11"},
        {"name": "全景现场", "code": "25634", "classify": "3"},
        {"name": "美数课", "code": "25635", "classify": "11"},
        {"name": "对齐Lab", "code": "138033", "classify": "4"},
        {"name": "快看", "code": "25600", "classify": "6"},
        {"name": "全球速报", "code": "25429", "classify": "7"},
        {"name": "澎湃世界观", "code": "122903", "classify": "7"},
        {"name": "澎湃明查", "code": "122904", "classify": "3"},
        {"name": "澎湃防务", "code": "25430", "classify": "8"},
        {"name": "外交学人", "code": "25481", "classify": "7"},
        {"name": "唐人街", "code": "25678", "classify": "7"},
        {"name": "大国外交", "code": "122905", "classify": "7"},
        {"name": "World全知道", "code": "122906", "classify": "7"},
        {"name": "寰宇开放麦", "code": "122907", "classify": "7"},
        {"name": "10%公司", "code": "25434", "classify": "2"},
        {"name": "能见度", "code": "25436", "classify": "13"},
        {"name": "地产界", "code": "25433", "classify": "13"},
        {"name": "财经上下游", "code": "25438", "classify": "2"},
        {"name": "区域经纬", "code": "124129", "classify": "2"},
        {"name": "金改实验室", "code": "25435", "classify": "2"},
        {"name": "牛市点线面", "code": "25437", "classify": "2"},
        {"name": "IPO最前线", "code": "119963", "classify": "2"},
        {"name": "澎湃商学院", "code": "25485", "classify": "2"},
        {"name": "自贸区连线", "code": "25432", "classify": "2"},
        {"name": "新引擎", "code": "145902", "classify": "2"},
        {"name": "进博会在线", "code": "37978", "classify": "2"},
        {"name": "科学湃", "code": "27234", "classify": "4"},
        {"name": "生命科学", "code": "119445", "classify": "4"},
        {"name": "未来2%", "code": "119447", "classify": "16"},
        {"name": "元宇宙观察", "code": "119446", "classify": "4"},
        {"name": "科创101", "code": "119448", "classify": "4"},
        {"name": "科学城邦", "code": "119449", "classify": "4"},
        {"name": "澎湃研究所", "code": "25445", "classify": "16"},
        {"name": "全球智库", "code": "25446", "classify": "7"},
        {"name": "城市漫步", "code": "26915", "classify": "10"},
        {"name": "市政厅", "code": "25456", "classify": "3"},
        {"name": "世界会客厅", "code": "104191", "classify": "7"},
        {"name": "社论", "code": "25444", "classify": "9"},
        {"name": "澎湃评论", "code": "27224", "classify": "9"},
        {"name": "思想湃", "code": "26525", "classify": "17"},
        {"name": "上海书评", "code": "26878", "classify": "9"},
        {"name": "思想市场", "code": "25483", "classify": "17"},
        {"name": "私家历史", "code": "25457", "classify": "9"},
        {"name": "上海文艺", "code": "135619", "classify": "9"},
        {"name": "翻书党", "code": "25574", "classify": "9"},
        {"name": "艺术评论", "code": "25455", "classify": "9"},
        {"name": "古代艺术", "code": "26937", "classify": "9"},
        {"name": "文化课", "code": "25450", "classify": "9"},
        {"name": "逝者", "code": "25482", "classify": "9"},
        {"name": "专栏", "code": "25536", "classify": "9"},
        {"name": "异次元", "code": "26506", "classify": "9"},
        {"name": "海平面", "code": "97313", "classify": "9"},
        {"name": "一问三知", "code": "103076", "classify": "9"},
        {"name": "有戏", "code": "25448", "classify": "6"},
        {"name": "文艺范", "code": "26609", "classify": "9"},
        {"name": "身体", "code": "25942", "classify": "12"},
        {"name": "私·奔", "code": "26015", "classify": "5"},
        {"name": "运动家", "code": "25599", "classify": "5"},
        {"name": "非常品", "code": "80623", "classify": "6"},
        {"name": "城势", "code": "26862", "classify": "13"},
        {"name": "生活方式", "code": "25769", "classify": "10"},
        {"name": "澎湃联播", "code": "25990", "classify": "16"},
        {"name": "视界", "code": "26173", "classify": "3"},
        {"name": "亲子学堂", "code": "26202", "classify": "10"},
        {"name": "赢家", "code": "26404", "classify": "5"},
        {"name": "汽车圈", "code": "26490", "classify": "13"},
        {"name": "IP SH", "code": "115327", "classify": "25"},
        {"name": "酒业", "code": "117340", "classify": "2"},
    ]

    headers = {
        "accept": "application/json",
        "accept-language": "zh-CN,zh;q=0.9",
        "client-type": "1",
        "content-type": "application/json",
        "origin": "https://www.thepaper.cn",
        "referer": "https://www.thepaper.cn/",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async def get_news_list(self, category: dict):
        """
        获取澎湃新闻列表
        """
        try:
            timestamp_milliseconds = int(time.time() * 1000)
            json_data = {
                "nodeId": category["code"],
                "excludeContIds": [],
                "pageSize": 20,
                "startTime": timestamp_milliseconds,
                "pageNum": 1,
            }

            response = await self.request(
                method="POST",
                url="https://api.thepaper.cn/contentapi/nodeCont/getByNodeIdPortal",
                headers=self.headers,
                data=json.dumps(json_data),
            )

            response_data = json.loads(response)
            try:
                news_list = response_data["data"]["list"]
            except:
                news_list = []
            result = []
            for item in news_list:
                if item.get("link"):
                    continue
                result.append(
                    {
                        "title": item["name"],
                        "article_url": f"https://www.thepaper.cn/newsDetail_forward_{quote(item['contId'])}",
                        "cover_url": item.get("pic", ""),
                        "date_str": time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(item["pubTimeLong"] / 1000),
                        ),
                        "contId": item["contId"],
                        "category": category["classify"],
                    }
                )

            return result

        except Exception as e:
            logger.error(f"获取澎湃新闻列表失败: {e}")

            return []

    async def get_news_info(self, item, category=None):
        """
        获取澎湃新闻详情
        """
        if item["article_url"] in pengpai_failed_urls:
            logger.warning(f"跳过已失败的url: {item['article_url']}")
            return None
        try:
            content = await self.request(url=item["article_url"])
            content_html = etree.HTML(content)

            img_list = content_html.xpath(
                '//*[@id="__next"]/main/div[4]/div[1]/div[1]/div/div[2]/img/@data-src'
            )

            txt = content_html.xpath(
                '//*[@id="__next"]/main/div[4]/div[1]/div[1]/div/div[2]/p'
            )
            article_info = ""
            for item_ in txt:
                t = item_.xpath(".//text()")
                for i in t:
                    article_info += i
                    article_info += "\n"
            if not article_info:
                logger.error(
                    f"获取澎湃新闻详情失败: article_info 为空 article_url: {item['article_url']}"
                )
                pengpai_failed_urls.add(item["article_url"])
                return None
            if len(article_info) < 50:
                return None
            data = {
                "title": item["title"],
                "article_url": item["article_url"],
                "cover_url": item["cover_url"],
                "date_str": item["date_str"],
                "article_info": article_info,
                "img_list": img_list,
                "category": item["category"],
            }
            return data

        except Exception as e:
            pengpai_failed_urls.add(item["article_url"])
            logger.error(f"获取澎湃新闻详情失败: {e}")
            return None

    async def crawl_and_save(
        self,
        code=None,
        limit=None,
        class_sleep_time=0,
        info_sleep_time=0,
        addition_msg="",
    ) -> int:
        for category in self.category_list:
            await super().crawl_and_save(
                category,
                limit,
                class_sleep_time,
                info_sleep_time,
                f"类别：{category['name']}",
            )
            if class_sleep_time:
                await asyncio.sleep(class_sleep_time)
        return True


if __name__ == "__main__":

    async def crawl_and_save() -> int:
        from database import db_manager

        if db_manager.pool is None:
            await db_manager.create_pool()
            await db_manager.init_tables()
            logger.success("数据库连接池已创建，数据表已初始化")
        it = PengPai()
        r = await it.crawl_and_save()
        return r

    asyncio.run(crawl_and_save())
