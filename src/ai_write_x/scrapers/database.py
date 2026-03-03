import asyncpg
from typing import Optional
from logger_utils import logger


class PostgreSQLManager:
    def __init__(
        self,
        host="localhost",
        port=5432,
        user="anning",
        password="123456",
        database="article_spider",
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool: Optional[asyncpg.Pool] = None

    async def create_pool(self):
        """创建连接池"""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            max_size=10,
            min_size=1,
        )

    async def close_pool(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()

    async def execute(self, sql, params: tuple = ()):
        """执行SQL语句"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(sql, *params)
            return result

    async def fetchone(self, sql, params=None):
        """查询单条记录"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(sql, *(params or []))
            return dict(row) if row else None

    async def fetchall(self, sql, params=None):
        """查询多条记录"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *(params or []))
            return [dict(row) for row in rows]

    async def init_tables(self):
        """初始化数据表"""
        check_table_sql = """
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'accounts_accountnews'
            """

        async with self.pool.acquire() as conn:
            result = await conn.fetchval(check_table_sql)
            logger.info(f"检查表存在性结果: {result}")
            # # 如果表不存在，则创建
            if result == 0:
                create_table_sql = """
                        CREATE TABLE accounts_accountnews (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(255) NOT NULL,
                            article_url VARCHAR(255) NOT NULL UNIQUE,
                            cover_url VARCHAR(255),
                            content TEXT,
                            date_str TIMESTAMP,
                            source VARCHAR(100),
                            img_list JSONB,
                            status SMALLINT DEFAULT 0,  -- 文章状态（0-未发布/1-已发布，用SMALLINT节省空间）
                            platform_data JSONB DEFAULT '{}'::JSONB,  -- 平台扩展数据（默认空对象）
                            category VARCHAR(100),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX idx_title ON accounts_accountnews USING btree (title);
                        CREATE INDEX idx_category ON accounts_accountnews USING btree (category);
                    """
                await conn.execute(create_table_sql)
                print("表 'accounts_accountnews' 已创建")
            else:
                print("表 'accounts_accountnews' 已存在，跳过创建")


# 全局数据库管理器实例
db_manager = PostgreSQLManager()
