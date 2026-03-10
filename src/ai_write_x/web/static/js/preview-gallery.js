class PreviewGallery {
    constructor() {
        this.container = document.getElementById('preview-gallery-container');
        this.batchDeleteBtn = document.getElementById('batch-delete-previews');
        this.selectedPaths = new Set();
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;
        await this.refresh();
        this.initialized = true;
    }

    async refresh() {
        try {
            this.container.innerHTML = '<div class="loading-state">正在加载仿真预览...</div>';
            const response = await fetch('/api/articles/previews');
            const result = await response.json();

            if (result.status === 'success') {
                this.render(result.data);
            } else {
                this.container.innerHTML = `<div class="error-state">加载失败: ${result.message}</div>`;
            }
        } catch (error) {
            this.container.innerHTML = `<div class="error-state">网络错误: ${error.message}</div>`;
        }
    }

    render(data) {
        if (!data || data.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📸</div>
                    <p>暂无预览截图，生成文章时将自动捕获</p>
                </div>`;
            return;
        }

        this.container.innerHTML = data.map(day => `
            <div class="gallery-day">
                <div class="day-title">${day.date}</div>
                <div class="gallery-grid">
                    ${day.articles.map(article => this.createArticleCard(article)).join('')}
                </div>
            </div>
        `).join('');

        this.bindEvents();
    }

    createArticleCard(article) {
        const screenshotsHtml = article.screenshots.map(src => `
            <img src="${src}" class="preview-screenshot-thumb" onclick="window.previewGallery.showLarge('${src}')">
        `).join('');

        return `
            <div class="preview-item-card" data-path="${article.path}">
                <input type="checkbox" class="preview-checkbox" onchange="window.previewGallery.toggleSelect('${article.path}', this.checked)">
                <div class="preview-screenshots-scroll">
                    ${screenshotsHtml}
                </div>
                <div class="preview-item-info">
                    <div class="preview-item-title" title="${article.title}">${article.title}</div>
                    <div class="preview-item-meta">
                        <span>${article.date}</span>
                        <span>${article.screenshots.length} 张截图</span>
                    </div>
                    <div class="preview-item-actions">
                        ${article.html_preview ? `<button class="btn btn-sm btn-secondary" onclick="window.previewGallery.openHtml('${article.html_preview}')">浏览器预览</button>` : ''}
                        <button class="btn btn-sm btn-danger" onclick="window.previewGallery.deleteSingle('${article.path}')">删除</button>
                    </div>
                </div>
            </div>
        `;
    }

    toggleSelect(path, isSelected) {
        if (isSelected) {
            this.selectedPaths.add(path);
        } else {
            this.selectedPaths.delete(path);
        }
        this.batchDeleteBtn.disabled = this.selectedPaths.size === 0;
        this.batchDeleteBtn.textContent = `批量删除 (${this.selectedPaths.size})`;
    }

    async deleteSingle(path) {
        if (!confirm('确定删除此预览记录吗？')) return;
        this.performDelete([path]);
    }

    async deleteSelected() {
        if (!confirm(`确定删除选中的 ${this.selectedPaths.size} 个项目吗？`)) return;
        this.performDelete(Array.from(this.selectedPaths));
    }

    async performDelete(paths) {
        try {
            const response = await fetch('/api/articles/previews', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paths })
            });
            const result = await response.json();
            if (result.status === 'success') {
                window.app?.showNotification(result.message, 'success');
                this.selectedPaths.clear();
                this.batchDeleteBtn.disabled = true;
                this.batchDeleteBtn.textContent = '批量删除';
                await this.refresh();
            } else {
                window.app?.showNotification('删除失败: ' + result.message, 'error');
            }
        } catch (error) {
            window.app?.showNotification('请求失败: ' + error.message, 'error');
        }
    }

    showLarge(src) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.zIndex = '20000';
        modal.onclick = () => modal.remove();
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 90%; max-height: 90%; padding: 0; background: transparent; box-shadow: none;">
                <img src="${src}" style="max-width: 100%; max-height: 90vh; border-radius: 8px; box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
                <div style="text-align: center; color: white; margin-top: 15px; font-weight: 600;">点击空白处关闭</div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    openHtml(url) {
        window.open(url, '_blank');
    }

    bindEvents() {
        // Additional events if needed
    }
}

window.previewGallery = new PreviewGallery();
