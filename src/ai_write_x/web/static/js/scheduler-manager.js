/**
 * SchedulerManager - 定时任务管理 JS 模块
 */

class SchedulerManager {
    constructor() {
        this.tasks = [];
        this.logs = [];
        this.selectedTaskId = null;
        this.refreshInterval = null;
    }

    init() {
        console.log("SchedulerManager initialized");
        this.refreshData();

        // 每 30 秒自动刷新一次列表和日志
        this.refreshInterval = setInterval(() => {
            if (document.getElementById('scheduler-view').style.display !== 'none') {
                this.refreshData();
            }
        }, 30000);
    }

    async refreshData() {
        await Promise.all([
            this.fetchTasks(),
            this.fetchLogs()
        ]);
        this.renderTasks();
        this.renderLogs();
        this.updateStats();
    }

    async fetchTasks() {
        try {
            const response = await fetch('/api/scheduler/tasks', {
                headers: {
                    'X-App-Client-Token': window.APP_CLIENT_TOKEN || window.appConfig?.token || localStorage.getItem('app_client_token') || ''
                }
            });
            if (response.ok) {
                this.tasks = await response.json();
            }
        } catch (error) {
            console.error("Fetch tasks failed:", error);
        }
    }

    async fetchLogs() {
        try {
            const response = await fetch('/api/scheduler/logs?limit=50', {
                headers: {
                    'X-App-Client-Token': window.APP_CLIENT_TOKEN || window.appConfig?.token || localStorage.getItem('app_client_token') || ''
                }
            });
            if (response.ok) {
                this.logs = await response.json();
            }
        } catch (error) {
            console.error("Fetch logs failed:", error);
        }
    }

