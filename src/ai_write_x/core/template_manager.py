import os
import glob
from dataclasses import dataclass
from src.ai_write_x.utils.path_manager import PathManager

@dataclass
class TemplateInfo:
    name: str
    category: str
    code: str

class TemplateManager:
    """V23.0: 模板管理中心，用于解耦内容与视觉包装"""
    
    def get_templates_by_platform(self, platform: str):
        """获取适用于特定平台的模板"""
        template_dir = PathManager.get_template_dir()
        templates = []
        
        if not os.path.exists(template_dir):
            return []

        # 常见平台映射到模板文件夹
        platform_keywords = {
            "wechat": ["wechat", "微信", "公众号"],
            "xiaohongshu": ["xiaohongshu", "小红书", "xhs"],
            "zhihu": ["zhihu", "知乎"]
        }
        
        keywords = platform_keywords.get(platform.lower(), [platform.lower()])
        
        for category in os.listdir(template_dir):
            category_path = os.path.join(template_dir, category)
            if not os.path.isdir(category_path):
                continue
            
            # 如果分类名匹配平台关键字，优先选取
            is_match = any(k in category.lower() for k in keywords)
            
            for file in glob.glob(os.path.join(category_path, "*.html")):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        code = f.read()
                        info = TemplateInfo(
                            name=os.path.basename(file),
                            category=category,
                            code=code
                        )
                        if is_match:
                            templates.insert(0, info) # 匹配的排在前面
                        else:
                            templates.append(info)
                except Exception:
                    continue
        
        return templates
