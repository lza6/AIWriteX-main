#!/usr/bin/env python3
"""测试模板生成器"""
import sys
sys.path.insert(0, 'src')

from ai_write_x.core.dynamic_template_generator import generate_dynamic_template

# 测试内容
title = '人工智能的最新发展趋势'
content = '''
# 引言
人工智能（AI）正在以惊人的速度发展，改变着我们的生活和工作方式。从自动驾驶汽车到智能助手，AI的应用无处不在。

## 深度学习的新突破
近年来，深度学习技术取得了重大突破。神经网络模型变得越来越复杂，能够处理更复杂的任务。

- **Transformer架构**：革新了自然语言处理领域
- **大语言模型**：如GPT系列，展示了惊人的理解能力
- **多模态AI**：能够同时处理文本、图像和音频

## 未来展望
AI的未来充满了无限可能。我们可以期待：

1. 更智能的个人助手
2. 更精准的医学诊断
3. 更高效的科学研究

> "人工智能是新的电力。" —— 吴恩达

让我们拥抱这个AI驱动的未来！
'''

# 生成模板
html = generate_dynamic_template(title, content, '科技')

# 保存到文件
with open('test_template.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('✅ 模板生成成功！已保存到 test_template.html')
print(f'📄 文件大小: {len(html):,} 字符')
