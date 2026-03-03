<div align="center">

# 🌅 Horizon

**AI 筛选科技新闻，你只需阅读。**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=flat-square)](https://github.com/astral-sh/uv)
[![Daily Summary](https://github.com/Thysrael/Horizon/actions/workflows/deploy-docs.yml/badge.svg?style=flat-square)](https://thysrael.github.io/Horizon/)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/Thysrael/Horizon?style=flat-square)](https://github.com/Thysrael/Horizon/commits/main)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

<br>

![Claude](https://img.shields.io/badge/Claude-f0daba?style=flat-square&logo=anthropic&logoColor=black)
![GPT-4](https://img.shields.io/badge/GPT--4-412991?style=flat-square&logo=openai&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=flat-square&logo=google&logoColor=white)
![DeepSeek](https://img.shields.io/badge/DeepSeek-0A6DC2?style=flat-square&logo=deepseek&logoColor=white)
![Doubao](https://img.shields.io/badge/Doubao-00D6C2?style=flat-square&logoColor=white)

Horizon 从多个可自定义的信息源中收集新闻，利用 AI 对新闻进行打分与过滤，最终生成一份包含摘要、社区讨论和背景知识的中英双语日报。

[📖 在线演示](https://thysrael.github.io/Horizon/) · [📋 配置指南](https://thysrael.github.io/Horizon/configuration) · [English](README.md)

</div>

## 截图

<table>
<tr>
<td width="50%">
<p align="center"><strong>日报总览</strong></p>
<img src="docs/assets/overview_zh.png" alt="日报总览" />
</td>
<td width="50%">
<p align="center"><strong>新闻详情</strong></p>
<img src="docs/assets/one_news_zh.png" alt="新闻详情" />
</td>
</tr>
</table>

<details>
<summary><strong>终端输出</strong></summary>
<br>
<p align="center">
  <img src="docs/assets/terminal_log.png" alt="终端输出" width="400" />
</p>
</details>

## 为什么需要 Horizon？

对于开发者来说，及时了解科技动态是一个重要需求。但现实情况是：

- **信息分散** — 有价值的新闻散落在 Hacker News、Reddit、Telegram、RSS 等不同平台
- **噪声太大** — RSS 订阅一旦增多，大量低质量内容淹没真正重要的信息
- **阅读门槛高** — 英文新闻涉及的背景知识不够了解，读完也不知道社区怎么看
- **耗费精力** — 每天手动浏览多个平台花费大量时间

Horizon 通过 **AI 自动打分过滤** + **背景知识补充** + **社区评论汇总** + **中英双语输出**，将每日信息获取从"大海捞针"变为"开箱即读"。

## 功能特性

- **📡 多源聚合** — 从 Hacker News、RSS、Reddit、Telegram 频道和 GitHub（Release 与用户动态）收集内容
- **🤖 AI 智能打分** — 支持 Claude、GPT-4、Gemini、DeepSeek、豆包（Doubao）及任何 OpenAI 兼容 API，对每条内容评分 0-10，过滤噪声
- **🌐 中英双语日报** — 同时生成英文和中文版本的每日摘要
- **🔍 背景知识补充** — 自动搜索网络，为新闻中的陌生概念提供解释，降低阅读门槛
- **💬 社区声音** — 收集并汇总来自 HackerNews、Reddit 等评论区的社区讨论
- **🔗 跨源去重** — 自动合并来自不同平台的重复内容
- **📰 静态站点生成** — 通过 GitHub Actions 部署为 GitHub Pages 站点，定时自动更新
- **⚙️ 高度可定制** — 单个 JSON 配置文件，轻松自定义信息源、过滤阈值和 AI 模型

## 工作原理

```
              ┌──────────┐
              │ Hacker   │
┌─────────┐   │ News     │   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  RSS    │──▶│ Reddit   │──▶│ AI Score │──▶│ Enrich   │──▶│ Summary  │
│ Telegram│   │ GitHub   │   │ & Filter │   │ & Search │   │ & Deploy │
└─────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
  Fetch from      Merge &        Score          Web search     Generate
  all sources    deduplicate     0-10 each      background     Markdown &
                                & filter        knowledge      deploy site
```

1. **抓取** — 并发拉取所有已配置信息源的最新内容
2. **去重** — 合并来自不同平台的相同 URL 内容
3. **打分** — AI 根据技术深度、新颖性和影响力对每条内容评分 0-10
4. **过滤** — 仅保留超过设定阈值的内容（默认：6.0）
5. **丰富** — 对高分内容搜索网络获取背景知识，收集社区讨论
6. **总结** — 生成结构化的 Markdown 报告，包含摘要、标签和参考链接
7. **部署** — 可选发布至 GitHub Pages，作为每日更新的静态站点

## 快速开始

### 1. 安装

```bash
git clone https://github.com/Thysrael/Horizon.git
cd horizon

# 使用 uv 安装（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 2. 配置

```bash
cp .env.example .env          # 添加 API 密钥
cp data/config.example.json data/config.json  # 自定义信息源
```

配置文件示例：

```jsonc
{
  "ai": {
    "provider": "doubao",       // 支持 "openai", "anthropic", "gemini", "doubao"
    "model": "doubao-1-5-pro-256k",
    "api_key_env": "DOUBAO_API_KEY",
    "languages": ["en", "zh"]   // 中英双语输出
  },
  "sources": {
    "hackernews": { "enabled": true, "fetch_top_stories": 20, "min_score": 100 },
    "rss": [
      { "name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/" }
    ],
    "reddit": {
      "subreddits": [{ "subreddit": "MachineLearning", "sort": "hot" }],
      "fetch_comments": 5
    },
    "telegram": {
      "channels": [{ "channel": "zaihuapd", "fetch_limit": 20 }]
    }
  },
  "filtering": {
    "ai_score_threshold": 6.0,
    "time_window_hours": 24
  }
}
```

完整配置参考请查看[配置指南](docs/configuration.md)。

### 3. 运行

```bash
uv run horizon              # 使用默认 24 小时窗口
uv run horizon --hours 48   # 抓取最近 48 小时的内容
```

生成的日报将保存在 `data/summaries/` 目录中。

### 4. 自动化（可选）

Horizon 非常适合作为 **GitHub Actions** 定时任务运行。查看 [`.github/workflows/daily-summary.yml`](.github/workflows/daily-summary.yml) 获取现成的工作流配置，可自动生成日报并部署到 GitHub Pages。

## 支持的信息源

| 信息源 | 抓取内容 | 评论收集 |
|--------|---------|---------|
| **Hacker News** | 按分数排序的热门文章 | 支持（前 N 条评论） |
| **RSS / Atom** | 任意 RSS 或 Atom 订阅源 | — |
| **Reddit** | Subreddit 帖子 + 用户动态 | 支持（前 N 条评论） |
| **Telegram** | 公开频道消息 | — |
| **GitHub** | 用户动态 & 仓库 Release | — |

## 路线图

- [x] 多源聚合（HN、RSS、Reddit、Telegram、GitHub）
- [x] 多 AI 模型打分（Claude、GPT-4、Gemini、DeepSeek、豆包）
- [x] 中英双语日报生成
- [x] 网络搜索补充背景知识
- [x] 社区讨论收集
- [x] GitHub Pages 部署
- [ ] 邮件 / Slack / Webhook 通知
- [x] Web UI 仪表板
- [ ] 更多信息源（Twitter/X、Discord 等）
- [ ] 按信息源自定义打分 Prompt

## 贡献

欢迎贡献！请随时提交 Issue 或 Pull Request。

## 许可证

[MIT](LICENSE)
