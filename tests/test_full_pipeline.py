#!/usr/bin/env python3
"""测试完整的内容生成和模板渲染流程"""
import sys
sys.path.insert(0, 'src')

from ai_write_x.core.dynamic_template_generator import DynamicTemplateGenerator

# 模拟AI生成的内容（带Markdown格式）
title = '哈梅内伊遇害事件深度分析'
content = '''
# 事件背景

2023年1月，伊朗最高领袖**哈梅内伊**的健康状况引发国际社会广泛关注。多家外媒报道称，现年83岁的哈梅内伊因健康问题暂停公开活动，随后网络传出其"遇害"的传言。

## 传言起源与传播

这一消息迅速在中东地区乃至全球引发震动，但伊朗官方很快出面辟谣，强调哈梅内伊健康状况稳定。

1. **消息源头**：传言最初出现在社交媒体平台，有匿名账号声称哈梅内伊在德黑兰郊外住所遭遇暗杀
2. **传播路径**：
   - 推特上#KhameneiAssassination话题一度登上趋势榜
   - 波斯语社交媒体出现大量讨论
   - 部分反伊朗政府组织宣称对事件负责
3. **官方回应**：伊朗新闻电视台(Press TV)在传言出现后6小时内发布哈梅内伊接见官员的视频

## 国际反应

### 地区国家态度
- **沙特阿拉伯**：未发表官方声明
- **以色列**：国防部长表示"不评论伊朗内部事务"
- **土耳其**：外交部呼吁各方保持克制

### 大国立场
- **美国**：白宫发言人表示"无法证实相关报道"
- **俄罗斯**：克里姆林宫称"相信伊朗能维护稳定"
- **中国**：外交部发言人表示"希望伊朗保持和平稳定"

> "此类传言反映伊朗面临的内部压力，但现行体制有完善的权力交接机制。"
> —— 中东问题专家张教授

## 结语

尽管"哈梅内伊遇害"传言最终被证实为谣言，但事件折射出伊朗政治生态的敏感性和复杂性。
'''

# 使用动态模板生成器生成完整HTML
generator = DynamicTemplateGenerator()
html = generator.generate_template_with_content(title, content, '新闻时事')

# 保存到文件
with open('test_full_article.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('✅ 完整文章生成成功！已保存到 test_full_article.html')
print(f'📄 文件大小: {len(html):,} 字符')

# 检查关键元素是否存在
checks = [
    ('<h1>事件背景</h1>' in html, '一级标题'),
    ('<h2>传言起源与传播</h2>' in html, '二级标题'),
    ('<strong>哈梅内伊</strong>' in html, '加粗文本'),
    ('<blockquote>' in html, '引用块'),
    ('<ol>' in html, '有序列表'),
    ('<ul>' in html, '无序列表'),
    ('glass-card' in html, '玻璃卡片样式'),
    ('reading-progress' in html, '阅读进度条'),
]

print('\n📋 格式检查:')
for passed, name in checks:
    status = '✅' if passed else '❌'
    print(f'  {status} {name}')
