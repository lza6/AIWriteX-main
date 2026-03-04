# AIWriteX 数据库结构定义 (V2.0 升级草案)

*(注：项目当前严重依赖 `data/topics_history.json`。为应对大型、高并发需求，V2.0 决定全面迁移至结构化的数据库，例如本地 SQLite 或 PostgreSQL)。*

## 1. 表名: `topics` (话题数据表)
用于存储各平台抓取来的全网热点话题、黑马话题等。
- `id` (UUID, 主键)
- `title` (String, 不为空, 话题标题)
- `source_platform` (String, 话题来源平台：微信、抖音、知乎等)
- `hot_score` (Integer, 动态热度指数)
- `status` (Enum: 待处理, 处理中, 已完成, 失败)
- `created_at` (Datetime, 抓取时间)
- `updated_at` (Datetime, 热点最新更新时间)

## 2. 表名: `articles` (文章数据表)
统一管理 AI 生成的不同版本文章、对应的评分及输出格式。
- `id` (UUID, 主键)
- `topic_id` (UUID, 外键 -> topics.id)
- `content` (Text, 长文本存储文章内容)
- `format` (String, 输出格式：HTML, Markdown 等)
- `version` (Integer, 版本号，默认1)
- `human_rating` (Integer, 用户反馈评分/反思评分，助力后期 AI 自主学习)
- `created_at` (Datetime, 创建生成时间)

## 3. 表名: `agent_memories` (智能体长期记忆表)
存储智能体历史生成的知识经验、提示词黑用语及文章基因。
- `id` (UUID, 主键)
- `agent_role` (String, 角色：如研究员, 审核员, 特写作家)
- `memory_text` (Text, 知识切片文本)
- `vector_embedding` (JSON/Array, 向量数据预留，用于语义相似性检索 RAG)
- `created_at` (Datetime)

## 4. 表名: `system_settings` (系统级配置表)
逐步接管 `config.yaml` 中需要高频读写或动态干预的设置项。
- `key` (String, 主键，设置项名称)
- `value` (JSON, 参数值)
- `updated_at` (Datetime)

## 数据库架构日志
- **2026-03-04**: 创建 V2 草案方案，规划基于 SQLite 和对象关系映射 (SQLAlchemy / SQLModel) 的迁移结构。