    renderTasks() {
        const container = document.getElementById('scheduler-task-list');
        if (!container) return;

        if (this.tasks.length === 0) {
            container.innerHTML = '<tr><td colspan="7" class="text-center py-5">暂无定时任务，点击“新增任务”开始</td></tr>';
            return;
        }

        container.innerHTML = this.tasks.map(task => `
            <tr>
                <td class="font-medium">${this.truncate(task.topic, 30)}</td>
                <td><span class="tag tag-outline">${task.platform}</span></td>
                <td>${task.execution_time}</td>
                <td>${task.is_recurring ? `每 ${task.interval_hours} 小时` : '单次'}</td>
                <td>
                    <span class="status-badge status-${task.status}">
                        ${this.getStatusText(task.status)}
                    </span>
                </td>
                <td class="text-secondary">${task.last_run_at || '尚未运行'}</td>
                <td>
                    <div class="table-actions">
                        <button class="btn btn-icon btn-sm" onclick="window.schedulerManager.toggleTask('${task.id}', '${task.status}')" title="${task.status === 'enabled' ? '禁用' : '启用'}">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                ${task.status === 'enabled' ? '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>' : '<polygon points="5 3 19 12 5 21 5 3"/>'}
                            </svg>
                        </button>
                        <button class="btn btn-icon btn-sm" onclick="window.schedulerManager.deleteTask('${task.id}')" title="删除">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    renderLogs() {
        const container = document.getElementById('scheduler-log-list');
        if (!container) return;

        if (this.logs.length === 0) {
            container.innerHTML = '<tr><td colspan="4" class="text-center py-5">暂无运行日志</td></tr>';
            return;
        }

        container.innerHTML = this.logs.map(log => `
            <tr>
                <td class="text-secondary" style="font-size: 12px; white-space: nowrap;">${log.run_time}</td>
                <td>
                    <span class="status-badge status-${log.status}" style="padding: 2px 6px; font-size: 11px;">
                        ${log.status === 'success' ? '成功' : log.status === 'failed' ? '失败' : '运行中'}
                    </span>
                </td>
                <td style="font-size: 13px;">${log.message}</td>
                <td>
                    ${log.article_id ? `<button class="btn btn-link btn-sm" onclick="window.articleManager.viewArticle('${log.article_id}')">查看</button>` : '-'}
                </td>
            </tr>
        `).join('');
    }

    updateStats() {
        const activeCount = this.tasks.filter(t => t.status === 'enabled' || t.status === 'running').length;
        const totalCount = this.tasks.length;
        const todayLogs = this.logs.filter(l => l.run_time.startsWith(new Date().toISOString().split('T')[0])).length;

        const elActive = document.getElementById('scheduler-active-count');
        const elTotal = document.getElementById('scheduler-total-count');
        const elLogs = document.getElementById('scheduler-log-count');

        if (elActive) elActive.innerText = activeCount;
        if (elTotal) elTotal.innerText = totalCount;
        if (elLogs) elLogs.innerText = todayLogs;
    }

    openAddTaskModal() {
        this.selectedTaskId = null;
        document.getElementById('task-modal-title').innerText = "新增定时任务";
        document.getElementById('task-topic').value = "";
        document.getElementById('task-exec-time').value = this.getNearestMinute();
        document.getElementById('task-recurring').checked = false;
        document.getElementById('task-beautify').checked = true;
        document.getElementById('task-article-count').value = "1";
        document.getElementById('task-interval').value = "24";
        document.getElementById('task-interval-group').style.display = 'none';
        document.getElementById('platform-verify-tip').style.display = 'none';
        document.getElementById('task-edit-modal').style.display = 'flex';
    }

    closeModal() {
        document.getElementById('task-edit-modal').style.display = 'none';
    }

    toggleInterval(checked) {
        document.getElementById('task-interval-group').style.display = checked ? 'block' : 'none';
    }

    setDelayTime(seconds) {
        const now = new Date();
        now.setSeconds(now.getSeconds() + seconds);
        const pad = (n) => n.toString().padStart(2, '0');
        const localISO = now.getFullYear() + '-' +
            pad(now.getMonth() + 1) + '-' +
            pad(now.getDate()) + 'T' +
            pad(now.getHours()) + ':' +
            pad(now.getMinutes()) + ':' +
            pad(now.getSeconds());
        // datetime-local typically doesn't show seconds in input unless step is used, 
        // but for '10s later' we want precision. 
        document.getElementById('task-exec-time').value = localISO.slice(0, 16);
    }

    async checkPlatformConnection(platform) {
        const tipEl = document.getElementById('platform-verify-tip');
        if (!tipEl) return;

        if (platform !== 'wechat') {
            tipEl.style.display = 'none';
            return;
        }

        tipEl.style.display = 'block';
        tipEl.className = 'text-secondary';
        tipEl.innerText = "⏳ 正在检测平台连接状态...";

        try {
            const response = await fetch(`/api/scheduler/verify-platform?platform=${platform}`, {
                headers: {
                    'X-App-Client-Token': window.APP_CLIENT_TOKEN || window.appConfig?.token || localStorage.getItem('app_client_token') || ''
                }
            });
            const data = await response.json();
            if (data.success) {
                tipEl.className = 'text-success';
                tipEl.innerText = "✅ 账号连接正常";
            } else {
                tipEl.className = 'text-error';
                tipEl.innerHTML = `❌ 连接失败: ${data.message} <br> <span style="cursor:pointer; text-decoration:underline" onclick="window.app.showView('config-manager')">前往配置</span>`;
            }
        } catch (error) {
            tipEl.innerText = "❌ 检测异常";
        }
    }

    async saveTask() {
        const topic = document.getElementById('task-topic').value || ""; // Allow empty
        const execTime = document.getElementById('task-exec-time').value;
        const platform = document.getElementById('task-platform').value;
        const isRecurring = document.getElementById('task-recurring').checked;
        const interval = document.getElementById('task-interval').value;
        const articleCount = document.getElementById('task-article-count').value;
        const useAIBeautify = document.getElementById('task-beautify').checked;

        if (!execTime) {
            window.showNotification ? window.showNotification("请选择执行时间", "warning") : alert("请选择执行时间");
            return;
        }

        // 格式化时间
        const formattedTime = execTime.replace("T", " ") + ":00";

        try {
            const response = await fetch('/api/scheduler/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-App-Client-Token': window.APP_CLIENT_TOKEN || window.appConfig?.token || localStorage.getItem('app_client_token') || ''
                },
                body: JSON.stringify({
                    topic,
                    execution_time: formattedTime,
                    platform,
                    is_recurring: isRecurring,
                    interval_hours: parseInt(interval),
                    article_count: parseInt(articleCount),
                    use_ai_beautify: useAIBeautify
                })
            });

            if (response.ok) {
                this.closeModal();
                this.refreshData();
                window.showNotification ? window.showNotification("任务已保存", "success") : null;
            } else {
                const err = await response.json();
                alert("保存失败: " + err.detail);
            }
        } catch (error) {
            console.error("Save task failed:", error);
        }
    }

    async toggleTask(id, currentStatus) {
        const newStatus = currentStatus === 'enabled' ? 'disabled' : 'enabled';
        try {
            const response = await fetch(`/api/scheduler/tasks/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-App-Client-Token': window.APP_CLIENT_TOKEN || window.appConfig?.token || localStorage.getItem('app_client_token') || ''
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (response.ok) {
                this.refreshData();
            }
        } catch (error) {
            console.error("Toggle task failed:", error);
        }
    }

    async deleteTask(id) {
        if (!confirm("确定要删除这个定时任务吗？")) return;

        try {
            const response = await fetch(`/api/scheduler/tasks/${id}`, {
                method: 'DELETE',
                headers: {
                    'X-App-Client-Token': window.APP_CLIENT_TOKEN || window.appConfig?.token || localStorage.getItem('app_client_token') || ''
                }
            });

            if (response.ok) {
                this.refreshData();
            }
        } catch (error) {
            console.error("Delete task failed:", error);
        }
    }

    getStatusText(status) {
        const map = {
            'enabled': '等待中',
            'disabled': '已暂停',
            'running': '正在执行',
            'completed': '单次已完成',
            'failed': '执行失败'
        };
        return map[status] || status;
    }

    truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '...' : str;
    }

    getNearestMinute() {
        const now = new Date();
        now.setMinutes(now.getMinutes() + 5);
        now.setSeconds(0);
        now.setMilliseconds(0);
        return now.toISOString().slice(0, 16);
    }
}

// 自动实例化
window.schedulerManager = new SchedulerManager();
document.addEventListener('DOMContentLoaded', () => {
    window.schedulerManager.init();
});
