// 自动寻猎展示面板核心
class SpiderManager {
    constructor() {
        this.spiders = [];
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
            await this.loadSpiders();
            this.initialized = true;
        } catch (error) {
            console.error('SpiderManager 初始化失败:', error);
        } finally {
            this.initializing = false;
        }
    }

    async loadSpiders() {
        try {
            const response = await fetch('/api/spider/list');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.spiders = data.spiders || [];
                    this.renderSpiderList();
                } else {
                    console.error('加载爬虫列表失败:', data.message);
                    this.spiders = [];
                    this.renderSpiderList();
                }
            } else {
                console.error('加载爬虫列表返回非200状态:', response.status);
                this.spiders = [];
                this.renderSpiderList();
            }
        } catch (error) {
            console.error('加载爬虫列表网络错误:', error);
            this.spiders = [];
            this.renderSpiderList();
        }
    }

    renderSpiderList() {
        const container = document.getElementById('spider-platform-grid');
        if (!container) return;

        if (this.spiders.length === 0) {
            container.innerHTML = '<div class="loading-pulse">暂无可用探测节点</div>';
            return;
        }

        container.innerHTML = this.spiders.map((spider, i) => `
            <div class="glass-spider-card" style="animation-delay: ${i * 0.05}s">
                <div class="card-icon-wrapper">
                    ${this.getIconForCategory(spider.category)}
                </div>
                <div class="card-info">
                    <div class="card-title">${spider.display_name}</div>
                    <div class="card-tags">
                        <span class="tag tag-primary">${spider.category}</span>
                        <span class="tag tag-status ${spider.enabled ? 'active' : 'inactive'}">
                            ${spider.enabled ? '🟢在线' : '🔴离线'}
                        </span>
                    </div>
                </div>
                <div class="card-bg-glow"></div>
            </div>
        `).join('');
    }

    getIconForCategory(category) {
        if (category.includes('GitHub') || category.includes('AI')) {
            return `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>`;
        } else if (category.includes('国际') || category.includes('World')) {
            return `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"></circle><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`;
        } else {
            return `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M19 20H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1m2 13a2 2 0 0 1-2-2V7m2 13a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path></svg>`;
        }
    }
}

// 由 main.js 统一管理初始化，避免重复创建实例