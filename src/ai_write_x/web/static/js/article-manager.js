// 文章管理器类
class ArticleManager {
    // 查看文章原始热点内容
    async showArticleSource(article) {
        try {
            // 从路径中提取文件名（不带扩展名）作为 article_name
            const filename = article.path.split(/[\\/]/).pop();
            const response = await fetch(`/api/articles/${encodeURIComponent(filename)}/source`);
            if (!response.ok) throw new Error('获取源内容失败');

            const result = await response.json();
            const content = result.content || '无内容';

            const dialogId = 'article-source-dialog';
            const existingDialog = document.getElementById(dialogId);
            if (existingDialog) existingDialog.remove();

            const dialogHtml = `
                <div class="modal-overlay" id="${dialogId}" style="z-index: 10000;">
                    <div class="modal-content" style="max-width: 800px; width: 90%; max-height: 85vh; display: flex; flex-direction: column;">
                        <div class="modal-header">
                            <h3 style="display: flex; align-items: center; gap: 8px;">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                    <circle cx="12" cy="12" r="3"/>
                                </svg>
                                原始热点参考内容 - ${this.escapeHtml(article.title)}
                            </h3>
                            <button class="modal-close" onclick="document.getElementById('${dialogId}').remove()">×</button>
                        </div>
                        <div class="modal-body" style="flex: 1; overflow: hidden; display: flex; flex-direction: column; gap: 12px; padding:  20px;">
                            <div style="background: var(--bg-tertiary, #f8fafc); border: 1px solid var(--border-color, #e2e8f0); border-radius: 8px; padding: 15px; flex: 1; overflow-y: auto; white-space: pre-wrap; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; line-height: 1.8; color: var(--text-primary);">
                                ${this.escapeHtml(content)}
                            </div>
                        </div>
                        <div class="modal-footer" style="display: flex; justify-content: flex-end; gap: 10px;">
                            <button class="btn btn-primary" onclick="window.articleManager.copyToClipboard(\`${content.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)">一键复制内容</button>
                            <button class="btn btn-secondary" onclick="document.getElementById('${dialogId}').remove()">关闭</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', dialogHtml);
        } catch (error) {
            this.showNotification('查看源内容失败: ' + error.message, 'error');
        }
    }

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('内容已成功复制到剪贴板', 'success');
        } catch (err) {
            console.error('复制失败:', err);
            // 兼容性兜底
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                this.showNotification('内容已成功复制到剪贴板', 'success');
            } catch (e) {
                this.showNotification('复制失败，请手动选择复制', 'error');
            }
            document.body.removeChild(textarea);
        }
    }

    constructor() {
        this.articles = [];
        this.filteredArticles = [];
        this.currentStatus = 'all';
        this.currentLayout = 'grid';
        this.batchMode = false;
        this.selectedArticles = new Set();
        this.observer = null;
        this.publishingArticles = [];
        this.platforms = null;
        this.platformAccounts = {};
        this.initialized = false;
        this.initializing = false;
        this.backgroundTasks = new Map(); // 存储后台任务: id -> {name, progress, status, controller}
        this.reTemplateAbortController = null;
    }

    async init() {
        // 防止重复初始化或并发初始化
        if (this.initialized || this.initializing) {
            return;
        }

        this.initializing = true;

        try {
            if (this.initialized) {
                await this.loadArticles();
                this.renderStatusTree();
                this._injectVoteStyles();
                if (this.observer) {
                    const cards = document.querySelectorAll('.content-card');
                    cards.forEach(card => {
                        if (card.querySelector('iframe[data-loaded="true"]')) {
                            return;
                        }
                        this.observer.observe(card);
                    });
                }
                return;
            }

            // 首次初始化逻辑
            await this.loadArticles();
            this.renderStatusTree();
            this.bindEvents();
            this.initIntersectionObserver();
            this.loadPlatforms().catch(err => {
                console.error('加载平台列表失败:', err);
            });
            this.updateStorageStats().catch(err => {
                console.error('更新存储统计失败:', err);
            });
            this.initialized = true;
        } catch (error) {
            console.error('ArticleManager 初始化失败:', error);
        } finally {
            this.initializing = false;
        }
    }

    // 加载平台列表(仅初始化时调用一次)  
    async loadPlatforms() {
        try {
            const response = await fetch('/api/config/platforms');
            if (response.ok) {
                const result = await response.json();
                this.platforms = result.data || [];
            }
        } catch (error) {
            console.error('加载平台列表失败:', error);
        }
    }

    // 加载文章列表  
    async loadArticles() {
        try {
            const response = await fetch('/api/articles');
            if (response.ok) {
                const result = await response.json();
                // 与模板管理保持一致,提取 data 字段  
                this.articles = result.data || [];
                this.filterArticles();
            }
        } catch (error) {
            console.error('加载文章失败:', error);
            this.showNotification('加载文章失败', 'error');
        }
    }

    // 渲染状态分类树  
    renderStatusTree() {
        const statusTree = document.getElementById('article-sidebar-tree');
        if (!statusTree) return;

        const statusCounts = {
            all: this.articles.length,
            published: this.articles.filter(a => a.status === 'published').length,
            failed: this.articles.filter(a => a.status === 'failed').length,
            unpublished: this.articles.filter(a => a.status === 'unpublished').length
        };

        const statuses = [
            {
                key: 'all',
                label: '全部文章',
                icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>  
                    <polyline points="14,2 14,8 20,8"/>  
                </svg>`
            },
            {
                key: 'published',
                label: '已发布',
                icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>  
                    <polyline points="22 4 12 14.01 9 11.01"/>  
                </svg>`
            },
            {
                key: 'failed',
                label: '发布失败',
                icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                    <circle cx="12" cy="12" r="10"/>  
                    <line x1="15" y1="9" x2="9" y2="15"/>  
                    <line x1="9" y1="9" x2="15" y2="15"/>  
                </svg>`
            },
            {
                key: 'unpublished',
                label: '未发布',
                icon: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                    <circle cx="12" cy="12" r="10"/>  
                    <line x1="8" y1="12" x2="16" y2="12"/>  
                </svg>`
            }
        ];

        statusTree.innerHTML = statuses.map(status => `  
            <div class="tree-item ${this.currentStatus === status.key ? 'active' : ''}"   
                data-status="${status.key}">  
                <div>  
                    <span class="tree-icon">${status.icon}</span>  
                    <span>${status.label}</span>  
                </div>  
                <span class="item-count">${statusCounts[status.key]}</span>  
            </div>  
        `).join('');
    }

    // 过滤文章  
    filterArticles() {
        if (this.currentStatus === 'all') {
            this.filteredArticles = [...this.articles];
        } else {
            this.filteredArticles = this.articles.filter(
                article => article.status === this.currentStatus
            );
        }
        this.renderArticles();
    }

    // 渲染文章卡片  
    renderArticles() {
        const grid = document.getElementById('article-content-grid');
        if (!grid) return;

        grid.className = `content-grid ${this.currentLayout === 'list' ? 'list-view' : ''}`;

        // 添加空状态判断  
        if (this.filteredArticles.length === 0) {
            grid.innerHTML = '<div class="empty-state">暂无文章</div>';
            return;
        }

        grid.innerHTML = '';

        this.filteredArticles.forEach(article => {
            const card = this.createArticleCard(article);
            grid.appendChild(card);
        });

        this.bindCardEvents();

        requestAnimationFrame(() => {
            if (this.observer) {
                const cards = grid.querySelectorAll('.content-card');
                cards.forEach(card => this.observer.observe(card));
            }
        });
    }

    // 创建文章卡片  
    createArticleCard(article) {
        const card = document.createElement('div');
        card.className = `content-card article-card ${this.batchMode ? 'batch-mode' : ''}`;
        card.dataset.path = article.path;
        card.dataset.title = article.title;

        const statusClass = {
            'published': 'published',
            'failed': 'failed',
            'unpublished': 'unpublished'
        }[article.status] || 'unpublished';

        const statusText = {
            'published': '已发布',
            'failed': '发布失败',
            'unpublished': '未发布'
        }[article.status] || '未发布';

        // 时间格式化函数  
        const formatTime = (timeStr) => {
            const date = new Date(timeStr);
            const today = new Date();
            const diffDays = Math.floor((today - date) / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return '今天';
            if (diffDays === 1) return '昨天';
            if (diffDays < 7) return `${diffDays}天前`;
            return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
        };

        card.innerHTML = `  
            <label class="checkbox-wrapper">  
                <input type="checkbox" class="batch-checkbox" ${this.selectedArticles.has(article.path) ? 'checked' : ''}>  
                <span class="checkbox-custom"></span>  
            </label>  
            <div class="card-preview">  
                <iframe sandbox="allow-same-origin allow-scripts"   
                        loading="lazy"   
                        data-article-path="${article.path}"  
                        data-loaded="false"
                        onload="this.parentElement.querySelector('.preview-loading').style.display='none'"
                        onerror="this.parentElement.querySelector('.preview-loading').style.display='none'"></iframe>  
                <div class="preview-loading">加载中...</div>  
            </div>  
            <div class="card-content">
                <h4 class="card-title" title="${this.escapeHtml(article.title)}">${this.escapeHtml(article.title)}</h4>
                <div class="card-meta">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                    <span class="time-info">${formatTime(article.updated_at || article.created_at)}</span>
                    ${article.size ? `<span class="size-info">${article.size}</span>` : ''}
                </div>
            </div>
            <div class="card-actions">  
                <button class="btn-icon" data-action="edit" title="编辑">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>  
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>  
                    </svg>  
                </button>  
                <button class="btn-icon" data-action="view-source" title="查看原始热点内容">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                    </svg>
                </button>
                <button class="btn-icon" data-action="re-template" title="AI 换模板">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
                    </svg>
                </button>
                <button class="btn-icon" data-action="optimize-title" title="AI 换标题">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        <path d="M9 11l3 3"/>
                    </svg>
                </button>
                <button class="btn-icon" data-action="generate-images" title="AI 配图">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>  
                        <circle cx="8.5" cy="8.5" r="1.5"/>  
                        <polyline points="21 15 16 10 5 21"/>  
                    </svg>  
                </button>  
                <button class="btn-icon" data-action="illustration" title="设计">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <rect x="3" y="3" width="7" height="7"/>  
                        <rect x="14" y="3" width="7" height="7"/>  
                        <rect x="3" y="14" width="7" height="7"/>  
                        <rect x="14" y="14" width="7" height="7"/>  
                        <path d="M10 10l4 4"/>  
                    </svg>     
                </button>  
                <button class="btn-icon" data-action="publish" title="发布">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <path d="M22 2L11 13"/>  
                        <path d="M22 2l-7 20-4-9-9-4 20-7z"/>  
                    </svg>  
                </button>  
                <button class="btn-icon vote-btn" data-action="vote" title="审美投票">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" style="color: #ff4d4f;">  
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l8.78-8.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>  
                    </svg>  
                </button>
                <button class="btn-icon" data-action="vote" title="审美投票 (影响 AI DNA)">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
                </svg>
            </button>
            <button class="btn-icon" data-action="delete" title="删除">
  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <polyline points="3 6 5 6 21 6"/>  
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>  
                    </svg>  
                </button>  
            </div>  
        `;

        return card;
    }

    async openImageDesigner(article) {
        try {
            // 检查文件扩展名  
            const ext = article.path.toLowerCase().split('.').pop();

            if (ext === 'md' || ext === 'markdown' || ext === 'txt') {
                // 显示警告对话框,让用户选择是否继续  
                window.dialogManager.showConfirm(
                    `警告: ${ext.toUpperCase()} 格式文件不适合使用可视化设计器编辑。\n` +
                    `使用页面设计器可能会破坏原始格式,建议使用"编辑"功能进行修改。\n` +
                    `是否仍要继续使用页面设计器？`,
                    async () => {
                        // 用户点击确认,继续打开设计器  
                        if (!window.imageDesignerDialog) {
                            window.imageDesignerDialog = new ImageDesignerDialog();
                        }
                        await window.imageDesignerDialog.open(article.path, article.title);
                    },
                    () => {
                        // 用户点击取消,不执行任何操作  
                    }
                );
            } else {
                // HTML 文件,直接打开  
                if (!window.imageDesignerDialog) {
                    window.imageDesignerDialog = new ImageDesignerDialog();
                }
                await window.imageDesignerDialog.open(article.path, article.title);
            }
        } catch (error) {
            this.showNotification('打开配图设计器失败: ' + error.message, 'error');
        }
    }

    // 添加新方法显示发布历史  
    async showPublishHistory(article) {
        try {
            const response = await fetch(`/api/articles/publish-history/${encodeURIComponent(article.path)}`);
            if (!response.ok) {
                throw new Error('获取发布历史失败');
            }

            const result = await response.json();
            const records = result.data.records || [];

            // 显示发布历史对话框  
            this.renderPublishHistoryDialog(article, records);
        } catch (error) {
            this.showNotification('获取发布历史失败: ' + error.message, 'error');
        }
    }

    renderPublishHistoryDialog(article, records) {
        const dialogHtml = `  
            <div class="modal-overlay" id="publish-history-dialog">  
                <div class="modal-content publish-history-modal">  
                    <div class="modal-header">  
                        <h3>发布记录</h3>  
                        <button class="modal-close" onclick="window.articleManager.closePublishHistoryDialog()">×</button>  
                    </div>  
                    <div class="modal-body">  
                        <div class="article-info">  
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>  
                                <polyline points="14,2 14,8 20,8"/>  
                            </svg>  
                            <span class="article-title">${this.escapeHtml(article.title)}</span>  
                        </div>  
                        
                        ${records.length === 0 ? `  
                            <div class="empty-state">  
                                <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor">  
                                    <circle cx="12" cy="12" r="10"/>  
                                    <line x1="12" y1="8" x2="12" y2="12"/>  
                                    <line x1="12" y1="16" x2="12.01" y2="16"/>  
                                </svg>  
                                <p>暂无发布记录</p>  
                            </div>  
                        ` : `  
                            <div class="history-timeline">  
                                ${records.map((record, index) => {
            // 【修改】从 account_info 中提取信息  
            const accountInfo = record.account_info || {};
            const platform = record.platform || 'unknown';
            const platformName = {
                'wechat': '微信公众号',
                'xiaohongshu': '小红书',
                'douyin': '抖音'
            }[platform] || platform;

            return `  
                                        <div class="history-item ${record.success ? 'success' : 'failed'}">  
                                            <div class="history-icon">  
                                                ${record.success ? `  
                                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">  
                                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>  
                                                        <polyline points="22 4 12 14.01 9 11.01"/>  
                                                    </svg>  
                                                ` : `  
                                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">  
                                                        <circle cx="12" cy="12" r="10"/>  
                                                        <line x1="15" y1="9" x2="9" y2="15"/>  
                                                        <line x1="9" y1="9" x2="15" y2="15"/>  
                                                    </svg>  
                                                `}  
                                            </div>  
                                            <div class="history-content">  
                                                <div class="history-header">  
                                                    <span class="history-platform">${this.escapeHtml(platformName)}</span>  
                                                    <span class="history-account">${this.escapeHtml(accountInfo.author || '未知账号')}</span>  
                                                    ${accountInfo.appid ? `<span class="history-appid">AppID: ${this.escapeHtml(accountInfo.appid)}</span>` : ''}  
                                                </div>  
                                                <div class="history-time">${this.formatHistoryTime(record.timestamp)}</div>  
                                                ${record.error ? `  
                                                    <div class="history-${record.success ? 'warning' : 'error'}">  
                                                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor">  
                                                            ${record.success ? `  
                                                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>  
                                                                <line x1="12" y1="9" x2="12" y2="13"/>  
                                                                <line x1="12" y1="17" x2="12.01" y2="17"/>  
                                                            ` : `  
                                                                <circle cx="12" cy="12" r="10"/>  
                                                                <line x1="12" y1="8" x2="12" y2="12"/>  
                                                                <line x1="12" y1="16" x2="12.01" y2="16"/>  
                                                            `}  
                                                        </svg>  
                                                        <span>${this.escapeHtml(this.truncateError(record.error))}</span>  
                                                    </div>  
                                                ` : ''}  
                                            </div>  
                                            ${index < records.length - 1 ? '<div class="history-line"></div>' : ''}  
                                        </div>  
                                    `;
        }).join('')}  
                            </div>  
                        `}  
                    </div>  
                </div>  
            </div>  
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);
    }

