# 🔐 Secrets — 密钥安全存储目录

> **⚠️ 重要：此目录下的 `api_keys.yaml` 文件已被 `.gitignore` 保护，不会上传至 GitHub。**

## 用途

所有 API 密钥、Token、微信公众号 appid/appsecret 等敏感信息，统一存放在本目录的 `api_keys.yaml` 中。  
程序启动时会自动从此文件读取密钥并合并到运行时配置。

## 使用方法

1. 复制 `api_keys.example.yaml` 为 `api_keys.yaml`
2. 在 `api_keys.yaml` 中填入你的真实密钥
3. **绝对不要**将 `api_keys.yaml` 提交到 Git

## 文件说明

| 文件 | 说明 | Git 跟踪 |
|:---|:---|:---|
| `README.md` | 本说明文件 | ✅ 跟踪 |
| `api_keys.example.yaml` | 密钥模板（占位符） | ✅ 跟踪 |
| `api_keys.yaml` | **你的真实密钥** | ❌ 已忽略 |

## 格式示例

```yaml
# 微信公众号
wechat:
  credentials:
    - appid: "你的appid"
      appsecret: "你的appsecret"

# LLM API 密钥
api:
  心流:
    api_key:
      - "sk-你的密钥"
  Deepseek:
    api_key:
      - "sk-你的密钥"

# 图片生成 API
img_api:
  ali:
    api_key: "你的阿里密钥"
  modelscope:
    api_key: "你的魔搭密钥"
```
