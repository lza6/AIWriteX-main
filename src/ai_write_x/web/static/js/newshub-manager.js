/**
 * NewsHub 热点聚合管理器
 */
class NewsHubManager {
    constructor() {
        this.news = [];
        this.trends = [];
        this.sources = [];
        this.autoRefreshInterval = null;
        this.refreshInterval = 300000; // 5分钟
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
            await this.loadSources();
            await this.loadTrends();
            await this.loadNews();
            await this.loadGitHubTrending();
            this.startAutoRefresh();
            this.initialized = true;
        } catch (error) {
            console.error('NewsHubManager 初始化失败:', error);
        } finally {
            this.initializing = false;
        }
    }

    bindEvents() {
        // 刷新按钮
        const refreshBtn = document.getElementById('nh-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.aggregateNow();
            });
        }

        // 分类筛选
        const categoryFilter = document.getElementById('nh-category-filter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', () => {
                this.loadNews();
            });
        }

        // 数据源配置
        const sourcesBtn = document.getElementById('nh-sources-btn');
        if (sourcesBtn) {
            sourcesBtn.addEventListener('click', () => {
                this.showSourcesConfig();
            });
        }

        // 自动刷新开关
        const autoRefresh = document.getElementById('nh-auto-refresh');
        if (autoRefresh) {
            autoRefresh.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // 模态框关闭按钮
        const modal = document.getElementById('nh-sources-modal');

        this.closeModal = () => {
            if (modal) modal.style.display = 'none';
        };

        const closeBtn = document.getElementById('nh-sources-close');
        if (closeBtn) closeBtn.addEventListener('click', this.closeModal);

        // 点击外部关闭模态框
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });
    }

    async loadSources() {
        try {
            const response = await fetch('/api/newshub/sources');
            const data = await response.json();

            if (data.status === 'success') {
                this.sources = data.sources;
                this.updateStats({
                    sources: data.enabled,
                    total_sources: data.total,
                });
            }
        } catch (error) {
            console.error('加载数据源失败:', error);
        }
    }

    async loadTrends() {
        try {
            const response = await fetch('/api/newshub/trends?limit=10');
            const data = await response.json();

            if (data.status === 'success') {
                this.trends = data.data;
                this.renderTrends();
            }
        } catch (error) {
            console.error('加载趋势失败:', error);
        }
    }

    async loadNews() {
        const category = document.getElementById('nh-category-filter')?.value || '';

        try {
            const response = await fetch('/api/newshub/aggregate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    categories: category ? [category] : [],
                    min_score: 0,
                    limit: 200,
                }),
            });

            const data = await response.json();

            if (data.status === 'success') {
                // 按分数降序排序，高分排前面
                this.news = data.data.sort((a, b) => b.score - a.score);
                this.renderNews();

                // 生成完整更新时间
                const now = new Date();
                const fullTime = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${now.toLocaleTimeString([], { hour12: false })}`;

                this.updateStats({
                    articles: data.data.length,
                    trends: data.trends?.length || 0,
                    last_update: now.toLocaleTimeString([], { hour12: false }),
                });

                // 更新工具栏的更新时间
                const timeEl = document.getElementById('nh-last-update-time');
                if (timeEl) timeEl.textContent = fullTime;

                // 更新新闻数量标签
                const countBadge = document.getElementById('nh-news-count-badge');
                if (countBadge) countBadge.textContent = `${data.data.length} 条`;
            }
        } catch (error) {
            console.error('加载新闻失败:', error);
            this.showError('加载新闻失败');
        }
    }

    async loadGitHubTrending() {
        try {
            const response = await fetch('/api/newshub/github/trending?limit=10');
            const data = await response.json();

            if (data.status === 'success') {
                this.renderGitHubTrending(data.data);
            }
        } catch (error) {
            console.error('加载GitHub趋势失败:', error);
        }
    }

    async aggregateNow() {
        const btn = document.getElementById('nh-refresh-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> 聚合中...';
        }

        try {
            await this.loadNews();
            await this.loadTrends();
            await this.loadGitHubTrending();
            this.showSuccess('聚合完成');
        } catch (error) {
            this.showError('聚合失败');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M23 4v6h-6M1 20v-6h6"/>
                        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                    </svg>
                    一键获取热点
                `;
            }
        }
    }

    renderTrends() {
        const container = document.getElementById('nh-trends-list');
        if (!container) return;

        if (this.trends.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无趋势数据</div>';
            return;
        }

        let html = '';
        this.trends.forEach((trend, index) => {
            const growthIcon = trend.growth_rate > 0 ? '📈' : trend.growth_rate < 0 ? '📉' : '➡️';
            const growthClass = trend.growth_rate > 0 ? 'positive' : trend.growth_rate < 0 ? 'negative' : '';

            html += `
                <div class="trend-item">
                    <span class="trend-rank">${index + 1}</span>
                    <span class="trend-keyword">${trend.keyword}</span>
                    <span class="trend-score">${trend.hot_score.toFixed(1)}°</span>
                    <span class="trend-growth ${growthClass}">${growthIcon} ${(Math.abs(trend.growth_rate) * 100).toFixed(0)}%</span>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    renderNews() {
        const container = document.getElementById('nh-news-list');
        if (!container) return;

        if (this.news.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无新闻数据</div>';
            return;
        }

        let html = '';
        this.news.forEach(item => {
            const sentimentClass = item.sentiment === 'positive' ? 'positive' :
                item.sentiment === 'negative' ? 'negative' : 'neutral';
            const sentimentIcon = item.sentiment === 'positive' ? '😊' :
                item.sentiment === 'negative' ? '😔' : '😐';

            html += `
                <div class="news-card" data-id="${item.id}">
                    <div class="news-header">
                        <span class="news-category">${item.category}</span>
                        <span class="news-score">评分: ${item.score.toFixed(1)}</span>
                    </div>
                    <h3 class="news-title">${item.title}</h3>
                    <p class="news-summary">${item.summary}</p>
                    <div class="news-footer">
                        <div class="news-keywords">
                            ${item.keywords.map(kw => `<span class="keyword-tag">${kw}</span>`).join('')}
                        </div>
                        <div class="news-meta">
                            <span class="news-source">${item.source}</span>
                            <span class="news-sentiment ${sentimentClass}">${sentimentIcon}</span>
                        </div>
                    </div>
                    <div class="news-actions">
                        <button class="action-btn" onclick="window.newshubManager.writeArticle('${item.id}')">
                            <svg viewBox="0 0 24 24" width="14" height="14">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                            创作文章
                        </button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    renderGitHubTrending(data) {
        const container = document.getElementById('nh-github-list');
        if (!container || !data) return;

        // 解析返回的文本数据
        const repos = this.parseGitHubData(data);

        if (repos.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无GitHub趋势数据</div>';
            return;
        }

        let html = '';
        repos.forEach((repo, index) => {
            html += `
                <div class="github-item">
                    <span class="github-rank">${index + 1}</span>
                    <div class="github-info">
                        <a href="${repo.url}" target="_blank" class="github-name">${repo.name}</a>
                        <p class="github-desc">${repo.description}</p>
                        <div class="github-meta">
                            <span class="github-stars">⭐ ${repo.stars.toLocaleString()}</span>
                            <span class="github-lang">${repo.language}</span>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    parseGitHubData(text) {
        // 简单解析GitHub返回的文本
        const repos = [];
        const lines = text.split('\n');

        let currentRepo = null;
        lines.forEach(line => {
            if (line.match(/^\d+\./)) {
                if (currentRepo) repos.push(currentRepo);
                const name = line.replace(/^\d+\./, '').trim();
                currentRepo = { name, description: '', stars: 0, language: '', url: '' };
            } else if (currentRepo && line.includes('⭐')) {
                const match = line.match(/⭐ ([\d,]+)/);
                if (match) currentRepo.stars = parseInt(match[1].replace(/,/g, ''));
                const langMatch = line.match(/\| ([\w#+]+) \|/);
                if (langMatch) currentRepo.language = langMatch[1];
            } else if (currentRepo && line.includes('🔗')) {
                currentRepo.url = line.replace('🔗', '').trim();
            } else if (currentRepo && line.trim() && !line.includes('===')) {
                currentRepo.description = line.trim();
            }
        });

        if (currentRepo) repos.push(currentRepo);
        return repos.slice(0, 10);
    }

    updateStats(stats) {
        if (stats.sources !== undefined) {
            const el = document.getElementById('nh-sources-count');
            if (el) el.textContent = stats.sources;
        }
        if (stats.articles !== undefined) {
            const el = document.getElementById('nh-articles-count');
            if (el) el.textContent = stats.articles;
        }
        if (stats.trends !== undefined) {
            const el = document.getElementById('nh-trends-count');
            if (el) el.textContent = stats.trends;
        }
        if (stats.last_update !== undefined) {
            const el = document.getElementById('nh-last-update');
            if (el) el.textContent = stats.last_update;
        }
    }

    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        this.autoRefreshInterval = setInterval(() => {
            this.loadNews();
            this.loadTrends();
        }, this.refreshInterval);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    showSourcesConfig() {
        const modal = document.getElementById('nh-sources-modal');
        if (!modal) return;

        modal.style.display = 'flex';
        this.renderSourcesList();
    }

    renderSourcesList() {
        const container = document.getElementById('nh-sources-list');
        if (!container) return;

        if (!this.sources || this.sources.length === 0) {
            container.innerHTML = '<div class="empty-state">没有可配置的数据源</div>';
            return;
        }

        let html = `
            <div class="nh-source-add-form" style="margin-bottom: 20px; padding: 15px; background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border-color);">
                <h4 style="margin-bottom: 10px; font-size: 14px; color: var(--text-primary);">添加自定义 RSS 源</h4>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <input type="text" id="nh-new-source-name" placeholder="源名称" style="flex: 1; min-width: 120px; padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-primary);">
                    <input type="text" id="nh-new-source-url" placeholder="RSS URL" style="flex: 2; min-width: 180px; padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-primary);">
                    <select id="nh-new-source-category" style="padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-primary);">
                        <option value="tech">科技</option>
                        <option value="finance">财经</option>
                        <option value="social">综合</option>
                        <option value="ai">人工智能</option>
                    </select>
                    <button class="toolbar-btn primary" onclick="window.newshubManager.addCustomSource()" style="padding: 6px 12px;">添加</button>
                </div>
            </div>
            <div class="sources-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;">
        `;

        this.sources.forEach(source => {
            const isEnabled = source.enabled;
            const statusClass = isEnabled ? 'running' : 'stopped';
            const statusText = isEnabled ? '已启用' : '已禁用';
            const isCustom = source.id.startsWith('custom_');

            html += `
                <div class="mcp-card" style="padding: 12px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--surface-color); position: relative;">
                    <div class="mcp-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h3 class="mcp-name" style="margin: 0; font-size: 14px; color: var(--text-primary);">${source.name}</h3>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            ${isCustom ? `
                                <button onclick="window.newshubManager.deleteSource('${source.id}')" style="background: none; border: none; color: #ef4444; cursor: pointer; padding: 2px;" title="删除">
                                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                                </button>
                            ` : ''}
                            <label class="switch" style="position: relative; display: inline-block; width: 34px; height: 18px;">
                                <input type="checkbox" data-source-id="${source.id}" ${isEnabled ? 'checked' : ''} style="opacity: 0; width: 0; height: 0;">
                                <span class="slider round"></span>
                            </label>
                        </div>
                    </div>
                    <p class="mcp-description" style="margin: 0 0 8px 0; font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${source.url}">${source.url || '系统默认源'}</p>
                    <div class="mcp-status ${statusClass}" style="font-size: 11px;">
                        <span class="status-indicator"></span> ${statusText}
                        <span style="margin-left: 8px; opacity: 0.7;">${source.category}</span>
                    </div>
                </div>
            `;
        });

        html += '</div>';

        // 注入小段专属开关 CSS (保持原样)
        if (!document.getElementById('nh-switch-css')) {
            const style = document.createElement('style');
            style.id = 'nh-switch-css';
            style.innerHTML = `
                .switch input:checked + .slider { background-color: var(--primary-color, #2196F3); }
                .switch input:focus + .slider { box-shadow: 0 0 1px var(--primary-color, #2196F3); }
                .switch input:checked + .slider:before { transform: translateX(16px); }
                .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 34px; }
                .slider:before { position: absolute; content: ""; height: 14px; width: 14px; left: 2px; bottom: 2px; background-color: white; transition: .4s; border-radius: 50%; }
            `;
            document.head.appendChild(style);
        }

        container.innerHTML = html;

        // 绑定数据源开关事件
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const sourceId = e.target.getAttribute('data-source-id');
                const isEnabled = e.target.checked;
                const card = e.target.closest('.mcp-card');
                const statusDiv = card.querySelector('.mcp-status');

                try {
                    const action = isEnabled ? 'enable' : 'disable';
                    const response = await fetch(`/api/newshub/sources/${sourceId}/${action}`, { method: 'POST' });
                    const result = await response.json();

                    if (result.status === 'success') {
                        // 更新内部状态
                        const src = this.sources.find(s => s.id === sourceId);
                        if (src) src.enabled = isEnabled;

                        // 更新UI
                        statusDiv.className = `mcp-status ${isEnabled ? 'running' : 'stopped'}`;
                        const statusIndicator = statusDiv.querySelector('.status-indicator').outerHTML;
                        statusDiv.innerHTML = `${statusIndicator} ${isEnabled ? '已启用' : '已禁用'} <span style="margin-left: 8px; opacity: 0.7;">${src.category}</span>`;

                        // 重新计算统计信息
                        const enabledCount = this.sources.filter(s => s.enabled).length;
                        this.updateStats({
                            sources: enabledCount,
                            total_sources: this.sources.length
                        });

                        if (window.app?.showNotification) {
                            window.app.showNotification(`${isEnabled ? '启用' : '禁用'}成功`, 'success');
                        }
                    } else {
                        e.target.checked = !isEnabled;
                    }
                } catch (error) {
                    console.error('配置数据源失败:', error);
                    e.target.checked = !isEnabled;
                }
            });
        });
    }

    async addCustomSource() {
        const nameInput = document.getElementById('nh-new-source-name');
        const urlInput = document.getElementById('nh-new-source-url');
        const catSelect = document.getElementById('nh-new-source-category');

        const name = nameInput?.value.trim();
        const url = urlInput?.value.trim();
        const category = catSelect?.value;

        if (!name || !url) {
            window.app?.showNotification('请填写源名称和 URL', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/newshub/sources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url, category, type: 'rss' })
            });

            if (response.ok) {
                window.app?.showNotification('数据源添加成功', 'success');
                await this.loadSources();
                this.renderSourcesList();
            } else {
                const err = await response.json();
                window.app?.showNotification('添加失败: ' + (err.detail || '未知错误'), 'error');
            }
        } catch (error) {
            window.app?.showNotification('网络错误', 'error');
        }
    }

    async deleteSource(sourceId) {
        if (!confirm('确定要删除这个数据源吗？')) return;

        try {
            const response = await fetch(`/api/newshub/sources/${sourceId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                window.app?.showNotification('数据源已删除', 'success');
                await this.loadSources();
                this.renderSourcesList();
            }
        } catch (error) {
            window.app?.showNotification('删除失败', 'error');
        }
    }

    writeArticle(newsId) {
        // 基于热点新闻创作文章
        const news = this.news.find(n => n.id === newsId);
        if (!news) return;

        // 切换到创意工坊并填充话题
        if (window.app) {
            window.app.switchView('creative-workshop');

            // 深度对齐主界面借鉴模式逻辑，增加鲁棒性
            const performIntegration = () => {
                // 检查管理器是否就绪
                if (!window.creativeWorkshopManager || !window.creativeWorkshopManager.initialized) {
                    // 如果还没初始化完，等一会儿再试
                    setTimeout(performIntegration, 200);
                    return;
                }

                // 填充话题
                const topicInput = document.getElementById('topic-input');
                if (topicInput) {
                    topicInput.value = news.title;
                    topicInput.dispatchEvent(new Event('input', { bubbles: true }));
                }

                // 填充参考链接
                const refUrlsInput = document.getElementById('reference-urls');
                if (refUrlsInput) {
                    refUrlsInput.value = news.url || '';
                    refUrlsInput.dispatchEvent(new Event('input', { bubbles: true }));
                }

                // 展开借鉴模式面板
                const refPanel = document.getElementById('reference-mode-panel');
                const refBtn = document.getElementById('reference-mode-btn');
                if (refPanel && refPanel.classList.contains('collapsed')) {
                    if (refBtn) refBtn.click(); // 通过模拟点击触发展开逻辑，确保内部状态同步
                }

                // 显示提示
                if (window.app.showNotification) {
                    window.app.showNotification('已自动启用借鉴模式，正在准备生成热点文章...', 'info');
                }

                // 自动点击开始生成按钮（等待面板展开动画）
                setTimeout(() => {
                    const generateBtn = document.getElementById('generate-btn');
                    if (generateBtn && !window.creativeWorkshopManager.isGenerating) {
                        generateBtn.click();
                    }
                }, 800);
            };

            // 稍微延迟一下确保视图切换逻辑完成
            setTimeout(performIntegration, 300);
        }
    }

    showSuccess(message) {
        if (window.app && window.app.showNotification) {
            window.app.showNotification(message, 'success');
        }
    }

    showError(message) {
        if (window.app && window.app.showNotification) {
            window.app.showNotification(message, 'error');
        }
    }
}

// ⚡ 懒加载：不在页面打开时立即初始化，而是等用户切换到 NewsHub 面板时才创建
// 由 main.js 中的 switchView('newshub') 触发 get_hub_manager()
if (typeof window !== 'undefined') {
    window.getNewsHubManager = function () {
        if (!window.newshubManager) {
            window.newshubManager = new NewsHubManager();
        }
        return window.newshubManager;
    };
}