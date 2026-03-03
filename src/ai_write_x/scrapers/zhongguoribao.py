import asyncio
from datetime import datetime
from lxml import etree
from base import BaseSpider
from logger_utils import logger

chinese_day_failed_urls = set()

class ChineseDayNews(BaseSpider):
    source_name = "中国日报"
    category = "新闻"
    category_list = [
        {
            "name": "时政要闻",
            "code": "https://china.chinadaily.com.cn/5bd5639ca3101a87ca8ff636",
            "classify": "1",
        },
        {
            "name": "台海动态",
            "code": "https://china.chinadaily.com.cn/5e1ea9f6a3107bb6b579a144",
            "classify": "1",
        },
        {
            "name": "台湾政策",
            "code": "https://china.chinadaily.com.cn/5e1ea9f6a3107bb6b579a147",
            "classify": "1",
        },
        {
            "name": "两岸人生",
            "code": "https://china.chinadaily.com.cn/5e23b3dea3107bb6b579ab68",
            "classify": "9",
        },
        {
            "name": "国际资讯",
            "code": "https://china.chinadaily.com.cn/5bd55927a3101a87ca8ff618",
            "classify": "7",
        },
        {
            "name": "中国日报专稿",
            "code": "https://cn.chinadaily.com.cn/5b753f9fa310030f813cf408/5bd54dd6a3101a87ca8ff5f8/5bd54e59a3101a87ca8ff606",
            "classify": "3",
        },
        {
            "name": "传媒动态",
            "code": "https://cn.chinadaily.com.cn/5b753f9fa310030f813cf408/5bd549f1a3101a87ca8ff5e0",
            "classify": "9",
        },
        {
            "name": "财经大事",
            "code": "https://caijing.chinadaily.com.cn/stock/5f646b7fa3101e7ce97253d3",
            "classify": "2",
        },
        {
            "name": "权威发布",
            "code": "https://caijing.chinadaily.com.cn/stock/5f646b7fa3101e7ce97253d6",
            "classify": "2",
        },
        {
            "name": "公告解读",
            "code": "https://caijing.chinadaily.com.cn/stock/5f646b7fa3101e7ce97253d9",
            "classify": "2",
        },
        {
            "name": "深度报道",
            "code": "https://caijing.chinadaily.com.cn/stock/5f646b7fa3101e7ce97253dc",
            "classify": "2",
        },
        {
            "name": "信息披露",
            "code": "https://caijing.chinadaily.com.cn/stock/5f646b7fa3101e7ce97253df",
            "classify": "2",
        },
        {
            "name": "头条新闻",
            "code": "https://cn.chinadaily.com.cn/wenlv/5b7628dfa310030f813cf495",
            "classify": "10",
        },
        {
            "name": "旅游要闻",
            "code": "https://cn.chinadaily.com.cn/wenlv/5b7628c6a310030f813cf48f",
            "classify": "10",
        },
        {
            "name": "酒店",
            "code": "https://cn.chinadaily.com.cn/wenlv/5b7628c6a310030f813cf48b",
            "classify": "10",
        },
        {
            "name": "旅游原创",
            "code": "https://cn.chinadaily.com.cn/wenlv/5b7628c6a310030f813cf492",
            "classify": "10",
        },
        {
            "name": "业界资讯",
            "code": "https://cn.chinadaily.com.cn/wenlv/5b7628c6a310030f813cf493",
            "classify": "10",
        },
        {
            "name": "时尚",
            "code": "https://fashion.chinadaily.com.cn/5b762404a310030f813cf467",
            "classify": "10",
        },
        {
            "name": "健康频道",
            "code": "https://cn.chinadaily.com.cn/jiankang",
            "classify": "12",
        },
        {
            "name": "教育",
            "code": "https://fashion.chinadaily.com.cn/5b762404a310030f813cf461",
            "classify": "11",
        },
        {
            "name": "体育",
            "code": "https://fashion.chinadaily.com.cn/5b762404a310030f813cf462",
            "classify": "5",
        },
    ]

    async def get_news_list(self, category: dict):
        """
        获取中国日报新闻列表
        """
        try:
            url = category["code"]

            content = await self.request(url=url)
            content_html = etree.HTML(content)

            # 初始化结果列表
            result = []
            div_elements = content_html.xpath(
                "//html/body/div[3]/div[1]/div/div[.//h3 and .//p/b]"
            )

            # 遍历每个元素，提取数据
            for element in div_elements:
                # 提取标题文字
                title = element.xpath(".//h3/a/text()")
                title = title[0].strip() if title else None

                # 提取文章 URL
                article_url = element.xpath(".//h3/a/@href")
                article_url = "https:" + article_url[0].strip() if article_url else None

                # 提取封面图片 URL
                cover_url = element.xpath('.//div[contains(@class, "mr10")]/a/img/@src')
                cover_url = "https:" + cover_url[0].strip() if cover_url else None

                # 提取时间字符串
                date_str = element.xpath(".//p/b/text()")
                date_str = date_str[0].strip() if date_str else None

                # 创建字典并添加到结果列表
                if title and article_url and date_str:
                    result.append(
                        {
                            "title": title,
                            "article_url": article_url,
                            "cover_url": cover_url,
                            "date_str": datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M"
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "category": category["classify"],
                        }
                    )

            result = sorted(result, key=lambda x: x["date_str"], reverse=True)
            return result

        except Exception as e:
            logger.error(f"获取中国日报新闻列表失败: {e}, 文章：{category['code']}")
            return []

    async def get_news_info(self, news, category=None):
        """
        获取中国日报新闻详情
        """
        article_url = news["article_url"]
        if article_url in chinese_day_failed_urls:
            logger.warning(f"跳过已失败的url: {article_url}")
            return None
        try:

            content = await self.request(url=article_url)
            content_html = etree.HTML(content)

            content_div = content_html.xpath('//div[@id="Content"]')[0]

            # 提取 p 标签的文本列表
            text_list = content_div.xpath(".//p/text()")
            # 提取 img 标签的 src 列表
            img_list = content_div.xpath(".//img/@src")
            img_list = ["https:" + i for i in img_list]
            article_info = ""
            for item in text_list:
                article_info += item
                article_info += "\n"
            if not article_info:
                return None
            if len(article_info) < 50:
                return None

            try:
                date_str = datetime.strptime(
                    news["date_str"], "%Y-%m-%d %H:%M"
                ).strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_str = news["date_str"]

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
            chinese_day_failed_urls.add(article_url)
            logger.error(f"获取中国日报新闻详情失败: {e}，文章：{article_url}")
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
            print("数据库连接池已创建，数据表已初始化")
        it = ChineseDayNews()
        r = await it.crawl_and_save()
        return r

    asyncio.run(crawl_and_save())
