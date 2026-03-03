#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/11/22 18:15
# @Author  : DNQTeach
# @File    : wangyi.py
import asyncio
import re
from datetime import datetime, timedelta
import json
from lxml import etree
from base import BaseSpider
from logger_utils import logger


class WangYi(BaseSpider):
    source_name = "网易新闻"
    category = "新闻"
    category_list = [
        {
            "name": "时事热点",
            "code": "https://news.163.com/special/cm_yaowen20200213/?callback=data_callback",
            "classify": "16",
        },
        {
            "name": "国内新闻",
            "code": "https://news.163.com/special/cm_guonei/?callback=data_callback",
            "classify": "3",
        },
        {
            "name": "国际新闻",
            "code": "https://news.163.com/special/cm_world/?callback=data_callback",
            "classify": "5",
        },
        {
            "name": "福建泉州",
            "code": "https://fj.news.163.com/special/cm_fujian/?callback=data_callback",
            "classify": "20",
        },
        {
            "name": "军事",
            "code": "https://news.163.com/special/cm_war/?callback=data_callback",
            "classify": "8",
        },
        {
            "name": "社会",
            "code": "https://news.163.com/special/cm_guonei/?callback=data_callback",
            "classify": "3",
        },
        {
            "name": "科技",
            "code": "https://tech.163.com/special/00097UHL/tech_datalist.js?callback=data_callback",
            "classify": "4",
        },
        {
            "name": "娱乐",
            "code": "https://ent.163.com/special/000381Q1/newsdata_movieidx.js?callback=data_callback",
            "classify": "6",
        },
        {
            "name": "经济",
            "code": "https://money.163.com/special/00259K2L/data_stock_redian.js?callback=data_callback",
            "classify": "2",
        },
        {
            "name": "教育",
            "code": "https://edu.163.com/special/002987KB/newsdata_edu_hot.js?callback=data_callback",
            "classify": "11",
        },
        {
            "name": "生活",
            "code": "https://baby.163.com/special/003687OS/newsdata_hot.js?callback=data_callback",
            "classify": "10",
        },
        {
            "name": "财经",
            "code": "https://money.163.com/special/00259K2L/data_stock_redian.js?callback=data_callback",
            "classify": "2",
        },
    ]

    async def get_news_list(self, category: dict):
        """
        获取网易新闻列表
        """
        try:
            url = category["code"]
            params = {
                "callback": "data_callback",
            }

            text = await self.request(url=url, params=params)
            res = text.replace("data_callback(", "")[0:-1]
            data_str = json.loads(res.rstrip(",\n ]").strip() + "]")

            result = []
            for item in data_str[:20]:
                if "video" not in item["docurl"]:
                    result.append(
                        {
                            "title": item["title"],
                            "article_url": item["docurl"],
                            "cover_url": item["imgurl"],
                            "date_str": datetime.strptime(
                                item["time"], "%m/%d/%Y %H:%M:%S"
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "category": category["classify"],
                        }
                    )

            result = sorted(result, key=lambda x: x["date_str"], reverse=True)
            return result

        except Exception as e:
            logger.error(f"获取网易新闻列表失败: {e}")
            return []

    async def get_news_info(self, item, category=None):
        """
        获取网易新闻详情
        """
        try:
            title = item["title"]
            article_url = item["article_url"]
            cover_url = item["cover_url"]

            if "video" not in article_url:

                content = await self.request(url=article_url)
                content_html = etree.HTML(content)

                try:
                    date_str = (
                        content_html.xpath('//*[@id="contain"]/div[2]/div[2]/text()')[0]
                        .strip()
                        .replace("　来源:", "")
                    )
                except:
                    try:
                        date_str = (
                            content_html.xpath(
                                '//*[@id="container"]/div[1]/div[2]/text()[1]'
                            )[0]
                            .strip()
                            .replace("　来源:", "")
                        )
                    except:
                        date_str = (
                            content_html.xpath(
                                '//*[@id="contain"]/div[1]/div[2]/text()'
                            )[0]
                            .strip()
                            .replace("　来源:", "")
                        )
                date_str = re.search(
                    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", date_str
                ).group()
                date_str = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                img_list = content_html.xpath('//*[@id="content"]/div[2]/p/img/@src')
                txt = content_html.xpath('//*[@id="content"]/div[2]/p')

                article_info = ""
                for item_ in txt:
                    t = item_.xpath(".//text()")
                    for i in t:
                        article_info += i
                        article_info += "\n"
                if len(article_info) > 0 and "不得转载" not in article_info:
                    data = {
                        "title": title,
                        "article_url": article_url,
                        "cover_url": cover_url,
                        "date_str": datetime.strftime(date_str, "%Y-%m-%d %H:%M:%S"),
                        "article_info": article_info,
                        "img_list": img_list,
                        "category": item["category"],
                    }
                    return data

            return None

        except Exception as e:
            logger.error(f"获取网易新闻详情失败: {e}， 文章链接: {item['article_url']}")
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
        it = WangYi()
        r = await it.crawl_and_save()
        return r

    asyncio.run(crawl_and_save())
