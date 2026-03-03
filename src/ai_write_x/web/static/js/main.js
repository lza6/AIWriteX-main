/**    
 * AIWriteX 主应用类    
 * 职责:应用初始化、视图路由、全局通知    
 */
class AIWriteXApp {
    constructor() {
        this.currentView = 'creative-workshop';

        // 【新增】拦截全局 Fetch 请求以注入客户端令牌
        this.setupFetchInterceptor();

        this.init();
    }

    /**
     * 设置 Fetch 拦截器
     * 从 Cookie 或 全局变量中读取令牌并注入 Header
     */
    setupFetchInterceptor() {
        const originalFetch = window.fetch;
        const getCookie = (name) => {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        };

        window.fetch = async (...args) => {
            let [resource, config] = args;

            // 如果是相对路径或本地服务器，则注入 Token
            if (typeof resource === 'string' && (resource.startsWith('/') || resource.includes('127.0.0.1'))) {
                config = config || {};
                config.headers = config.headers || {};

                // 优先从全局变量读取，其次从 Cookie 读取
                const token = window.APP_CLIENT_TOKEN || getCookie('app_client_token');
                if (token) {
                    if (config.headers instanceof Headers) {
                        config.headers.set('X-App-Client-Token', token);
                    } else {
                        config.headers['X-App-Client-Token'] = token;
                    }
                }
            }

            return originalFetch(resource, config);
        };
    }

    init() {
        this.setupNavigation();
        this.showView(this.currentView);
        this.setupResizeListener();
        new UpdateChecker();
    }