    // 辅助方法:格式化时间  
    formatHistoryTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return '刚刚';
        if (diffMins < 60) return `${diffMins}分钟前`;
        if (diffHours < 24) return `${diffHours}小时前`;
        if (diffDays < 7) return `${diffDays}天前`;

        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // 辅助方法:截断错误信息  
    truncateError(error) {
        if (!error) return '';
        const maxLength = 100;
        return error.length > maxLength ? error.substring(0, maxLength) + '...' : error;
    }

    closePublishHistoryDialog() {
        const dialog = document.getElementById('publish-history-dialog');
        if (dialog) dialog.remove();
    }

    // 绑定卡片事件  
    bindCardEvents() {
        const grid = document.getElementById('article-content-grid');
        if (!grid) return;

        grid.querySelectorAll('.article-card').forEach(card => {
            // 状态徽章点击事件  
            const statusBadge = card.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.addEventListener('click', (e) => {
                    e.stopPropagation(); // 阻止事件冒泡  
                    const path = card.dataset.path;
                    const article = this.articles.find(a => a.path === path);
                    if (article) {
                        this.showPublishHistory(article);
                    }
                });
            }

            // 卡片点击预览  
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.card-actions') &&
                    !e.target.closest('.batch-checkbox') &&
                    !e.target.closest('.checkbox-wrapper')) {
                    const path = card.dataset.path;
                    const article = this.articles.find(a => a.path === path);
                    if (article) {
                        this.previewArticle(article);
                    }
                }
            });

            // 操作按钮点击  
            card.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const action = btn.dataset.action;
                    const path = card.dataset.path;
                    const article = this.articles.find(a => a.path === path);
                    if (article) {
                        this.handleCardAction(action, article);
                    }
                });
            });
        });
    }

    async handleCardAction(action, article) {
        switch (action) {
            case 'edit':
                await this.editArticle(article);
                break;
            case 're-template':
                if (window.taskQueue) {
                    window.taskQueue.enqueue({
                        type: 're-template',
                        title: `AI 换模板: ${article.topic || '未命名'}`,
                        data: article
                    });
                } else {
                    await this.openReTemplateModal(article);
                }
                break;
            case 'generate-images':
                if (window.taskQueue) {
                    window.taskQueue.enqueue({
                        type: 'image-gen',
                        title: `AI 智能配图: ${article.topic || '未命名'}`,
                        data: article
                    });
                } else {
                    await this.generateImages(article);
                }
                break;
            case 'illustration':
                await this.openImageDesigner(article)
                break;
            case 'publish':
                await this.showPublishDialog(article.path);
                break;
            case 'delete':
                await this.deleteArticle(article.path);
                break;
            case 'view-source':
                await this.showArticleSource(article);
                break;
            case 'optimize-title':
                await this.optimizeTitle(article);
                break;
            case 'vote':
                if (window.aestheticVotingManager) {
                    await window.aestheticVotingManager.open({
                        type: 'article',
                        path: article.path,
                        title: article.title
                    });
                } else {
                    window.app?.showNotification('投票管理器未加载', 'error');
                }
                break;
        }
    }

    // AI 后期补图 - 带进度弹窗
    async generateImages(article) {
        // 创建进度弹窗
        const dialogId = 'img-gen-progress-dialog';
        const existingDialog = document.getElementById(dialogId);
        if (existingDialog) existingDialog.remove();

        const dialogHtml = `
            <div class="modal-overlay" id="${dialogId}">
                <div class="modal-content" style="max-width:560px;max-height:80vh;display:flex;flex-direction:column">
                    <div class="modal-header">
                        <h3 style="display:flex;align-items:center;gap:8px">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                <circle cx="8.5" cy="8.5" r="1.5"/>
                                <polyline points="21 15 16 10 5 21"/>
                            </svg>
                            AI 配图 - ${this.escapeHtml(article.title.slice(0, 30))}
                        </h3>
                        <button class="modal-close" id="img-gen-close-btn" disabled>×</button>
                    </div>
                    <div class="modal-body" style="flex:1;overflow:hidden;display:flex;flex-direction:column;gap:12px">
                        <div id="img-gen-status" style="font-weight:600;color:var(--primary-color,#3a7bd5);display:flex;align-items:center;gap:8px">
                            <svg class="spin" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" id="img-gen-spinner">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                            </svg>
                            <span id="img-gen-status-text">正在扫描文章占位符...</span>
                        </div>
                        <div style="background:var(--bg-tertiary,#1a1a2e);border-radius:8px;padding:12px;flex:1;overflow-y:auto;font-family:monospace;font-size:12px;line-height:1.6;color:#a0aec0;min-height:200px;max-height:400px" id="img-gen-log">
                            <div style="color:#718096">[${new Date().toLocaleTimeString()}] 开始处理...</div>
                        </div>
                        <div id="img-gen-progress-bar" style="height:6px;border-radius:3px;background:var(--border-color,#2a2a3e);overflow:hidden;display:none">
                            <div id="img-gen-progress-fill" style="height:100%;width:0%;background:linear-gradient(90deg,#3a7bd5,#00d2ff);border-radius:3px;transition:width 0.5s ease"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', dialogHtml);

        // 添加 spin 动画样式
        if (!document.getElementById('spin-style')) {
            const style = document.createElement('style');
            style.id = 'spin-style';
            style.textContent = `@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}.spin{animation:spin 1s linear infinite}`;
            document.head.appendChild(style);
        }

        const logEl = document.getElementById('img-gen-log');
        const statusText = document.getElementById('img-gen-status-text');
        const closeBtn = document.getElementById('img-gen-close-btn');
        const spinner = document.getElementById('img-gen-spinner');
        const progressBar = document.getElementById('img-gen-progress-bar');
        const progressFill = document.getElementById('img-gen-progress-fill');

        const addLog = (msg, type = 'info') => {
            const colors = { info: '#a0aec0', success: '#68d391', error: '#fc8181', warning: '#f6ad55', status: '#63b3ed' };
            const icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️', status: '🎨' };
            const div = document.createElement('div');
            div.style.color = colors[type] || colors.info;
            div.innerHTML = `<span style="opacity:0.5">[${new Date().toLocaleTimeString()}]</span> ${icons[type] || ''} ${msg}`;
            logEl.appendChild(div);
            logEl.scrollTop = logEl.scrollHeight;
        };

        // 注册到后台任务管理，以便可以在全局任务列表中看到
        this.addTask('current-img-gen', {
            name: `AI 配图: ${article.title}`,
            type: 'image-gen',
            id: 'current-img-gen'
        });

        // 开始轮询后端日志
        let polling = true;
        let lastLogIndex = 0;
        const pollLogs = async () => {
            while (polling) {
                try {
                    const res = await fetch(`/api/articles/logs?since=${lastLogIndex}&limit=50`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.logs && data.logs.length > 0) {
                            for (const log of data.logs) {
                                const msg = log.message || log;
                                if (typeof msg === 'string') {
                                    let type = 'info';
                                    if (msg.includes('✅') || msg.includes('成功') || msg.includes('完毕')) type = 'success';
                                    else if (msg.includes('❌') || msg.includes('失败') || msg.includes('ERROR') || msg.includes('错误')) type = 'error';
                                    else if (msg.includes('⚠') || msg.includes('警告') || msg.includes('WARNING')) type = 'warning';
                                    else if (msg.includes('🎨') || msg.includes('正在生成')) type = 'status';
                                    addLog(msg.replace(/\[.*?\]\s*/, ''), type);

                                    // 更新进度条 - 匹配 "第 X/Y 张" 格式
                                    const progressMatch = msg.match(/第\s*(\d+)\/(\d+)\s*张/);
                                    if (progressMatch) {
                                        const current = parseInt(progressMatch[1]);
                                        const total = parseInt(progressMatch[2]);
                                        progressBar.style.display = 'block';
                                        progressFill.style.width = `${(current / total) * 100}%`;
                                        statusText.textContent = `正在生成第 ${current}/${total} 张图片...`;
                                    }
                                    // 也匹配采样进度 "采样 X/Y"
                                    const samplingMatch = msg.match(/采样.*?(\d+)\/(\d+)/);
                                    if (samplingMatch) {
                                        const step = parseInt(samplingMatch[1]);
                                        const maxStep = parseInt(samplingMatch[2]);
                                        statusText.textContent = `采样中 ${step}/${maxStep}...`;
                                    }
                                }
                            }
                            lastLogIndex = data.nextIndex || (lastLogIndex + data.logs.length);
                        }
                    }
                } catch (e) { /* ignore poll errors */ }
                await new Promise(r => setTimeout(r, 800));
            }
        };

        // 启动日志轮询（不阻塞）
        const pollPromise = pollLogs();

        // 调用后端生成
        return new Promise(async (resolve, reject) => {
            try {
                addLog('正在调用图片生成 API...', 'status');
                statusText.textContent = '正在调用图片生成 API...';

                const res = await fetch('/api/articles/generate-images', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: article.path })
                });
                const data = await res.json();

                polling = false; // 停止轮询
                await new Promise(r => setTimeout(r, 500)); // 等最后一批日志

                if (res.ok && data.status === 'success') {
                    if (data.generated > 0) {
                        progressBar.style.display = 'block';
                        progressFill.style.width = '100%';
                        statusText.textContent = `✅ ${data.message}`;
                        spinner.style.display = 'none';
                        addLog(data.message, 'success');
                        await this.loadArticles();
                        resolve(true); // 完成
                    } else {
                        statusText.textContent = `ℹ️ ${data.message}`;
                        spinner.style.display = 'none';
                        addLog(data.message, 'info');
                        resolve(true); // 无需生成也算完成
                    }
                } else {
                    statusText.textContent = `❌ 生成失败`;
                    spinner.style.display = 'none';
                    addLog(`错误: ${data.detail || '未知错误'}`, 'error');
                    resolve(false); // 失败也算结束任务
                }
            } catch (e) {
                polling = false;
                statusText.textContent = `❌ 请求失败`;
                spinner.style.display = 'none';
                addLog(`网络错误: ${e.message}`, 'error');
                resolve(false);
            }

            // 启用关闭按钮
            closeBtn.disabled = false;
            closeBtn.style.cursor = 'pointer';
            closeBtn.addEventListener('click', () => {
                document.getElementById(dialogId)?.remove();
            });

            // 通知任务队列此任务已执行完毕
            if (window.taskQueue && window.taskQueue.currentTask && window.taskQueue.currentTask.type === 'image-gen') {
                window.taskQueue.taskComplete(window.taskQueue.currentTask.id);
            }

            // 更新后台任务状态
            this.updateTask('current-img-gen', { progress: 100, status: 'done' });
            setTimeout(() => this.removeTask('current-img-gen'), 3000);
        });
    }

    // 初始化懒加载观察器    
    initIntersectionObserver() {
        const options = {
            root: document.querySelector('#article-manager-view .manager-main'),
            rootMargin: '200px',  // 提前200px开始加载  
            threshold: 0.01
        };

        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const card = entry.target;  // 观察的是卡片本身  
                    const iframe = card.querySelector('iframe[data-article-path]');
                    if (iframe && iframe.dataset.loaded !== 'true') {
                        this.loadSinglePreview(iframe);
                        this.observer.unobserve(card);  // 加载后立即取消观察  
                    }
                }
            });
        }, options);
    }

    // 加载单个预览    
    async loadSinglePreview(iframe) {
        if (iframe.dataset.loaded === 'true') return;
        const card = iframe.closest('.article-card');
        const path = card.dataset.path;
        const loadingEl = card.querySelector('.preview-loading');

        try {
            const response = await fetch(`/api/articles/content?path=${encodeURIComponent(path)}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const content = await response.text();

            const ext = path.toLowerCase().split('.').pop();
            let htmlContent = content;

            if ((ext === 'md' || ext === 'markdown') && window.markdownRenderer) {
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                htmlContent = window.markdownRenderer.render(content, isDark);
            } else if (ext === 'txt') {
                htmlContent = content.split('\n')
                    .map(line => line.trim() ? `<p>${line}</p>` : '<br>')
                    .join('\n');
            }

            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const bgColor = isDark ? '#1a1a1a' : '#ffffff';
            const textColor = isDark ? '#e0e0e0' : '#333333';
            const borderColor = isDark ? '#333333' : '#eeeeee';
            const preBg = isDark ? '#2d2d2d' : '#f5f5f5';

            const styledHtml = `
                <style>
                    body {
                        margin: 0;
                        padding: 0; /* 移除默认 padding，让全宽模板可以正常撑满 */
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        font-size: 11px;
                        line-height: 1.6;
                        color: ${textColor};
                        background: ${bgColor};
                        overflow-x: hidden;
                    }
                    /* 给普通内容添加基础内间距容器，防止贴边 */
                    .article-container { 
                        padding: 16px; 
                    }
                    /* 如果是自定义 HTML 模板内容，不加容器 */
                    /* 标题样式 */
                    h1, h2, h3, h4, h5, h6 { margin: 8px 0 4px 0; font-weight: 600; color: ${isDark ? '#fff' : '#000'}; }
                    h1 { font-size: 1.4em; }
                    h2 { font-size: 1.25em; }
                    h3 { font-size: 1.1em; }
                    /* 段落样式 */
                    p { margin: 0 0 6px 0; }
                    /* 引用块样式 */
                    blockquote {
                        margin: 4px 0;
                        padding: 2px 8px;
                        border-left: 3px solid #3a7bd5;
                        background: ${isDark ? '#252525' : '#f0f7ff'};
                        font-style: italic;
                    }
                    /* 代码样式 */
                    code { background: ${preBg}; padding: 1px 3px; border-radius: 3px; font-family: monospace; }
                    pre { background: ${preBg}; padding: 6px; border-radius: 4px; overflow: hidden; margin: 6px 0; }
                    pre code { background: none; padding: 0; }
                    /* 列表样式 */
                    ul, ol { margin: 4px 0; padding-left: 16px; }
                    li { margin-bottom: 2px; }
                    /* 图片样式 */
                    img { max-width: 100%; height: auto; border-radius: 4px; }
                    /* 隐藏滚动条 */
                    ::-webkit-scrollbar { display: none !important; }
                    * { scrollbar-width: none !important; }
                    ul, ol {
                        margin: 2px 0;
                        padding-left: 16px;
                    }

                    li {
                        margin: 1px 0;
                    }

                    /* 分割线样式 */
                    hr {
                        height: 1px;
                        background: #ddd;
                        border: 0;
                        margin: 4px 0;
                    }

                </style>
                ${htmlContent}
            `;

            iframe.srcdoc = styledHtml;
            iframe.dataset.loaded = 'true';
            if (loadingEl) loadingEl.style.display = 'none';

        } catch (error) {
            console.error('加载预览失败:', error);
            const is404 = error.message.includes('404');
            const errorMsg = is404 ? '文章文件已删除 (可能已发布并触发自动清理)' : `加载预览失败: ${error.message}`;
            iframe.srcdoc = `<div style="padding:20px; color:#999; text-align:center; font-size:12px; display:flex; flex-direction:column; align-items:center; gap:10px;">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <span>${errorMsg}</span>
            </div>`;
        }
    }


    // 绑定事件  
    bindEvents() {
        // 状态树点击    
        document.getElementById('article-sidebar-tree')?.addEventListener('click', (e) => {
            const item = e.target.closest('.tree-item');
            if (item) {
                this.currentStatus = item.dataset.status;
                this.filterArticles();
                this.renderStatusTree();
            }
        });

        // 搜索    
        document.getElementById('article-search')?.addEventListener('input', (e) => {
            this.searchArticles(e.target.value);
        });

        // 视图切换 - 删除全局绑定,只保留限定作用域的绑定  
        const articleView = document.getElementById('article-manager-view');
        if (articleView) {
            articleView.querySelectorAll('.view-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    // 只移除文章管理视图内的active状态    
                    articleView.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.currentLayout = btn.dataset.layout;
                    this.renderArticles();
                });
            });
        }

        // 批量操作模式    
        document.getElementById('batch-mode-toggle')?.addEventListener('click', () => {
            this.toggleBatchMode();
        });

        // 批量删除    
        document.getElementById('batch-delete')?.addEventListener('click', () => {
            this.batchDelete();
        });

        // 批量发布    
        document.getElementById('batch-publish')?.addEventListener('click', () => {
            this.batchPublish();
        });

        // 全选
        document.getElementById('batch-select-all')?.addEventListener('click', () => {
            this.selectAll();
        });

        // 反选
        document.getElementById('batch-select-invert')?.addEventListener('click', () => {
            this.invertSelection();
        });

        // 卡片复选框变化    
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('batch-checkbox')) {
                const card = e.target.closest('.article-card');
                const path = card.dataset.path;
                if (e.target.checked) {
                    this.selectedArticles.add(path);
                } else {
                    this.selectedArticles.delete(path);
                }
                this.updateBatchCount();
            }
        });

        // 平台选择变化  
        const platformSelect = document.getElementById('publish-platform-select');
        if (platformSelect) {
            platformSelect.addEventListener('change', (e) => {
                this.onPlatformChange(e.target.value);
            });
        }

        // 快捷键刷新 (F5 或 Ctrl+R) - 隐藏功能    
        document.addEventListener('keydown', (e) => {
            const articleView = document.getElementById('article-manager-view');
            if (articleView && articleView.style.display !== 'none') {
                if (e.key === 'F5' || ((e.ctrlKey || e.metaKey) && e.key === 'r')) {
                    e.preventDefault();
                    this.refreshArticles();
                }
            }
        });
    }

    async refreshArticles() {
        try {
            await this.loadArticles();
            this.renderStatusTree();
            this.renderArticles();

            window.app?.showNotification('已刷新文章列表', 'success');
        } catch (error) {
            window.app?.showNotification('刷新失败: ' + error.message, 'error');
        }
    }

    // 搜索文章  
    searchArticles(query) {
        if (!query.trim()) {
            this.filterArticles();
            return;
        }

        const lowerQuery = query.toLowerCase();
        this.filteredArticles = this.articles.filter(article =>
            article.title.toLowerCase().includes(lowerQuery)
        );
        this.renderArticles();
    }

    // 切换批量操作模式  
    toggleBatchMode() {
        this.batchMode = !this.batchMode;

        const toggleBtn = document.getElementById('batch-mode-toggle');
        const subActions = document.querySelector('.batch-sub-actions');
        const batchCount = toggleBtn.querySelector('.batch-count');
        const batchText = toggleBtn.querySelector('.batch-mode-text');

        if (this.batchMode) {
            // 进入批量模式  
            toggleBtn.classList.add('active');
            batchText.textContent = '退出批量';
            batchCount.style.display = 'inline';
            subActions.style.display = 'flex';

            // 只更新卡片class,不重新渲染  
            document.querySelectorAll('.article-card').forEach(card => {
                card.classList.add('batch-mode');
            });
        } else {
            // 退出批量模式  
            toggleBtn.classList.remove('active');
            batchText.textContent = '批量操作';
            batchCount.style.display = 'none';
            subActions.style.display = 'none';

            // 清空选中状态  
            this.selectedArticles.clear();

            // 只更新卡片class,不重新渲染  
            document.querySelectorAll('.article-card').forEach(card => {
                card.classList.remove('batch-mode');
                const checkbox = card.querySelector('.batch-checkbox');
                if (checkbox) checkbox.checked = false;
            });
        }

        this.updateBatchCount();
    }

    // 全选
    selectAll() {
        if (!this.filteredArticles || this.filteredArticles.length === 0) return;

        this.filteredArticles.forEach(article => {
            this.selectedArticles.add(article.path);
        });

        // 更新 UI
        document.querySelectorAll('.article-card').forEach(card => {
            const checkbox = card.querySelector('.batch-checkbox');
            if (checkbox) checkbox.checked = true;
        });

        this.updateBatchCount();
    }

    // 反选
    invertSelection() {
        if (!this.filteredArticles || this.filteredArticles.length === 0) return;

        this.filteredArticles.forEach(article => {
            if (this.selectedArticles.has(article.path)) {
                this.selectedArticles.delete(article.path);
            } else {
                this.selectedArticles.add(article.path);
            }
        });

        // 更新 UI
        document.querySelectorAll('.article-card').forEach(card => {
            const path = card.dataset.path;
            const checkbox = card.querySelector('.batch-checkbox');
            if (checkbox) {
                checkbox.checked = this.selectedArticles.has(path);
            }
        });

        this.updateBatchCount();
    }

    updateBatchCount() {
        const count = this.selectedArticles.size;
        const batchCount = document.querySelector('.batch-count');
        const batchPublish = document.getElementById('batch-publish');
        const batchDelete = document.getElementById('batch-delete');

        if (batchCount) {
            batchCount.textContent = `(已选 ${count})`;
        }

        // 根据选中数量启用/禁用子按钮  
        if (batchPublish) batchPublish.disabled = count === 0;
        if (batchDelete) batchDelete.disabled = count === 0;
    }

    // 更新批量操作按钮状态  
    updateBatchButtons() {
        const batchDelete = document.getElementById('batch-delete');
        const batchPublish = document.getElementById('batch-publish');

        if (this.selectedArticles.size > 0) {
            batchDelete.style.display = 'block';
            batchPublish.style.display = 'block';
        } else {
            batchDelete.style.display = 'none';
            batchPublish.style.display = 'none';
        }
    }

    // 预览文章  
    async previewArticle(article) {
        try {
            const response = await fetch(`/api/articles/content?path=${encodeURIComponent(article.path)}`);
            if (response.ok) {
                const content = await response.text();

                // 检测是否为HTML内容 (即使扩展名是.md)
                const isHtml = content.trim().startsWith('<');
                const ext = article.path.toLowerCase().split('.').pop();
                let htmlContent = content;

                if (isHtml) {
                    // 如果内容本身就是HTML,无论扩展名是什么,都直接作为HTML预览
                    htmlContent = content;
                } else if ((ext === 'md' || ext === 'markdown') && window.markdownRenderer) {
                    // 只有在不是HTML的情况下,才尝试Markdown渲染
                    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                    htmlContent = window.markdownRenderer.renderWithStyles(content, isDark);
                } else if (ext === 'txt') {
                    // TXT文件:生成带滚动条的完整文档  
                    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                    const computedStyle = getComputedStyle(document.documentElement);
                    const bgColor = computedStyle.getPropertyValue('--background-color').trim();
                    const borderColor = computedStyle.getPropertyValue('--border-color').trim();
                    const secondaryColor = computedStyle.getPropertyValue('--secondary-color').trim();
                    const textColor = computedStyle.getPropertyValue('--text-primary').trim();

                    // 将纯文本转换为HTML段落  
                    const txtHtml = content.split('\n')
                        .map(line => line.trim() ? `<p>${line}</p>` : '<br>')
                        .join('\n');

                    htmlContent = `
                        <!DOCTYPE html>
                            <html>
                                <head>
                                    <meta charset="UTF-8">
                                        <style>
                                            body {
                                                margin: 0;
                                            padding: 16px;
                                            overflow: auto;
                                            color: ${textColor};
                                            background: transparent;
                                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                                            line-height: 1.6;  
            }

                                            p {
                                                margin: 0 0 16px 0;  
            }

                                            /* 使用与全局CSS相同的滚动条样式 */
                                            ::-webkit-scrollbar {
                                                width: 6px;
                                            height: 6px;  
            }

                                            ::-webkit-scrollbar-track {
                                                background: ${bgColor};  
            }

                                            ::-webkit-scrollbar-thumb {
                                                background: ${borderColor};
                                            border-radius: 3px;  
            }

                                            ::-webkit-scrollbar-thumb:hover {
                                                background: ${secondaryColor};  
            }
                                        </style>
                                </head>
                                <body>
                                    ${txtHtml}
                                </body>
                            </html>
                    `;
                }

                // 更新预览面板
                if (window.previewPanelManager) {
                    window.previewPanelManager.showWithActions(htmlContent, article);
                } else {
                    window.app?.showNotification('预览面板未初始化', 'error');
                }
            } else if (response.status === 404) {
                window.app?.showNotification('文章文件已删除（可能已发布并触发自动清理）', 'warning');
            } else {
                window.app?.showNotification(`获取文章内容失败 (HTTP ${response.status})`, 'error');
            }
        } catch (error) {
            console.error('预览异常:', error);
            window.app?.showNotification('预览失败: ' + error.message, 'error');
        }
    }

    // 显示发布对话框  
    async showPublishDialog(path) {
        this.publishingArticles = [path];
        await this.loadAccountsAndShowDialog();
    }

    // 批量发布  
    async batchPublish() {
        if (this.selectedArticles.size === 0) {
            window.app?.showNotification('请先选择要发布的文章', 'warning');
            return;
        }

        this.publishingArticles = Array.from(this.selectedArticles);
        await this.loadAccountsAndShowDialog();
    }

    // 加载平台并显示对话框  
    async loadAccountsAndShowDialog() {
        try {
            // 清除缓存,强制重新加载    
            this.platformAccounts = {};

            // 如果平台列表未加载,先加载  
            if (!this.platforms) {
                await this.loadPlatforms();
            }

            // 填充平台选择器  
            const platformSelect = document.getElementById('publish-platform-select');
            if (platformSelect) {
                platformSelect.innerHTML = '<option value="">请选择发布平台...</option>' +
                    this.platforms.map(p => `<option value="${p.value}">${p.label}</option>`).join('');
            }

            // 隐藏账号选择区域,等待用户选择平台  
            document.getElementById('account-selection-group').style.display = 'none';
            document.getElementById('no-accounts-tip').style.display = 'none';

            // 禁用确认按钮  
            document.getElementById('confirm-publish-btn').disabled = true;

            // 显示对话框  
            document.getElementById('publish-dialog').style.display = 'flex';
        } catch (error) {
            window.app?.showNotification('加载平台列表失败: ' + error.message, 'error');
        }
    }

    // 平台选择变化    
    async onPlatformChange(platformId) {
        const accountSelectionGroup = document.getElementById('account-selection-group');
        const noAccountsTip = document.getElementById('no-accounts-tip');
        const accountList = document.getElementById('account-list');

        if (!platformId) {
            accountSelectionGroup.style.display = 'none';
            noAccountsTip.style.display = 'none';
            this.updatePublishButtonState();
            return;
        }

        try {
            // 检查缓存    
            if (this.platformAccounts[platformId]) {
                this.renderPlatformAccounts(platformId, this.platformAccounts[platformId]);
                return;
            }

            // 获取该平台的账号列表    
            const response = await fetch('/api/config/');
            if (!response.ok) throw new Error('加载配置失败');

            const config = await response.json();
            let accounts = [];

            if (platformId === 'wechat') {
                const allCredentials = config.data?.wechat?.credentials || [];
                const validCredentials = allCredentials.filter(cred => cred.appid && cred.appid.trim() !== '');

                accounts = validCredentials.map((cred, index) => ({
                    index: allCredentials.indexOf(cred),
                    author: cred.author || '未命名',
                    appid: cred.appid
                }));
            }

            // 缓存账号列表    
            this.platformAccounts[platformId] = accounts;

            this.renderPlatformAccounts(platformId, accounts);
        } catch (error) {
            window.app?.showNotification('加载账号失败: ' + error.message, 'error');
        }
    }

    // 渲染平台账号列表    
    renderPlatformAccounts(platformId, accounts) {
        const accountSelectionGroup = document.getElementById('account-selection-group');
        const noAccountsTip = document.getElementById('no-accounts-tip');
        const accountList = document.getElementById('account-list');

        if (accounts.length === 0) {
            accountSelectionGroup.style.display = 'none';
            noAccountsTip.style.display = 'block';
            this.updatePublishButtonState();
        } else {
            noAccountsTip.style.display = 'none';
            accountSelectionGroup.style.display = 'block';

            // 渲染账号列表 - 新设计:可点击选择  
            accountList.innerHTML = accounts.map(account => `
                        <div class="account-item" data-account-index="${account.index}">    
                    <div class="account-info">    
                        <span class="account-name" title="${account.author}">${account.author}</span>  
                        <span class="account-detail">AppID: ${account.appid}</span>  
                    </div>  
                    <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">  
                        <polyline points="20 6 9 17 4 12"/>  
                    </svg>  
                </div>
                        `).join('');

            // 绑定点击事件  
            accountList.querySelectorAll('.account-item').forEach(item => {
                item.addEventListener('click', () => {
                    item.classList.toggle('selected');
                    this.updateSelectedAccountCount();
                    this.updatePublishButtonState();
                });
            });

            this.updateSelectedAccountCount();
            this.updatePublishButtonState();
        }
    }

    // 更新已选账号数量  
    updateSelectedAccountCount() {
        const selectedItems = document.querySelectorAll('.account-item.selected');  // ✅ 修正  
        const count = selectedItems.length;

        document.getElementById('selected-account-count').textContent = `(已选 ${count} 个)`;
        document.getElementById('confirm-publish-btn').disabled = count === 0;
    }

    // 全选账号  
    selectAllAccounts() {
        document.querySelectorAll('.account-item').forEach(item => {
            item.classList.add('selected');
        });
        this.updateSelectedAccountCount();
    }

    // 取消全选  
    deselectAllAccounts() {
        document.querySelectorAll('.account-item').forEach(item => {
            item.classList.remove('selected');
        });
        this.updateSelectedAccountCount();
    }

    // 更新发布按钮状态  
    updatePublishButtonState() {
        const platformSelected = document.getElementById('publish-platform-select')?.value;
        const accountSelected = document.querySelectorAll('.account-item.selected').length > 0;
        const confirmBtn = document.getElementById('confirm-publish-btn');

        if (confirmBtn) {
            confirmBtn.disabled = !(platformSelected && accountSelected);
        }
    }

    // 前往设置  
    goToSettings() {
        this.closePublishDialog();
        // 切换到系统设置-微信公众号  
        const settingsLink = document.querySelector('[data-view="config-manager"]');
        if (settingsLink) {
            settingsLink.click();
            // 延迟切换到微信公众号配置  
            setTimeout(() => {
                const wechatConfig = document.querySelector('[data-config="wechat"]');
                if (wechatConfig) wechatConfig.click();
            }, 100);
        }
    }

    // 关闭发布对话框  
    closePublishDialog() {
        document.getElementById('publish-dialog').style.display = 'none';
        this.publishingArticles = [];
    }

    // 确认发布  
    // 确认发布  
    async confirmPublish() {
        const platformId = document.getElementById('publish-platform-select')?.value;
        const selectedAccounts = Array.from(
            document.querySelectorAll('.account-item.selected')
        ).map(item => parseInt(item.dataset.accountIndex));

        if (!platformId || selectedAccounts.length === 0) {
            window.app?.showNotification('请选择平台和账号', 'warning');
            return;
        }

        const articlePaths = [...this.publishingArticles];
        this.closePublishDialog();

        // 显示进度对话框  
        this.showPublishProgressDialog(articlePaths.length, selectedAccounts.length, true);

        // 获取文章标题列表
        const articleTitles = articlePaths.map(path => {
            const article = this.articles.find(a => a.path === path);
            return article ? article.title : '';
        });

        try {
            const response = await fetch('/api/articles/publish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    article_paths: articlePaths,
                    account_indices: selectedAccounts,
                    platform: platformId,
                    article_titles: articleTitles
                })
            });

            if (response.ok) {
                const result = await response.json();

                // 构建标题前缀  
                let titlePrefix = '';
                if (articleTitles.length === 1) {
                    titlePrefix = `《${articleTitles[0]}》 `;
                } else if (articleTitles.length > 1) {
                    titlePrefix = `《${articleTitles[0]}》等${articleTitles.length} 篇 `;
                }

                // 检查进度对话框是否仍然存在  
                const progressDialog = document.getElementById('publish-progress-dialog');

                if (progressDialog) {
                    // 对话框仍然打开 - 更新为结果显示,不显示右上角通知  
                    this.updateProgressDialogWithResult(result);
                } else {
                    // 对话框已关闭 - 显示右上角通知(简洁版本,包含文章标题)  
                    let notificationMessage = titlePrefix + '发布完成: ';  // 添加标题前缀  
                    if (result.success_count > 0 && result.fail_count > 0) {
                        notificationMessage += `成功 ${result.success_count}, 失败 ${result.fail_count} `;
                    } else if (result.success_count > 0) {
                        notificationMessage += `成功 ${result.success_count} `;
                    } else {
                        notificationMessage += `失败 ${result.fail_count} `;
                    }

                    window.app?.showNotification(
                        notificationMessage,
                        result.fail_count === 0 ? 'success' : (result.success_count > 0 ? 'warning' : 'error')
                    );
                }

                // 构建走马灯消息(包含文章标题)  
                let marqueeMessage = titlePrefix;  // 以标题开头  

                if (result.success_count > 0 && result.fail_count === 0) {
                    marqueeMessage += `发布完成: 成功 ${result.success_count} `;
                } else if (result.success_count > 0 && result.fail_count > 0) {
                    marqueeMessage += `发布完成: 成功 ${result.success_count}, 失败 ${result.fail_count} `;
                } else {
                    marqueeMessage += `发布完成: 失败 ${result.fail_count} `;
                }

                // 添加详细信息(最多3条)  
                if (result.error_details && result.error_details.length > 0) {
                    const details = result.error_details.slice(0, 3).join('; ');
                    marqueeMessage += ` | 详情: ${details} `;
                    if (result.error_details.length > 3) {
                        marqueeMessage += `...等${result.error_details.length} 条`;
                    }
                }

                // 判断消息类型(正确区分成功/警告/错误)  
                let messageType;
                if (result.fail_count === 0) {
                    // 全部成功  
                    if (result.error_details && result.error_details.length > 0) {
                        messageType = 'warning';  // 成功但有警告(如权限回收) - 橙色  
                    } else {
                        messageType = 'success';  // 完全成功 - 绿色  
                    }
                } else if (result.success_count > 0) {
                    messageType = 'warning';  // 部分成功 - 橙色  
                } else {
                    messageType = 'error';  // 全部失败 - 红色  
                }

                // 推送到走马灯(循环3次,使用正确的颜色)  
                if (window.footerMarquee) {
                    window.footerMarquee.addMessage(
                        marqueeMessage,
                        messageType,
                        false,
                        1
                    );
                }

                // 显示已删除文章提示
                if (result.deleted_articles && result.deleted_articles.length > 0) {
                    window.app?.showNotification(
                        `已自动删除 ${result.deleted_articles.length} 篇成功发布的文章`,
                        'info'
                    );
                }

                await this.loadArticles();
                this.renderStatusTree();                // 更新已发布文章的状态徽章,不重新渲染整个卡片  
                articlePaths.forEach(path => {
                    const card = document.querySelector(`.article-card[data-path="${path}"]`);
                    if (card) {
                        const statusBadge = card.querySelector('.status-badge');
                        const article = this.articles.find(a => a.path === path);
                        if (statusBadge && article) {
                            statusBadge.className = `status-badge ${article.status} `;
                            statusBadge.textContent = {
                                'published': '已发布',
                                'failed': '发布失败',
                                'unpublished': '未发布'
                            }[article.status] || '未发布';
                        }
                    }
                });

                // 退出批量模式  
                this.selectedArticles.clear();
                this.batchMode = false;
                this.toggleBatchMode();
            } else {
                throw new Error('发布请求失败');
            }
        } catch (error) {
            window.app?.showNotification('发布失败: ' + error.message, 'error');

            if (window.articleManager && typeof window.articleManager.updateQueueUI === 'function') {
                window.articleManager.updateQueueUI();
            }
            if (window.footerMarquee) {
                window.footerMarquee.addMessage(
                    '发布失败: ' + error.message,
                    'error',
                    false,
                    1
                );
            }

            const progressDialog = document.getElementById('publish-progress-dialog');
            if (progressDialog) progressDialog.remove();
        }
    }

    // 在进度对话框中显示结果  
    updateProgressDialogWithResult(result) {
        const dialog = document.getElementById('publish-progress-dialog');
        if (!dialog) return;

        const modalBody = dialog.querySelector('.modal-body');
        if (!modalBody) return;

        // 判断标题颜色  
        const hasWarnings = result.warning_details && result.warning_details.length > 0;
        const hasErrors = result.error_details && result.error_details.length > 0;
        const resultType = result.fail_count === 0 ? 'success' : (result.success_count > 0 ? 'warning' : 'error');

        // 合并所有详情信息  
        const allDetails = [];

        // 添加警告信息(橙色竖线)  
        if (hasWarnings) {
            result.warning_details.forEach(detail => {
                allDetails.push({ text: detail, type: 'warning' });
            });
        }

        // 添加错误信息(红色竖线)  
        if (hasErrors) {
            result.error_details.forEach(detail => {
                allDetails.push({ text: detail, type: 'error' });
            });
        }

        modalBody.innerHTML = `
                        <div class="result-summary ${resultType}">
                            <h4>发布完成</h4>  
                ${result.success_count > 0 ? `<p>✓ 成功: ${result.success_count}</p>` : ''}  
                ${result.fail_count > 0 ? `<p>✗ 失败: ${result.fail_count}</p>` : ''}  
            </div>
                        ${allDetails.length > 0 ? `  
                <div class="error-details">  
                    <h5 style="color: ${result.fail_count > 0 && result.success_count === 0 ? '#ef4444' : '#f59e0b'};">结果详情</h5>  
                    <div class="error-list">  
                        ${allDetails.map(item => `  
                            <div class="${item.type === 'warning' ? 'warning-item' : 'error-item'}">${this.escapeHtml(item.text)}</div>  
                        `).join('')}  
                    </div>  
                </div>  
            ` : ''
            }
                    `;

        // 更新对话框头部和按钮  
        const header = dialog.querySelector('.modal-header h3');
        if (header) header.textContent = '发布结果';

        const closeBtn = dialog.querySelector('.modal-close');
        if (closeBtn) closeBtn.onclick = () => this.closeProgressDialog();

        // 添加底部按钮  
        let footer = dialog.querySelector('.modal-footer');
        if (!footer) {
            footer = document.createElement('div');
            footer.className = 'modal-footer';
            dialog.querySelector('.modal-content').appendChild(footer);
        }

        footer.innerHTML = `
                        <button class="btn btn-secondary" onclick="window.articleManager.closeProgressDialog()">关闭</button>
                            <button class="btn btn-primary" onclick="window.open('https://mp.weixin.qq.com', '_blank')">打开公众号后台</button>
                    `;
    }

    // 格式化发布结果为走马灯消息  
    formatPublishMarqueeMessage(result) {
        const { success_count, fail_count } = result;
        const parts = [];

        if (success_count > 0) {
            parts.push(`成功 ${success_count} `);
        }
        if (fail_count > 0) {
            parts.push(`失败 ${fail_count} `);
        }

        return parts.length > 0 ? `发布完成: ${parts.join(', ')} ` : '发布完成';
    }

    // 推送发布结果到走马灯  
    // AI 换模板功能
    // ================= 全局任务管理 =================
    addTask(id, taskInfo) {
        this.backgroundTasks.set(id, {
            id,
            startTime: new Date(),
            progress: 0,
            status: 'running',
            ...taskInfo
        });
        this.updateGlobalTaskAgent(true, `正在执行: ${taskInfo.name} `, 0);
        this.renderTaskList();
    }

    updateTask(id, updates) {
        const task = this.backgroundTasks.get(id);
        if (task) {
            Object.assign(task, updates);
            // 如果是当前正在展示的主任务，同步更新 Agent
            const activeTask = Array.from(this.backgroundTasks.values()).find(t => t.status === 'running');
            if (activeTask && activeTask.id === id) {
                this.updateGlobalTaskAgent(true, activeTask.name, activeTask.progress);
            }
            this.renderTaskList();
        }
    }

    removeTask(id) {
        this.backgroundTasks.delete(id);
        const runningTasks = Array.from(this.backgroundTasks.values()).filter(t => t.status === 'running');
        if (runningTasks.length > 0) {
            const next = runningTasks[0];
            this.updateGlobalTaskAgent(true, next.name, next.progress);
        } else {
            this.updateGlobalTaskAgent(false);
        }
        this.renderTaskList();
    }

    renderTaskList() {
        const container = document.getElementById('task-list-container');
        if (!container) return;

        // 获取排队任务
        let queuedTasks = [];
        let runningQueueTask = null;
        if (window.taskQueue) {
            queuedTasks = window.taskQueue.queue;
            runningQueueTask = window.taskQueue.currentTask;
        }

        if (this.backgroundTasks.size === 0 && queuedTasks.length === 0 && !runningQueueTask) {
            container.innerHTML = `
                        <div style="text-align: center; color: #94a3b8; padding: 40px 0;">
                    <div style="font-size: 40px; margin-bottom: 10px;">📋</div>
                    <p>当前暂无进行中的后台任务</p>
                </div>`;
            return;
        }

        container.innerHTML = '';

        // 渲染基础 backgroundTasks
        this.backgroundTasks.forEach(task => {
            // 如果这个任务刚好是当前正在执行的全局任务，跳过以避免重复渲染
            if (runningQueueTask && runningQueueTask.id === task.id) return;

            const taskEl = document.createElement('div');
            taskEl.className = 'task-item';
            taskEl.style.marginBottom = '12px';
            taskEl.style.padding = '12px';
            taskEl.style.background = '#fff';
            taskEl.style.borderRadius = '8px';
            taskEl.style.border = '1px solid #e2e8f0';
            taskEl.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 18px;">${task.type === 're-template' ? '🎨' : '🤖'}</span>
                        <div style="font-weight: 600; color: #1e293b;">${task.name}</div>
                    </div>
                    <span style="font-size: 11px; color: #64748b;">${task.startTime.toLocaleTimeString()}</span>
                </div>
                <div style="margin-top: 5px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-bottom: 4px;">
                        <span>处理进度</span>
                        <span>${Math.round(task.progress)}%</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
                        <div style="width: ${task.progress}%; height: 100%; background: var(--primary-color); transition: width 0.3s;"></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 5px;">
                    ${task.type === 're-template' ? `<button class="btn btn-secondary btn-sm" onclick="window.articleManager.openReTemplateModal(true)" style="padding: 2px 10px; font-size: 11px;">查看详情</button>` : ''}
                    <button class="btn btn-danger btn-sm" onclick="window.articleManager.cancelBackgroundTask('${task.id}')" style="padding: 2px 8px; font-size: 11px;">停止任务</button>
                </div>
                    `;
            container.appendChild(taskEl);
        });

        // 渲染正在运行的全局队列任务
        if (runningQueueTask) {
            // 获取可能存在于 backgroundTasks 的对应进度
            let progress = 0;
            const bgTask = this.backgroundTasks.get(runningQueueTask.id) || this.backgroundTasks.get('current-re-template');
            if (bgTask) progress = bgTask.progress;

            const taskLabel = runningQueueTask.type === 'image-gen' ? 'AI 智能配图' : 'AI 换模板';
            const icon = runningQueueTask.type === 'image-gen' ? '🖼️' : '🎨';

            const taskEl = document.createElement('div');
            taskEl.className = 'task-item running';
            taskEl.style.marginBottom = '12px';
            taskEl.style.padding = '12px';
            taskEl.style.background = '#f0fdf4';
            taskEl.style.borderRadius = '8px';
            taskEl.style.border = '1px solid #bbf7d0';
            taskEl.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 18px;">${icon}</span>
                        <div style="font-weight: 600; color: #166534;">正在处理: ${taskLabel} - ${runReTemplateTitle(runningQueueTask.data)}</div>
                    </div>
                    <span style="font-size: 11px; color: #166534; font-weight: 500;">执行中...</span>
                </div>
                <div style="margin-top: 5px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #15803d; margin-bottom: 4px;">
                        <span>处理进度</span>
                        <span>${Math.round(progress)}%</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: #bbf7d0; border-radius: 3px; overflow: hidden;">
                        <div style="width: ${progress}%; height: 100%; background: #22c55e; transition: width 0.3s;"></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 5px;">
                    <button class="btn btn-danger btn-sm" onclick="window.taskQueue.abort('${runningQueueTask.id}'); window.articleManager.renderTaskList();" style="padding: 2px 8px; font-size: 11px;">强制停止</button>
                </div>
                    `;
            container.appendChild(taskEl);
        }

        // 渲染排队中的任务
        if (queuedTasks.length > 0) {
            const queueHeader = document.createElement('div');
            queueHeader.style.margin = '20px 0 10px 0';
            queueHeader.style.fontSize = '12px';
            queueHeader.style.fontWeight = 'bold';
            queueHeader.style.color = '#64748b';
            queueHeader.style.display = 'flex';
            queueHeader.style.justifyContent = 'space-between';
            queueHeader.innerHTML = `<span>⏳ 等待队列(${queuedTasks.length})</span>`;
            container.appendChild(queueHeader);

            queuedTasks.forEach((task, index) => {
                const taskLabel = task.type === 'image-gen' ? 'AI配图' : 'AI换模板';
                const icon = task.type === 'image-gen' ? '🖼️' : '🎨';

                const taskEl = document.createElement('div');
                taskEl.className = 'task-item queued';
                taskEl.style.marginBottom = '8px';
                taskEl.style.padding = '10px 12px';
                taskEl.style.background = '#f8fafc';
                taskEl.style.borderRadius = '8px';
                taskEl.style.border = '1px dashed #cbd5e1';
                taskEl.style.display = 'flex';
                taskEl.style.justifyContent = 'space-between';
                taskEl.style.alignItems = 'center';
                taskEl.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 12px; font-weight: bold; color: #94a3b8;">#${index + 1}</span>
                        <span style="font-size: 16px; opacity: 0.7;">${icon}</span>
                        <div style="font-weight: 500; color: #475569; font-size: 13px;">${taskLabel} - ${runReTemplateTitle(task.data)}</div>
                    </div>
                        <button class="btn btn-secondary btn-sm" onclick="window.taskQueue.abort('${task.id}'); window.articleManager.renderTaskList();" style="padding: 2px 8px; font-size: 11px;">取消排队</button>
                    `;
                container.appendChild(taskEl);
            });
        }

        function runReTemplateTitle(data) {
            if (!data) return '未知任务';
            if (data.title) return data.title.length > 20 ? data.title.substring(0, 20) + '...' : data.title;
            return '未命名文章';
        }
    }

    openTaskList() {
        const modal = document.getElementById('task-list-modal');
        if (modal) {
            modal.style.display = 'flex';
            this.renderTaskList();
        }
    }

    cancelBackgroundTask(id) {
        const task = this.backgroundTasks.get(id);
        if (task && task.controller) {
            task.controller.abort();
            showToast(`任务 ${task.name} 已取消`, "info");
            this.removeTask(id);
            if (id === 'current-re-template') {
                this.reTemplateAbortController = null;
                // 重置 modal 里的 loading
                document.getElementById('re-template-loading').style.display = 'none';
                document.getElementById('re-template-retry-btn').disabled = false;
                if (document.getElementById('re-template-stop-btn')) {
                    document.getElementById('re-template-stop-btn').style.display = 'none';
                }
            }
        }
    }

    updateQueueUI() {
        this.renderTaskList();
        // 如果有控制任务代理显示的逻辑，可以在这里更新
        const runningTasks = Array.from(this.backgroundTasks.values()).filter(t => t.status === 'running');
        const queuedTasks = window.taskQueue ? window.taskQueue.queue : [];
        const currentQueueTask = window.taskQueue ? window.taskQueue.currentTask : null;

        if (runningTasks.length > 0 || queuedTasks.length > 0 || currentQueueTask) {
            // 如果有正在运行的非队列任务（如 re-template 还在跑），已经在 addTask/updateTask 里处理了
            // 这里主要处理队列变动时的视觉反馈
            if (currentQueueTask && !runningTasks.some(t => t.id === currentQueueTask.id)) {
                this.updateGlobalTaskAgent(true, `正在处理: ${currentQueueTask.title} `, 0);
            }
        }
    }

    stopGenerateImage() {
        // AI 配图的中止逻辑
        const dialogId = 'img-gen-progress-dialog';
        const dialog = document.getElementById(dialogId);
        if (dialog) {
            const closeBtn = document.getElementById('img-gen-close-btn');
            if (closeBtn) closeBtn.disabled = false;

            // 如果正在轮询或请求中，可以通过标志位停止
            // 在 generateImages 闭包中处理较好，这里主要关闭 UI
            // 如果已经开始了 fetch，可能无法简单的 abort 除非传入 signal
            // 简单处理：提示用户已停止
            const statusText = document.getElementById('img-gen-status-text');
            if (statusText) statusText.textContent = '🛑 任务已从队列中止';
        }

        this.updateGlobalTaskAgent(false);
    }

    // ===============================================

    async openReTemplateModal(articleOrBackground = false) {
        // 如果传入的是文章对象，则设置为当前处理对象
        if (typeof articleOrBackground === 'object') {
            this.currentReTemplateArticle = articleOrBackground;
        }

        const modal = document.getElementById('re-template-modal');
        if (!modal) return;
        modal.style.display = 'flex';

        // 如果是后台模式且已有文章，直接显示即可
        if (articleOrBackground === true && this.currentReTemplateArticle) {
            this.updateGlobalTaskAgent(false);
            return;
        }

        // 重置状态
        document.getElementById('re-template-status-list').innerHTML = '<div style="color: #888;">正在初始化 AI 设计环境...</div>';
        document.getElementById('re-template-save-btn').disabled = true;
        document.getElementById('re-template-iframe').srcdoc = '';
        const codeView = document.getElementById('re-template-code-view');
        if (codeView) codeView.value = '';
        const stopBtn = document.getElementById('re-template-stop-btn');
        if (stopBtn) stopBtn.style.display = 'none';

        // 自动开始生成
        this.runReTemplate();
    }

    /**
     * 自动美化入口 — 由创意工坊生成完成后自动调用
     * 自动切换到文章管理视图并打开换模板弹窗
     */
    async triggerAutoReTemplate(article) {
        if (!article) return;

        window.app?.showNotification('🎨 AI 自动美化启动中...', 'info');

        // 切换到文章管理视图（确保 modal 容器存在）
        const articleViewLink = document.querySelector('[data-view="article-manager"]');
        if (articleViewLink) {
            articleViewLink.click();
            // 等待视图切换完成
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        // 调用 openReTemplateModal，它会自动设置文章并开始执行
        await this.openReTemplateModal(article);
    }

    stopReTemplate() {
        if (this.reTemplateAbortController) {
            this.reTemplateAbortController.abort();
            this.reTemplateAbortController = null;
            const stopBtn = document.getElementById('re-template-stop-btn');
            if (stopBtn) stopBtn.style.display = 'none';
            document.getElementById('re-template-loading').style.display = 'none';
            document.getElementById('re-template-retry-btn').disabled = false;

            const div = document.createElement('div');
            div.style.marginBottom = '8px';
            div.style.color = '#dc3545';
            div.style.fontWeight = 'bold';
            div.innerHTML = `<span style="opacity: 0.6; margin-right: 5px;">${new Date().toLocaleTimeString()}</span> 🛑 用户已手动终止 AI 设计任务`;
            document.getElementById('re-template-status-list').appendChild(div);

            this.updateGlobalTaskAgent(false);
        }
    }

    updateGlobalTaskAgent(show, title = "", progress = 0) {
        const agent = document.getElementById('global-task-agent');
        if (!agent) return;

        if (show) {
            agent.style.display = 'flex';

            // 添加提示动效
            if (!agent.classList.contains('task-agent-active')) {
                agent.style.transform = 'scale(1.05)';
                agent.classList.add('task-agent-active');
                setTimeout(() => agent.style.transform = '', 200);
            }

            document.getElementById('task-agent-title').textContent = title;
            document.getElementById('task-agent-progress').style.width = `${progress}% `;
            document.getElementById('task-agent-percent').textContent = `${Math.round(progress)}% `;
        } else {
            agent.style.display = 'none';
            agent.classList.remove('task-agent-active');
        }
    }

    closeReTemplateModal() {
        const modal = document.getElementById('re-template-modal');
        if (modal) modal.style.display = 'none';

        // 如果 AI 还在跑，显示全局小助手
        if (this.reTemplateAbortController) {
            this.updateGlobalTaskAgent(true, "AI 正在后台设计模板...", 50);
            showToast("AI 设计任务已转入后台运行", "info");
        }
    }

    async runReTemplate() {
        if (!this.currentReTemplateArticle) return;

        const statusList = document.getElementById('re-template-status-list');
        const loadingImg = document.getElementById('re-template-loading');
        const retryBtn = document.getElementById('re-template-retry-btn');
        const saveBtn = document.getElementById('re-template-save-btn');
        const stopBtn = document.getElementById('re-template-stop-btn');
        const iframe = document.getElementById('re-template-iframe');
        const codeView = document.getElementById('re-template-code-view');
        const codeTabBtn = document.getElementById('re-template-view-code-btn');

        // 确保状态列表有平滑滚动的样式基础
        statusList.style.scrollBehavior = 'smooth';
        if (!document.getElementById('re-template-style')) {
            const style = document.createElement('style');
            style.id = 're-template-style';
            style.textContent = `
                    @keyframes fadeInStatus {
                    from { opacity: 0; transform: translateY(5px); }
                    to { opacity: 1; transform: translateY(0); }
                        @keyframes pulse-dot {
                            0% { transform: scale(0.8); opacity: 0.5; }
                            50% { transform: scale(1.2); opacity: 1; }
                            100% { transform: scale(0.8); opacity: 0.5; }
                        }
                .pulse-dot {
                            display: inline-block;
                            width: 8px;
                            height: 8px;
                            background-color: #ff4d4f;
                            border-radius: 50%;
                            margin-left: 5px;
                            animation: pulse-dot 1s ease-in-out infinite;
                        }
                .spinner-small {
                            width: 14px;
                            height: 14px;
                            border: 2px solid rgba(58, 123, 213, 0.2);
                            border-top-color: #3a7bd5;
                            border-radius: 50%;
                            animation: spin 0.8s linear infinite;
                            display: inline-block;
                            vertical-align: middle;
                            margin-right: 6px;
                        }
                        `;
            document.head.appendChild(style);
        }

        if (!document.getElementById('ai-retemplate-extra-style')) {
            const style = document.createElement('style');
            style.id = 'ai-retemplate-extra-style';
            style.innerHTML = `
                            .spinner-small {
                            width: 14px;
                            height: 14px;
                            border: 2px solid rgba(58, 123, 213, 0.2);
                            border-top-color: #3a7bd5;
                            border-radius: 50%;
                            animation: spin 0.8s linear infinite;
                            display: inline-block;
                            vertical-align: middle;
                            margin-right: 6px;
                        }
                .ai-thought-bubble {
                            background: #f0f7ff;
                            border-left: 3px solid #3a7bd5;
                            padding: 8px 12px;
                            margin: 8px 0;
                            border-radius: 0 8px 8px 0;
                            font-style: italic;
                            color: #4a5568;
                            font-size: 12.5px;
                            animation: slideIn 0.3s ease-out;
                        }
                        @keyframes slideIn {
                    from { opacity: 0; transform: translateX(-10px); }
                    to { opacity: 1; transform: translateX(0); }
                        }
                        `;
            document.head.appendChild(style);
        }

        const addStatus = (msg, color = '#666', isLog = true) => {
            const div = document.createElement('div');
            div.style.marginBottom = '10px';
            div.style.color = color;
            div.style.borderLeft = isLog ? '3px solid #3a7bd5' : 'none';
            div.style.paddingLeft = isLog ? '10px' : '0';
            div.style.animation = 'fadeInStatus 0.3s ease-out forwards';
            div.style.fontSize = '13px';
            div.style.lineHeight = '1.5';
            div.innerHTML = `<span style="opacity: 0.5; margin-right: 8px; font-family: monospace;">[${new Date().toLocaleTimeString([], { hour12: false })}]</span><span>${msg}</span>`;
            statusList.appendChild(div);
            // 自动滚动到底部
            statusList.scrollTo({
                top: statusList.scrollHeight,
                behavior: 'smooth'
            });
        };

        loadingImg.style.display = 'flex';
        retryBtn.disabled = true;
        saveBtn.disabled = true;
        if (stopBtn) stopBtn.style.display = 'inline-block';

        statusList.innerHTML = '';
        iframe.srcdoc = '';
        document.getElementById('re-template-code-view').value = '';
        const insightsContent = document.getElementById('re-template-insights-content');
        if (insightsContent) insightsContent.innerHTML = '<div style="color: #999; text-align: center; margin-top: 50px;">正在深度分析文章结构...</div>';
        this.currentReTemplateHtml = null;

        addStatus('🚀 正在建立 AI 设计实验室流式连接...', '#3a7bd5');
        addStatus('📡 正在发送模型推理请求，请稍候 (Seed: ' + Math.floor(Math.random() * 9999) + ')...', '#666');

        // 启动计时器
        const startTime = Date.now();
        let timerInterval = setInterval(() => {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            loadingImg.innerHTML = `<div class="spinner-small"></div> AI 正在设计中... (${elapsed}s)`;
        }, 100);

        // 创建中止控制器
        this.reTemplateAbortController = new AbortController();
        const signal = this.reTemplateAbortController.signal;

        // 注册到后台任务管理器
        this.addTask('current-re-template', {
            name: `AI 换模板: ${this.currentReTemplateArticle.title || '未命名'}`,
            type: 're-template',
            controller: this.reTemplateAbortController
        });

        return new Promise(async (resolve, reject) => {
            try {
                const res = await fetch('/api/articles/re-template', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: this.currentReTemplateArticle.path }),
                    signal: signal
                });

                if (!res.ok) throw new Error('网络请求异常: ' + res.status);

                const connectTime = (Date.now() - startTime) / 1000;
                addStatus(`✅ 连接成功!(握手延迟: ${connectTime.toFixed(2)}s)，AI 已开始输出设计流...`, '#28a745');

                const reader = res.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";
                let liveHtml = "";
                let chunkCount = 0;
                let totalBytes = 0;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    totalBytes += value.length;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // reserve the incomplete line

                    for (const line of lines) {
                        if (!line.trim()) continue;

                        // 尝试解析为 JSON (SSE/Standard Format)
                        try {
                            const data = JSON.parse(line);
                            if (data.type === 'log') {
                                addStatus(data.message, '#3a7bd5');

                                // 同步实时推送到 AI 深度分析面板
                                const insightsContent = document.getElementById('re-template-insights-content');
                                if (insightsContent) {
                                    // 清除初始等待提示
                                    if (insightsContent.querySelector('[style*="color: #999"]')) {
                                        insightsContent.innerHTML = '';
                                    }
                                    const logEntry = document.createElement('div');
                                    logEntry.style.cssText = 'margin-bottom: 10px; padding: 8px 12px; background: #f8fafc; border-radius: 6px; font-size: 13px; color: #475569; border-left: 3px solid #3a7bd5; animation: slideIn 0.3s ease-out;';
                                    logEntry.innerHTML = `<span style="opacity: 0.5; margin-right:6px; font-family:monospace;">[${new Date().toLocaleTimeString([], { hour12: false })}]</span> ${data.message} `;
                                    insightsContent.appendChild(logEntry);
                                    insightsContent.parentElement.scrollTo(0, insightsContent.parentElement.scrollHeight);
                                }
                            } else if (data.type === 'thought') {
                                // 实时显示 AI 思考过程 (增量更新到日志)
                                let thoughtDiv = statusList.querySelector('.ai-thought-bubble:last-child');
                                if (!thoughtDiv || thoughtDiv.dataset.final === 'true') {
                                    thoughtDiv = document.createElement('div');
                                    thoughtDiv.className = 'ai-thought-bubble';
                                    statusList.appendChild(thoughtDiv);
                                }
                                thoughtDiv.textContent = `💭 AI 思考: ${data.content} `;
                                statusList.scrollTo(0, statusList.scrollHeight);

                                // 同时更新“AI 深度分析”选项卡内容
                                const insightsContent = document.getElementById('re-template-insights-content');
                                if (insightsContent) {
                                    // 如果是第一次更新，清除等待提示
                                    if (insightsContent.querySelector('[style*="color: #999"]')) {
                                        insightsContent.innerHTML = '';
                                    }

                                    // 我们把思考过程累积显示在分析面板中
                                    let p = insightsContent.querySelector('p:last-child');
                                    if (!p) {
                                        p = document.createElement('p');
                                        p.style.marginBottom = '15px';
                                        p.style.padding = '12px';
                                        p.style.background = '#fff';
                                        p.style.borderRadius = '8px';
                                        p.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';
                                        p.style.borderLeft = '4px solid var(--primary-color)';
                                        insightsContent.appendChild(p);
                                    }
                                    p.textContent = data.content;
                                    insightsContent.parentElement.scrollTo(0, insightsContent.parentElement.scrollHeight);
                                }
                            } else if (data.type === 'chunk') {
                                chunkCount++;
                                // 基础数据同步
                                this.currentReTemplateHtml = data.content;

                                // 在 Agent 模式下，清洗 HTML
                                let displayHtml = data.content;
                                displayHtml = displayHtml.replace(/```html /gi, '').replace(/```/g, '').trim();

                                // 关键优化：只有预览窗口可见或是最终阶段才物理刷新 iframe
                                // 否则只更新内容变量，避免频繁渲染导致的 UI 阻塞
                                const isPreviewActive = document.getElementById('re-template-preview-view').style.display !== 'none';

                                if (isPreviewActive || !data.is_fragment) {
                                    iframe.srcdoc = displayHtml;
                                }

                                if (codeView) {
                                    codeView.value = displayHtml;
                                    if (isPreviewActive && codeView.offsetParent !== null) {
                                        // 仅在可见时更新滚动条
                                        codeView.scrollTop = codeView.scrollHeight;
                                    }
                                }

                                // 源代码按钮动效引导
                                if (codeTabBtn && !codeTabBtn.dataset.receiving) {
                                    codeTabBtn.dataset.receiving = "true";
                                    codeTabBtn.innerHTML = `源代码 <span class="stage-badge">Stage ${data.stage || '?'}</span> <span class="pulse-dot"></span>`;
                                } else if (codeTabBtn && data.stage) {
                                    const stageBadge = codeTabBtn.querySelector('.stage-badge');
                                    if (stageBadge) stageBadge.textContent = `Stage ${data.stage}`;
                                }
                            } else if (data.type === 'full_html') {
                                addStatus('🎊 AI 模板设计与内容深度装饰全部完成！', '#28a745');

                                // 数据清洗，防止偶发的 Markdown 标记泄露
                                let finalHtml = data.content;
                                finalHtml = finalHtml.replace(/```html/gi, '').replace(/```/g, '').trim();

                                this.currentReTemplateHtml = finalHtml;
                                iframe.srcdoc = finalHtml;
                                const codeView = document.getElementById('re-template-code-view');
                                if (codeView) codeView.value = finalHtml;
                                saveBtn.disabled = false;

                                this.updateTask('current-re-template', { progress: 100, status: 'done' });
                                setTimeout(() => this.removeTask('current-re-template'), 3000);
                                this.reTemplateAbortController = null;
                                resolve(true); // 成功完成
                            } else if (data.type === 'done') {
                                if (this.currentReTemplateHtml) saveBtn.disabled = false;
                                this.updateTask('current-re-template', { progress: 100, status: 'done' });
                                setTimeout(() => this.removeTask('current-re-template'), 3000);
                                this.reTemplateAbortController = null;
                                if (stopBtn) stopBtn.style.display = 'none';
                                resolve(true); // 成功完成
                            }
                        } catch (e) {
                            // 如果不是标准 JSON，则视为流式直接日志输出 (某些 LLM API 或 中转层的行为)
                            const cleanLine = line.replace(/^data:/, '').trim();
                            if (cleanLine && cleanLine !== '[DONE]') {
                                addStatus(`👉 AI 思考中: ${cleanLine}`, '#666');
                            }
                        }
                    }
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    console.log('AI design cancelled by user');
                } else {
                    addStatus(`❌ 严重错误: ${error.message}`, '#dc3545');
                    this.updateGlobalTaskAgent(false);
                }
                resolve(false); // 异常结束
            } finally {
                if (timerInterval) clearInterval(timerInterval);
                const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
                addStatus(`🏁 任务结束，本次执行总耗时: ${totalTime}s`, '#333', false);

                // 清除按钮动效
                if (codeTabBtn) {
                    delete codeTabBtn.dataset.receiving;
                    codeTabBtn.innerHTML = '源代码';
                }

                loadingImg.style.display = 'none';
                loadingImg.innerHTML = '<div class="spinner-small"></div> AI 正在设计中...'; // 重置 innerHTML
                retryBtn.disabled = false;
                if (stopBtn) stopBtn.style.display = 'none';

                // 通知任务队列此任务已执行完毕
                if (window.taskQueue && window.taskQueue.currentTask && window.taskQueue.currentTask.type === 're-template') {
                    window.taskQueue.taskComplete(window.taskQueue.currentTask.id);
                }
            }
        });
    }

    toggleReTemplateView(viewType) {
        const iframe = document.getElementById('re-template-iframe');
        const codeView = document.getElementById('re-template-code-view');
        const insightsView = document.getElementById('re-template-insights-view');
        const previewBtn = document.getElementById('re-template-view-preview-btn');
        const codeBtn = document.getElementById('re-template-view-code-btn');
        const insightsBtn = document.getElementById('re-template-view-insights-btn');
        const copyBtn = document.getElementById('re-template-copy-code-btn');

        if (viewType === 'preview') {
            iframe.style.display = 'block';
            codeView.style.display = 'none';
            insightsView.style.display = 'none';
            previewBtn.style.background = '#fff';
            previewBtn.style.borderColor = '#ddd';
            codeBtn.style.background = 'transparent';
            codeBtn.style.borderColor = 'transparent';
            insightsBtn.style.background = 'transparent';
            insightsBtn.style.borderColor = 'transparent';
            copyBtn.style.display = 'none';
        } else if (viewType === 'insights') {
            iframe.style.display = 'none';
            codeView.style.display = 'none';
            insightsView.style.display = 'block';
            previewBtn.style.background = 'transparent';
            previewBtn.style.borderColor = 'transparent';
            codeBtn.style.background = 'transparent';
            codeBtn.style.borderColor = 'transparent';
            insightsBtn.style.background = '#fff';
            insightsBtn.style.borderColor = '#ddd';
            copyBtn.style.display = 'none';
        } else {
            iframe.style.display = 'none';
            codeView.style.display = 'block';
            insightsView.style.display = 'none';
            previewBtn.style.background = 'transparent';
            previewBtn.style.borderColor = 'transparent';
            codeBtn.style.background = '#fff';
            codeBtn.style.borderColor = '#ddd';
            insightsBtn.style.background = 'transparent';
            insightsBtn.style.borderColor = 'transparent';
            copyBtn.style.display = 'inline-block';
        }
    }

    async copyReTemplateCode() {
        const code = document.getElementById('re-template-code-view').value;
        if (!code) return;
        try {
            await navigator.clipboard.writeText(code);
            const btn = document.getElementById('re-template-copy-code-btn');
            const originalText = btn.innerText;
            btn.innerText = '已复制!';
            setTimeout(() => { btn.innerText = originalText; }, 2000);
        } catch (err) {
            console.error('Copy failed:', err);
            alert('复制失败，请手动选择复制');
        }
    }

    async saveReTemplate() {
        if (!this.currentReTemplateArticle || !this.currentReTemplateHtml) return;

        const saveBtn = document.getElementById('re-template-save-btn');
        if (!saveBtn) return;
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<div class="spinner-small"></div> 正在保存...';

        try {
            const response = await fetch('/api/articles/content', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: this.currentReTemplateArticle.path,
                    content: this.currentReTemplateHtml
                })
            });

            if (response.ok) {
                window.app?.showNotification('模板已永久保存至文章本尊', 'success');
                // 更新内存中的数据
                const article = this.articles.find(a => a.path === this.currentReTemplateArticle.path);
                if (article) article.content = this.currentReTemplateHtml;

                // 刷新预览
                const card = document.querySelector(`.article-card[data-path="${this.currentReTemplateArticle.path}"]`);
                if (card) {
                    const iframe = card.querySelector('iframe');
                    if (iframe) {
                        iframe.dataset.loaded = 'false';
                        this.loadSinglePreview(iframe);
                    }
                }

                // 如果有正在运行的任务，给予收纳提示并确保代理显示
                if (this.reTemplateAbortController && this.backgroundTasks.has('current-re-template')) {
                    window.app?.showNotification('✨ AI 正在后台继续为您进行深度设计。您可以通过右下角的“任务图标”↘️ 查看进度。', 'info');
                    // 获取当前任务名称和进度传给 agent
                    const task = this.backgroundTasks.get('current-re-template');
                    this.updateGlobalTaskAgent(true, task.name, task.progress);
                }

                this.closeReTemplateModal();
            } else {
                const err = await response.json();
                throw new Error(err.detail || '保存失败');
            }
        } catch (error) {
            window.app?.showNotification('保存失败: ' + error.message, 'error');
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
    }


    pushResultToMarquee(result) {
        if (!window.footerMarquee) return;

        const { success_count, fail_count, error_details } = result;

        // 构建详细的结果消息  
        let message = '发布完成: ';

        // 只显示非零的统计  
        if (success_count > 0 && fail_count > 0) {
            message += `成功 ${success_count}, 失败 ${fail_count}`;
        } else if (success_count > 0) {
            message += `成功 ${success_count}`;
        } else if (fail_count > 0) {
            message += `失败 ${fail_count}`;
        }

        // 添加失败详情(最多显示3条)  
        if (fail_count > 0 && error_details && error_details.length > 0) {
            const details = error_details.slice(0, 3).join('; ');
            message += ` | 失败详情: ${details}`;
            if (error_details.length > 3) {
                message += `...还有${error_details.length - 3}个错误`;
            }
        }

        // 推送到走马灯  
        window.footerMarquee.addMessage(
            message,
            fail_count === 0 ? 'success' : (success_count > 0 ? 'warning' : 'error'),
            false,  // persistent=false (临时消息)  
            1       // loopCount=1 (立即显示一次,不循环)  
        );
    }

    showPublishProgressDialog(articleCount, accountCount, showCloseButton = true) {  // ✅ 改为showCloseButton  
        const dialogHtml = `    
            <div class="modal-overlay" id="publish-progress-dialog" data-user-closed="false">    
                <div class="modal-content publish-progress-modal">    
                    <div class="modal-header">    
                        <h3>正在发布</h3>    
                        ${showCloseButton ? '<button class="btn-icon modal-close" onclick="window.articleManager.closeProgressDialog()">×</button>' : ''}    
                    </div>  
                    <div class="modal-body">    
                        <div class="progress-info">    
                            <p>正在发布 ${articleCount} 篇文章到 ${accountCount} 个账号...</p>    
                            <p class="progress-detail">您可以关闭此窗口,发布将在后台继续</p>    
                        </div>    
                        <div class="progress-spinner">    
                            <svg class="spinner" viewBox="0 0 50 50">    
                                <circle cx="25" cy="25" r="20" fill="none" stroke-width="4"></circle>    
                            </svg>    
                        </div>    
                    </div>    
                </div>    
            </div>    
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);
    }

    // 关闭进度对话框(转为后台执行)  
    closeProgressDialog() {
        const dialog = document.getElementById('publish-progress-dialog');
        if (dialog) dialog.remove();
    }

    // 显示简洁的发布通知  
    showPublishNotification(result) {
        const { success_count, fail_count } = result;

        // 构建简洁消息  
        let message = '发布完成';
        const parts = [];

        if (success_count > 0) {
            parts.push(`成功 ${success_count}`);
        }
        if (fail_count > 0) {
            parts.push(`失败 ${fail_count}`);
        }

        if (parts.length > 0) {
            message += ': ' + parts.join(', ');
        }

        const type = fail_count === 0 ? 'success' : (success_count > 0 ? 'warning' : 'error');
        window.app?.showNotification(message, type);
    }

    // 显示详细结果对话框  
    showPublishResultDialog(result) {
        const { success_count, fail_count, error_details } = result;

        let statusClass = 'success';
        let statusText = '发布成功';
        if (fail_count > 0 && success_count > 0) {
            statusClass = 'warning';
            statusText = '部分成功';
        } else if (fail_count > 0) {
            statusClass = 'error';
            statusText = '发布失败';
        }

        const dialogHtml = `  
            <div id="publish-result-dialog" class="modal-overlay">  
                <div class="modal-content publish-result-modal">  
                    <div class="modal-header">  
                        <h3>发布结果</h3>  
                        <button class="modal-close" onclick="window.articleManager.closeResultDialog()">×</button>  
                    </div>  
                    <div class="modal-body">  
                        <div class="result-summary ${statusClass}">  
                            <h4>${statusText}</h4>  
                            <div class="result-stats">  
                                ${success_count > 0 ? `  
                                    <div class="stat-item">  
                                        <div class="stat-number success">${success_count}</div>  
                                        <div class="stat-label">成功</div>  
                                    </div>  
                                ` : ''}  
                                ${fail_count > 0 ? `  
                                    <div class="stat-item">  
                                        <div class="stat-number failed">${fail_count}</div>  
                                        <div class="stat-label">失败</div>  
                                    </div>  
                                ` : ''}  
                            </div>  
                        </div>  
                        
                        ${error_details && error_details.length > 0 ? `  
                            <div class="error-details-section">  
                                <div class="error-details-header">  
                                    <span class="error-details-title">失败详情</span>  
                                </div>  
                                <div class="error-list">  
                                    ${error_details.map(err => `  
                                        <div class="error-item">${this.escapeHtml(err)}</div>  
                                    `).join('')}  
                                </div>  
                            </div>  
                        ` : ''}  
                    </div>  
                    <div class="modal-footer">  
                        <button class="btn btn-secondary" onclick="window.articleManager.closeResultDialog()">关闭</button>  
                        <button class="btn btn-primary" onclick="window.open('https://mp.weixin.qq.com', '_blank')">打开公众号后台</button>  
                    </div>  
                </div>  
            </div>  
        `;

        // 移除进度对话框  
        const progressDialog = document.getElementById('publish-progress-dialog');
        if (progressDialog) progressDialog.remove();

        document.body.insertAdjacentHTML('beforeend', dialogHtml);
    }

    closeResultDialog() {
        const dialog = document.getElementById('publish-result-dialog');
        if (dialog) dialog.remove();
    }

    // 删除文章  
    async deleteArticle(path) {
        window.dialogManager.showConfirm(
            '确认删除这篇文章吗?',
            async () => {
                try {
                    const response = await fetch(`/api/articles/?path=${encodeURIComponent(path)}`, {
                        method: 'DELETE'
                    });

                    if (response.ok) {
                        window.app?.showNotification('文章已删除', 'success');
                        await this.loadArticles();
                        this.renderStatusTree();
                    } else {
                        const error = await response.json();
                        window.app?.showNotification('删除失败: ' + (error.detail || '未知错误'), 'error');
                    }
                } catch (error) {
                    window.app?.showNotification('删除失败: ' + error.message, 'error');
                }
            }
        );
    }

    // 批量删除  
    async batchDelete() {
        if (this.selectedArticles.size === 0) {
            window.app?.showNotification('请先选择要删除的文章', 'warning');
            return;
        }

        const count = this.selectedArticles.size;

        window.dialogManager.showConfirm(
            `确认删除选中的 ${count} 篇文章吗?`,
            async () => {
                const paths = Array.from(this.selectedArticles);
                let successCount = 0;

                for (const path of paths) {
                    try {
                        const response = await fetch(`/api/articles/?path=${encodeURIComponent(path)}`, {
                            method: 'DELETE'
                        });
                        if (response.ok) {
                            successCount++;
                            const card = document.querySelector(`.article-card[data-path="${path}"]`);
                            if (card) card.remove();
                        }
                    } catch (error) {
                        console.error('删除失败:', path, error);
                    }
                }

                window.app?.showNotification(`删除完成: ${successCount}/${count}`, 'success');

                // 更新数据  
                await this.loadArticles();
                this.renderStatusTree();

                // 退出批量模式  
                this.selectedArticles.clear();
                this.batchMode = false;
                this.toggleBatchMode();
            }
        );
    }

    // HTML转义  
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ==================== AI一键换标题功能 ====================
    async optimizeTitle(article) {
        const dialogId = 'optimize-title-dialog';
        const existingDialog = document.getElementById(dialogId);
        if (existingDialog) existingDialog.remove();

        // 创建弹窗HTML
        const dialogHtml = `
            <div class="modal-overlay" id="${dialogId}" style="z-index: 9999;">
                <div class="modal-content" style="max-width: 640px; max-height: 85vh; display: flex; flex-direction: column;">
                    <div class="modal-header">
                        <h3 style="display: flex; align-items: center; gap: 8px;">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                            AI 智能换标题
                        </h3>
                        <button class="modal-close" onclick="window.articleManager.closeOptimizeTitleDialog()">×</button>
                    </div>
                    <div class="modal-body" style="flex: 1; overflow: hidden; display: flex; flex-direction: column; gap: 12px;">
                        <!-- 当前标题 -->
                        <div style="background: var(--bg-secondary); padding: 12px 16px; border-radius: 8px; border-left: 3px solid var(--primary-color);">
                            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 4px;">当前标题</div>
                            <div id="opt-title-current" style="font-weight: 600; color: var(--text-primary);">${this.escapeHtml(article.title)}</div>
                        </div>
                        
                        <!-- 平台选择 -->
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <label style="font-size: 14px; color: var(--text-secondary);">目标平台：</label>
                            <select id="opt-title-platform" style="flex: 1; padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-tertiary); color: var(--text-primary);">
                                <option value="">通用平台</option>
                                <option value="微信公众号">微信公众号</option>
                                <option value="今日头条">今日头条</option>
                                <option value="知乎">知乎</option>
                                <option value="抖音">抖音</option>
                                <option value="小红书">小红书</option>
                            </select>
                            <button class="btn btn-primary" id="opt-title-generate-btn" onclick="window.articleManager.generateTitleOptions('${encodeURIComponent(article.path)}')">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" style="margin-right: 4px;">
                                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                                </svg>
                                生成标题
                            </button>
                        </div>

                        <!-- 日志区域 -->
                        <div id="opt-title-log-container" style="display: none; background: var(--bg-tertiary); border-radius: 8px; padding: 12px; font-family: monospace; font-size: 12px; color: var(--text-secondary); max-height: 120px; overflow-y: auto;">
                            <div style="color: var(--primary-color);">🤖 正在分析文章内容...</div>
                        </div>

                        <!-- 标题选项区域 -->
                        <div id="opt-title-options" style="flex: 1; overflow-y: auto; display: none; flex-direction: column; gap: 10px;">
                            <!-- 动态生成的标题选项 -->
                        </div>

                        <!-- 加载状态 -->
                        <div id="opt-title-loading" style="display: none; flex-direction: column; align-items: center; justify-content: center; padding: 40px; gap: 12px;">
                            <svg class="spin" viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                            </svg>
                            <span style="color: var(--text-secondary);">AI正在生成爆款标题...</span>
                        </div>
                    </div>
                    <div class="modal-footer" style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="font-size: 12px; color: var(--text-secondary);">
                            💡 点击"生成标题"开始AI分析
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn btn-secondary" onclick="window.articleManager.closeOptimizeTitleDialog()">取消</button>
                            <button class="btn btn-primary" id="opt-title-apply-btn" onclick="window.articleManager.applyNewTitle('${encodeURIComponent(article.path)}')" disabled>
                                应用选中标题
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        this.currentOptimizeArticle = article;
        this.selectedNewTitle = null;
    }

    closeOptimizeTitleDialog() {
        const dialog = document.getElementById('optimize-title-dialog');
        if (dialog) dialog.remove();
        this.currentOptimizeArticle = null;
        this.selectedNewTitle = null;
    }

    async generateTitleOptions(articlePathEncoded) {
        const articlePath = decodeURIComponent(articlePathEncoded);
        const platform = document.getElementById('opt-title-platform').value;
        const logContainer = document.getElementById('opt-title-log-container');
        const loading = document.getElementById('opt-title-loading');
        const optionsContainer = document.getElementById('opt-title-options');
        const generateBtn = document.getElementById('opt-title-generate-btn');

        // 显示加载状态
        logContainer.style.display = 'block';
        loading.style.display = 'flex';
        optionsContainer.style.display = 'none';
        generateBtn.disabled = true;

        this.addOptimizeTitleLog('正在调用AI标题优化引擎...');

        try {
            const response = await fetch('/api/articles/optimize-title', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ article_path: articlePath, platform: platform })
            });

            if (!response.ok) {
                throw new Error(`请求失败: ${response.status}`);
            }

            const result = await response.json();

            // 检查后端返回的错误状态
            if (result.status === 'error') {
                console.error('[optimizeTitle] 后端返回错误:', result);
                this.addOptimizeTitleLog(`❌ ${result.message || 'AI服务暂时不可用'}`);

                // 显示错误信息在选项区域
                const optionsContainer = document.getElementById('opt-title-options');
                optionsContainer.innerHTML = `
                    <div style="text-align: center; padding: 30px; color: #e74c3c;">
                        <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">AI标题生成失败</div>
                        <div style="color: var(--text-secondary); font-size: 14px; line-height: 1.6;">
                            ${result.message || 'AI服务暂时不可用，请检查API配置'}
                        </div>
                        <div style="margin-top: 20px; font-size: 12px; color: #888;">
                            错误类型: ${result.error_type || 'unknown'}
                        </div>
                    </div>
                `;
                optionsContainer.style.display = 'flex';
                return;
            }

            this.addOptimizeTitleLog('✅ AI标题生成完成！');

            // 显示标题选项
            this.renderTitleOptions(result.titles, result.original_title, result.recommended);

        } catch (error) {
            console.error('生成标题失败:', error);
            this.addOptimizeTitleLog(`❌ 错误: ${error.message}`);

            // 显示错误信息在选项区域
            const optionsContainer = document.getElementById('opt-title-options');
            optionsContainer.innerHTML = `
                <div style="text-align: center; padding: 30px; color: #e74c3c;">
                    <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">请求失败</div>
                    <div style="color: var(--text-secondary); font-size: 14px;">
                        ${error.message || '网络错误，请检查连接后重试'}
                    </div>
                </div>
            `;
            optionsContainer.style.display = 'flex';

            window.app?.showNotification('生成标题失败，请重试', 'error');
        } finally {
            loading.style.display = 'none';
            generateBtn.disabled = false;
        }
    }

    addOptimizeTitleLog(message) {
        const logContainer = document.getElementById('opt-title-log-container');
        const time = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.style.marginBottom = '4px';
        logEntry.textContent = `[${time}] ${message}`;
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    renderTitleOptions(titles, originalTitle, recommended) {
        const container = document.getElementById('opt-title-options');
        container.innerHTML = '';
        container.style.display = 'flex';

        console.log('[renderTitleOptions] 收到标题数据:', titles);

        if (!titles || titles.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-secondary);">未能生成标题选项，请重试</div>';
            return;
        }

        // 标题类型样式（支持多种格式）
        const typeStyles = {
            '标题1': { label: '悬念型', color: '#ff6b6b' },
            '标题2': { label: '数字型', color: '#4ecdc4' },
            '标题3': { label: '情感型', color: '#45b7d1' },
            '标题4': { label: '热点型', color: '#f9ca24' },
            '标题5': { label: '实用型', color: '#6c5ce7' },
            '1': { label: '悬念型', color: '#ff6b6b' },
            '2': { label: '数字型', color: '#4ecdc4' },
            '3': { label: '情感型', color: '#45b7d1' },
            '4': { label: '热点型', color: '#f9ca24' },
            '5': { label: '实用型', color: '#6c5ce7' }
        };

        let validCount = 0;
        titles.forEach((item, index) => {
            // 过滤掉无效标题（太短或为空）
            if (!item.title || item.title.length < 5) {
                console.warn(`[renderTitleOptions] 跳过无效标题: type=${item.type}, title=${item.title}`);
                return;
            }
            validCount++;

            const typeInfo = typeStyles[item.type] || { label: item.type || '其他', color: '#888' };
            const isRecommended = item.title === recommended || item.is_recommended;

            const optionHtml = `
                <div class="opt-title-item" data-title="${this.escapeHtml(item.title)}" 
                     onclick="window.articleManager.selectTitleOption(this, '${item.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')"
                     style="cursor: pointer; padding: 14px 16px; border-radius: 10px; border: 2px solid ${isRecommended ? typeInfo.color : 'var(--border-color)'}; 
                            background: ${isRecommended ? typeInfo.color + '10' : 'var(--bg-secondary)'}; transition: all 0.2s;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                        <span style="background: ${typeInfo.color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">${typeInfo.label}</span>
                        ${isRecommended ? '<span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">⭐ 推荐</span>' : ''}
                    </div>
                    <div style="font-weight: 600; font-size: 15px; color: var(--text-primary); margin-bottom: 6px; line-height: 1.4;">${this.escapeHtml(item.title)}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4;">${this.escapeHtml(item.explanation || '暂无说明')}</div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', optionHtml);
        });

        if (validCount === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-secondary);">生成的标题格式异常，请重试</div>';
        } else {
            console.log(`[renderTitleOptions] 成功渲染 ${validCount} 个有效标题`);
        }

        // 默认选中推荐项
        const recommendedItem = container.querySelector('[data-title="' + recommended.replace(/"/g, '\\"') + '"]');
        if (recommendedItem) {
            this.selectTitleOption(recommendedItem, recommended);
        }
    }

    selectTitleOption(element, title) {
        // 从dataset获取HTML转义的标题，并解码
        const encodedTitle = element.dataset.title;
        // HTML解码：创建一个临时元素来解码
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = encodedTitle;
        const decodedTitle = tempDiv.textContent || tempDiv.innerText || title;

        // 移除其他选中状态
        document.querySelectorAll('.opt-title-item').forEach(el => {
            el.style.borderColor = el.dataset.title === encodedTitle ? '#667eea' : 'var(--border-color)';
            el.style.background = el.dataset.title === encodedTitle ? 'rgba(102, 126, 234, 0.1)' : 'var(--bg-secondary)';
        });

        this.selectedNewTitle = decodedTitle;
        document.getElementById('opt-title-apply-btn').disabled = false;
    }

    async applyNewTitle(articlePathEncoded) {
        if (!this.selectedNewTitle) {
            window.app?.showNotification('请先选择一个标题', 'warning');
            return;
        }

        const articlePath = decodeURIComponent(articlePathEncoded);
        const applyBtn = document.getElementById('opt-title-apply-btn');
        applyBtn.disabled = true;
        applyBtn.textContent = '应用中...';

        try {
            const response = await fetch('/api/articles/apply-title', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    article_path: articlePath,
                    platform: this.selectedNewTitle  // 复用platform字段传递新标题
                })
            });

            if (response.ok) {
                window.app?.showNotification('标题已更新成功！', 'success');
                this.closeOptimizeTitleDialog();
                await this.loadArticles();  // 刷新列表
            } else {
                throw new Error('应用失败');
            }
        } catch (error) {
            console.error('应用标题失败:', error);
            window.app?.showNotification('应用标题失败，请重试', 'error');
            applyBtn.disabled = false;
            applyBtn.textContent = '应用选中标题';
        }
    }

    // 显示通知  
    showNotification(message, type = 'info') {
        if (window.app?.showNotification) {
            window.app.showNotification(message, type);
        }
    }

    async editArticle(article) {
        try {
            if (!window.contentEditorDialog) {
                window.contentEditorDialog = new ContentEditorDialog();
            }
            await window.contentEditorDialog.open(article.path, article.title, 'article');
        } catch (error) {
            window.app?.showNotification('打开编辑器失败: ' + error.message, 'error');
        }
    }

    // ==================== 图片库管理 ====================

    // 显示图片库视图
    async showImageGallery() {
        const articleGrid = document.getElementById('article-content-grid');
        const galleryContainer = document.getElementById('image-gallery-container');
        const toolbar = document.querySelector('.manager-toolbar');
        const galleryBtn = document.getElementById('image-gallery-btn');

        if (articleGrid) articleGrid.style.display = 'none';
        if (toolbar) toolbar.style.display = 'none';
        if (galleryContainer) galleryContainer.style.display = 'block';
        if (galleryBtn) galleryBtn.style.background = 'var(--hover-bg, rgba(108,92,231,.12))';

        await this.loadImages();
    }

    // 返回文章列表
    showArticleList() {
        const articleGrid = document.getElementById('article-content-grid');
        const galleryContainer = document.getElementById('image-gallery-container');
        const toolbar = document.querySelector('.manager-toolbar');
        const galleryBtn = document.getElementById('image-gallery-btn');

        if (articleGrid) articleGrid.style.display = '';
        if (toolbar) toolbar.style.display = '';
        if (galleryContainer) galleryContainer.style.display = 'none';
        if (galleryBtn) galleryBtn.style.background = 'none';
    }

    // 加载图片列表
    async loadImages() {
        try {
            const response = await fetch('/api/articles/images');
            if (!response.ok) throw new Error('加载图片失败');
            const result = await response.json();
            const images = result.data || [];

            // 更新 badge
            const badge = document.getElementById('image-count-badge');
            if (badge) {
                if (images.length > 0) {
                    badge.textContent = images.length;
                    badge.style.display = 'inline';
                } else {
                    badge.style.display = 'none';
                }
            }

            // 更新计数
            const countEl = document.getElementById('gallery-count');
            if (countEl) countEl.textContent = `(共 ${images.length} 张)`;

            this.renderImageGallery(images);
        } catch (error) {
            window.app?.showNotification('加载图片列表失败: ' + error.message, 'error');
        }
    }

    // 渲染图片卡片网格
    renderImageGallery(images) {
        const grid = document.getElementById('image-gallery-grid');
        const emptyEl = document.getElementById('image-gallery-empty');
        if (!grid) return;

        if (images.length === 0) {
            grid.innerHTML = '';
            if (emptyEl) emptyEl.style.display = 'block';
            return;
        }
        if (emptyEl) emptyEl.style.display = 'none';

        grid.innerHTML = images.map(img => `
            <div class="image-gallery-card" style="background:var(--card-bg,#fff);border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:transform .2s,box-shadow .2s;border:1px solid var(--border-color,#e0e0e0)">
                <div style="position:relative;aspect-ratio:1;overflow:hidden;cursor:pointer" onclick="window.open('${img.path}','_blank')">
                    <img src="${img.path}" alt="${img.filename}" loading="lazy" style="width:100%;height:100%;object-fit:cover;transition:transform .3s" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                </div>
                <div style="padding:10px 12px">
                    <div style="font-size:12px;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${img.filename}">${img.filename}</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
                        <span style="font-size:11px;color:var(--text-tertiary)">${img.size_display} · ${img.create_time}</span>
                        <button onclick="window.articleManager?.deleteImage('${img.filename}')" style="background:none;border:none;cursor:pointer;color:var(--danger-color,#ef4444);font-size:14px;padding:2px 4px;border-radius:4px;transition:background .2s" title="删除" onmouseover="this.style.background='rgba(239,68,68,.1)'" onmouseout="this.style.background='none'">🗑️</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // 删除单张图片
    async deleteImage(filename) {
        window.dialogManager.showConfirm(
            `确认删除图片 "${filename}" 吗？`,
            async () => {
                try {
                    const response = await fetch(`/api/articles/images/${encodeURIComponent(filename)}`, {
                        method: 'DELETE'
                    });
                    if (response.ok) {
                        window.app?.showNotification('图片已删除', 'success');
                        await this.loadImages();
                    } else {
                        const err = await response.json();
                        window.app?.showNotification('删除失败: ' + (err.detail || '未知错误'), 'error');
                    }
                } catch (error) {
                    window.app?.showNotification('删除失败: ' + error.message, 'error');
                }
            }
        );
    }

    // 清空全部图片
    async clearAllImages() {
        window.dialogManager.showConfirm(
            '确认清空所有图片吗？此操作不可恢复！',
            async () => {
                try {
                    const response = await fetch('/api/articles/images');
                    const result = await response.json();
                    const images = result.data || [];

                    let deleted = 0;
                    for (const img of images) {
                        try {
                            const res = await fetch(`/api/articles/images/${encodeURIComponent(img.filename)}`, { method: 'DELETE' });
                            if (res.ok) deleted++;
                        } catch (e) { /* skip */ }
                    }

                    window.app?.showNotification(`已清空 ${deleted}/${images.length} 张图片`, 'success');
                    await this.loadImages();
                } catch (error) {
                    window.app?.showNotification('清空失败: ' + error.message, 'error');
                }
            }
        );
    }

    /* V19.6 & 13: 数据库智理与存储统计 */

    // 更新磁盘占用与路径信息
    async updateStorageStats() {
        try {
            const response = await fetch('/api/articles/system/storage-stats');
            if (response.ok) {
                const data = await response.json();

                const stats = data.data;
                const totalSizeEl = document.getElementById('storage-total-size');
                const rootPathEl = document.getElementById('storage-root-path');

                if (totalSizeEl) totalSizeEl.textContent = stats.total_size_formatted;
                if (rootPathEl) {
                    rootPathEl.textContent = stats.root_path;
                    rootPathEl.title = stats.root_path; // 完整路径作为悬停提示
                }
            }
        } catch (e) {
            console.warn('Failed to update storage stats:', e);
        }
    }

    // 执行 AI 智能清理
    async runSmartClean() {
        if (!window.dialogManager) return;

        window.dialogManager.showConfirm(
            '🤖 AI 建议清理：\n确认启动 AI 智能清理吗？此操作将自动识别并删除 30 天前已成功发布的冗余文章文件，以释放磁盘空间。',
            async () => {
                const btn = document.getElementById('smart-clean-btn');
                const originalText = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<span>⏳</span> 正在 AI 智能处理...';

                try {
                    const res = await fetch('/api/articles/system/smart-clean', { method: 'POST' });
                    if (res.ok) {
                        const result = await res.json();
                        this.showNotification(`✅ ${result.message}`, 'success');
                        await this.loadArticles();
                        await this.updateStorageStats();
                    } else {
                        throw new Error('清理失败');
                    }
                } catch (err) {
                    this.showNotification('❌ AI 清理失败: ' + err.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            }
        );
    }
}

// 不要在这里自动初始化,由 main.js 控制
// window.articleManager = new ArticleManager();
