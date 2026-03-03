# -*- coding: utf-8 -*-
"""
测试自适应模板引擎
"""

from src.ai_write_x.core.adaptive_template_engine import generate_adaptive_template
from src.ai_write_x.core.dynamic_template_generator import DynamicTemplateGenerator

# 测试内容
test_cases = [
    {
        "title": "哈梅内伊遇袭事件：中东局势的转折点",
        "topic": "新闻时事",
        "content": """# 事件经过

据多家国际媒体报道，当地时间今日，伊朗最高领袖阿亚图拉·阿里·哈梅内伊在首都德黑兰附近遭遇袭击。

## 现场情况

初步调查显示，袭击发生在哈梅内伊参加宗教活动的途中。目击者称听到剧烈爆炸声，随后安保人员与袭击者发生交火。

## 各方反应

- **伊朗国内**：革命卫队进入最高警戒状态
- **国际社会**：联合国秘书长呼吁各方保持克制
- **大国立场**：美国白宫表示密切关注事态发展

## 历史背景

哈梅内伊自1989年起担任伊朗最高领袖，是伊朗政治和宗教体系的最高权威。在其执政期间主导了伊朗核问题谈判。

> "此次事件可能改变中东地区力量平衡，任何误判都可能导致局势失控。"

## 潜在影响

1. 权力交接危机：根据伊朗宪法，专家会议需在最短时间内选出新领袖
2. 地区安全局势：可能引发伊朗对疑似幕后主使的报复行动
3. 能源市场波动：国际油价可能因局势紧张而上涨
4. 核问题走向：伊核协议谈判或将陷入更复杂局面"""
    },
    {
        "title": "AI革命：改变世界的智能新纪元",
        "topic": "科技数码",
        "content": """# 人工智能技术已从实验室走向主流

人工智能正在以前所未有的速度重塑我们的生活、工作和社会结构。

## 大型语言模型的崛起

自从GPT系列模型问世以来，大型语言模型（LLMs）已经成为AI领域最引人注目的突破之一。

这些模型能够：
- 创作文章、诗歌、剧本和其他创意内容
- 协助程序员编写、调试和优化代码
- 与人类进行自然、连贯的对话交流

## 市场规模

2024年，全球AI市场规模已突破5000亿美元，预计到2030年将超过1.5万亿美元。

## 专家观点

> "人工智能是新的电力。它将改变几乎每个行业，创造巨大的经济价值。"

## 未来展望

1. 通用人工智能（AGI）的研究进展
2. AI安全与伦理问题的解决方案
3. 人机协作的新模式探索
4. AI在教育、医疗、科学发现中的应用"""
    }
]

if __name__ == "__main__":
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试案例 {i}: {test['title']}")
        print(f"{'='*60}\n")
        
        # 使用自适应模板引擎
        html = generate_adaptive_template(
            title=test['title'],
            content=test['content'],
            topic=test['topic']
        )
        
        # 保存文件
        output_file = f"test_adaptive_{i}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 模板生成成功！已保存到 {output_file}")
        print(f"📄 文件大小: {len(html):,} 字符")
        
        # 检查包含的组件
        components = []
        if 'hero' in html.lower() or '英雄区' in html:
            components.append("Hero")
        if 'intro-card' in html.lower() or '导语' in html:
            components.append("导语卡片")
        if 'quote' in html.lower() or '引用' in html:
            components.append("引用卡片")
        if 'feature' in html.lower() or '特性列表' in html:
            components.append("特性列表")
        if 'timeline' in html.lower() or '时间线' in html:
            components.append("时间线")
        if 'gradient' in html.lower():
            components.append("渐变效果")
        if 'shadow' in html.lower():
            components.append("阴影效果")
        
        print(f"🎨 检测到的组件: {', '.join(components) if components else '标准内容区块'}")

    print(f"\n{'='*60}")
    print("所有测试完成！")
    print(f"{'='*60}")
