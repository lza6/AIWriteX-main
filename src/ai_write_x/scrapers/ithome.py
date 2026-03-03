#!/usr/bin/python
# -*- coding: UTF-8 -*-
# @author:anning
# @email:anningforchina@gmail.com
# @time:2024/12/21 22:38
# @file:ithome.py
import asyncio
from datetime import datetime
from typing import Any, Coroutine
from urllib.parse import urlparse, unquote, quote

from lxml import etree
from base import BaseSpider
from logger_utils import logger


class ITHome(BaseSpider):
    source_name = "IT之家"
    category = "科技"

    def convert_time_str(self, time_str, date_str=None):
        """
        将时间字符串转换为标准的日期时间格式 %Y-%m-%d %H:%M:%S
        支持 "HH:MM" 或 "HH MM" 格式
        """
        try:
            if date_str:
                date_part = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                date_part = datetime.now().date()

            # 根据是否包含 ":" 判断时间格式
            if ":" in time_str:
                hour, minute = map(int, time_str.strip().split(":"))
            else:
                hour, minute = map(int, time_str.strip().split())

            full_datetime = datetime.combine(date_part, datetime.min.time()).replace(
                hour=hour, minute=minute, second=0
            )
            return full_datetime.strftime("%Y-%m-%d %H:%M:%S")

        except ValueError as ve:
            return f"输入格式错误: {ve}"
        except Exception as e:
            return f"发生错误: {e}"

    async def get_news_list(self, code="https://www.ithome.com/"):
        """
        获取IT之家新闻列表
        """
        try:
            content = await self.request(url=code)
            content_html = etree.HTML(content)
            result = []

            # 获取新闻列表
            news_items = content_html.xpath('//*[@id="nnews"]/div[3]/ul/li')
            for item in news_items:
                title_elements = item.xpath(".//a")
                if title_elements:
                    title = title_elements[0].text.strip()
                    link = title_elements[0].get("href").strip()

                    date_str = item.xpath("./b//text()")
                    if date_str:
                        date_str = self.convert_time_str(date_str[0].strip().replace("\u2009", ""))
                else:
                    # 如果没有标题或链接，跳过该条目
                    continue
                # 只添加有实际内容的条目
                if title and link and date_str:
                    # 将数据添加到列表中
                    result.append(
                        {"title": title, "article_url": link, "date_str": date_str}
                    )
            return result

        except Exception as e:
            logger.error(f"获取IT之家新闻列表失败: {e}")
            return []

    async def get_base_url(self, url):
        """安全提取URL基础部分，忽略查询参数和片段"""
        parsed = urlparse(url)
        # 重新组合协议、域名和路径
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    async def get_news_info(self, item, category="4"):
        """
        获取IT之家新闻详情
        """
        try:
            content = await self.request(url=item["article_url"])
            content_html = etree.HTML(content)
            content_div = content_html.xpath('//*[@id="paragraph"]')[0]
            # 提取 p 标签的文本列表
            text_list = content_div.xpath(
                './/p[not(@class="ad-tips") and not(descendant::dir)]/text()'
            )

            # 提取 img 标签的 src 列表
            data_original_list = content_div.xpath(
                './/p[not(@class="ad-tips") and not(descendant::dir)]//img/@data-original'
            )
            src_list = content_div.xpath(
                './/p[not(@class="ad-tips") and not(descendant::dir)]//img/@src'
            )

            # 组合结果，优先使用 data-original
            img_list = []
            for data_original, src in zip(data_original_list, src_list):
                if data_original and not data_original.strip().startswith("//"):
                    img_url = data_original.strip()
                elif data_original and data_original.strip().startswith("//"):
                    img_url = "https:" + data_original.strip()
                else:
                    img_url = src.strip()
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                img_parse_url = await self.get_base_url(img_url)
                img_list.append(img_parse_url)

            article_info = ""
            for item_ in text_list:
                article_info += item_
                article_info += "\n"
            if not article_info:
                return None
            if len(article_info) < 50:
                return None
            data = {
                "title": item["title"],
                "article_url": item["article_url"],
                "cover_url": img_list[0] if img_list else "",
                "date_str": item["date_str"],
                "article_info": article_info.replace("\u3000", "").replace("\xa0", ""),
                "img_list": img_list,
                "category": category,
            }
            return data

        except Exception as e:
            logger.error(f"获取IT之家新闻详情失败: {e}")
            return None

    async def crawl_and_save(
        self,
        code="https://www.ithome.com/",
        limit=None,
        class_sleep_time=0,
        info_sleep_time=0,
        addition_msg="",
    ) -> int:
        return await super().crawl_and_save(
            code, limit, class_sleep_time, info_sleep_time, addition_msg
        )


if __name__ == "__main__":
    import asyncio

    async def crawl_and_save() -> int:
        from database import db_manager

        if db_manager.pool is None:
            await db_manager.create_pool()
            await db_manager.init_tables()
            logger.success("数据库连接池已创建，数据表已初始化")
        it = ITHome()
        r = await it.crawl_and_save()
        return r

    asyncio.run(crawl_and_save())
