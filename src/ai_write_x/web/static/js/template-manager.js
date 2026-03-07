class TemplateManager {
    constructor() {
        this.templates = [];
        this.categories = [];
        this.currentTemplate = null;
        this.currentLayout = 'grid';
        this.currentCategory = null;
        this.observer = null;
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
            // 首次初始化：并行加载数据
            // 使用 allSettled 更加健壮，即使某个加载失败也不影响整体初始化流程
            await Promise.allSettled([
                this.loadDefaultCategories().catch(err => console.error('加载默认分类失败:', err)),
                this.loadCategories().catch(err => console.error('加载分类失败:', err)),
                this.loadTemplates().catch(err => console.error('加载模板失败:', err))
            ]);

            this.setupIntersectionObserver();
            this.bindEvents();
            this.renderCategoryTree();
            this.renderTemplateGrid();
            this.initialized = true;
            this.updateAddTemplateButtonState();
        } catch (error) {
            console.error('TemplateManager 初始化发生严重错误:', error);
            // 即使核心流程失败，也尝试绑定基本事件
            this.bindEvents();
        } finally {
            this.initializing = false;
        }
    }

    // 从后端加载默认分类  
    async loadDefaultCategories() {
        try {
            const response = await fetch('/api/templates/default-template-categories');
            if (response.ok) {
                const result = await response.json();
                this.defaultCategories = result.data || [];
            } else {
                this.defaultCategories = [];
            }
        } catch (error) {
            this.defaultCategories = [];
        }
    }

    isDefaultCategory(categoryName) {
        return this.defaultCategories.includes(categoryName);
    }

    async loadCategories() {
        try {
            const response = await fetch('/api/templates/categories');
            if (response.ok) {
                const result = await response.json();
                this.categories = result.data || [];
            } else {
                console.error('加载分类列表返回非200状态:', response.status);
                this.categories = [];
            }
        } catch (error) {
            console.error('加载分类列表网络错误:', error);
            this.categories = [];
        }
    }

    async loadTemplates(category = null) {
        try {
            const url = category
                ? `/api/templates?category=${encodeURIComponent(category)}`
                : '/api/templates';
            const response = await fetch(url);
            if (response.ok) {
                const result = await response.json();
                this.templates = result.data || [];
            } else {
                console.error('加载模板列表返回非200状态:', response.status);
                this.templates = [];
            }
        } catch (error) {
            console.error('加载模板列表网络错误:', error);
            this.templates = [];
        }
    }

    bindEvents() {
        // 新建模板    
        const addTemplateBtn = document.getElementById('add-template');
        if (addTemplateBtn) {
            addTemplateBtn.addEventListener('click', () => {
                this.showCreateTemplateDialog();
            });
        }

        // 新建分类    
        const addCategoryBtn = document.getElementById('add-category');
        if (addCategoryBtn) {
            addCategoryBtn.addEventListener('click', () => {
                this.showCreateCategoryDialog();
            });
        }

        // 搜索    
        const searchInput = document.getElementById('template-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTemplates(e.target.value);
            });
        }

        // 视图切换 - 删除全局绑定,只保留限定作用域的绑定  
        const templateView = document.getElementById('template-manager-view');
        if (templateView) {
            templateView.querySelectorAll('.view-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    templateView.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.currentLayout = btn.dataset.layout === 'grid' ? 'grid' : 'list';
                    this.renderTemplateGrid();
                });
            });
        }

        // 分类树点击    
        const categoryTree = document.getElementById('template-sidebar-tree');
        if (categoryTree) {
            categoryTree.addEventListener('click', (e) => {
                const categoryItem = e.target.closest('.tree-item');
                if (categoryItem) {
                    this.selectCategory(categoryItem.dataset.category);
                }
            });
        }

        // 快捷键刷新 (F5 或 Ctrl+R) - 隐藏功能    
        document.addEventListener('keydown', (e) => {
            const templateView = document.getElementById('template-manager-view');
            if (templateView && templateView.style.display !== 'none') {
                if (e.key === 'F5' || ((e.ctrlKey || e.metaKey) && e.key === 'r')) {
                    e.preventDefault();
                    this.refreshTemplates();
                }
            }
        });
    }

    async refreshTemplates() {
        try {
            await this.loadCategories();
            await this.loadTemplates(this.currentCategory);
            this.renderCategoryTree();
            this.renderTemplateGrid();
            window.app?.showNotification('已刷新模板列表', 'success');
        } catch (error) {
            window.app?.showNotification('刷新失败: ' + error.message, 'error');
        }
    }

    renderCategoryTree() {
        const tree = document.getElementById('template-sidebar-tree');
        if (!tree) return;

        const allCount = this.templates.length;
        tree.innerHTML = `    
            <div class="tree-item ${!this.currentCategory ? 'active' : ''}" data-category="">    
                <span class="tree-icon">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">  
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>  
                    </svg>
                </span>    
                <span class="tree-name" title="全部模板">全部模板</span>    
                <span class="item-count">${allCount}</span>    
            </div>    
            ${this.categories.map(cat => `    
                <div class="tree-item ${this.currentCategory === cat.name ? 'active' : ''}"     
                    data-category="${cat.name}">    
                    <span class="tree-icon">  
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">  
                            <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2z"/>  
                        </svg>  
                    </span>    
                    <span class="tree-name" title="${cat.name}">${cat.name}</span>    
                    <span class="item-count">${cat.template_count}</span>    
                </div>    
            `).join('')}    
        `;

        // 绑定右键菜单事件    
        tree.querySelectorAll('.tree-item[data-category]:not([data-category=""])').forEach(item => {
            item.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                const categoryName = item.dataset.category;
                this.showCategoryContextMenu(e, categoryName);
            });
        });

        // 绑定拖拽接收事件    
        this.bindCategoryDropEvents();
    }

    bindCategoryDropEvents() {
        const tree = document.getElementById('template-sidebar-tree');
        if (!tree) return;

        // 为所有分类项(除了"全部模板")绑定拖拽接收事件  
        tree.querySelectorAll('.tree-item[data-category]:not([data-category=""])').forEach(item => {
            // 拖拽悬停  
            item.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';

                // 获取源分类  
                const sourceCategory = e.dataTransfer.getData('template-category');
                const targetCategory = item.dataset.category;

                // 如果是同一分类,显示禁止图标  
                if (sourceCategory === targetCategory) {
                    e.dataTransfer.dropEffect = 'none';
                    item.classList.remove('drag-over');
                } else {
                    item.classList.add('drag-over');
                }
            });

            // 拖拽离开  
            item.addEventListener('dragleave', (e) => {
                item.classList.remove('drag-over');
            });

            // 拖拽放下  
            item.addEventListener('drop', async (e) => {
                e.preventDefault();
                item.classList.remove('drag-over');

                const sourcePath = e.dataTransfer.getData('template-path');
                const templateName = e.dataTransfer.getData('template-name');
                const sourceCategory = e.dataTransfer.getData('template-category');
                const targetCategory = item.dataset.category;

                // 如果是同一分类,不执行操作  
                if (sourceCategory === targetCategory) {
                    return;
                }

                // 弹出确认对话框  
                this.showMoveConfirmDialog(sourcePath, templateName, sourceCategory, targetCategory);
            });
        });
    }

    showMoveConfirmDialog(sourcePath, templateName, sourceCategory, targetCategory) {
        const message = `确认将模板 "${templateName}" 从 "${sourceCategory}" 移动到 "${targetCategory}"?`;

        window.dialogManager.showConfirm(
            message,
            async () => {
                try {
                    const response = await fetch('/api/templates/move', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source_path: sourcePath,
                            target_category: targetCategory
                        })
                    });

                    if (response.ok) {
                        // 刷新数据  
                        await this.loadCategories();
                        await this.loadTemplates(this.currentCategory);
                        this.renderCategoryTree();
                        this.renderTemplateGrid();

                        window.app?.showNotification(`模板已移动到 "${targetCategory}"`, 'success');
                    } else {
                        const error = await response.json();
                        window.dialogManager.showAlert('移动失败: ' + (error.detail || '未知错误'), 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('移动失败: ' + error.message, 'error');
                }
            }
        );
    }

    showCategoryContextMenu(e, categoryName) {
        // 检查是否为系统内置分类  
        if (this.isDefaultCategory(categoryName)) {
            e.preventDefault();
            return; // 直接返回,不显示菜单  
        }

        const existingMenu = document.querySelector('.category-context-menu');
        if (existingMenu) {
            existingMenu.remove();
        }

        // 创建菜单    
        const menu = document.createElement('div');
        menu.className = 'category-context-menu';
        menu.style.left = `${e.pageX}px`;
        menu.style.top = `${e.pageY}px`;

        // 编辑选项    
        const editItem = document.createElement('div');
        editItem.className = 'context-menu-item';
        editItem.innerHTML = '<span>✏️</span> 编辑分类';
        editItem.addEventListener('click', () => {
            menu.remove();
            this.editCategory(categoryName);
        });

        // 删除选项    
        const deleteItem = document.createElement('div');
        deleteItem.className = 'context-menu-item context-menu-item-danger';
        deleteItem.innerHTML = '<span>🗑️</span> 删除分类';
        deleteItem.addEventListener('click', () => {
            menu.remove();
            this.deleteCategory(categoryName);
        });

        menu.appendChild(editItem);
        menu.appendChild(deleteItem);
        document.body.appendChild(menu);

        // 点击外部关闭菜单    
        setTimeout(() => {
            const closeMenu = () => {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            };
            document.addEventListener('click', closeMenu);
        }, 0);
    }

    async editCategory(oldCategoryName) {
        window.dialogManager.showInput(
            '编辑分类',
            '请输入新的分类名称:',
            oldCategoryName,
            async (newName) => {
                if (!newName || newName === oldCategoryName) {
                    return;
                }

                // 检查新名称是否已存在    
                if (this.categories.some(cat => cat.name === newName)) {
                    window.dialogManager.showAlert('分类名称已存在', 'error');
                    return;
                }

                try {
                    const response = await fetch(`/api/templates/categories/${encodeURIComponent(oldCategoryName)}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            old_name: oldCategoryName,  // 添加这一行  
                            new_name: newName
                        })
                    });

                    if (response.ok) {
                        await this.updateConfigIfNeeded(oldCategoryName, newName);
                        await this.loadCategories();
                        this.renderCategoryTree();

                        if (this.currentCategory === oldCategoryName) {
                            await this.selectCategory(newName);
                        }

                        window.app?.showNotification('分类已重命名', 'success');
                    } else {
                        const error = await response.json();
                        const errorMessage = typeof error.detail === 'string'
                            ? error.detail
                            : JSON.stringify(error.detail);
                        window.dialogManager.showAlert('重命名失败: ' + errorMessage, 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('重命名失败: ' + error.message, 'error');
                }
            }
        );
    }

    async deleteCategory(categoryName) {
        const category = this.categories.find(cat => cat.name === categoryName);
        const templateCount = category ? category.template_count : 0;

        const message = templateCount > 0
            ? `确认删除分类 "${categoryName}" 及其包含的 ${templateCount} 个模板?\n\n此操作不可撤销!`
            : `确认删除空分类 "${categoryName}"?`;

        window.dialogManager.showConfirm(
            message,
            async () => {
                try {
                    const response = await fetch(`/api/templates/categories/${encodeURIComponent(categoryName)}?force=true`, {
                        method: 'DELETE'
                    });

                    if (response.ok) {
                        await this.updateConfigIfNeeded(categoryName, null);
                        await this.loadCategories();
                        await this.loadTemplates();
                        this.renderCategoryTree();
                        this.renderTemplateGrid();

                        if (this.currentCategory === categoryName) {
                            await this.selectCategory(null);
                        }

                        window.app?.showNotification('分类已删除', 'success');
                    } else {
                        const error = await response.json();
                        const errorMessage = typeof error.detail === 'string'
                            ? error.detail
                            : JSON.stringify(error.detail);
                        window.dialogManager.showAlert('删除失败: ' + errorMessage, 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('删除失败: ' + error.message, 'error');
                }
            }
        );
    }

    async updateConfigIfNeeded(oldCategoryName, newCategoryName) {
        try {
            // 获取当前配置  
            const configResponse = await fetch('/api/config/');
            if (!configResponse.ok) return;

            const configData = await configResponse.json();
            const currentCategory = configData.data?.template_category;

            // 如果当前配置的分类就是被修改/删除的分类  
            if (currentCategory === oldCategoryName) {
                // 更新配置  
                const updateResponse = await fetch('/api/config/', {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        template_category: newCategoryName || ''  // 删除时设为空字符串  
                    })
                });

                if (updateResponse.ok) {
                    // 持久化到磁盘  
                    await fetch('/api/config/', { method: 'POST' });

                    if (newCategoryName) {
                        window.app?.showNotification(`配置已自动更新为新分类: ${newCategoryName}`, 'info');
                    } else {
                        window.app?.showNotification('配置中的分类设置已清空', 'info');
                    }
                }
            }
        } catch (error) {
            // 配置更新失败不影响分类操作本身  
        }
    }

    setupIntersectionObserver() {
        // 清理旧的observer  
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }

        // 创建新的observer  
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const card = entry.target;
                    const iframe = card.querySelector('iframe[data-template-path]');
                    if (iframe && iframe.dataset.loaded !== 'true') {
                        this.loadSinglePreview(iframe);
                        this.observer.unobserve(card);
                    }
                }
            });
        }, {
            root: document.querySelector('#template-manager-view .manager-main'),
            rootMargin: '200px',
            threshold: 0.01
        });
    }

    renderTemplateGrid() {
        const grid = document.getElementById('template-content-grid');
        if (!grid) return;

        grid.className = this.currentLayout === 'grid' ? 'content-grid' : 'content-grid list-view';

        if (this.templates.length === 0) {
            grid.innerHTML = '<div class="empty-state">暂无模板</div>';
            return;
        }

        // 使用 DocumentFragment 批量添加  
        const fragment = document.createDocumentFragment();
        this.templates.forEach(template => {
            const card = this.createTemplateCard(template);
            fragment.appendChild(card);
        });

        grid.innerHTML = '';
        grid.appendChild(fragment);

        this.bindCardEvents();
        this.bindDragEvents();

        requestAnimationFrame(() => {
            if (this.observer) {
                const cards = grid.querySelectorAll('.template-card');
                cards.forEach(card => this.observer.observe(card));
            }
        });
    }

    createTemplateCard(template) {
        const card = document.createElement('div');
        card.className = 'content-card template-card';
        card.dataset.templatePath = template.path;
        card.dataset.templateName = template.name;
        card.dataset.templateCategory = template.category;
        card.draggable = true;

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
            <div class="card-preview">  
                <iframe sandbox="allow-same-origin allow-scripts"   
                        loading="lazy"  
                        data-template-path="${template.path}"  
                        data-loaded="false"></iframe>  
                <div class="preview-loading">加载中...</div>  
            </div>  
            <div class="card-content">  
                <h4 class="card-title" title="${template.name}">${template.name}</h4>  
                <div class="card-meta">  
                    <span class="category-badge" title="${template.category}">${template.category}</span>  
                    <span class="meta-divider">•</span>  
                    <span class="size-info">${template.size}</span>  
                    <span class="meta-divider">•</span>  
                    <span class="time-info">${formatTime(template.create_time)}</span>  
                </div>  
            </div>  
            <div class="card-actions">  
                <button class="btn-icon" data-action="vote" title="审美投票 (影响 AI DNA)">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
                    </svg>
                </button>
                <button class="btn-icon" data-action="edit" title="编辑">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>  
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>  
                    </svg>  
                </button>  
                <button class="btn-icon" data-action="rename" title="重命名">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <path d="M4 7h16M4 12h10M4 17h10"/>  
                        <path d="M20 17l-4-4 4-4"/>  
                    </svg>  
                </button>  
                <button class="btn-icon" data-action="copy" title="复制">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>  
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>  
                    </svg>  
                </button>  
                <button class="btn-icon" data-action="delete" title="删除">  
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">  
                        <polyline points="3 6 5 6 21 6"/>  
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>  
                    </svg>  
                </button>  
            </div>  
        `;

        return card;
    }

    async loadSinglePreview(iframe) {
        const templatePath = iframe.dataset.templatePath;
        const loadingEl = iframe.parentElement.querySelector('.preview-loading');

        try {
            const response = await fetch(`/api/templates/content/${encodeURIComponent(templatePath)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const content = await response.text();

            // 检测文件扩展名    
            const ext = templatePath.toLowerCase().split('.').pop();
            let htmlContent = content;

            // 如果是Markdown文件,渲染HTML内容    
            if ((ext === 'md' || ext === 'markdown') && window.markdownRenderer) {
                htmlContent = window.markdownRenderer.render(content);
            } else if (ext === 'txt') {
                // TXT文件:将换行符转换为HTML段落  
                htmlContent = content.split('\n')
                    .map(line => line.trim() ? `<p>${line}</p>` : '<br>')
                    .join('\n');
            }

            // 为卡片预览添加完整的Markdown样式(紧凑版)  
            const styledHtml = `    
                <style>    
                    body {     
                        overflow: hidden !important;     
                        margin: 0;  
                        padding: 8px;  
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;  
                        line-height: 1.4;  
                        font-size: 12px;  
                    }  
                    
                    /* 标题样式 - 紧凑版 */  
                    h1, h2, h3, h4, h5, h6 {  
                        margin: 4px 0 2px 0;  
                        font-weight: 600;  
                    }  
                    h1 { font-size: 16px; }  
                    h2 { font-size: 14px; }  
                    h3 { font-size: 13px; }  
                    h4, h5, h6 { font-size: 12px; }  
                    
                    /* 段落样式 */  
                    p {  
                        margin: 2px 0 4px 0;  
                    }  
                    
                    /* 引用块样式 - 关键修复 */  
                    blockquote {  
                        margin: 4px 0;  
                        padding: 2px 8px;  
                        border-left: 3px solid #ddd;  
                        background: #f9f9f9;  
                        font-style: italic;  
                        font-size: 11px;  
                    }  
                    
                    /* 代码样式 */  
                    code {  
                        background: #f0f0f0;  
                        padding: 1px 3px;  
                        border-radius: 2px;  
                        font-family: 'Consolas', 'Monaco', monospace;  
                        font-size: 10px;  
                    }  
                    
                    pre {  
                        background: #f0f0f0;  
                        padding: 6px;  
                        border-radius: 3px;  
                        overflow-x: auto;  
                        font-size: 10px;  
                        margin: 4px 0;  
                    }  
                    
                    pre code {  
                        background: none;  
                        padding: 0;  
                    }  
                    
                    /* 表格样式 */  
                    table {  
                        border-collapse: collapse;  
                        width: 100%;  
                        font-size: 10px;  
                        margin: 4px 0;  
                    }  
                    
                    table th, table td {  
                        padding: 2px 4px;  
                        border: 1px solid #ddd;  
                    }  
                    
                    table th {  
                        background: #f0f0f0;  
                        font-weight: 600;  
                    }  
                    
                    /* 链接样式 */  
                    a {  
                        color: #0366d6;  
                        text-decoration: none;  
                    }  
                    
                    /* 列表样式 */  
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
                    
                    /* 强调样式 */  
                    strong { font-weight: 600; }  
                    em { font-style: italic; }  
                    
                    /* 隐藏滚动条 */  
                    ::-webkit-scrollbar { display: none !important; }    
                    * { scrollbar-width: none !important; }    
                </style>    
                ${htmlContent}    
            `;

            iframe.srcdoc = styledHtml;
            iframe.dataset.loaded = 'true';
            if (loadingEl) loadingEl.style.display = 'none';
        } catch (error) {
            iframe.srcdoc = '<div style="padding: 20px; color: red;">加载失败</div>';
            if (loadingEl) loadingEl.textContent = '加载失败';
        }
    }

    bindCardEvents() {
        const grid = document.getElementById('template-content-grid');
        if (!grid) return;

        grid.querySelectorAll('.template-card').forEach(card => {
            // 卡片点击预览  
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.card-actions')) {
                    const templatePath = card.dataset.templatePath;
                    const template = this.templates.find(t => t.path === templatePath);
                    if (template) {
                        this.previewTemplate(template);
                    }
                }
            });

            // 操作按钮点击  
            card.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const action = btn.dataset.action;
                    const templatePath = card.dataset.templatePath;
                    const template = this.templates.find(t => t.path === templatePath);
                    if (template) {
                        this.handleCardAction(action, template);
                    }
                });
            });
        });
    }

    bindDragEvents() {
        const grid = document.getElementById('template-content-grid');
        if (!grid) return;

        // 为所有模板卡片绑定拖拽开始事件  
        grid.querySelectorAll('.template-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                const templatePath = card.dataset.templatePath;
                const templateName = card.dataset.templateName;
                const templateCategory = card.dataset.templateCategory;

                // 存储拖拽数据  
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('template-path', templatePath);
                e.dataTransfer.setData('template-name', templateName);
                e.dataTransfer.setData('template-category', templateCategory);

                // 添加拖拽样式  
                card.classList.add('dragging');
                card.style.opacity = '0.5';
            });

            card.addEventListener('dragend', (e) => {
                // 移除拖拽样式  
                card.classList.remove('dragging');
                card.style.opacity = '1';
            });
        });
    }

    async handleCardAction(action, template) {
        switch (action) {
            case 'rename':  // 新增  
                await this.renameTemplate(template);
                break;
            case 'preview':
                this.previewTemplate(template);
                break;
            case 'edit':
                await this.editTemplate(template);
                break;
            case 'copy':
                await this.copyTemplate(template);
                break;
            case 'delete':
                await this.deleteTemplate(template);
                break;
            case 'vote':
                if (window.aestheticVotingManager) {
                    await window.aestheticVotingManager.open({
                        type: 'template',
                        path: template.path,
                        title: template.name
                    });
                } else {
                    window.app?.showNotification('投票管理器未加载', 'error');
                }
                break;
        }
    }

    // 重命名方法  
    async renameTemplate(template) {
        window.dialogManager.showInput(
            '重命名模板',
            '请输入新的模板名称:',
            template.name,
            async (newName) => {
                if (!newName || newName === template.name) return;

                try {
                    const response = await fetch('/api/templates/rename', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            old_path: template.path,
                            new_name: newName
                        })
                    });

                    if (response.ok) {
                        await this.loadCategories();
                        await this.loadTemplates(this.currentCategory);
                        this.renderCategoryTree();
                        this.renderTemplateGrid();
                        window.app?.showNotification('模板已重命名', 'success');
                    } else {
                        const error = await response.json();
                        window.dialogManager.showAlert('重命名失败: ' + (error.detail || '未知错误'), 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('重命名失败: ' + error.message, 'error');
                }
            }
        );
    }

    previewTemplate(template) {
        fetch(`/api/templates/content/${encodeURIComponent(template.path)}`)
            .then(res => res.text())
            .then(html => {
                if (window.previewPanelManager) {
                    window.previewPanelManager.show(html);
                }
            })
            .catch(err => {
                window.dialogManager.showAlert('预览失败: ' + err.message, 'error');
            });
    }

    async editTemplate(template) {
        try {
            // 确保编辑器实例存在  
            if (!window.contentEditorDialog) {
                window.contentEditorDialog = new ContentEditorDialog();
            }
            await window.contentEditorDialog.open(template.path, template.name, 'template');
        } catch (error) {
            window.dialogManager?.showAlert('打开编辑器失败: ' + error.message, 'error');
        }
    }

    async copyTemplate(template) {
        window.dialogManager.showInput(
            '复制模板',
            '请输入新模板名称:',
            template.name + '_copy',
            async (newName) => {
                if (!newName) return;

                try {
                    const response = await fetch('/api/templates/copy', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            source_path: template.path,
                            new_name: newName,
                            target_category: template.category
                        })
                    });

                    if (response.ok) {
                        await this.loadCategories();  // 添加这一行  
                        await this.loadTemplates(this.currentCategory);
                        this.renderCategoryTree();  // 添加这一行  
                        this.renderTemplateGrid();
                        window.app?.showNotification('模板已复制', 'success');
                    } else {
                        const error = await response.json();
                        window.dialogManager.showAlert('复制失败: ' + (error.detail || '未知错误'), 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('复制失败: ' + error.message, 'error');
                }
            }
        );
    }

    async deleteTemplate(template) {
        window.dialogManager.showConfirm(
            `确认删除模板"${template.name}"?`,
            async () => {
                try {
                    const response = await fetch(`/api/templates/${encodeURIComponent(template.path)}`, {
                        method: 'DELETE'
                    });

                    if (response.ok) {
                        await this.loadCategories();
                        await this.loadTemplates(this.currentCategory);
                        this.renderCategoryTree();
                        this.renderTemplateGrid();
                        window.app?.showNotification('模板已删除', 'success');
                    } else {
                        const error = await response.json();
                        window.dialogManager.showAlert('删除失败: ' + (error.detail || '未知错误'), 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('删除失败: ' + error.message, 'error');
                }
            }
        );
    }

    switchLayout(layout) {
        this.currentLayout = layout;
        document.querySelectorAll('.view-toggle .view-btn').forEach(btn => {
            if (btn.dataset.layout === layout) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // 重新渲染  
        this.renderTemplateGrid();
    }

    async selectCategory(category) {
        this.currentCategory = category || null;
        await this.loadTemplates(this.currentCategory);
        this.renderCategoryTree();
        this.renderTemplateGrid();

        // 更新新建模板按钮状态  
        this.updateAddTemplateButtonState();
    }

    updateAddTemplateButtonState() {
        const addTemplateBtn = document.getElementById('add-template');
        if (!addTemplateBtn) return;

        // 当选中"全部模板"(currentCategory为null)时禁用按钮  
        if (this.currentCategory === null) {
            addTemplateBtn.disabled = true;
            addTemplateBtn.style.opacity = '0.5';
            addTemplateBtn.style.cursor = 'not-allowed';
            addTemplateBtn.title = '请先选择一个分类';
        } else {
            addTemplateBtn.disabled = false;
            addTemplateBtn.style.opacity = '1';
            addTemplateBtn.style.cursor = 'pointer';
            addTemplateBtn.title = '新建模板';
        }
    }

    filterTemplates(searchText) {
        const filtered = this.templates.filter(template =>
            template.name.toLowerCase().includes(searchText.toLowerCase())
        );

        const grid = document.getElementById('template-content-grid');
        if (!grid) return;

        // 临时替换templates进行渲染  
        const originalTemplates = this.templates;
        this.templates = filtered;
        this.renderTemplateGrid();
        this.templates = originalTemplates;
    }

    async showCreateTemplateDialog() {
        // 如果没有选中分类,不应该执行到这里(按钮已禁用)  
        if (!this.currentCategory) {
            window.dialogManager.showAlert('请先选择一个分类', 'error');
            return;
        }

        window.dialogManager.showInput(
            '新建模板',
            '请输入模板名称:',
            '',
            async (name) => {
                if (!name) return;

                try {
                    const response = await fetch('/api/templates/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: name,
                            category: this.currentCategory,  // 使用当前选中的分类  
                            content: ''
                        })
                    });

                    if (response.ok) {
                        await this.loadCategories();
                        await this.loadTemplates(this.currentCategory);
                        this.renderCategoryTree();
                        this.renderTemplateGrid();
                        window.app?.showNotification('模板已创建', 'success');
                    } else {
                        const error = await response.json();
                        window.dialogManager.showAlert('创建失败: ' + error.detail, 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('创建失败: ' + error.message, 'error');
                }
            }
        );
    }

    async showCreateCategoryDialog() {
        window.dialogManager.showInput(
            '新建分类',
            '请输入分类名称:',
            '',
            async (name) => {
                if (!name) {
                    window.dialogManager.showAlert('分类名称不能为空', 'error');
                    return;
                }

                try {
                    const response = await fetch('/api/templates/categories', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: name })
                    });

                    if (response.ok) {
                        await this.loadCategories();
                        this.renderCategoryTree();

                        // 自动切换到新创建的分类  
                        await this.selectCategory(name);

                        window.app?.showNotification('分类已创建', 'success');
                    } else {
                        const error = await response.json();
                        window.dialogManager.showAlert('创建失败: ' + error.detail, 'error');
                    }
                } catch (error) {
                    window.dialogManager.showAlert('创建失败: ' + error.message, 'error');
                }
            }
        );
    }
}

// 初始化  
// window.templateManager = new TemplateManager();