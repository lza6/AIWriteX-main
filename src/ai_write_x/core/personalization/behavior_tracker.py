"""
AIWriteX V19.0 - Behavior Tracker Module
行为追踪模块 - 用户行为数据采集与分析

功能:
1. 事件追踪: 记录用户交互事件
2. 行为分析: 分析用户行为模式
3. 漏斗分析: 追踪用户转化路径
4. 热力图: 记录用户点击分布
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from uuid import uuid4
from collections import defaultdict, deque
import numpy as np


class EventType(Enum):
    """事件类型"""
    PAGE_VIEW = "page_view"             # 页面浏览
    CLICK = "click"                     # 点击
    SCROLL = "scroll"                   # 滚动
    SEARCH = "search"                   # 搜索
    GENERATE = "generate"               # 生成内容
    EDIT = "edit"                       # 编辑
    PUBLISH = "publish"                 # 发布
    SHARE = "share"                     # 分享
    FEEDBACK = "feedback"               # 反馈
    EXPORT = "export"                   # 导出
    IMPORT = "import"                   # 导入
    SETTING_CHANGE = "setting_change"   # 设置变更


@dataclass
class BehaviorEvent:
    """行为事件"""
    id: str
    user_id: str
    event_type: EventType
    timestamp: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    page_url: str = ""
    referrer: str = ""
    device_info: Dict[str, str] = field(default_factory=dict)


class BehaviorTracker:
    """
    行为追踪器
    
    追踪和分析用户行为
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.events: deque = deque(maxlen=10000)  # 限制事件数量
        self.sessions: Dict[str, Dict] = {}
        self.event_counts: Dict[EventType, int] = defaultdict(int)
        self.hourly_stats: Dict[int, int] = defaultdict(int)
        
    def track(
        self,
        user_id: str,
        event_type: EventType,
        properties: Dict = None,
        page_url: str = "",
        session_id: str = ""
    ) -> BehaviorEvent:
        """追踪事件"""
        event = BehaviorEvent(
            id=str(uuid4()),
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.now(),
            properties=properties or {},
            session_id=session_id or self._get_session_id(user_id),
            page_url=page_url
        )
        
        self.events.append(event)
        self.event_counts[event_type] += 1
        self.hourly_stats[datetime.now().hour] += 1
        
        # 更新会话
        self._update_session(event)
        
        return event
    
    def _get_session_id(self, user_id: str) -> str:
        """获取或创建会话ID"""
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "session_id": str(uuid4()),
                "start_time": datetime.now(),
                "events": []
            }
        return self.sessions[user_id]["session_id"]
    
    def _update_session(self, event: BehaviorEvent):
        """更新会话数据"""
        if event.user_id in self.sessions:
            self.sessions[event.user_id]["events"].append(event.id)
            self.sessions[event.user_id]["last_activity"] = event.timestamp
    
    def get_user_events(
        self,
        user_id: str,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[BehaviorEvent]:
        """获取用户事件"""
        filtered = []
        
        for event in reversed(self.events):  # 从新到旧
            if event.user_id != user_id:
                continue
            
            if event_type and event.event_type != event_type:
                continue
            
            if start_time and event.timestamp < start_time:
                continue
            
            if end_time and event.timestamp > end_time:
                continue
            
            filtered.append(event)
            
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def get_event_funnel(
        self,
        steps: List[EventType],
        user_id: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """
        获取事件漏斗
        
        Args:
            steps: 漏斗步骤（事件类型列表）
            user_id: 指定用户（None则为所有用户）
            days: 时间范围
            
        Returns:
            漏斗分析结果
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        # 统计每个步骤的用户数
        step_counts = []
        for step in steps:
            if user_id:
                count = len(set(
                    e.user_id for e in self.events
                    if e.event_type == step 
                    and e.user_id == user_id
                    and e.timestamp > cutoff
                ))
            else:
                count = len(set(
                    e.user_id for e in self.events
                    if e.event_type == step 
                    and e.timestamp > cutoff
                ))
            step_counts.append(count)
        
        # 计算转化率
        conversion_rates = []
        for i in range(1, len(step_counts)):
            if step_counts[i-1] > 0:
                rate = step_counts[i] / step_counts[i-1]
            else:
                rate = 0.0
            conversion_rates.append(rate)
        
        return {
            "steps": [s.value for s in steps],
            "counts": step_counts,
            "conversion_rates": conversion_rates,
            "overall_conversion": step_counts[-1] / step_counts[0] if step_counts[0] > 0 else 0
        }
    
    def get_user_journey(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> List[Dict]:
        """获取用户旅程"""
        events = self.get_user_events(user_id, limit=1000)
        
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "event": e.event_type.value,
                "properties": e.properties,
                "page": e.page_url
            }
            for e in sorted(events, key=lambda x: x.timestamp)
        ]
    
    def analyze_behavior_patterns(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """分析用户行为模式"""
        cutoff = datetime.now() - timedelta(days=days)
        events = self.get_user_events(user_id, start_time=cutoff, limit=10000)
        
        if not events:
            return {}
        
        # 事件类型分布
        type_distribution = defaultdict(int)
        hourly_distribution = defaultdict(int)
        daily_counts = defaultdict(int)
        
        for event in events:
            type_distribution[event.event_type.value] += 1
            hourly_distribution[event.timestamp.hour] += 1
            daily_counts[event.timestamp.date().isoformat()] += 1
        
        # 活跃时段
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0]
        
        # 使用频率
        active_days = len(daily_counts)
        avg_daily_events = len(events) / max(active_days, 1)
        
        return {
            "total_events": len(events),
            "active_days": active_days,
            "avg_daily_events": round(avg_daily_events, 2),
            "peak_hour": peak_hour,
            "event_distribution": dict(type_distribution),
            "hourly_pattern": dict(hourly_distribution),
            "favorite_features": sorted(
                type_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def get_active_users(
        self,
        days: int = 7,
        min_events: int = 1
    ) -> List[str]:
        """获取活跃用户"""
        cutoff = datetime.now() - timedelta(days=days)
        
        user_event_counts = defaultdict(int)
        for event in self.events:
            if event.timestamp > cutoff:
                user_event_counts[event.user_id] += 1
        
        return [
            uid for uid, count in user_event_counts.items()
            if count >= min_events
        ]
    
    def get_retention(
        self,
        cohort_days: int = 7,
        retention_days: List[int] = [1, 3, 7, 14, 30]
    ) -> Dict:
        """
        计算留存率
        
        Returns:
            {第N天: 留存率, ...}
        """
        # 获取起始用户群
        cohort_start = datetime.now() - timedelta(days=cohort_days)
        cohort_end = cohort_start + timedelta(days=1)
        
        cohort_users = set()
        for event in self.events:
            if cohort_start <= event.timestamp < cohort_end:
                cohort_users.add(event.user_id)
        
        if not cohort_users:
            return {}
        
        # 计算各天留存
        retention = {}
        for day in retention_days:
            check_date = cohort_start + timedelta(days=day)
            active_users = set()
            
            for event in self.events:
                if event.timestamp.date() == check_date.date():
                    active_users.add(event.user_id)
            
            retained = len(cohort_users & active_users)
            retention[f"day_{day}"] = retained / len(cohort_users)
        
        return retention
    
    def export_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """导出事件数据"""
        filtered = []
        
        for event in self.events:
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            filtered.append({
                "id": event.id,
                "user_id": event.user_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "properties": event.properties,
                "session_id": event.session_id,
                "page_url": event.page_url
            })
        
        return filtered
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_events": len(self.events),
            "unique_users": len(set(e.user_id for e in self.events)),
            "active_sessions": len(self.sessions),
            "event_distribution": dict(self.event_counts),
            "hourly_distribution": dict(self.hourly_stats)
        }


# 全局行为追踪器实例
behavior_tracker = BehaviorTracker()


def get_behavior_tracker() -> BehaviorTracker:
    """获取行为追踪器实例"""
    return behavior_tracker
