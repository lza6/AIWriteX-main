#!/usr/bin/env python3
"""测试AI动态模板生成"""
import sys
import asyncio
sys.path.insert(0, 'src')

# 先加载配置
from ai_write_x.config.config import Config
config = Config.get_instance()
config.load_config()  # 显式加载配置

from ai_write_x.agents.ai_template_designer import AITemplateDesigner

# 测试内容
title = '测试AI动态模板生成'
content = '''
# 这是一个测试文章

**重点词**需要高亮显示。

## 人物介绍

**张三**是一位著名的科学家，他在**2024年**获得了诺贝尔奖。

1. 第一项成就
2. 第二项成就
3. 第三项成就

> 这是一段引用文字

## 结语

感谢阅读！
'''

async def test_ai_template():
    """测试AI模板生成"""
    designer = AITemplateDesigner()
    
    print("🎨 正在使用AI生成独特模板...")
    print(f"标题: {title}")
    print()
    
    # 生成模板
    html = await designer.generate_unique_template(
        title=title,
        content=content,
        topic='科技',
        keywords=['AI', '模板', '设计']
    )
    
    # 保存到文件
    with open('test_ai_generated.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ AI模板生成成功！已保存到 test_ai_generated.html")
    print(f"📄 文件大小: {len(html):,} 字符")
    
    # 检查关键元素
    checks = [
        ('<!DOCTYPE' in html or '<html' in html, '完整HTML结构'),
        ('{{content}}' in html or '{content}' in html, '内容占位符'),
        ('<style' in html or 'style=' in html, 'CSS样式'),
        ('<h1' in html or '<h2' in html, '标题标签'),
        ('strong' in html or 'font-weight' in html, '加粗样式'),
    ]
    
    print('\n📋 格式检查:')
    for passed, name in checks:
        status = '✅' if passed else '❌'
        print(f'  {status} {name}')

if __name__ == '__main__':
    asyncio.run(test_ai_template())
