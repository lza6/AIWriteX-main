# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) 服务管理器
支持动态添加、启用/禁用、监控 MCP 服务器
"""

import asyncio
import json
import os
import subprocess
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager


class MCPServiceStatus(Enum):
    """MCP服务状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class MCPServiceConfig:
    """MCP服务配置"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    auto_start: bool = False
    description: str = ""
    tools: List[str] = field(default_factory=list)  # 该服务提供的工具列表
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "description": self.description,
            "tools": self.tools,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServiceConfig":
        return cls(
            name=data.get("name", ""),
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            enabled=data.get("enabled", True),
            auto_start=data.get("auto_start", False),
            description=data.get("description", ""),
            tools=data.get("tools", []),
        )


@dataclass
class MCPServiceInstance:
    """MCP服务实例"""
    config: MCPServiceConfig
    status: MCPServiceStatus = MCPServiceStatus.STOPPED
    process: Optional[subprocess.Popen] = None
    error_message: str = ""
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


# 预定义的 MCP 服务模板
PREDEFINED_MCP_SERVICES = {
    "fetch": {
        "name": "fetch",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "description": "网页内容抓取服务，支持将HTML转换为Markdown",
        "tools": ["fetch"],
        "enabled": False,
        "auto_start": False,
    },
    "playwright": {
        "name": "playwright",
        "command": "npx",
        "args": ["@playwright/mcp@latest"],
        "description": "Playwright浏览器自动化服务，支持网页导航、截图、表单填写等",
        "tools": [
            "browser_navigate", "browser_click", "browser_type", 
            "browser_snapshot", "browser_screenshot", "browser_hover",
            "browser_drag", "browser_press_key", "browser_wait",
            "browser_close", "browser_save_as_pdf"
        ],
        "enabled": False,
        "auto_start": False,
    },
    "chrome-devtools": {
        "name": "chrome-devtools",
        "command": "npx",
        "args": ["chrome-devtools-mcp@latest"],
        "description": "Chrome DevTools MCP，支持浏览器调试、性能分析、网络监控",
        "tools": [
            "click", "fill", "hover", "drag", "navigate_page",
            "take_screenshot", "take_snapshot", "list_console_messages",
            "list_network_requests", "performance_start_trace", 
            "performance_stop_trace", "evaluate_script"
        ],
        "enabled": False,
        "auto_start": False,
    },
    "memory": {
        "name": "memory",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "description": "知识图谱内存服务，支持实体、关系、观察的持久化存储",
        "tools": [
            "create_entities", "create_relations", "add_observations",
            "delete_entities", "delete_observations", "delete_relations",
            "read_graph", "search_nodes", "open_nodes"
        ],
        "enabled": False,
        "auto_start": False,
    },
    "verge-news": {
        "name": "verge-news",
        "command": "npx",
        "args": ["-y", "verge-news-mcp"],
        "description": "The Verge新闻服务，获取科技新闻、搜索文章，支持每日/每周新闻和关键词搜索",
        "tools": [
            "get-daily-news",      # 获取过去24小时的新闻
            "get-weekly-news",     # 获取过去一周的新闻
            "search-news",         # 搜索新闻文章
        ],
        "enabled": False,
        "auto_start": False,
    },
    "pulse-cn": {
        "name": "pulse-cn",
        "command": "npx",
        "args": ["-y", "pulse-cn-mcp"],
        "description": "中国互联网实时热门内容，支持微博热搜、今日头条、澎湃新闻、知乎等18个平台",
        "tools": [
            "weibo-hotspots",                  # 微博实时热搜
            "horoscope",                       # 每日星座运势
            "daily-english-sentence",          # 每日励志英语
            "internet-hotspots-aggregator",    # 热搜热榜聚合
            "today-headlines-hotspots",        # 今日头条热搜
            "paper-news-hotspots",             # 澎湃新闻热搜
            "zhihu-realtime-hotspots",         # 知乎实时热搜
            "bilibili-daily-hotspots",         # B站日榜
            "douyin-hotspots",                 # 抖音热点
            "baidu-hotspots",                  # 百度热点
        ],
        "enabled": False,
        "auto_start": False,
    },
}


class MCPManager:
    """
    MCP服务管理器
    负责管理多个MCP服务的生命周期、配置和工具调用
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self.services: Dict[str, MCPServiceInstance] = {}
        self.config_path = self._get_config_path()
        self._load_config()
        
    @classmethod
    def get_instance(cls) -> "MCPManager":
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        config_dir = PathManager.get_config_dir()
        return config_dir / "mcp_services.json"
    
    def _load_config(self):
        """加载配置文件"""
        # 加载预定义服务
        for name, config in PREDEFINED_MCP_SERVICES.items():
            self.services[name] = MCPServiceInstance(
                config=MCPServiceConfig.from_dict(config)
            )
        
        # 加载用户自定义配置
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                
                for name, config in user_config.get("services", {}).items():
                    if name in self.services:
                        # 更新预定义服务的配置
                        self.services[name].config = MCPServiceConfig.from_dict(config)
                    else:
                        # 添加自定义服务
                        self.services[name] = MCPServiceInstance(
                            config=MCPServiceConfig.from_dict(config)
                        )
                
                log.print_log(f"已加载 {len(self.services)} 个MCP服务配置")
            except Exception as e:
                log.print_log(f"加载MCP配置失败: {e}", "error")
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            config_data = {
                "services": {
                    name: instance.config.to_dict() 
                    for name, instance in self.services.items()
                },
                "updated_at": datetime.now().isoformat(),
            }
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            log.print_log(f"保存MCP配置失败: {e}", "error")
            return False
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """获取所有服务列表"""
        result = []
        for name, instance in self.services.items():
            result.append({
                "name": name,
                "status": instance.status.value,
                "enabled": instance.config.enabled,
                "auto_start": instance.config.auto_start,
                "description": instance.config.description,
                "command": instance.config.command,
                "args": instance.config.args,
                "tools": instance.config.tools,
                "error_message": instance.error_message,
                "started_at": instance.started_at.isoformat() if instance.started_at else None,
            })
        return result
    
    def get_service(self, name: str) -> Optional[Dict[str, Any]]:
        """获取单个服务详情"""
        if name not in self.services:
            return None
        
        instance = self.services[name]
        return {
            "name": name,
            "status": instance.status.value,
            "config": instance.config.to_dict(),
            "error_message": instance.error_message,
            "started_at": instance.started_at.isoformat() if instance.started_at else None,
            "last_activity": instance.last_activity.isoformat() if instance.last_activity else None,
        }
    
    def add_service(self, config: Dict[str, Any]) -> bool:
        """添加新服务"""
        name = config.get("name")
        if not name:
            log.print_log("服务名称不能为空", "error")
            return False
        
        if name in self.services:
            log.print_log(f"服务 {name} 已存在", "error")
            return False
        
        self.services[name] = MCPServiceInstance(
            config=MCPServiceConfig.from_dict(config)
        )
        self.save_config()
        log.print_log(f"已添加MCP服务: {name}")
        return True
    
    def update_service(self, name: str, config: Dict[str, Any]) -> bool:
        """更新服务配置"""
        if name not in self.services:
            log.print_log(f"服务 {name} 不存在", "error")
            return False
        
        # 如果服务正在运行，先停止
        instance = self.services[name]
        if instance.status == MCPServiceStatus.RUNNING:
            self.stop_service(name)
        
        # 更新配置
        updated_config = MCPServiceConfig.from_dict({**instance.config.to_dict(), **config})
        updated_config.name = name  # 确保名称不变
        instance.config = updated_config
        
        self.save_config()
        log.print_log(f"已更新MCP服务: {name}")
        return True
    
    def remove_service(self, name: str) -> bool:
        """删除服务"""
        if name not in self.services:
            log.print_log(f"服务 {name} 不存在", "error")
            return False
        
        # 如果是预定义服务，只禁用不删除
        if name in PREDEFINED_MCP_SERVICES:
            self.services[name].config.enabled = False
            log.print_log(f"已禁用预定义MCP服务: {name}")
        else:
            # 停止服务
            self.stop_service(name)
            del self.services[name]
            log.print_log(f"已删除MCP服务: {name}")
        
        self.save_config()
        return True
    
    def enable_service(self, name: str) -> bool:
        """启用服务"""
        if name not in self.services:
            return False
        
        self.services[name].config.enabled = True
        self.save_config()
        return True
    
    def disable_service(self, name: str) -> bool:
        """禁用服务"""
        if name not in self.services:
            return False
        
        self.stop_service(name)
        self.services[name].config.enabled = False
        self.save_config()
        return True
    
    def start_service(self, name: str) -> bool:
        """启动服务"""
        if name not in self.services:
            log.print_log(f"服务 {name} 不存在", "error")
            return False
        
        instance = self.services[name]
        
        if not instance.config.enabled:
            log.print_log(f"服务 {name} 未启用", "error")
            return False
        
        if instance.status == MCPServiceStatus.RUNNING:
            log.print_log(f"服务 {name} 已在运行", "warning")
            return True
        
        try:
            instance.status = MCPServiceStatus.STARTING
            instance.error_message = ""
            
            # 构建命令
            cmd = [instance.config.command] + instance.config.args
            
            # 设置环境变量
            env = os.environ.copy()
            env.update(instance.config.env)
            
            # 启动进程
            if os.name == 'nt':  # Windows
                # 在Windows上使用shell=True来确保能找到PATH中的命令
                # 将命令列表转换为字符串
                cmd_str = subprocess.list2cmdline(cmd)
                instance.process = subprocess.Popen(
                    cmd_str,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:  # Unix-like
                instance.process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid,
                )
            
            instance.status = MCPServiceStatus.RUNNING
            instance.started_at = datetime.now()
            instance.last_activity = datetime.now()
            
            log.print_log(f"MCP服务 {name} 已启动 (PID: {instance.process.pid})")
            return True
            
        except FileNotFoundError:
            instance.status = MCPServiceStatus.ERROR
            instance.error_message = f"找不到命令: {instance.config.command}"
            log.print_log(instance.error_message, "error")
            return False
        except Exception as e:
            instance.status = MCPServiceStatus.ERROR
            instance.error_message = str(e)
            log.print_log(f"启动MCP服务 {name} 失败: {e}", "error")
            return False
    
    def stop_service(self, name: str) -> bool:
        """停止服务"""
        if name not in self.services:
            return False
        
        instance = self.services[name]
        
        if instance.status != MCPServiceStatus.RUNNING:
            return True
        
        try:
            if instance.process:
                if os.name == 'nt':  # Windows
                    instance.process.terminate()
                else:  # Unix-like
                    os.killpg(os.getpgid(instance.process.pid), subprocess.signal.SIGTERM)
                
                # 等待进程结束
                try:
                    instance.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name == 'nt':
                        instance.process.kill()
                    else:
                        os.killpg(os.getpgid(instance.process.pid), subprocess.signal.SIGKILL)
            
            instance.status = MCPServiceStatus.STOPPED
            instance.process = None
            instance.started_at = None
            
            log.print_log(f"MCP服务 {name} 已停止")
            return True
            
        except Exception as e:
            instance.error_message = str(e)
            log.print_log(f"停止MCP服务 {name} 失败: {e}", "error")
            return False
    
    def restart_service(self, name: str) -> bool:
        """重启服务"""
        self.stop_service(name)
        return self.start_service(name)
    
    def start_all_enabled(self) -> Dict[str, bool]:
        """启动所有已启用的服务"""
        results = {}
        for name, instance in self.services.items():
            # 只要服务已启用，就尝试启动
            if instance.config.enabled:
                results[name] = self.start_service(name)
        return results
    
    def stop_all(self) -> Dict[str, bool]:
        """停止所有服务"""
        results = {}
        for name, instance in self.services.items():
            if instance.status == MCPServiceStatus.RUNNING:
                results[name] = self.stop_service(name)
        return results
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具列表"""
        tools = []
        for name, instance in self.services.items():
            if instance.config.enabled and instance.status == MCPServiceStatus.RUNNING:
                for tool_name in instance.config.tools:
                    tools.append({
                        "name": tool_name,
                        "service": name,
                        "status": "available",
                    })
            elif instance.config.enabled:
                for tool_name in instance.config.tools:
                    tools.append({
                        "name": tool_name,
                        "service": name,
                        "status": "service_not_running",
                    })
        return tools
    
    def check_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """检查MCP服务的依赖"""
        import platform
        import os
        
        results = {}
        system = platform.system()
        
        # 在Windows上，需要使用shell=True来获取完整的PATH环境变量
        use_shell = system == "Windows"
        
        # 检查 Node.js (npx)
        try:
            result = subprocess.run(
                ["npx", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10,
                shell=use_shell
            )
            if result.returncode == 0:
                results["npx"] = {
                    "available": True,
                    "version": result.stdout.strip(),
                    "message": "Node.js npx 可用"
                }
            else:
                raise Exception(result.stderr or "命令执行失败")
        except Exception as e:
            # 尝试在常见路径中查找
            npx_paths = [
                os.path.expanduser("~\\AppData\\Roaming\\npm\\npx.cmd"),
                os.path.expanduser("~\\AppData\\Roaming\\npm\\npx"),
                "C:\\Program Files\\nodejs\\npx.cmd",
            ]
            found = False
            for path in npx_paths:
                if os.path.exists(path):
                    try:
                        result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            results["npx"] = {
                                "available": True,
                                "version": result.stdout.strip(),
                                "message": f"Node.js npx 可用 (路径: {path})"
                            }
                            found = True
                            break
                    except:
                        continue
            
            if not found:
                results["npx"] = {
                    "available": False,
                    "version": None,
                    "message": f"npx 不可用: {str(e)}"
                }
        
        # 检查 uvx (uv)
        try:
            result = subprocess.run(
                ["uvx", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10,
                shell=use_shell
            )
            if result.returncode == 0:
                results["uvx"] = {
                    "available": True,
                    "version": result.stdout.strip(),
                    "message": "uv/uvx 可用"
                }
            else:
                raise Exception(result.stderr or "命令执行失败")
        except Exception as e:
            # 尝试在常见路径中查找
            uvx_paths = [
                os.path.expanduser("~\\.local\\bin\\uvx"),
                os.path.expanduser("~\\.cargo\\bin\\uvx"),
                os.path.expanduser("~\\AppData\\Local\\uv\\uvx.exe"),
            ]
            found = False
            for path in uvx_paths:
                if os.path.exists(path):
                    try:
                        result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            results["uvx"] = {
                                "available": True,
                                "version": result.stdout.strip(),
                                "message": f"uv/uvx 可用 (路径: {path})"
                            }
                            found = True
                            break
                    except:
                        continue
            
            if not found:
                results["uvx"] = {
                    "available": False,
                    "version": None,
                    "message": f"uvx 不可用: {str(e)}"
                }
        
        return results
    
    def install_dependency(self, dep_name: str) -> Dict[str, Any]:
        """
        安装MCP依赖
        
        Args:
            dep_name: 依赖名称 (npx/nodejs 或 uvx/uv)
        
        Returns:
            安装结果
        """
        import platform
        
        system = platform.system()
        results = {
            "success": False,
            "message": "",
            "commands": [],
            "output": ""
        }
        
        if dep_name in ["npx", "nodejs", "node"]:
            # 安装 Node.js
            if system == "Windows":
                # Windows: 使用 winget 或 choco
                results["commands"] = [
                    "# 方法1: 使用 winget (需要管理员权限)",
                    "winget install OpenJS.NodeJS.LTS",
                    "",
                    "# 方法2: 使用 Chocolatey",
                    "choco install nodejs-lts",
                    "",
                    "# 方法3: 手动下载安装 (推荐)",
                    "# 访问 https://nodejs.org/ 下载LTS版本安装",
                ]
                results["message"] = "请选择以下任一方式安装 Node.js："
                
                # 尝试使用 winget 安装
                try:
                    log.print_log("[MCP] 正在尝试使用 winget 安装 Node.js...")
                    proc = subprocess.run(
                        ["winget", "install", "OpenJS.NodeJS.LTS", "--accept-source-agreements", "--accept-package-agreements"],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    log.print_log(f"[MCP] winget 返回码: {proc.returncode}")
                    log.print_log(f"[MCP] winget 输出: {proc.stdout[:500] if proc.stdout else '无'}")
                    
                    if proc.returncode == 0:
                        results["success"] = True
                        results["output"] = proc.stdout
                        results["message"] = "Node.js 安装成功！\n\n⚠️ 重要：请关闭当前终端窗口，重新打开一个新终端，然后重新启动应用才能使用 npx。"
                    else:
                        results["output"] = proc.stderr or proc.stdout
                        # 检查是否已安装
                        if "已安装" in str(proc.stdout) or "already installed" in str(proc.stdout).lower():
                            results["success"] = True
                            results["message"] = "Node.js 已经安装！\n\n⚠️ 重要：请关闭当前终端窗口，重新打开一个新终端，然后重新启动应用才能使用 npx。"
                        else:
                            results["message"] = "自动安装失败，请使用管理员权限运行或手动安装 Node.js"
                except FileNotFoundError:
                    results["message"] = "winget 不可用，请手动安装 Node.js"
                    log.print_log("[MCP] winget 命令未找到")
                except subprocess.TimeoutExpired:
                    results["message"] = "安装超时，请手动安装 Node.js"
                    log.print_log("[MCP] winget 安装超时")
                except Exception as e:
                    results["output"] = str(e)
                    results["message"] = f"安装出错: {str(e)}"
                    log.print_log(f"[MCP] 安装异常: {e}")
                    
            elif system == "Darwin":  # macOS
                results["commands"] = [
                    "# 使用 Homebrew 安装",
                    "brew install node",
                ]
                try:
                    proc = subprocess.run(["brew", "install", "node"], capture_output=True, text=True, timeout=300)
                    if proc.returncode == 0:
                        results["success"] = True
                        results["output"] = proc.stdout
                        results["message"] = "Node.js 安装成功！"
                except Exception as e:
                    results["output"] = str(e)
                    
            else:  # Linux
                results["commands"] = [
                    "# Ubuntu/Debian",
                    "sudo apt update && sudo apt install -y nodejs npm",
                    "",
                    "# CentOS/RHEL",
                    "sudo yum install -y nodejs npm",
                    "",
                    "# Arch Linux",
                    "sudo pacman -S nodejs npm",
                ]
        
        elif dep_name in ["uvx", "uv"]:
            # 安装 uv (uvx 是 uv 的一部分)
            results["commands"] = [
                "# 官方安装脚本 (推荐)",
                "pip install uv",
                "",
                "# 或者使用 pipx",
                "pipx install uv",
            ]
            
            try:
                log.print_log("[MCP] 正在使用 pip 安装 uv...")
                proc = subprocess.run(
                    ["pip", "install", "uv"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if proc.returncode == 0:
                    results["success"] = True
                    results["output"] = proc.stdout
                    results["message"] = "uv/uvx 安装成功！"
                else:
                    results["output"] = proc.stderr or proc.stdout
            except Exception as e:
                results["output"] = str(e)
                results["message"] = "安装失败，请手动执行: pip install uv"
        
        else:
            results["message"] = f"未知的依赖: {dep_name}"
        
        return results
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        total = len(self.services)
        enabled = sum(1 for i in self.services.values() if i.config.enabled)
        running = sum(1 for i in self.services.values() if i.status == MCPServiceStatus.RUNNING)
        error = sum(1 for i in self.services.values() if i.status == MCPServiceStatus.ERROR)
        
        return {
            "total": total,
            "enabled": enabled,
            "running": running,
            "stopped": total - running - error,
            "error": error,
        }
