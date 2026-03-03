#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/11/22 16:22
# @Author  : DNQTeach
# @File    : tengxuntiyu.py
import json
import re
from datetime import datetime

from base import BaseSpider
from logger_utils import logger


class TenXun(BaseSpider):
    source_name = "腾讯体育"
    category = "体育"

    async def get_news_list(self, code="https://matchweb.sports.qq.com/feeds/areaInfo"):
        """
        获取腾讯体育新闻列表
        """
        try:
            sceneFlag = ["pc_208", "pc_100000", "pc_100000"]
            data = []

            for s in sceneFlag:
                if s == "pc_100008":
                    page_id = "pc_100008_1502_0_88674"
                    type_ = "type1502"
                elif s == "pc_100000":
                    page_id = "pc_100000_1507_0_88605"
                    type_ = "type1507"
                elif s == "pc_208":
                    page_id = "pc_208_1502_0_88675"
                    type_ = "type1502"

                params = {
                    "sceneFlag": f"{s}",
                }
                response = await self.request(url=code, params=params)

                response_data = json.loads(response)
                for item in response_data["data"]["topItem"]:
                    if item["id"] == page_id:
                        info = item[type_]["list"]
                        for item_info in info:
                            # 将时间戳转换为 datetime 对象
                            dt_object = datetime.fromtimestamp(
                                int(item_info["createTime"])
                            )
                            # 将 datetime 对象格式化为字符串
                            date_str = dt_object.strftime("%Y-%m-%d %H:%M:%S")
                            title = item_info["title"]
                            id = item_info["id"]

                            data.append(
                                {
                                    "title": title,
                                    "article_url": id,
                                    "cover_url": item_info["pic"],
                                    "date_str": date_str,
                                }
                            )
            result = sorted(data, key=lambda x: x["date_str"], reverse=True)
            return result

        except Exception as e:
            logger.error(f"获取腾讯体育新闻列表失败: {e}")
            return []

    async def get_news_info(self, new_data, category=None):
        """
        获取腾讯体育新闻详情
        """
        try:
            article_id = new_data["article_url"]
            cover_url = new_data["cover_url"]
            title = new_data["title"]
            date_str = new_data["date_str"]

            params = {
                "tid": f"{article_id}",
                "page": "1",
            }

            response = await self.request(
                url="https://shequweb.sports.qq.com/reply/listCite", params=params
            )
            content = json.loads(response)

            try:
                contents = content["data"]["topic"]["content"]
            except:
                if "msg" in content and content["msg"] == "参数不合法":
                    logger.skip("转发内容无法抓取")
                    return None
                # 使用正则表达式提取 JSON 部分
                match = re.search(r"\(({.*})\)", response)
                json_string = match.group(1)
                # 解析 JSON
                json_data = json.loads(json_string)
                # 输出解析后的 JSON 数据
                contents = json_data["data"]["topic"]["content"]

            article_info = ""
            img_list = []
            for c in contents:
                t = c["info"]
                if "https://sports3.gtimg.com/community" in t:
                    try:
                        img_list.append(t["image"]["cur"]["url"])
                    except:
                        img_list.append(t)
                else:
                    article_info += t
                    article_info += "\n"
            if len(article_info) > 0 and "不得转载" not in article_info:
                return {
                    "title": title,
                    "article_url": f"https://shequweb.sports.qq.com/reply/listCite?tid={article_id}&page=1",
                    "cover_url": cover_url,
                    "date_str": date_str,
                    "article_info": article_info,
                    "img_list": img_list,
                    "category": "5",
                }

            return None

        except Exception as e:
            logger.error(f"获取腾讯体育新闻详情失败: {e}")
            return None

    async def crawl_and_save(
        self,
        code="https://matchweb.sports.qq.com/feeds/areaInfo",
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
        it = TenXun()
        r = await it.crawl_and_save()
        return r

    asyncio.run(crawl_and_save())
