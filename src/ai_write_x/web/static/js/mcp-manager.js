/**
 * MCP服务管理器
 * 负责MCP服务的管理界面和交互
 */
class MCPManager {
    constructor() {
        this.services = [];
        this.dependencies = {};
        this.selectedService = null;
        this.refreshInterval = null;
        this.initialized = false;
        this.initializing = false;
    }

    async init() {
        // 防止重复初始化或并发初始化
        if (this.initialized || this.initializing) {
            return;
        }

        this.initializing = true;

        try {
            this.bindEvents();
            await this.loadDependencies();
            await this.loadServices();
            this.startAutoRefresh();
            this.initialized = true;
        } catch (error) {
            console.error('MCPManager 初始化失败:', error);
        } finally {
            this.initializing = false;
        }
    }
    
    bindEvents() {
        // 添加服务按钮
        const addBtn = document.getElementById('mcp-add-service-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showAddServiceModal());
        }
        
        // 刷新按钮
        const refreshBtn = document.getElementById('mcp-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadServices());
        }
        
        // 启动所有按钮
        const startAllBtn = document.getElementById('mcp-start-all-btn');
        if (startAllBtn) {
            startAllBtn.addEventListener('click', () => this.startAllServices());
        }
        
        // 停止所有按钮
        const stopAllBtn = document.getElementById('mcp-stop-all-btn');
        if (stopAllBtn) {
            stopAllBtn.addEventListener('click', () => this.stopAllServices());
        }
    }
    
