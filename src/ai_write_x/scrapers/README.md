# Article Spider

一个基于 Python 异步编程的新闻文章爬虫项目，支持从多个中文新闻网站抓取文章并存储到 PostgreSQL 数据库。

## 支持的新闻源

| 新闻源 | 文件 | 说明 |
|--------|------|------|
| 网易新闻 | `wangyi.py` | 网易新闻各频道 |
| 搜狐新闻 | `souhu.py` | 搜狐新闻 |
| 新浪新闻 | `xinlang.py` | 新浪新闻 |
| 澎湃新闻 | `pengpai.py` | 澎湃新闻 |
| IT之家 | `ithome.py` | IT科技资讯 |
| 腾讯新闻 | `tengxunxinwen.py` | 腾讯新闻 |
| 腾讯体育 | `tengxuntiyu.py` | 腾讯体育新闻 |
| 中国日报 | `zhongguoribao.py` | 中国日报 |

## 环境要求

- Python 3.12+
- PostgreSQL 数据库
- uv 包管理器（推荐）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Anning01/article-spider.git
cd article-spider
```

### 2. 安装依赖

使用 uv（推荐）：
```bash
uv sync
```

或使用 pip：
```bash
pip install -e .
```

### 3. 配置环境变量

复制 `.env.example` 或直接编辑 `.env` 文件：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_username
DB_PASSWORD=your_password
DB_DATABASE=article_spider
DB_MAX_CONNECTIONS=10
DB_MIN_CONNECTIONS=1

# 爬虫运行间隔时间（秒）
ITHOME_INTERVAL=180
PENGPAI_INTERVAL=180
WANGYI_INTERVAL=180
SOUHU_INTERVAL=180
TENGXUNXINWEN_INTERVAL=180
TENGXUNTIYU_INTERVAL=180
XINLANG_INTERVAL=180
ZHONGGUORIBAO_INTERVAL=180

# 全局爬虫配置
DEFAULT_LIMIT=0  # 0 表示无限制
```

### 4. 创建数据库

确保 PostgreSQL 服务已启动，创建数据库：

```sql
CREATE DATABASE article_spider;
```

程序首次运行时会自动创建所需的表结构。

### 5. 运行爬虫

```bash
uv run python main.py
```

或激活虚拟环境后运行：
```bash
source .venv/bin/activate
python main.py
```

## 项目结构

```
article-spider/
├── main.py              # 主入口，管理爬虫协程任务
├── base.py              # BaseSpider 爬虫基类
├── database.py          # PostgreSQL 数据库管理器
├── logger_utils.py      # 彩色日志工具
├── classify.py          # 文章分类工具
├── wangyi.py            # 网易新闻爬虫
├── souhu.py             # 搜狐新闻爬虫
├── xinlang.py           # 新浪新闻爬虫
├── pengpai.py           # 澎湃新闻爬虫
├── ithome.py            # IT之家爬虫
├── tengxunxinwen.py     # 腾讯新闻爬虫
├── tengxuntiyu.py       # 腾讯体育爬虫
├── zhongguoribao.py     # 中国日报爬虫
├── .env                 # 环境配置文件
├── pyproject.toml       # 项目配置
└── spider.log           # 运行日志
```

## 如何添加新的爬虫

### 1. 创建爬虫文件

创建新文件，例如 `xinhuashe.py`：

```python
from base import BaseSpider
from lxml import etree

class XinHuaShe(BaseSpider):
    source_name = "新华社"
    category = "新闻"

    async def get_news_list(self, html: str) -> list:
        """解析列表页，返回文章链接列表"""
        tree = etree.HTML(html)
        # 根据网站结构编写 XPath
        links = tree.xpath('//a[@class="news-link"]/@href')
        return links

    async def get_news_info(self, html: str, url: str) -> dict | None:
        """解析详情页，返回文章信息"""
        tree = etree.HTML(html)
        return {
            'title': tree.xpath('//h1/text()')[0],
            'content': ''.join(tree.xpath('//div[@class="content"]//text()')),
            'publish_time': tree.xpath('//span[@class="time"]/text()')[0],
            'author': tree.xpath('//span[@class="author"]/text()')[0],
        }
```

### 2. 注册爬虫

在 `main.py` 的 `spiders` 字典中添加：

```python
from xinhuashe import XinHuaShe

spiders = {
    # ... 现有爬虫
    'xinhuashe': {
        'spider': XinHuaShe,
        'url': 'https://www.xinhuanet.com/',
        'interval': int(os.getenv('XINHUASHE_INTERVAL', 180)),
    },
}
```

### 3. 添加配置

在 `.env` 文件中添加：

```env
XINHUASHE_INTERVAL=180
```

## 核心类说明

### BaseSpider（base.py）

爬虫基类，提供通用功能：

| 方法 | 说明 |
|------|------|
| `request(url)` | 异步 HTTP 请求，自动处理编码 |
| `get_news_list(html)` | 解析列表页（需子类实现） |
| `get_news_info(html, url)` | 解析详情页（需子类实现） |
| `save_article(article)` | 保存文章到数据库 |
| `crawl_and_save(limit)` | 执行抓取流程 |

### PostgreSQLManager（database.py）

数据库连接池管理：

| 方法 | 说明 |
|------|------|
| `create_pool()` | 创建连接池 |
| `close_pool()` | 关闭连接池 |
| `execute(sql, *args)` | 执行 SQL |
| `fetchone(sql, *args)` | 查询单条记录 |
| `fetchall(sql, *args)` | 查询多条记录 |
| `init_tables()` | 初始化数据表 |

## 配置说明

### 爬虫间隔时间

每个爬虫的 `INTERVAL` 配置控制两次抓取之间的等待时间（秒）。建议：
- 设置合理的间隔，避免对目标网站造成压力
- 生产环境建议 180 秒以上

### 抓取数量限制

`DEFAULT_LIMIT` 控制每次抓取的文章数量：
- `0`：无限制，抓取所有可见文章
- `>0`：限制抓取数量

## 日志

运行日志保存在 `spider.log` 文件中，同时输出到控制台（带颜色）。

查看实时日志：
```bash
tail -f spider.log
```

## 技术栈

- **异步框架**: asyncio
- **HTTP 客户端**: aiohttp
- **数据库**: PostgreSQL + asyncpg
- **HTML 解析**: lxml
- **环境配置**: python-dotenv

## 注意事项

1. 请遵守目标网站的 robots.txt 规则
2. 合理设置抓取间隔，避免给目标网站造成压力
3. 仅用于学习和研究目的

## License

MIT
