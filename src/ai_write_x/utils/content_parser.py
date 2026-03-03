import re
import time
from typing import Dict, Any, List
from dataclasses import dataclass
from bs4 import BeautifulSoup


@dataclass
class ParsedContent:
    """解析后的内容结构"""

    title: str
    content: str
    summary: str
    confidence: float
    sections: List[Dict[str, str]]
    metadata: Dict[str, Any]


class ContentParser:
    """内容解析器，支持多种格式的内容解析和结构化"""

    def __init__(self):
        self.title_patterns = [
            r"^#\s+(.+)$",  # Markdown H1
            r"^(.+)\n=+$",  # 下划线标题
            r"^(.+)\n-+$",  # 短划线标题
            r"<h1[^>]*>(.+?)</h1>",  # HTML H1
            r"<title[^>]*>(.+?)</title>",  # HTML title
        ]

        self.section_patterns = [
            r"^#{2,6}\s+(.+)$",  # Markdown headers
            r"<h[2-6][^>]*>(.+?)</h[2-6]>",  # HTML headers
        ]

    def parse(self, raw_content: str) -> ParsedContent:
        """解析原始内容为结构化格式"""
        if not raw_content or not raw_content.strip():
            return self._create_empty_result()

        # 清理内容
        cleaned_content = self._clean_content(raw_content)

        # 检测内容格式
        content_type = self._detect_content_type(cleaned_content)

        # 根据格式选择解析策略
        if content_type == "html":
            return self._parse_html_content(cleaned_content)
        elif content_type == "markdown":
            return self._parse_markdown_content(cleaned_content)
        else:
            return self._parse_plain_text(cleaned_content)

    def _clean_content(self, content: str) -> str:
        """清理内容，移除多余的空白和特殊字符"""
        # 移除多余的空行
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        # 移除行首行尾空白
        lines = [line.strip() for line in content.split("\n")]
        content = "\n".join(lines)

        # 移除特殊控制字符
        content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", content)

        return content.strip()

    def _detect_content_type(self, content: str) -> str:
        """检测内容类型"""
        # HTML检测
        if re.search(r"<[^>]+>", content):
            return "html"

        # Markdown检测
        markdown_indicators = [
            r"^#+\s",  # Headers
            r"^\*\*.*\*\*",  # Bold
            r"^\*.*\*",  # Italic
            r"^\-\s",  # Lists
            r"^\d+\.\s",  # Numbered lists
            r"```",  # Code blocks
        ]

        for pattern in markdown_indicators:
            if re.search(pattern, content, re.MULTILINE):
                return "markdown"

        return "plain"

    def _parse_html_content(self, content: str) -> ParsedContent:
        """解析HTML内容"""
        soup = BeautifulSoup(content, "html.parser")

        # 提取标题
        title = self._extract_html_title(soup)

        # 提取正文
        main_content = self._extract_html_main_content(soup)

        # 提取章节
        sections = self._extract_html_sections(soup)

        # 生成摘要
        summary = self._generate_summary(main_content)

        # 计算置信度
        confidence = self._calculate_html_confidence(soup, title, main_content)

        return ParsedContent(
            title=title,
            content=main_content,
            summary=summary,
            confidence=confidence,
            sections=sections,
            metadata={
                "content_type": "html",
                "parsed_at": time.time(),
                "section_count": len(sections),
                "word_count": len(main_content.split()),
            },
        )

    def _parse_markdown_content(self, content: str) -> ParsedContent:
        """解析Markdown内容"""
        lines = content.split("\n")

        # 提取标题
        title = self._extract_markdown_title(lines)

        # 提取正文（移除标题行）
        content_lines = self._remove_title_from_lines(lines, title)
        main_content = "\n".join(content_lines).strip()

        # 提取章节
        sections = self._extract_markdown_sections(lines)

        # 生成摘要
        summary = self._generate_summary(main_content)

        # 计算置信度
        confidence = self._calculate_markdown_confidence(lines, title, main_content)

        return ParsedContent(
            title=title,
            content=main_content,
            summary=summary,
            confidence=confidence,
            sections=sections,
            metadata={
                "content_type": "markdown",
                "parsed_at": time.time(),
                "section_count": len(sections),
                "word_count": len(main_content.split()),
            },
        )

    def _parse_plain_text(self, content: str) -> ParsedContent:
        """解析纯文本内容"""
        lines = content.split("\n")

        # 尝试从第一行提取标题
        title = self._extract_plain_title(lines)

        # 正文处理
        if title and lines and lines[0].strip() == title:
            main_content = "\n".join(lines[1:]).strip()
        else:
            main_content = content

        # 简单的段落分割作为章节
        sections = self._extract_plain_sections(main_content)

        # 生成摘要
        summary = self._generate_summary(main_content)

        # 计算置信度
        confidence = self._calculate_plain_confidence(content, title, main_content)

        return ParsedContent(
            title=title,
            content=main_content,
            summary=summary,
            confidence=confidence,
            sections=sections,
            metadata={
                "content_type": "plain",
                "parsed_at": time.time(),
                "section_count": len(sections),
                "word_count": len(main_content.split()),
            },
        )

    def _extract_html_title(self, soup: BeautifulSoup) -> str:
        """从HTML中提取标题"""
        # 优先级：h1 > title > meta title
        selectors = ["h1", "title", 'meta[property="og:title"]', 'meta[name="title"]']

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == "meta":
                    title = elem.get("content", "").strip()  # type: ignore
                else:
                    title = elem.get_text().strip()

                if title and len(title) > 3 and len(title) < 200:
                    return self._clean_title(title)

        return "Untitled"

    def _extract_markdown_title(self, lines: List[str]) -> str:
        """从Markdown中提取标题"""
        for line in lines[:5]:  # 只检查前5行
            line = line.strip()
            if not line:
                continue

            # H1 标题
            if line.startswith("# "):
                return self._clean_title(line[2:].strip())

            # 检查下一行是否为下划线标题
            idx = lines.index(line)
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].strip()
                if re.match(r"^=+$", next_line) and len(line) > 3:
                    return self._clean_title(line)

        return "Untitled"

    def _extract_plain_title(self, lines: List[str]) -> str:
        """从纯文本中提取标题"""
        for line in lines[:3]:  # 只检查前3行
            line = line.strip()
            if line and len(line) > 3 and len(line) < 100:
                # 简单启发式：短行且不包含句号可能是标题
                if "。" not in line and "." not in line[-5:]:
                    return self._clean_title(line)

        return "Untitled"

    def _clean_title(self, title: str) -> str:
        """清理标题"""
        # 移除HTML标签
        title = re.sub(r"<[^>]+>", "", title)

        # 移除多余空白
        title = re.sub(r"\s+", " ", title).strip()

        # 移除特殊字符
        title = re.sub(r"[^\w\s\u4e00-\u9fff\-_()（）]", "", title)

        return title[:100]  # 限制长度

    def _generate_summary(self, content: str) -> str:
        """生成内容摘要"""
        if not content:
            return ""

        # 移除Markdown格式
        clean_content = re.sub(r"[#*`_\[\]()]", "", content)

        # 分句
        sentences = re.split(r"[。！？.!?]", clean_content)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

        # 取前2-3句作为摘要
        summary_sentences = sentences[:3]
        summary = "。".join(summary_sentences)

        # 限制长度
        if len(summary) > 200:
            summary = summary[:200] + "..."

        return summary

    def _extract_html_sections(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """提取HTML章节"""
        sections = []
        headers = soup.find_all(["h2", "h3", "h4", "h5", "h6"])

        for header in headers:
            section_title = header.get_text().strip()
            section_content = ""

            # 获取标题后的内容直到下一个同级或更高级标题
            current = header.next_sibling
            while current:
                if hasattr(current, "name") and current.name in [  # type: ignore
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                ]:
                    break
                if hasattr(current, "get_text"):
                    section_content += current.get_text()
                current = current.next_sibling

            if section_title:
                sections.append(
                    {
                        "title": section_title,
                        "content": section_content.strip()[:500],  # 限制长度
                        "level": int(header.name[1]),  # type: ignore
                    }
                )

        return sections

    def _extract_markdown_sections(self, lines: List[str]) -> List[Dict[str, str]]:
        """提取Markdown章节"""
        sections = []
        current_section = None

        for line in lines:
            line = line.strip()

            # 检测标题
            header_match = re.match(r"^(#{2,6})\s+(.+)$", line)
            if header_match:
                # 保存前一个章节
                if current_section:
                    sections.append(current_section)

                # 开始新章节
                level = len(header_match.group(1))
                title = header_match.group(2)
                current_section = {"title": title, "content": "", "level": level}
            elif current_section and line:
                # 添加内容到当前章节
                current_section["content"] += line + "\n"

        # 添加最后一个章节
        if current_section:
            current_section["content"] = current_section["content"].strip()[:500]
            sections.append(current_section)

        return sections

    def _extract_plain_sections(self, content: str) -> List[Dict[str, str]]:
        """提取纯文本章节（基于段落）"""
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        sections = []

        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) > 50:  # 只处理较长的段落
                # 使用段落的前20个字符作为标题
                title = paragraph[:20] + "..." if len(paragraph) > 20 else paragraph
                sections.append({"title": title, "content": paragraph[:500], "level": 1})

        return sections

    def _calculate_html_confidence(self, soup: BeautifulSoup, title: str, content: str) -> float:
        """计算HTML解析置信度"""
        confidence = 0.5  # 基础分数

        # 有明确的HTML结构
        if soup.find(["h1", "h2", "h3", "title"]):
            confidence += 0.2

        # 有合理的标题
        if title and title != "Untitled" and len(title) > 5:
            confidence += 0.2

        # 有足够的内容
        if len(content) > 100:
            confidence += 0.1

        return min(confidence, 1.0)

    def _calculate_markdown_confidence(self, lines: List[str], title: str, content: str) -> float:
        """计算Markdown解析置信度"""
        confidence = 0.5  # 基础分数

        # 检查Markdown特征
        markdown_features = 0

        # 检查标题格式
        for line in lines[:5]:
            if re.match(r"^#+\s", line.strip()):
                markdown_features += 1
                break

        # 检查列表格式
        for line in lines:
            if re.match(r"^\s*[-*+]\s", line) or re.match(r"^\s*\d+\.\s", line):
                markdown_features += 1
                break

        # 检查强调格式
        content_str = "\n".join(lines)
        if re.search(r"\*\*.*?\*\*", content_str) or re.search(r"__.*?__", content_str):
            markdown_features += 1

        # 检查代码块
        if "```" in content_str or re.search(r"`[^`]+`", content_str):
            markdown_features += 1

        # 检查链接格式
        if re.search(r"\[.*?\]\(.*?\)", content_str):
            markdown_features += 1

        # 根据Markdown特征调整置信度
        confidence += min(markdown_features * 0.1, 0.3)

        # 有合理的标题
        if title and title != "Untitled" and len(title) > 5:
            confidence += 0.1

        # 有足够的内容
        if len(content) > 100:
            confidence += 0.1

        return min(confidence, 1.0)

    def _calculate_plain_confidence(self, content: str, title: str, main_content: str) -> float:
        """计算纯文本解析置信度"""
        confidence = 0.3  # 基础分数较低，因为纯文本信息较少

        # 有合理的标题
        if title and title != "Untitled" and len(title) > 5:
            confidence += 0.2

        # 有足够的内容
        if len(main_content) > 100:
            confidence += 0.2

        # 内容结构良好（有段落分割）
        paragraphs = [p.strip() for p in main_content.split("\n\n") if p.strip()]
        if len(paragraphs) > 2:
            confidence += 0.2

        # 内容长度合理
        if 500 <= len(main_content) <= 10000:
            confidence += 0.1

        return min(confidence, 1.0)

    def _remove_title_from_lines(self, lines: List[str], title: str) -> List[str]:
        """从行列表中移除标题行"""
        if not title or title == "Untitled":
            return lines

        result_lines = []
        title_removed = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # 跳过标题行
            if not title_removed:
                # H1 格式标题
                if line_stripped == f"# {title}":
                    title_removed = True
                    continue

                # 普通标题 + 下划线
                if line_stripped == title and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r"^=+$", next_line):
                        title_removed = True
                        continue

                # 下划线行
                if title_removed and re.match(r"^=+$", line_stripped):
                    continue

            result_lines.append(line)

        return result_lines

    def _extract_html_main_content(self, soup: BeautifulSoup) -> str:
        """从HTML中提取主要内容"""
        # 移除脚本和样式标签
        for script in soup(["script", "style"]):
            script.decompose()

        # 尝试多种内容选择器
        content_selectors = [
            "#js_content",  # 微信公众号
            "article",
            ".content",
            ".article-content",
            "main",
            ".post-content",
            ".entry-content",
            ".markdown-body",  # GitHub风格
            ".document",
            "[class*='article']",
            "[class*='content']",
        ]

        for selector in content_selectors:
            try:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text().strip()
                    if len(content) > 100:  # 确保有足够内容
                        return content
            except Exception:
                continue  # 忽略选择器错误，继续尝试下一个

        # 如果没有找到特定容器，返回body内容
        body = soup.find("body")
        if body:
            return body.get_text().strip()

        # 最后返回全部文本
        return soup.get_text().strip()

    def _create_empty_result(self) -> ParsedContent:
        """创建空的解析结果"""
        return ParsedContent(
            title="Untitled",
            content="",
            summary="",
            confidence=0.0,
            sections=[],
            metadata={
                "content_type": "empty",
                "parsed_at": time.time(),
                "section_count": 0,
                "word_count": 0,
            },
        )