    setupResizeListener() {
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                // 窗口缩放时强制触发一次当前视图的显示逻辑，确保布局正确
                this.showView(this.currentView);
                console.log('Layout refreshed on resize');
            }, 250);
        });
    }

    // ========== 导航管理 ==========    
    setupNavigation() {
        // 主导航菜单点击事件    
        document.querySelectorAll('.nav-link:not(.nav-toggle)').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = link.dataset.view;
                this.showView(view);
            });
        });

        // 系统配置主菜单切换    
        const navToggle = document.querySelector('.nav-toggle');
        if (navToggle) {
            navToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const navItem = e.target.closest('.nav-item-expandable');
                if (navItem) {
                    navItem.classList.toggle('expanded');
                }
                this.showView('config-manager');
            });
        }

        // 配置二级菜单点击事件    
        document.querySelectorAll('.nav-sublink').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const configType = link.dataset.config;

                // 更新二级菜单状态    
                document.querySelectorAll('.nav-sublink').forEach(sublink => {
                    sublink.classList.remove('active');
                });
                link.classList.add('active');

                // 委托给配置管理器    
                if (window.configManager) {
                    window.configManager.showConfigPanel(configType);
                }
            });
        });
    }

    showView(viewName) {
        // 先检查目标视图是否存在
        const targetView = document.getElementById(`${viewName}-view`);
        if (!targetView) {
            console.error(`View not found: ${viewName}-view`);
            return;
        }

        // 更新导航状态
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.dataset.view === viewName) {
                link.classList.add('active');
            }
        });

        // 切换视图时关闭预览面板
        if (window.previewPanelManager) {
            window.previewPanelManager.reset();
        }

        // 隐藏所有视图
        document.querySelectorAll('.view-content').forEach(view => {
            view.classList.remove('active');
            view.style.display = '';
        });

        // 显示目标视图 - 添加 active 类，让 CSS 控制具体的 display 类型
        targetView.classList.add('active');

        // 初始化各个管理器
        this.initializeViewManager(viewName);

        // 处理配置管理视图的特殊逻辑
        this.handleConfigViewSwitch(viewName);

        // 控制预览按钮的显示/隐藏
        this.updatePreviewButtonVisibility(viewName);

        this.currentView = viewName;
    }

    initializeViewManager(viewName) {
        switch (viewName) {
            case 'creative-workshop':
                if (!window.creativeWorkshopManager) {
                    window.creativeWorkshopManager = new CreativeWorkshopManager();
                }
                // 确保初始化被调用
                if (window.creativeWorkshopManager && !window.creativeWorkshopManager.initialized) {
                    window.creativeWorkshopManager.init();
                }
                break;
            case 'template-manager':
                if (!window.templateManager) {
                    window.templateManager = new TemplateManager();
                }
                // 确保初始化被调用
                if (window.templateManager && !window.templateManager.initialized) {
                    window.templateManager.init();
                }
                break;
            case 'article-manager':
                if (!window.articleManager) {
                    window.articleManager = new ArticleManager();
                }
                // 确保初始化被调用
                if (window.articleManager && !window.articleManager.initialized) {
                    window.articleManager.init();
                }
                break;
            case 'spider-manager':
                if (!window.spiderManager) {
                    window.spiderManager = new SpiderManager();
                }
                // 确保初始化被调用
                if (window.spiderManager && typeof window.spiderManager.init === 'function' && !window.spiderManager.initialized) {
                    window.spiderManager.init();
                }
                break;
            case 'mcp-manager':
                if (!window.mcpManager) {
                    window.mcpManager = new MCPManager();
                }
                // 确保初始化被调用
                if (window.mcpManager && typeof window.mcpManager.init === 'function' && !window.mcpManager.initialized) {
                    window.mcpManager.init();
                }
                break;
            case 'newshub':
                if (!window.newshubManager) {
                    window.newshubManager = new NewsHubManager();
                }
                // 确保初始化被调用
                if (window.newshubManager && typeof window.newshubManager.init === 'function' && !window.newshubManager.initialized) {
                    window.newshubManager.init();
                }
                break;
        }
    }

    handleConfigViewSwitch(viewName) {
        if (viewName === 'config-manager') {
            // 清除所有子菜单的active状态    
            document.querySelectorAll('.nav-sublink').forEach(sublink => {
                sublink.classList.remove('active');
            });

            // 激活界面设置子菜单    
            const uiConfigSublink = document.querySelector('[data-config="ui"]');
            if (uiConfigSublink) {
                uiConfigSublink.classList.add('active');
            }

            // 显示界面设置面板    
            if (window.configManager) {
                window.configManager.showConfigPanel('ui');
            }
        } else {
            // 如果切换到非配置管理视图,折叠系统设置菜单    
            const expandableNavItem = document.querySelector('.nav-item-expandable');
            if (expandableNavItem) {
                expandableNavItem.classList.remove('expanded');
            }

            // 同时清除所有子菜单的 active 状态    
            document.querySelectorAll('.nav-sublink').forEach(sublink => {
                sublink.classList.remove('active');
            });
        }
    }

    updatePreviewButtonVisibility(viewName) {
        const previewTrigger = document.getElementById('preview-trigger');
        if (previewTrigger) {
            const viewsWithPreview = ['creative-workshop', 'article-manager', 'template-manager'];
            previewTrigger.style.display = viewsWithPreview.includes(viewName) ? 'flex' : 'none';
        }
    }

    // ========== 全局通知系统 ==========    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `    
            <div class="notification-content">    
                <span>${message}</span>    
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>    
            </div>    
        `;

        document.body.appendChild(notification);

        // 3秒后自动移除    
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 3000);
    }

    // ========== 预览面板控制 ==========    
    showPreview(content) {
        if (window.previewPanelManager) {
            window.previewPanelManager.show(content);
        }
    }

    hidePreview() {
        if (window.previewPanelManager) {
            window.previewPanelManager.hide();
        }
    }
}

// 初始化应用    
let app;
document.addEventListener('DOMContentLoaded', () => {
    // 初始化任务队列
    window.taskQueue = new TaskQueueManager();

    app = new AIWriteXApp();
    window.app = app;
});

// ========== 文章对比功能全局逻辑 ==========
window.openArticleComparison = async function (articleInfo) {
    if (!articleInfo || !articleInfo.path) {
        window.app?.showNotification('文章信息不完整', 'error');
        return;
    }

    const modal = document.getElementById('comparison-modal');
    if (!modal) return;

    // 显示模态框
    modal.style.display = 'flex';

    // 检查是否有全局的多篇文章列表(创意工坊批量生成时注入)
    let isBatchComparison = false;
    let targetArticle = articleInfo;

    if (window._comparisonArticles && window._comparisonArticles.length > 0) {
        isBatchComparison = true;

        // 尝试定位当前请求对比的文章在列表中的索引
        const idx = window._comparisonArticles.findIndex(a => a.path === articleInfo.path || a.title === articleInfo.title);
        if (idx !== -1) {
            window._currentComparisonIndex = idx;
            targetArticle = window._comparisonArticles[idx];
        } else {
            // 如果不在列表中（比如单篇直接点击），则只使用这个单篇
            window._comparisonArticles = [articleInfo];
            window._currentComparisonIndex = 0;
            targetArticle = articleInfo;
        }
    } else {
        window._comparisonArticles = [articleInfo];
        window._currentComparisonIndex = 0;
    }

    await window.renderComparisonContent(targetArticle);
};

window.renderComparisonContent = async function (articleInfo) {
    if (!articleInfo) return;

    // 更新分页控件UI
    const pagination = document.getElementById('comparison-pagination');
    const pageInfo = document.getElementById('comp-page-info');
    const prevBtn = document.getElementById('comp-prev-btn');
    const nextBtn = document.getElementById('comp-next-btn');

    const total = window._comparisonArticles.length;
    const current = window._currentComparisonIndex + 1;

    if (pagination && pageInfo) {
        if (total > 1) {
            pagination.style.display = 'flex';
            pageInfo.textContent = `第 ${current} / ${total} 篇`;
            prevBtn.disabled = current <= 1;
            nextBtn.disabled = current >= total;
        } else {
            pagination.style.display = 'none';
        }
    }

    const sourceContainer = document.getElementById('comp-source-content');
    const generatedContainer = document.getElementById('comp-generated-content');

    if (sourceContainer) sourceContainer.innerHTML = '正在加载原稿内容...';
    if (generatedContainer) generatedContainer.innerHTML = '正在加载生成结果...';

    // 1. 获取最终生成的 HTML
    try {
        const genRes = await fetch(`/api/articles/content?path=${encodeURIComponent(articleInfo.path)}`);
        if (genRes.ok) {
            const content = await genRes.text();
            let htmlContent = content;
            const ext = articleInfo.path.toLowerCase().split('.').pop();

            if ((ext === 'md' || ext === 'markdown') && window.markdownRenderer) {
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                htmlContent = window.markdownRenderer.renderWithStyles(content, isDark);
            }
            if (generatedContainer) generatedContainer.innerHTML = htmlContent;
        } else {
            if (generatedContainer) generatedContainer.innerHTML = '<span style="color:red">生成结果加载失败</span>';
        }
    } catch (e) {
        if (generatedContainer) generatedContainer.innerHTML = '<span style="color:red">生成结果加载失败: ' + e.message + '</span>';
    }

    // 2. 获取源文本 .source.txt
    try {
        // articleInfo.name 通常是去除后缀的文件名
        let articleName = articleInfo.name;
        if (!articleName && articleInfo.path) {
            const parts = articleInfo.path.split(/[\/\\]/);
            const filename = parts[parts.length - 1];
            articleName = filename.substring(0, filename.lastIndexOf('.')) || filename;
        }

        const srcRes = await fetch(`/api/articles/${encodeURIComponent(articleName)}/source`);
        if (srcRes.ok) {
            const data = await srcRes.json();
            if (sourceContainer) {
                if (data.status === 'success' && data.content) {
                    sourceContainer.textContent = data.content;
                } else {
                    sourceContainer.innerHTML = '<span style="color:#999">【找不到源文本文件】</span>';
                }
            }
        } else {
            if (sourceContainer) sourceContainer.innerHTML = '<span style="color:red">源文本加载失败</span>';
        }
    } catch (e) {
        if (sourceContainer) sourceContainer.innerHTML = '<span style="color:red">源文本加载异常: ' + e.message + '</span>';
    }
};

window.compareNext = async function (offset) {
    if (!window._comparisonArticles || window._comparisonArticles.length === 0) return;

    let newIndex = window._currentComparisonIndex + offset;
    if (newIndex < 0) newIndex = 0;
    if (newIndex >= window._comparisonArticles.length) newIndex = window._comparisonArticles.length - 1;

    if (newIndex !== window._currentComparisonIndex) {
        window._currentComparisonIndex = newIndex;
        await window.renderComparisonContent(window._comparisonArticles[newIndex]);
    }
};