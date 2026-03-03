# AIWriteX V2 — 项目规格说明

## 概述
AIWriteX 是一个**多智能体 AI 内容创作引擎**，专为微信公众号自动化写作、排版和发布设计。

## 核心特性 (V2)
- 🧠 **多智能体协同** — CrewAI 驱动的作者-编辑-终审三层 Agent 流水线
- 🔄 **Reflexion 自进化** — 终审不通过自动触发零污染打磨重写循环 (最多 3 轮)
- 🎨 **自适应模板引擎** — Glassmorphism + 暗黑模式 + 滚动微动画
- 🖼️ **智能视觉资产** — VL 视觉理解 + 多源图像生成 (Ali/ModelScope/ComfyUI/Picsum)
- 🔍 **热点智脑** — 多平台热搜聚合 + 三天内话题自动去重
- 🛡️ **反 AI 痕迹** — 结构粉碎器 + 动态风格模仿回避检测器
- 📊 **ComfyUI 节点进度** — 实时可视化每步模型参数、迭代轮次

## 目录结构
```
AIWriteX-main/
├── main.py                        # 入口
├── secrets/                       # 🔐 密钥存储（.gitignore 保护）
├── docs/                          # 文档 & 截图
│   ├── screenshots/
│   └── project_specs.md
├── tests/                         # 测试文件
├── src/ai_write_x/
│   ├── core/                      # 核心引擎（LLM、模板、工作流、平台适配、创意维度）
│   ├── config/                    # 配置管理
│   ├── tools/                     # 工具集（爬虫、MCP、发布器、视觉处理）
│   ├── utils/                     # 工具函数
│   ├── assets/
│   │   └── branding/              # 品牌资产（图标、名称、版本）
│   ├── news_aggregator/           # 新闻聚合
│   ├── scrapers/                  # 爬虫引擎
│   ├── orchestrators/             # 编排器
│   ├── mcp_agents/                # MCP 代理
│   └── web/                       # Web UI（HTML/CSS/JS + FastAPI）
└── services/                      # TypeScript/Deno 子系统
```

## 当前版本
- **版本**: V2.0 (Phase 13)
- **最新完成**: 项目结构治理 — 密钥隔离、品牌目录、冗余合并
