import os
import glob
import random
import sys
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.ai_write_x.utils import utils
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log
from src.ai_write_x.tools import search_template
from src.ai_write_x.utils.path_manager import PathManager


class ReadTemplateToolInput(BaseModel):
    pass


# 1. Read Template Tool
class ReadTemplateTool(BaseTool):
    name: str = "read_template_tool"
    description: str = (
        "从本地读取HTML模板文件，此模板必须作为最终输出的基础结构，保持视觉风格和布局效果，仅替换内容部分"
    )
    args_schema: Type[BaseModel] = ReadTemplateToolInput

    def _run(self) -> str:
        config = Config.get_instance()

        # 获取模板文件的绝对路径
        template_dir_abs = PathManager.get_template_dir()

        # 根据custom_topic是否为空选择配置源
        if config.custom_topic:
            # 使用自定义话题的模板配置
            template_category = config.custom_template_category
            template = config.custom_template
        else:
            # 使用应用配置
            template_category = config.template_category
            template = config.template

        random_template = True
        selected_template_file: str = ""

        # 如果指定了具体模板且存在，则不随机
        if template and template != "":  # 随机模板的条件是""
            template_filename = template if template.endswith(".html") else f"{template}.html"

            # 如果指定了分类，在分类目录下查找
            if template_category and template_category != "":  # 实际上选则了模板，也一定选择了分类
                category_dir = os.path.join(template_dir_abs, template_category)
                selected_template_file = os.path.join(category_dir, template_filename)

            if os.path.exists(path=selected_template_file):
                random_template = False

        # 需要随机选择模板
        if random_template:
            # 排除的目录
            excluded_dirs = {"components", "__pycache__", ".git"}

            # 如果指定了分类且不是随机分类
            if template_category and template_category != "":
                category_dir = os.path.join(template_dir_abs, template_category)
                template_files_abs = glob.glob(os.path.join(category_dir, "*.html"))
            else:
                # 随机分类或未指定分类，从所有分类的模板中选择
                template_files_abs = []
                for category_dir in os.listdir(template_dir_abs):
                    category_path = os.path.join(template_dir_abs, category_dir)
                    if os.path.isdir(category_path) and category_dir not in excluded_dirs:
                        template_files_abs.extend(glob.glob(os.path.join(category_path, "*.html")))

            if not template_files_abs:
                log.print_log(
                    f"在目录 '{template_dir_abs}' 中未找到任何模板文件。如果没有模板请将config.yaml中的use_template设置为false"
                )
                sys.exit(1)

            selected_template_file = random.choice(template_files_abs)

        with open(selected_template_file, "r", encoding="utf-8") as file:
            selected_template_content = file.read()

        template_content = utils.compress_html(
            selected_template_content,
            config.use_compress,
        )

        log.print_log("模板填充适配处理比较耗时，请耐心等待...")
        return f"""
        【HTML模板 - 必须作为最终输出的基础】
        {template_content}

        【模板使用指南】
        1. 上面是完整的HTML模板，您必须基于此模板进行内容适配
        2. 必须保持的元素：
        - 所有<section>的布局结构和内联样式（不要修改颜色、间距等）
        - 原有的视觉层次、色彩方案和排版风格
        - 卡片式布局、圆角和阴影效果
        - SVG动画元素和交互特性
        3. 内容适配规则：
        - 标题替换标题、段落替换段落、列表替换列表
        - 当新内容比原模板内容长或短时，请直接复制并复用原模板中相同级别的带样式的 `<section>` 或 `<p>` 标签，绝不可破坏布局
        - 绝对禁止输出任何 Markdown 标记（例如 `**粗体**`, `*斜体*`, `# 标题`）。必须完全使用 HTML 标签进行排版
        - 若要强调内容，必须使用 HTML的 `<span>` 或 `<strong>`，并参考原模板的配色给其添加合适的内联 `style`
        - 保持图片位置不变
        4. 严格禁止：
        - 不输出任何 Markdown 字符
        - 不添加新的style标签或外部CSS
        - 不改变原有的色彩方案（限制在三种色系内）
        - 不修改模板的整体视觉效果和布局结构
        5. 最终输出必须是基于此模板的一套纯净 HTML 代码，保持相同的视觉效果和样式，但内容已更新

        【重要提示】
        您的任务是将前置任务生成的文章内容严格按照模板骨架克隆构建，而不是创建新的HTML，更不是写 Markdown。
        请仔细观察模板结构中的颜色配比与行高间距，识别内容区域，原汁原味地把新内容完美嵌进去。
        """


