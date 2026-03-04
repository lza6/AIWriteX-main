# -*- coding: UTF-8 -*-
"""
爬虫数据管理器 - 使用 JSON 文件存储
"""
import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import shutil


class SpiderDataManager:
    """简化版爬虫数据管理器，使用 JSON 文件存储"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "spider")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "articles.json"
        self.failed_file = self.data_dir / "failed.json"
        self.settings_file = self.data_dir / "settings.json"
        
        # 文章存储根目录
        self.articles_root = self.data_dir / "articles"
        self.articles_root.mkdir(parents=True, exist_ok=True)

    def _load_articles(self) -> List[Dict]:
        """加载文章列表"""
        if not self.data_file.exists():
            return []
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def _save_articles(self, articles: List[Dict]):
        """保存文章列表"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
    
    def _load_failed(self) -> List[Dict]:
        """加载失败记录"""
        if not self.failed_file.exists():
            return []
        try:
            with open(self.failed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_failed(self, failed_list: List[Dict]):
        """保存失败记录"""
        with open(self.failed_file, 'w', encoding='utf-8') as f:
            json.dump(failed_list, f, ensure_ascii=False, indent=2)
    
    def _load_settings(self) -> Dict:
        """加载设置"""
        if not self.settings_file.exists():
            return {
                "auto_delete_enabled": False,
                "auto_delete_days": 7
            }
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {
                "auto_delete_enabled": False,
                "auto_delete_days": 7
            }
    
    def _save_settings(self, settings: Dict):
        """保存设置"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    def _sanitize_filename(self, title: str, max_length: int = 50) -> str:
        """清理文件名，去除非法字符，截断长度"""
        # 去除非法文件名字符
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        # 去除多余空格
        filename = re.sub(r'\s+', '_', filename)
        # 截断长度
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename

    def _save_article_to_file(self, article_data: Dict) -> str:
        """保存文章内容到文件，按日期分类"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 创建日期文件夹
        date_folder = self.articles_root / today
        date_folder.mkdir(parents=True, exist_ok=True)
        
        # 获取标题作为文件名
        title = article_data.get('title', '无标题')
        filename = self._sanitize_filename(title)
        
        # 确保文件名唯一
        file_path = date_folder / f"{filename}.txt"
        counter = 1
        while file_path.exists():
            file_path = date_folder / f"{filename}_{counter}.txt"
            counter += 1
        
        # 写入内容
        content = article_data.get('content', '')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)

    def save_article(self, article_data: Dict) -> bool:
        """保存单篇文章 (包含敏感词过滤)"""
        # 敏感词黑名单 (过滤国家领导人及大政方针相关热点)
        sensitive_keywords = ["总书记", "习近平", "主席", "国家大政方针", "李强", "总理", "中共中央"]
        title = article_data.get('title', '')
        
        for keyword in sensitive_keywords:
            if keyword in title:
                # 命中敏感词，丢弃该文章
                print(f"[拦截] 过滤包含敏感词的热点新闻: {title}")
                return False

        articles = self._load_articles()
        
        # 检查是否已存在
        for article in articles:
            if article.get('article_url') == article_data.get('article_url'):
                return False  # 已存在
        
        # 生成唯一 ID（使用时间戳）
        article_data['id'] = int(datetime.now().timestamp() * 1000)
        article_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        article_data['save_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # 保存到文件
        file_path = self._save_article_to_file(article_data)
        article_data['file_path'] = file_path
        
        articles.append(article_data)
        self._save_articles(articles)
        return True
    
    def add_failed(self, url: str, error: str, spider_name: str = ""):
        """添加失败记录"""
        failed_list = self._load_failed()
        
        # 检查是否已存在
        for item in failed_list:
            if item.get('url') == url:
                return  # 已存在
        
        failed_item = {
            "url": url,
            "error": error,
            "spider": spider_name,
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        failed_list.append(failed_item)
        
        # 保留最近100条失败记录
        if len(failed_list) > 100:
            failed_list = failed_list[-100:]
        
        self._save_failed(failed_list)
    
    def get_failed(self) -> List[Dict]:
        """获取失败记录"""
        return self._load_failed()
    
    def clear_failed(self) -> bool:
        """清空失败记录"""
        self._save_failed([])
        return True

    def get_articles(self, limit: int = 100, source: str = None, category: str = None) -> List[Dict]:
        """获取文章列表"""
        articles = self._load_articles()
        need_save = False
        
        # 为旧文章添加 ID（如果缺失）
        for i, article in enumerate(articles):
            if 'id' not in article or not article['id']:
                # 使用时间戳生成唯一 ID，加上索引确保唯一性
                article['id'] = int(datetime.now().timestamp() * 1000) + i
                need_save = True
        
        # 如果有新添加的 ID，保存更新
        if need_save:
            self._save_articles(articles)
        
        # 筛选
        if source:
            articles = [a for a in articles if a.get('source') == source]
        if category:
            articles = [a for a in articles if a.get('category') == category]
        
        # 按时间倒序
        articles.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return articles[:limit]
    
    def get_articles_by_date(self, date: str = None) -> List[Dict]:
        """获取指定日期的文章"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        articles = self._load_articles()
        return [a for a in articles if a.get('save_date') == date]

    def get_sources(self) -> List[str]:
        """获取所有来源"""
        articles = self._load_articles()
        return list(set(a.get('source', '未知') for a in articles))

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        articles = self._load_articles()
        return list(set(a.get('category', '未分类') for a in articles))
    
    def get_article_dates(self) -> List[str]:
        """获取所有文章日期"""
        articles = self._load_articles()
        dates = list(set(a.get('save_date', '') for a in articles))
        dates.sort(reverse=True)
        return dates

    def delete_article(self, article_url: str) -> bool:
        """删除文章"""
        articles = self._load_articles()
        article_to_delete = None
        for article in articles:
            if article.get('article_url') == article_url:
                article_to_delete = article
                break
        
        # 删除文件
        if article_to_delete and article_to_delete.get('file_path'):
            try:
                file_path = Path(article_to_delete['file_path'])
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        
        articles = [a for a in articles if a.get('article_url') != article_url]
        self._save_articles(articles)
        return True
    
    def delete_article_by_id(self, article_id: str) -> bool:
        """通过ID删除文章"""
        articles = self._load_articles()
        article_to_delete = None
        for article in articles:
            if str(article.get('id', '')) == str(article_id):
                article_to_delete = article
                break
        
        if not article_to_delete:
            return False
        
        # 删除文件
        if article_to_delete.get('file_path'):
            try:
                file_path = Path(article_to_delete['file_path'])
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        
        articles = [a for a in articles if str(a.get('id', '')) != str(article_id)]
        self._save_articles(articles)
        return True
    
    def delete_articles_by_date(self, date: str) -> int:
        """删除指定日期的文章"""
        articles = self._load_articles()
        deleted_count = 0
        
        for article in articles[:]:
            if article.get('save_date') == date:
                # 删除文件
                if article.get('file_path'):
                    try:
                        file_path = Path(article['file_path'])
                        if file_path.exists():
                            file_path.unlink()
                    except Exception:
                        pass
                articles.remove(article)
                deleted_count += 1
        
        self._save_articles(articles)
        return deleted_count

    def clear_articles(self) -> bool:
        """清空所有文章"""
        # 删除所有文章文件
        try:
            if self.articles_root.exists():
                shutil.rmtree(self.articles_root)
                self.articles_root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        self._save_articles([])
        return True
    
    def get_total_count(self) -> int:
        """获取文章总数"""
        return len(self._load_articles())
    
    def get_save_path(self) -> str:
        """获取文章保存根目录"""
        return str(self.articles_root)
    
    # 设置相关方法
    def get_settings(self) -> Dict:
        """获取设置"""
        return self._load_settings()
    
    def save_settings(self, settings: Dict) -> bool:
        """保存设置"""
        self._save_settings(settings)
        return True
    
    def set_auto_delete(self, enabled: bool, days: int = 7) -> bool:
        """设置自动删除"""
        settings = self._load_settings()
        settings['auto_delete_enabled'] = enabled
        settings['auto_delete_days'] = days
        self._save_settings(settings)
        return True
    
    def auto_delete_old_articles(self) -> int:
        """自动删除旧文章"""
        settings = self._load_settings()
        if not settings.get('auto_delete_enabled', False):
            return 0
        
        days = settings.get('auto_delete_days', 7)
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        articles = self._load_articles()
        deleted_count = 0
        
        for article in articles[:]:
            if article.get('save_date', '') < cutoff_date:
                # 删除文件
                if article.get('file_path'):
                    try:
                        file_path = Path(article['file_path'])
                        if file_path.exists():
                            file_path.unlink()
                    except Exception:
                        pass
                articles.remove(article)
                deleted_count += 1
        
        self._save_articles(articles)
        return deleted_count


# 全局实例
spider_data_manager = SpiderDataManager()