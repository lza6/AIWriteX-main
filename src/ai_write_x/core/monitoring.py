import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import threading


@dataclass
class ExecutionLog:
    workflow_name: str
    timestamp: datetime
    duration: float
    success: bool
    input_data: Dict[str, Any]
    error_message: Optional[str] = None


@dataclass
class WorkflowMetrics:
    count: int = 0
    success_rate: float = 0.0
    avg_duration: float = 0.0
    total_duration: float = 0.0
    last_execution: Optional[datetime] = None


class WorkflowMonitor:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.metrics: Dict[str, WorkflowMetrics] = {}
        self.logs: List[ExecutionLog] = []
        self.max_logs = 1000  # 最大日志条数

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def track_execution(
        self,
        workflow_name: str,
        duration: float,
        success: bool,
        input_data: Dict[str, Any] | None = None,
    ):
        """记录工作流执行指标"""
        with self._lock:
            if workflow_name not in self.metrics:
                self.metrics[workflow_name] = WorkflowMetrics()

            metrics = self.metrics[workflow_name]
            metrics.count += 1
            metrics.total_duration += duration
            metrics.avg_duration = metrics.total_duration / metrics.count

            # 计算成功率
            if success:
                success_count = metrics.count * metrics.success_rate + 1
            else:
                success_count = metrics.count * metrics.success_rate
            metrics.success_rate = success_count / metrics.count

            metrics.last_execution = datetime.now()

            # 记录详细日志
            log_entry = ExecutionLog(
                workflow_name=workflow_name,
                timestamp=datetime.now(),
                duration=duration,
                success=success,
                input_data=input_data or {},
            )
            self.logs.append(log_entry)

            # 限制日志数量
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs :]  # noqa 501

    def log_error(
        self, workflow_name: str, error_message: str, input_data: Dict[str, Any] | None = None
    ):
        """记录错误日志"""
        with self._lock:
            log_entry = ExecutionLog(
                workflow_name=workflow_name,
                timestamp=datetime.now(),
                duration=0.0,
                success=False,
                input_data=input_data or {},
                error_message=error_message,
            )
            self.logs.append(log_entry)

    def get_metrics(self, workflow_name: str | None = None) -> Dict[str, Any]:
        """获取指标数据"""
        if workflow_name:
            return asdict(self.metrics.get(workflow_name, WorkflowMetrics()))
        return {name: asdict(metrics) for name, metrics in self.metrics.items()}

    def get_recent_logs(
        self, workflow_name: str | None = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        logs = self.logs
        if workflow_name:
            logs = [log for log in logs if log.workflow_name == workflow_name]

        recent_logs = logs[-limit:] if len(logs) > limit else logs
        return [asdict(log) for log in recent_logs]

    def export_metrics(self, filepath: str):
        """导出指标到文件"""
        data = {
            "metrics": self.get_metrics(),
            "recent_logs": self.get_recent_logs(limit=100),
            "export_time": datetime.now().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """V3: 仪表板数据汇总 — 总生成次数、成功率、平均耗时、24h趋势"""
        with self._lock:
            # 基础汇总
            total_count = sum(m.count for m in self.metrics.values())
            total_success = sum(m.count * m.success_rate for m in self.metrics.values())
            overall_success_rate = (total_success / total_count * 100) if total_count > 0 else 0
            avg_duration = (
                sum(m.total_duration for m in self.metrics.values()) / total_count
                if total_count > 0 else 0
            )

            # 最近24小时趋势
            now = datetime.now()
            recent_24h = [
                log for log in self.logs
                if (now - log.timestamp).total_seconds() < 86400
            ]

            hourly_trend = {}
            for log_entry in recent_24h:
                hour_key = log_entry.timestamp.strftime("%H:00")
                if hour_key not in hourly_trend:
                    hourly_trend[hour_key] = {"total": 0, "success": 0}
                hourly_trend[hour_key]["total"] += 1
                if log_entry.success:
                    hourly_trend[hour_key]["success"] += 1

            # V5: Token用量 — 修复原 get_llm_client 函数不存在的Bug，改为LLMClient单例
            token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            try:
                from src.ai_write_x.core.llm_client import LLMClient
                token_usage = LLMClient().get_token_usage()
            except Exception:
                pass  # LLMClient未初始化时静默降级

            return {
                "total_generations": total_count,
                "success_rate": round(overall_success_rate, 1),
                "avg_duration_seconds": round(avg_duration, 2),
                "recent_24h_count": len(recent_24h),
                "hourly_trend": hourly_trend,
                "token_usage": token_usage,
                "workflows": {
                    name: {
                        "count": m.count,
                        "success_rate": round(m.success_rate * 100, 1),
                        "avg_duration": round(m.avg_duration, 2),
                        "last_execution": m.last_execution.isoformat() if m.last_execution else None
                    }
                    for name, m in self.metrics.items()
                }
            }
