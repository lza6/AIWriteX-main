import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xinhua import XinhuaNews
from bbc import BBCChinese
from wsj import WSJ
from nytimes import NYTimes
from zaobao import ZaoBao
from voa import VOAChinese

import sys
import io

# 设置终端输出编码
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except:
        pass

def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('gbk', errors='replace').decode('gbk'))

async def test_spider(name, spider_class):
    safe_print(f"\n--- Testing Spider: {name} ---")
    spider = spider_class()
    try:
        results = await spider.get_news_list()
        if results:
            safe_print(f"Successfully fetched {len(results)} items")
            try:
                # 尝试打印第一个标题，处理编码
                title = results[0]['title']
                safe_print(f"First item: {title}")
            except Exception as e:
                safe_print(f"Error printing title: {e}")
            safe_print(f"URL: {results[0]['article_url']}")
            return True
        else:
            safe_print("Fetched 0 items.")
            return False
    except Exception as e:
        safe_print(f"Failed: {e}")
        return False

async def main():
    r1 = await test_spider("Xinhua", XinhuaNews)
    r2 = await test_spider("BBC", BBCChinese)
    r3 = await test_spider("WSJ", WSJ)
    r4 = await test_spider("NYTimes", NYTimes)
    r5 = await test_spider("ZaoBao", ZaoBao)
    r6 = await test_spider("VOA", VOAChinese)
    
    if all([r1, r2, r3, r4, r5, r6]):
        print("\nAll spiders verified successfully!")
    else:
        print("\nSome spiders failed verification.")

if __name__ == "__main__":
    asyncio.run(main())