# 2. Web Search Tool (替代原AIForge搜索)
class WebSearchToolInput(BaseModel):
    """输入参数模型"""

    topic: str = Field(..., description="要搜索的话题")
    urls: List[str] = Field(default=[], description="参考文章链接数组")
    reference_ratio: float = Field(..., description="参考文章借鉴比例")


class WebSearchTool(BaseTool):
    """网络搜索工具"""

    name: str = "web_search_tool"
    description: str = "搜索关于特定主题的最新信息、数据和趋势。"

    args_schema: type[BaseModel] = WebSearchToolInput

    def _run(self, topic: str, urls: List[str], reference_ratio: float) -> str:
        """执行搜索"""
        results = None
        config = Config.get_instance()
        original_cwd = os.getcwd()

        log.print_log("[PROGRESS:SEARCH:START]", "internal")

        if len(urls) == 0:
            log.print_log("开始执行搜索，请耐心等待...")
            results = self._execute_search(topic)
            source_type = "搜索"
        else:
            log.print_log("开始提取参考链接中的文章信息，请耐心等待...")
            extract_results = search_template.extract_urls_content(urls, topic)
            if search_template.validate_search_result(
                extract_results, min_results=1, search_type="reference_article"
            ):
                results = extract_results.get("results")
            source_type = "参考文章"

        os.chdir(original_cwd)

        try:
            fmt_result = self._formatted_result(topic, urls, reference_ratio, source_type, results)
        except Exception:
            fmt_result = "未找到最新信息"

        log.print_log("[PROGRESS:SEARCH:END]", "internal")
        log.print_log("[PROGRESS:WRITING:START]", "internal")

        return fmt_result

    def _execute_search(self, topic: str):
        """执行网络搜索（使用简单搜索或返回空结果）"""
        try:
            # 尝试使用search_template中的搜索功能
            results = search_template.search_topic(topic)
            if results:
                return results
            return None
        except Exception as e:
            log.print_traceback("搜索过程中发生错误：", e)
            return None

    def _formatted_result(self, topic, urls, reference_ratio, source_type, results):
        """格式化搜索结果，限制内容长度避免 LLM 处理失败"""
        MAX_TOTAL_LENGTH = 8000  # 最大总长度
        MAX_CONTENT_LENGTH = 1500  # 单条内容最大长度
        
        if results:
            # 根据模式过滤掉相应字段为空的条目
            filtered_results = []
            for result in results:
                title = result.get("title", "").strip()

                # 根据模式判断不同的内容字段
                if len(urls) > 0:
                    content_field = result.get("content", "").strip()
                else:
                    content_field = (
                        result.get("abstract", "").strip() or result.get("content", "").strip()
                    )

                if title and content_field:
                    filtered_results.append(result)

            if filtered_results:
                if len(urls) > 0:
                    formatted = (
                        f"关于'{topic}'的{source_type}结果（参考比例：{reference_ratio}）：\n\n"
                    )
                else:
                    formatted = f"关于'{topic}'的{source_type}结果：\n\n"

                for i, result in enumerate(filtered_results, 1):
                    # 检查总长度是否超出限制
                    if len(formatted) >= MAX_TOTAL_LENGTH:
                        formatted += f"\n... 已截断，共 {len(filtered_results)} 条结果\n"
                        break
                    
                    title = result.get("title", "无标题")
                    if len(title) > 80:
                        title = title[:80] + "..."

                    abstract = result.get("abstract", "无摘要")
                    if len(abstract) > 200:
                        abstract = abstract[:200] + "..."

                    formatted += f"## 结果 {i}\n"
                    formatted += f"**标题**: {title}\n"
                    formatted += f"**发布时间**: {result.get('pub_time', '未知时间')}\n"
                    formatted += f"**摘要**: {abstract}\n"

                    if len(urls) > 0 and "content" in result:
                        content = result.get("content", "")
                        # 动态计算剩余可用长度
                        remaining = MAX_TOTAL_LENGTH - len(formatted) - 500
                        content_limit = min(MAX_CONTENT_LENGTH, max(500, remaining))
                        if len(content) > content_limit:
                            content = content[:content_limit] + "..."
                        formatted += f"**内容**: {content}\n"
                    formatted += "\n"
                
                # 最终截断保护
                if len(formatted) > MAX_TOTAL_LENGTH:
                    formatted = formatted[:MAX_TOTAL_LENGTH] + "\n... 内容已截断"
                
                log.print_log(f"搜索结果格式化完成，总长度: {len(formatted)} 字符", "debug")
                return formatted
            else:
                return f"未能找到关于'{topic}'的有效{source_type}结果。"
        else:
            return f"未能找到关于'{topic}'的{source_type}结果。"


# 保持兼容性：AIForgeSearchTool 作为 WebSearchTool 的别名
AIForgeSearchTool = WebSearchTool