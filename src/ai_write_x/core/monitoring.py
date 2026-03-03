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
