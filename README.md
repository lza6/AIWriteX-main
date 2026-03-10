# AIWriteX V23.0- 智能内容创作平台 🚀

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.102.0+-green.svg)](https://www.crewai.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-23.0.0-orange.svg)](https://github.com/iniwap/AIWriteX)

**新一代 AI 驱动的多平台智能内容创作神器** - 从选题到发布的全流程自动化，支持微信公众号、小红书、抖音、知乎等多平台一键发布。

---

## 📖 目录

- [快速开始](#-快速开始)
- [核心功能](#-核心功能)
- [技术架构](#-技术架构)
- [安装配置](#-安装配置)
- [使用教程](#-使用教程)
- [常见问题](#-常见问题)
- [版本历史](#-版本历史)
- [贡献指南](#-贡献指南)

---

## 🌟 快速开始

### 视频教程
- **最新 V23 版本教程**: https://youtu.be/I80b-Lo3pKg
- **基础使用教程**: https://youtu.be/ODPR-PXDWLI

### 大模型资源
本地文生图模型下载：https://www.123865.com/s/61xiVv-X9hkH?pwd=kfob#

---

## 🎯 核心功能

### 1. 全网热点雷达 🌩️
- **多平台聚合**: 微博/抖音/小红书/热搜数据实时抓取
- **黑马挖掘**: AI 预测未来 12 小时热度走势，提前捕捉潜力话题
- **深度分析**: 自动生成爆点提纲 + 完整写作指导

### 2. 多智能体协作系统 🤖
基于 CrewAI 框架，四大智能体协同工作:
- **研究员**: 搜索最新资讯，收集相关素材
- **作家**: 基于素材生成原创内容
- **审核员**: 检查内容质量与逻辑一致性
- **设计师**: 自动排版与视觉优化

### 3. AI 对抗检测引擎 🛡️
- **动态风格拟态**: 提取参考文章的"用词 DNA",实现风格复刻
- **结构粉碎**: 打破 AI 生成的固定模式，增加自然度
- **情感增强**: 注入主观色彩表达与反问句
- **评分反馈**: 持续优化去 AI 味效果

### 4. 多平台一键发布 📤
已支持平台:
- ✅ 微信公众号 (含认证号群发接口)
- ✅ 小红书 (图文笔记)
- ✅ 抖音 (视频/图文)
- ✅ 知乎 (长文/问答)
- ✅ 今日头条
- ✅ 百家号

### 5. Swarm 群体智能系统 🐝 (V17+)
- **分布式协作**: 多个智能体并行工作，提升生产效率
- **负载均衡**: 智能分配任务到不同节点
- **神经信息素通信**: 模拟蚁群算法的高效协作机制

### 6. 向量数据库与语义检索 🔍 (V17+)
- **多库支持**: Milvus/Pinecone/Qdrant
- **语义级搜索**: 基于向量相似度找到真正相关的内容
- **Rust 加速**: 高性能向量运算核心

### 7. 多模态引擎 🎨 (V19+)
- **文生图**: 智能封面、配图生成
- **文生视频**: 短视频脚本、分镜生成
- **文生音频**: TTS 情感合成，多音色支持
- **跨模态检索**: 统一语义空间的相似度匹配

### 8. 企业级架构 🏗️ (V19+)
- **统一配置中心**: 热更新、版本管理、加密存储
- **全局异常处理**: 智能恢复、熔断降级、告警通知
- **结构化日志**: JSON 格式、链路追踪、异步写入
- **完善测试体系**: 核心模块 90%+测试覆盖率

### 9. 认知架构 🧠 (V22+)
- **群体意识中枢**: Self-organizing agent networks
- **集体思维**: Collective mind for complex reasoning
- **共识协议**: Consensus protocol for decision making
- **自愈机制**: Self-healing for system stability
- **知识有机体**: Knowledge organism for continuous learning

---

## 🛠️ 技术架构

### 核心技术栈

| 技术/框架 | 版本 | 用途 |
|---------|------|------|
| Python | 3.10+ | 核心开发语言 |
| CrewAI | 0.102.0+ | 多智能体协作框架 |
| AIForge | 0.0.19+ | 实时搜索与内容借鉴 |
| FastAPI | 0.116.1+ | 后端 API 服务 |
| PyWebView | 4.0.0+ | 可视化界面 |
| WebSocket | - | 实时通信 |
| SQLModel | - | 异步数据库 |
| Three.js | - | 3D 可视化面板 |
| Qdrant/Milvus | - | 向量数据库 |

### 项目结构

```
AIWriteX-main/
├── main.py                       # 程序入口
├── src/ai_write_x/                # 核心代码
│   ├── core/                      # 核心引擎
│   │   ├── swarm/                 # 群体智能系统
│   │   ├── cognitive/             # 认知架构集群 (13+ 模块)
│   │   ├── multimodal/            # 多模态引擎
│   │   ├── config_center/         # 配置中心
│   │   ├── vector_db/             # 向量数据库
│   │   └── quantum_architecture_v21.py  # 量子架构核心
│   ├── database/                  # 数据库层 (仓储模式)
│   ├── scrapers/                  # 爬虫模块
│   ├── tools/                     # 工具集 (发布器/模板等)
│   ├── web/                       # Web 界面
│   │   ├── dashboard/             # 智能仪表盘
│   │   ├── components/            # UI 组件
│   │   └── middleware/            # 中间件 (性能/限流)
│   └── utils/                     # 工具函数
├── tests/                         # 测试文件 (50+ 测试用例)
├── config/                        # 配置文件
├── secrets/                       # 密钥存储 (需手动创建)
├── docs/                          # 文档
└── setup.bat / 启动.bat           # 一键脚本
```

---

## 📦 安装配置

### 方式一：软件模式 (推荐普通用户)

1. **下载安装**: 双击 `.exe` 安装程序完成安装
2. **配置信息**: 在软件界面配置 `API Key` 和公众号信息
3. **开始创作**: 点击`开始执行`按钮即可

### 方式二：源码模式 (开发者)

#### 前置要求
- Python 3.10 或更高版本
- Git (用于克隆代码)

#### 安装步骤

1. **克隆代码**
```bash
git clone https://github.com/iniwap/AIWriteX.git
cd AIWriteX
```

2. **一键配置**
```bash
# Windows 用户
双击运行 "setup.bat"

# Linux/Mac 用户
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example.env
```

3. **配置密钥**
编辑 `.env` 文件，填入以下必要配置:
```env
# OpenRouter API (推荐使用)
OPENROUTER_API_KEY=your_key_here

# 微信公众号配置 (可选)
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret

# 图片生成 API (可选)
IMG_API_KEY=your_key
```

4. **启动项目**
```bash
# Windows 用户
双击运行 "启动.bat"

# Linux/Mac 用户
python main.py
```

---

## 📝 使用教程

### 1. 基础使用流程

1. **热点选题**: 打开「热点雷达」，选择感兴趣的话题
2. **素材收集**: AI 自动搜索相关内容并整理素材库
3. **文章生成**: 多智能体协作生成初稿
4. **人工审核**: 在编辑器中查看并修改内容
5. **排版发布**: 选择模板排版后一键发布到目标平台

### 2. 高级功能

#### Swarm 群体智能
在配置文件中启用 Swarm 模式:
```yaml
swarm:
  enabled: true
  agent_count: 4
  communication_protocol: "neural_pheromone"
```

#### 向量数据库配置
```yaml
vector_db:
  type: "qdrant"  # 或 milvus/pinecone
  url: "http://localhost:6333"
  collection_name: "aiwritex_knowledge"
```

#### 定时任务配置
```yaml
scheduler:
  enabled: true
  cron: "0 9 * * *"  # 每天上午 9 点
  auto_pick_topic: true  # 自动选取热点
  article_count: 3  # 每次生成文章数
```

---

## ❓ 常见问题

### 1. 微信公众号发布问题

**Q: 提示 IP 白名单错误？**
A: 微信 API 需要将当前 IP 添加到公众号后台白名单。解决方案:
- 使用云服务器转发请求
- 或通过阿里云函数计算代理请求

**Q: 个人账号无法发布？**
A: 自 2025 年 7 月起，个人主体账号失去发布草稿权限。建议:
- 尽快完成公众号认证
- 或使用已认证账号发布

### 2. API Key 配置

**Q: 如何获取 OpenRouter API Key?**
A: 访问 https://openrouter.ai/ 注册账号，在 API Keys 页面创建密钥

**Q: 支持哪些大模型？**
A: 支持 OpenRouter 平台所有模型，推荐:
- deepseek/deepseek-chat-v3-0324:free (免费额度)
- anthropic/claude-3-opus (高质量创作)

### 3. 性能优化

**Q: 启动速度慢？**
A: 首次启动需要加载模型和初始化数据库，后续启动会快很多。建议:
- 保持数据库文件不删除
- 使用 SSD 硬盘存储项目

**Q: 内存占用高？**
A: 多智能体系统需要较多内存，建议:
- 关闭不必要的浏览器标签页
- 调整 `agent_count` 参数减少并发智能体数量

---

## 📈 版本历史

### V23.0.0- Cognitive Architecture (Current)
- ✅ 群体意识中枢与集体思维
- ✅ 共识协议与自愈机制
- ✅ 知识有机体持续学习
- ✅ 认知架构集群 (13+ 模块)

### V22.0 - Autonomous Agent Swarms
- ✅ Self-organizing agent networks
- ✅ 群体智能 V2 架构
- ✅ 去中心化通信协议

### V21.0 - Quantum Leap Architecture
- ✅ 量子增强架构核心
- ✅ 下一代超智能缓存
- ✅ 全链路可观测性平台
- ✅ WebGPU 可视化引擎
- ✅ HTTP/3 + QUIC 支持

### V20.0- Reality Synthesis
- ✅ 实时数据融合引擎
- ✅ 个性化推荐系统
- ✅ 多模态内容生成

### V19.0 - Cognitive Architecture
- ✅ 神经认知核心
- ✅ 多模态引擎
- ✅ 配置中心与异常处理
- ✅ 结构化日志系统

### V17.0- Omnisynapse Nexus
- ✅ Swarm 群体智能系统
- ✅ 向量数据库支持
- ✅ 多模态生成引擎
- ✅ 实时协作系统

*更多历史版本请参考 [CHANGELOG.md](docs/CHANGELOG.md)*

---

## 🎯 技术亮点评级

| 技术点 | 创新性 | 实用性 | 难度 | 评分 |
|-------|-------|-------|------|------|
| 多智能体协作 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **9.5/10** |
| Swarm 群体智能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **9.8/10** |
| 向量数据库检索 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **9.0/10** |
| AI 对抗检测 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **9.5/10** |
| 热点预测算法 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **9.0/10** |
| 多平台发布 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | **8.0/10** |

---

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发环境搭建
```bash
git clone https://github.com/iniwap/AIWriteX.git
cd AIWriteX
pip install -e ".[dev]"
pytest tests/  # 运行测试
```

### 代码规范
- 遵循 PEP 8 规范
- 所有公共方法需包含 docstring
- 核心模块需包含单元测试

---

## 📄 开源协议

本项目采用 MIT 协议开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 🙏 致谢

感谢以下开源项目:
- [CrewAI](https://www.crewai.com/) - 多智能体协作框架
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
- [Qdrant](https://qdrant.tech/) - 向量数据库
- [Three.js](https://threejs.org/) - 3D 图形库

---

## 📬 联系方式

- **作者**: iniwap
- **邮箱**: iniwaper@gmail.com
- **GitHub**: [@iniwap](https://github.com/iniwap)
- **项目地址**: https://github.com/iniwap/AIWriteX

---

<div align="center">

**🌟 喜欢这个项目？请点个 Star 支持一下吧！**

[![Star History Chart](https://api.star-history.com/svg?repos=iniwap/AIWriteX&type=Date)](https://star-history.com/#iniwap/AIWriteX&Date)

Made with ❤️ by AIWriteX Team

</div>