    async loadDependencies() {
        try {
            const response = await fetch('/api/mcp/dependencies');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.dependencies = data.data;
                this.renderDependencies();
            }
        } catch (error) {
            console.error('加载MCP依赖失败:', error);
        }
    }
    
    async loadServices() {
        try {
            const response = await fetch('/api/mcp/');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.services = data.data.services;
                this.renderServices();
                this.renderSummary(data.data.summary);
            }
        } catch (error) {
            console.error('加载MCP服务失败:', error);
            this.showError('加载服务列表失败');
        }
    }
    
    renderDependencies() {
        const container = document.getElementById('mcp-dependencies');
        if (!container) return;
        
        let html = '<div class="deps-grid">';
        
        for (const [name, info] of Object.entries(this.dependencies)) {
            const statusClass = info.available ? 'dep-available' : 'dep-unavailable';
            const statusIcon = info.available ? '✓' : '✗';
            const installBtn = info.available ? '' : `
                <button class="dep-install-btn" data-dep="${name}">
                    安装
                </button>
            `;
            
            html += `
                <div class="dep-item ${statusClass}">
                    <span class="dep-icon">${statusIcon}</span>
                    <div class="dep-info">
                        <span class="dep-name">${name}</span>
                        <span class="dep-version">${info.version || '未安装'}</span>
                    </div>
                    ${installBtn}
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
        
        // 绑定安装按钮点击事件
        container.querySelectorAll('.dep-install-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const depName = btn.dataset.dep;
                this.installDependency(depName, btn);
            });
        });
    }
    
    async installDependency(depName, btnElement) {
        // 显示安装中状态
        const btn = btnElement || document.querySelector(`.dep-install-btn[data-dep="${depName}"]`);
        const originalText = btn ? btn.textContent : '安装';
        if (btn) {
            btn.textContent = '安装中...';
            btn.disabled = true;
        }
        
        try {
            const response = await fetch(`/api/mcp/install-dependency/${depName}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            const result = data.data || {};
            
            if (data.status === 'success' && result.success) {
                // 显示成功提示（包含重启提醒）
                this.showInstallResult(depName, result);
                // 刷新依赖状态
                await this.loadDependencies();
            } else {
                // 显示安装指南
                if (result.commands && result.commands.length > 0) {
                    this.showInstallCommands(depName, result);
                } else {
                    this.showError(result.message || '安装失败');
                }
            }
        } catch (error) {
            console.error('安装依赖失败:', error);
            this.showError('安装请求失败');
        } finally {
            if (btn) {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
    }
    
    showInstallResult(depName, result) {
        const modal = document.createElement('div');
        modal.className = 'mcp-modal-overlay';
        modal.innerHTML = `
            <div class="mcp-modal install-commands-modal">
                <div class="modal-header">
                    <h3>✅ ${depName} 安装完成</h3>
                    <button class="modal-close" onclick="this.closest('.mcp-modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="install-success-message">
                        ${result.message ? result.message.replace(/\n/g, '<br>') : '安装成功！'}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-primary" onclick="this.closest('.mcp-modal-overlay').remove()">我知道了</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    showInstallCommands(depName, result) {
        const modal = document.createElement('div');
        modal.className = 'mcp-modal-overlay';
        modal.innerHTML = `
            <div class="mcp-modal install-commands-modal">
                <div class="modal-header">
                    <h3>安装 ${depName}</h3>
                    <button class="modal-close" onclick="this.closest('.mcp-modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <p class="install-message">${result.message}</p>
                    <div class="install-commands">
                        ${result.commands.map(cmd => 
                            cmd.startsWith('#') 
                                ? `<div class="command-comment">${cmd}</div>`
                                : `<code class="command-line" onclick="navigator.clipboard.writeText(this.textContent)">${cmd}</code>`
                        ).join('')}
                    </div>
                    <p class="install-hint">点击命令可复制到剪贴板</p>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    renderServices() {
        const container = document.getElementById('mcp-services-list');
        if (!container) return;
        
        if (this.services.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无MCP服务配置</p>
                    <p style="font-size: 12px; color: var(--text-secondary); margin-top: 10px;">
                        预定义服务已加载但默认未启用。<br>
                        请先点击「添加服务」或在服务卡片中启用服务。
                    </p>
                </div>
            `;
            return;
        }
        
        let html = '';
        
        for (const service of this.services) {
            const statusClass = this.getStatusClass(service.status);
            const statusText = this.getStatusText(service.status);
            const enabledClass = service.enabled ? 'enabled' : 'disabled';
            
            html += `
                <div class="mcp-service-card ${enabledClass}" data-name="${service.name}">
                    <div class="service-header">
                        <div class="service-info">
                            <h3 class="service-name">${service.name}</h3>
                            <span class="service-status ${statusClass}">${statusText}</span>
                        </div>
                        <div class="service-toggle">
                            <label class="toggle-switch">
                                <input type="checkbox" 
                                       ${service.enabled ? 'checked' : ''} 
                                       onchange="window.mcpManager.toggleService('${service.name}', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>
                    
                    <p class="service-description">${service.description || '无描述'}</p>
                    
                    <div class="service-meta">
                        <span class="meta-item">
                            <svg viewBox="0 0 24 24" width="14" height="14">
                                <path d="M4 17l6-6-6-6 1.41-1.41L12 10.59l6.59-6.59L20 6l-6 6 6 6-1.41 1.41L12 13.41l-6.59 6.59L4 17z"/>
                            </svg>
                            ${service.command}
                        </span>
                        <span class="meta-item tools-count">
                            <svg viewBox="0 0 24 24" width="14" height="14">
                                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                            </svg>
                            ${service.tools.length} 个工具
                        </span>
                    </div>
                    
                    <div class="service-actions">
                        ${this.renderServiceActions(service)}
                    </div>
                    
                    ${service.error_message ? `
                        <div class="service-error">
                            <svg viewBox="0 0 24 24" width="16" height="16">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="12" y1="8" x2="12" y2="12"/>
                                <line x1="12" y1="16" x2="12.01" y2="16"/>
                            </svg>
                            ${service.error_message}
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        container.innerHTML = html;
    }
    
    renderServiceActions(service) {
        const actions = [];
        
        if (service.status === 'running') {
            actions.push(`
                <button class="action-btn stop" onclick="window.mcpManager.stopService('${service.name}')">
                    <svg viewBox="0 0 24 24" width="14" height="14">
                        <rect x="6" y="6" width="12" height="12"/>
                    </svg>
                    停止
                </button>
            `);
        } else if (service.status === 'stopped' || service.status === 'error') {
            if (service.enabled) {
                actions.push(`
                    <button class="action-btn start" onclick="window.mcpManager.startService('${service.name}')">
                        <svg viewBox="0 0 24 24" width="14" height="14">
                            <polygon points="5,3 19,12 5,21"/>
                        </svg>
                        启动
                    </button>
                `);
            }
        }
        
        actions.push(`
            <button class="action-btn config" onclick="window.mcpManager.showServiceConfig('${service.name}')">
                <svg viewBox="0 0 24 24" width="14" height="14">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
                配置
            </button>
        `);
        
        if (service.status === 'running') {
            actions.push(`
                <button class="action-btn restart" onclick="window.mcpManager.restartService('${service.name}')">
                    <svg viewBox="0 0 24 24" width="14" height="14">
                        <polyline points="23,4 23,10 17,10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                    重启
                </button>
            `);
        }
        
        return actions.join('');
    }
    
    renderSummary(summary) {
        const container = document.getElementById('mcp-summary');
        if (!container) return;
        
        container.innerHTML = `
            <div class="summary-item">
                <span class="summary-value">${summary.total}</span>
                <span class="summary-label">总计</span>
            </div>
            <div class="summary-item enabled">
                <span class="summary-value">${summary.enabled}</span>
                <span class="summary-label">已启用</span>
            </div>
            <div class="summary-item running">
                <span class="summary-value">${summary.running}</span>
                <span class="summary-label">运行中</span>
            </div>
            <div class="summary-item error">
                <span class="summary-value">${summary.error}</span>
                <span class="summary-label">错误</span>
            </div>
        `;
    }
    
    getStatusClass(status) {
        const classes = {
            'stopped': 'status-stopped',
            'starting': 'status-starting',
            'running': 'status-running',
            'error': 'status-error'
        };
        return classes[status] || 'status-stopped';
    }
    
    getStatusText(status) {
        const texts = {
            'stopped': '已停止',
            'starting': '启动中',
            'running': '运行中',
            'error': '错误'
        };
        return texts[status] || '未知';
    }
    
    async toggleService(name, enabled) {
        try {
            const endpoint = enabled ? 'enable' : 'disable';
            const response = await fetch(`/api/mcp/${name}/${endpoint}`, { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                await this.loadServices();
            } else {
                throw new Error(data.detail || '操作失败');
            }
        } catch (error) {
            console.error('切换服务状态失败:', error);
            this.showError(error.message);
            await this.loadServices();
        }
    }
    
    async startService(name) {
        try {
            this.updateServiceStatus(name, 'starting');
            
            const response = await fetch(`/api/mcp/${name}/start`, { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                await this.loadServices();
            } else {
                throw new Error(data.detail || '启动失败');
            }
        } catch (error) {
            console.error('启动服务失败:', error);
            this.showError(error.message);
            await this.loadServices();
        }
    }
    
    async stopService(name) {
        try {
            const response = await fetch(`/api/mcp/${name}/stop`, { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                await this.loadServices();
            } else {
                throw new Error(data.detail || '停止失败');
            }
        } catch (error) {
            console.error('停止服务失败:', error);
            this.showError(error.message);
            await this.loadServices();
        }
    }
    
    async restartService(name) {
        try {
            this.updateServiceStatus(name, 'starting');
            
            const response = await fetch(`/api/mcp/${name}/restart`, { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                await this.loadServices();
            } else {
                throw new Error(data.detail || '重启失败');
            }
        } catch (error) {
            console.error('重启服务失败:', error);
            this.showError(error.message);
            await this.loadServices();
        }
    }
    
    async startAllServices() {
        // 检查是否有启用的服务
        const enabledServices = this.services.filter(s => s.enabled);
        if (enabledServices.length === 0) {
            this.showError('没有启用的服务。请先启用需要的服务（点击服务卡片上的开关）');
            return;
        }
        
        try {
            const response = await fetch('/api/mcp/start-all', { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                await this.loadServices();
            }
        } catch (error) {
            console.error('启动所有服务失败:', error);
            this.showError('启动失败');
        }
    }
    
    async stopAllServices() {
        try {
            const response = await fetch('/api/mcp/stop-all', { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                await this.loadServices();
            }
        } catch (error) {
            console.error('停止所有服务失败:', error);
            this.showError('停止失败');
        }
    }
    
    updateServiceStatus(name, status) {
        const card = document.querySelector(`.mcp-service-card[data-name="${name}"]`);
        if (card) {
            const statusEl = card.querySelector('.service-status');
            if (statusEl) {
                statusEl.className = `service-status ${this.getStatusClass(status)}`;
                statusEl.textContent = this.getStatusText(status);
            }
        }
    }
    
    showServiceConfig(name) {
        const service = this.services.find(s => s.name === name);
        if (!service) return;
        
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content mcp-config-modal">
                <div class="modal-header">
                    <h2>服务配置 - ${name}</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="config-section">
                        <h3>基本信息</h3>
                        <div class="config-row">
                            <label>命令</label>
                            <input type="text" id="config-command" value="${service.command}" readonly>
                        </div>
                        <div class="config-row">
                            <label>参数</label>
                            <input type="text" id="config-args" value="${service.args.join(' ')}" readonly>
                        </div>
                        <div class="config-row">
                            <label>描述</label>
                            <textarea id="config-description" rows="2">${service.description || ''}</textarea>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <h3>启动选项</h3>
                        <div class="config-row checkbox">
                            <label>
                                <input type="checkbox" id="config-auto-start" ${service.auto_start ? 'checked' : ''}>
                                自动启动
                            </label>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <h3>可用工具 (${service.tools.length})</h3>
                        <div class="tools-list">
                            ${service.tools.map(t => `<span class="tool-tag">${t}</span>`).join('')}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">关闭</button>
                    <button class="btn-primary" onclick="window.mcpManager.saveServiceConfig('${name}')">保存</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    async saveServiceConfig(name) {
        const description = document.getElementById('config-description').value;
        const autoStart = document.getElementById('config-auto-start').checked;
        
        try {
            const response = await fetch(`/api/mcp/${name}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    description: description,
                    auto_start: autoStart
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                document.querySelector('.mcp-config-modal').closest('.modal-overlay').remove();
                await this.loadServices();
            } else {
                throw new Error(data.detail || '保存失败');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }
    
    showAddServiceModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content mcp-add-modal">
                <div class="modal-header">
                    <h2>添加MCP服务</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="config-row">
                        <label>服务名称 *</label>
                        <input type="text" id="new-service-name" placeholder="例如: my-mcp-server">
                    </div>
                    <div class="config-row">
                        <label>命令 *</label>
                        <input type="text" id="new-service-command" placeholder="例如: npx 或 uvx">
                    </div>
                    <div class="config-row">
                        <label>参数</label>
                        <input type="text" id="new-service-args" placeholder="空格分隔的参数">
                    </div>
                    <div class="config-row">
                        <label>描述</label>
                        <textarea id="new-service-description" rows="2" placeholder="服务描述"></textarea>
                    </div>
                    <div class="config-row">
                        <label>工具列表</label>
                        <input type="text" id="new-service-tools" placeholder="逗号分隔的工具名称">
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">取消</button>
                    <button class="btn-primary" onclick="window.mcpManager.addService()">添加</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    async addService() {
        const name = document.getElementById('new-service-name').value.trim();
        const command = document.getElementById('new-service-command').value.trim();
        const argsStr = document.getElementById('new-service-args').value.trim();
        const description = document.getElementById('new-service-description').value.trim();
        const toolsStr = document.getElementById('new-service-tools').value.trim();
        
        if (!name || !command) {
            this.showError('服务名称和命令为必填项');
            return;
        }
        
        const config = {
            name: name,
            command: command,
            args: argsStr ? argsStr.split(/\s+/) : [],
            description: description,
            tools: toolsStr ? toolsStr.split(',').map(t => t.trim()) : [],
            enabled: true,
            auto_start: false
        };
        
        try {
            const response = await fetch('/api/mcp/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showSuccess(data.message);
                document.querySelector('.mcp-add-modal').closest('.modal-overlay').remove();
                await this.loadServices();
            } else {
                throw new Error(data.detail || '添加失败');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }
    
    startAutoRefresh() {
        // 每30秒自动刷新服务状态
        this.refreshInterval = setInterval(() => {
            this.loadServices();
        }, 30000);
    }
    
    showSuccess(message) {
        if (window.app) {
            window.app.showNotification(message, 'success');
        }
    }
    
    showError(message) {
        if (window.app) {
            window.app.showNotification(message, 'error');
        }
    }
}
