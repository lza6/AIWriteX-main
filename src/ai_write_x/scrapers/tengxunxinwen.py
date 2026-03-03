#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/11/22 20:31
# @Author  : DNQTeach
# @File    : tengxuxinwen.py

import asyncio
from lxml import etree
import json
from base import BaseSpider
from logger_utils import logger


class TenXuNews(BaseSpider):
    source_name = "腾讯新闻"
    category = "新闻"
    category_list = [
        {"name": "经济", "code": "news_news_finance", "classify": "2"},
        {"name": "科技", "code": "news_news_tech", "classify": "4"},
        {"name": "娱乐", "code": "news_news_ent", "classify": "6"},
        {"name": "国际", "code": "news_news_world", "classify": "7"},
        {"name": "军事", "code": "news_news_mil", "classify": "8"},
        {"name": "游戏", "code": "news_news_game", "classify": "26"},
        {"name": "民生", "code": "news_news_auto", "classify": "13"},
        {"name": "房地产", "code": "news_news_house", "classify": "13"},
        {"name": "健康", "code": "news_news_antip", "classify": "12"},
        {"name": "教育", "code": "news_news_edu", "classify": "11"},
        {"name": "文化", "code": "news_news_history", "classify": "9"},
        {"name": "生活", "code": "news_news_baby", "classify": "10"},
    ]

    async def get_news_list(self, category: dict):
        """
        获取腾讯新闻列表
        """
        try:
            json_data = {
                "base_req": {
                    "from": "pc",
                },
                "forward": "2",
                "qimei36": "0_C47K1MESdC7T6",
                "device_id": "0_C47K1MESdC7T6",
                "flush_num": 1,
                "channel_id": category["code"],
                "item_count": 12,
                "is_local_chlid": "0",
            }

            response = await self.request(
                method="POST",
                url="https://i.news.qq.com/web_feed/getPCList",
                json=json_data,
            )

            response_data = json.loads(response)
            data = []

            for item in response_data["data"]:
                if item.get("sub_item"):
                    pass
                else:
                    data.append(
                        {
                            "title": item["title"],
                            "cover_url": item["pic_info"]["big_img"],
                            "date_str": item["publish_time"],
                            "article_url": f'https://news.qq.com/rain/a/{item["id"]}',
                            "category": category["classify"],
                        }
                    )

            result = sorted(data, key=lambda x: x["date_str"], reverse=True)
            return result

        except Exception as e:
            logger.error(f"获取腾讯新闻列表失败: {e}")
            return []

    async def get_news_info(self, news_data, category=None):
        """
        获取腾讯新闻详情
        """
        try:
            title = news_data["title"]
            cover_url = news_data["cover_url"]
            if isinstance(cover_url, list):
                cover_url = cover_url[0]
            date_str = news_data["date_str"]
            article_url = news_data["article_url"]
            if not date_str:
                logger.error(f"获取腾讯新闻详情失败: {article_url} 没有日期")
                return None

            content = await self.request(url=article_url)
            content_html = etree.HTML(content)

            content_elements = content_html.xpath(
                '//*[@id="article-content"]/div[2]/div/p'
            )
            img_list = []
            article_info = ""
            # todo 单个P里面含div，需要处理
            for info in content_elements:
                try:
                    img = info.xpath(".//img/@data-src")
                    if len(img) > 0:
                        img_list.append(img[0])
                except:
                    pass

                txt = info.xpath(".//text()")
                for i in txt:
                    article_info += i
                    article_info += "\n"

            return {
                "title": title,
                "article_url": article_url,
                "cover_url": cover_url,
                "date_str": date_str,
                "article_info": article_info,
                "img_list": img_list,
                "category": news_data["category"],
            }

        except Exception as e:
            logger.error(f"获取腾讯新闻详情失败: {e}")
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
        it = TenXuNews()
        r = await it.crawl_and_save()
        return r

    asyncio.run(crawl_and_save())
