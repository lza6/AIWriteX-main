import ast
import asyncio

from lxml import etree
from datetime import datetime, timedelta
import re
import json
from base import BaseSpider
from logger_utils import logger


# Create your tests here.


class SouHu(BaseSpider):
    source_name = "搜狐新闻"
    category = "新闻"
    category_list = [
        {"name": "时政", "code": "438647_15", "classify": "16"},
        {"name": "国际", "code": "1649_13", "classify": "7"},
        {"name": "财经", "code": "54401_15", "classify": "2"},
        {"name": "明星新闻", "code": "55955_15", "classify": "6"},
        {"name": "综艺新闻", "code": "438682_15", "classify": "6"},
        {"name": "影视音乐", "code": "55968_15", "classify": "6"},
        {"name": "网红", "code": "55962_15", "classify": "6"},
        {"name": "幼儿教育", "code": "659_13", "classify": "11"},
        {"name": "中小学", "code": "657_13", "classify": "11"},
        {"name": "高考", "code": "653_13", "classify": "11"},
        {"name": "高校", "code": "656_13", "classify": "11"},
        {"name": "考研考公", "code": "978_13", "classify": "11"},
        {"name": "教资法考", "code": "979_13", "classify": "11"},
        {"name": "留学", "code": "661_13", "classify": "11"},
        {"name": "学习资料", "code": "977_13", "classify": "11"},
        {"name": "时尚", "code": "55103_15", "classify": "10"},
        {"name": "明星", "code": "55105_15", "classify": "10"},
        {"name": "格调生活", "code": "57749_15", "classify": "10"},
        {"name": "美容", "code": "55107_15", "classify": "10"},
        {"name": "奢品", "code": "54954_15", "classify": "10"},
        {"name": "男士", "code": "723_13", "classify": "10"},
        {"name": "生活方式", "code": "1510_13", "classify": "10"},
        {"name": "通讯", "code": "667_13", "classify": "4"},
        {"name": "数码", "code": "672_13", "classify": "4"},
        {"name": "手机", "code": "56306_15", "classify": "4"},
        {"name": "互联网", "code": "666_13", "classify": "16"},
        {"name": "5G", "code": "677_13", "classify": "16"},
        {"name": "智能硬件", "code": "676_13", "classify": "16"},
        {"name": "宇宙发现", "code": "1107_13", "classify": "16"},
        {"name": "世界未解之谜", "code": "53812_15", "classify": "17"},
        {"name": "科学发现", "code": "1108_13", "classify": "4"},
        {"name": "物理帝国", "code": "52796_15", "classify": "4"},
        {"name": "搜狐科学feed流", "code": "52990_15", "classify": "17"},
        {"name": "经济解码", "code": "706_13", "classify": "2"},
        {"name": "股票", "code": "707_13", "classify": "2"},
        {"name": "基金", "code": "1351_13", "classify": "2"},
        {"name": "IPO", "code": "46857_15", "classify": "2"},
        {"name": "新赛道", "code": "52519_15", "classify": "2"},
        {"name": "搜狐酒业", "code": "7176_13", "classify": "2"},
        {"name": "备孕指南", "code": "879_13", "classify": "12"},
        {"name": "怀胎十月", "code": "880_13", "classify": "12"},
        {"name": "生产必备", "code": "881_13", "classify": "3"},
        {"name": "月子", "code": "882_13", "classify": "12"},
        {"name": "新生儿", "code": "883_13", "classify": "12"},
        {"name": "历史", "code": "396_13", "classify": "9"},
        {"name": "国内资讯", "code": "2027_13", "classify": "8"},
        {"name": "国际资讯", "code": "2028_13", "classify": "7"},
        {"name": "风云人物", "code": "2036_13", "classify": "8"},
        {"name": "战争历史", "code": "2037_13", "classify": "9"},
        {"name": "军情纵横", "code": "275_13", "classify": "8"},
        {"name": "网红餐厅", "code": "2085_13", "classify": "10"},
        {"name": "行业聚焦", "code": "2099_13", "classify": "10"},
        {"name": "餐饮界", "code": "2100_13", "classify": "10"},
        {"name": "休闲食品", "code": "474_13", "classify": "10"},
        {"name": "流行餐单", "code": "455_13", "classify": "10"},
        {"name": "读书", "code": "419_13", "classify": "9"},
        {"name": "人物", "code": "420_13", "classify": "9"},
        {"name": "收藏", "code": "423_13", "classify": "9"},
        {"name": "影视", "code": "422_13", "classify": "9"},
        {"name": "艺术", "code": "421_13", "classify": "9"},
        {"name": "运势", "code": "43827_15", "classify": "25"},
        {"name": "情感", "code": "46018_15", "classify": "25"},
        {"name": "性格解读", "code": "53716_15", "classify": "25"},
        {"name": "生肖风水", "code": "53710_15", "classify": "25"},
        {"name": "心理测试", "code": "53709_15", "classify": "25"},
        {"name": "电竞", "code": "57629_15", "classify": "26"},
        {"name": "手游", "code": "56214_15", "classify": "26"},
        {"name": "单机", "code": "56215_15", "classify": "26"},
        {"name": "网游", "code": "56216_15", "classify": "26"},
        {"name": "攻略", "code": "56217_15", "classify": "26"},
        {"name": "赛事追踪", "code": "56211_15", "classify": "26"},
        {"name": "职业选手", "code": "56212_15", "classify": "26"},
        {"name": "赛圈八卦", "code": "56213_15", "classify": "26"},
        {"name": "搞笑feed流", "code": "51219_15", "classify": "17"},
        {"name": "搞笑美女", "code": "51228_15", "classify": "17"},
        {"name": "国漫推荐", "code": "947_13", "classify": "6"},
        {"name": "日漫推荐", "code": "948_13", "classify": "6"},
        {"name": "美漫推荐", "code": "949_13", "classify": "6"},
        {"name": "养宠经验", "code": "303_13", "classify": "10"},
        {"name": "喵星人", "code": "304_13", "classify": "10"},
        {"name": "汪星人", "code": "305_13", "classify": "10"},
    ]

    def parse_relative_time(self, relative_time: str) -> str:
        """
        将类似"xx秒前", "xx分钟前", "xx小时前", "昨天xx:xx", "前天xx:xx", "x天前" 的时间字符串
        转换为标准时间格式 "%Y-%m-%d %H:%M:%S"
        """
        now = datetime.now()

        # 匹配不同的时间格式
        if match := re.match(r"(\d+)秒前", relative_time):
            seconds = int(match.group(1))
            result_time = now - timedelta(seconds=seconds)
        elif match := re.match(r"(\d+)分钟前", relative_time):
            minutes = int(match.group(1))
            result_time = now - timedelta(minutes=minutes)
        elif match := re.match(r"(\d+)小时前", relative_time):
            hours = int(match.group(1))
            result_time = now - timedelta(hours=hours)
        elif match := re.match(r"昨天(\d{2}):(\d{2})", relative_time):
            hour, minute = map(int, match.groups())
            result_time = now - timedelta(days=1)
            result_time = result_time.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        elif match := re.match(r"前天(\d{2}):(\d{2})", relative_time):
            hour, minute = map(int, match.groups())
            result_time = now - timedelta(days=2)
            result_time = result_time.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        elif match := re.match(r"(\d+)天前", relative_time):
            days = int(match.group(1))
            result_time = now - timedelta(days=days)
        else:
            return relative_time  # 如果没有匹配到，则返回原始时间字符串

        # 返回标准时间格式
        return result_time.strftime("%Y-%m-%d %H:%M:%S")

    async def get_news_list(self, category: dict):
        """
        获取搜狐新闻列表
        """
        try:
            productId, productType = category["code"].split("_")
            json_data = {
                "mainContent": {
                    "productType": "13",
                    "productId": "1524",
                    "secureScore": "50",
                    "categoryId": "47",
                },
                "resourceList": [
                    {
                        "tplCompKey": "TPLFeedMul_2_9_feedData",
                        "isServerRender": False,
                        "isSingleAd": False,
                        "configSource": "mp",
                        "content": {
                            "productId": productId,
                            "productType": productType,
                            "size": 20,
                            "pro": "0,1",
                            "feedType": "XTOPIC_LATEST",  # 默认 XTOPIC_SYNTHETICAL  最新 XTOPIC_LATEST
                            "view": "feedMode",
                            "innerTag": "channel",
                            "spm": "smpc.channel_114.block3_77_O0F7zf_1_fd",
                            "page": 1,
                            "requestId": "1732260842796Adk66ZV_1524",
                        },
                    },
                ],
            }

            response = await self.request(
                method="POST",
                url="https://odin.sohu.com/odin/api/blockdata",
                json=json_data,
            )

            response_data = json.loads(response)
            data_list = response_data["data"]["TPLFeedMul_2_9_feedData"]["list"]

            result = []
            for item in data_list:
                if item["icon"] in ["images", "video"]:
                    continue

                date_str = (
                    item["extraInfoList"][1]["text"] if item["extraInfoList"] else ""
                )
                cover = item["cover"][0] if item["cover"] else ""

                result.append(
                    {
                        "title": item["title"],
                        "article_url": f"https://www.sohu.com{item['url']}",
                        "cover_url": (
                            f"https:{cover}"
                            if cover and "https:" not in cover
                            else cover
                        ),
                        "date_str": self.parse_relative_time(date_str),
                        "category": category["classify"],
                    }
                )

            result = sorted(result, key=lambda x: x["date_str"], reverse=True)
            return result

        except Exception as e:
            logger.error(f"获取搜狐新闻列表失败: {e}")
            return []

    async def get_news_info(self, news, category=None):
        """
        获取搜狐新闻详情
        """
        try:
            article_url = news["article_url"]

            content = await self.request(url=article_url)
            content_html = etree.HTML(content)
            try:
                article_element = content_html.xpath('//article[@id="mp-editor"]')[0]
            except:
                return await self.get_qiche_info(news, category, content_html)

            if not news["date_str"]:
                date_str = content_html.xpath('//span[@id="news-time"]/text()')[
                    0
                ].strip()
            else:
                date_str = news["date_str"]

            # 移除 id="backsohucom" 的整个元素
            for backsohu_element in article_element.xpath('.//a[@id="backsohucom"]'):
                backsohu_element.getparent().remove(backsohu_element)

            # 提取文本列表，过滤掉"责任编辑"内容
            text_list = [
                p.xpath("string(.)").strip()
                for p in article_element.xpath('.//p[not(contains(., "责任编辑"))]')
                if p.xpath("string(.)").strip()
            ]

            match = re.search(r"imgsList:\s*(\[[^\]]+\])", content, re.DOTALL)
            if match:
                try:
                    imgs_list_str = match.group(1)
                    img_list = ast.literal_eval(imgs_list_str)
                    img_list = [
                        (
                            f"https:{item['url']}"
                            if "https:" not in item["url"]
                            else item["url"]
                        )
                        for item in img_list
                    ]
                except Exception as e:
                    img_list = []
            else:
                img_list = []

            article_info = ""
            for item in text_list:
                article_info += item
                article_info += "\n"

            if not article_info:
                return None
            return {
                "title": news["title"],
                "article_url": article_url,
                "cover_url": news["cover_url"],
                "date_str": date_str,
                "article_info": article_info,
                "img_list": img_list,
                "category": news["category"],
            }

        except Exception as e:
            logger.error(f"获取搜狐新闻详情失败: {e}，文章链接: {news['article_url']}")
            return None

    async def get_qiche_info(self, news, category=None, content_html=None):
        """
        获取搜狐汽车的结构不同，需要写新类型
        """
        try:
            base_xpath = '//*[@id="app"]/section[2]/section[2]/div[2]'

            article_info = ""
            p_elements = content_html.xpath(f"{base_xpath}//p")
            for p in p_elements:
                if p.text:
                    article_info += p.text.strip()
                    article_info += "\n"

            # 提取所有<img>标签的src属性
            img_elements = content_html.xpath(f"{base_xpath}//img")
            img_list = [
                "https:" + (img.get("data-src") or img.get("src"))
                for img in img_elements
                if img.get("src")
            ]
            date_str = content_html.xpath(
                '//*[@id="app"]/section[2]/section[2]/div[1]/span[1]/text()'
            )[0]
        except Exception as e:
            logger.error(
                f"获取搜狐汽车新闻详情失败: {e}，文章链接: {news['article_url']}"
            )
            return None
        return {
            "title": news["title"],
            "article_url": news["article_url"],
            "cover_url": news["cover_url"],
            "date_str": date_str,
            "article_info": article_info,
            "img_list": img_list,
            "category": news["category"],
        }

    # async def get_yuanchuang_info(self, news, category=None, content_html=None):
    #     """
    #     获取搜狐原创的结构不同，需要写新类型
    #     """
    #     try:
    #         content_html = content_html.xpath('//article[@id="mp-editor"]')[0]
    #
    #         article_info = ""
    #         p_elements = content_html.xpath(f"{base_xpath}//p")
    #         for p in p_elements:
    #             if p.text:
    #                 article_info += p.text.strip()
    #                 article_info += "\n"
    #
    #         # 提取所有<img>标签的src属性
    #         img_elements = content_html.xpath(f"{base_xpath}//img")
    #         img_list = [
    #             "https:" + (img.get("data-src") or img.get("src"))
    #             for img in img_elements
    #             if img.get("src")
    #         ]
    #         date_str = content_html.xpath(
    #             '//*[@id="app"]/section[2]/section[2]/div[1]/span[1]/text()'
    #         )[0]
    #     except Exception as e:
    #         logger.error(
    #             f"获取搜狐原创新闻详情失败: {e}，文章链接: {news['article_url']}"
    #         )
    #         return None
    #     return {
    #         "title": news["title"],
    #         "article_url": news["article_url"],
    #         "cover_url": news["cover_url"],
    #         "date_str": date_str,
    #         "article_info": article_info,
    #         "img_list": img_list,
    #         "category": news["category"],
    #     }


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
        it = SouHu()
        r = await it.crawl_and_save()
        return r

    asyncio.run(crawl_and_save())
