/**        
 * 创意工坊管理器        
 * 职责:话题输入、内容生成、配置面板管理、日志流式传输        
 */
const ErrorType = {
    PROCESS: 'process',
    SYSTEM: 'system',
    VALIDATION: 'validation'
};

class CreativeWorkshopManager {

    constructor() {
        this.isGenerating = false;
        this.currentTopic = '';
        this.generationHistory = [];
        this.templateCategories = [];
        this.templates = [];
        this.logWebSocket = null;
        this.statusPollInterval = null;
        this.bottomProgress = new BottomProgressManager();
        this._hotSearchPlatform = '';

        this.messageQueue = [];  // 消息队列
        this.isProcessingQueue = false;  // 是否正在处理队列
        // 实时预览相关
        this.livePreviewContent = '';
        this.isCapturingContent = false;

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
            this.bindEventListeners();
            this.loadHistory();
            this.initKeyboardShortcuts();
            await this.loadTemplateCategories();
            await this.loadArticleList();  // 加载文章列表
            this.initialized = true;
        } catch (error) {
            console.error('CreativeWorkshopManager 初始化失败:', error);
        } finally {
            this.initializing = false;
        }
    }

    destroy() {
        // 断开 WebSocket  
        this.disconnectLogWebSocket();

        // 停止状态轮询  
        this.stopStatusPolling();
    }

    // ========== 模板数据加载 ==========      

    async loadTemplateCategories() {
        try {
            const response = await fetch('/api/templates/categories');
            if (response.ok) {
                const result = await response.json();
                this.templateCategories = result.data || [];
                this.populateTemplateCategoryOptions();
            } else {
                console.error('加载模板分类失败:', response.status);
                this.templateCategories = [];
                this.populateTemplateCategoryOptions();
            }
        } catch (error) {
            console.error('加载模板分类失败:', error);
            this.templateCategories = [];
            this.populateTemplateCategoryOptions();
        }
    }

    populateTemplateCategoryOptions() {
        const select = document.getElementById('workshop-template-category');
        if (!select || !this.templateCategories) return;

        select.innerHTML = '';

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '随机分类';
        select.appendChild(defaultOption);

        this.templateCategories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            select.appendChild(option);
        });
    }

    async loadTemplatesByCategory(category) {
        try {
            if (!category) {
                return [];
            }

            const response = await fetch(`/api/templates?category=${encodeURIComponent(category)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            return result.data || [];
        } catch (error) {
            console.error('加载模板列表失败:', error);
            return [];
        }
    }

    populateTemplateOptions(templates) {
        const select = document.getElementById('workshop-template-name');
        if (!select) return;

        select.innerHTML = '';

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '随机模板';
        select.appendChild(defaultOption);

        templates.forEach(template => {
            const option = document.createElement('option');
            option.value = template;
            option.textContent = template;
            select.appendChild(option);
        });
    }

    // ========== 事件监听器 ==========      

    bindEventListeners() {
        const topicInput = document.getElementById('topic-input');
        if (topicInput) {
            topicInput.addEventListener('input', (e) => {
                this.currentTopic = e.target.value;
            });

            topicInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (!this.isGenerating) {
                        this.startGeneration();
                    }
                }
            });
        }

        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                if (this.isGenerating) {
                    this.stopGeneration();
                } else {
                    this.startGeneration();
                }
            });
        }

        //  借鉴模式按钮事件  
        const referenceModeBtn = document.getElementById('reference-mode-btn');
        if (referenceModeBtn) {
            referenceModeBtn.addEventListener('click', () => {
                this.toggleReferenceMode();
            });
        }

        const logProgressBtn = document.getElementById('log-progress-btn');
        if (logProgressBtn) {
            logProgressBtn.addEventListener('click', () => {
                const logPanel = document.getElementById('generation-progress');
                const refPanel = document.getElementById('reference-mode-panel');
                const referenceModeBtn = document.getElementById('reference-mode-btn');

                if (logPanel) {
                    // 展开日志面板前,先关闭借鉴面板  
                    if (refPanel && !refPanel.classList.contains('collapsed')) {
                        refPanel.classList.add('collapsed');

                        // 只有在非生成状态下才移除 active 类  
                        if (referenceModeBtn && !this.isGenerating) {
                            referenceModeBtn.classList.remove('active');
                        }
                    }

                    logPanel.classList.toggle('collapsed');
                }
            });
        }

        // 实时预览按钮
        const livePreviewBtn = document.getElementById('live-preview-btn');
        if (livePreviewBtn) {
            livePreviewBtn.addEventListener('click', () => {
                this.toggleLivePreview();
            });
        }

        // 预览面板控制按钮
        const scrollBtn = document.getElementById('live-preview-scroll-btn');
        if (scrollBtn) {
            scrollBtn.addEventListener('click', () => {
                const content = document.getElementById('live-preview-content');
                const container = content?.parentElement;
                if (container) container.scrollTop = container.scrollHeight;
            });
        }
        const clearPreviewBtn = document.getElementById('live-preview-clear-btn');
        if (clearPreviewBtn) {
            clearPreviewBtn.addEventListener('click', () => {
                this.livePreviewContent = '';
                const contentEl = document.getElementById('live-preview-content');
                if (contentEl) {
                    contentEl.innerHTML = '<div id="live-preview-placeholder" style="text-align:center;padding:32px;color:var(--text-tertiary)"><div style="font-size:36px;margin-bottom:8px">📄</div><p>已清空</p></div>';
                }
            });
        }

        const exportLogsBtn = document.getElementById('export-logs-btn');
        if (exportLogsBtn) {
            exportLogsBtn.addEventListener('click', () => {
                this.exportLogs();
            });
        }

        const clearLogsBtn = document.getElementById('clear-logs-btn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => {
                const logsOutput = document.getElementById('logs-output');
                if (logsOutput) {
                    logsOutput.innerHTML = '';
                }
            });
        }

        // 一键复制所有日志
        const copyLogsBtn = document.getElementById('copy-logs-btn');
        if (copyLogsBtn) {
            copyLogsBtn.addEventListener('click', async () => {
                const logsOutput = document.getElementById('logs-output');
                if (!logsOutput) return;

                // 获取所有日志文本
                const logEntries = logsOutput.querySelectorAll('.log-entry');
                let allLogs = '';
                logEntries.forEach(entry => {
                    const time = entry.querySelector('.log-time')?.textContent || '';
                    const content = entry.querySelector('.log-content')?.textContent || entry.textContent || '';
                    allLogs += `[${time}] ${content}\n`;
                });

                if (!allLogs) {
                    this.showNotification('没有日志可复制', 'warning');
                    return;
                }

                try {
                    await navigator.clipboard.writeText(allLogs);
                    this.showNotification('日志已复制到剪贴板', 'success');
                } catch (err) {
                    // 降级方案
                    const textarea = document.createElement('textarea');
                    textarea.value = allLogs;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    this.showNotification('日志已复制到剪贴板', 'success');
                }
            });
        }

        // 加载文章按钮事件
        const loadArticleBtn = document.getElementById('load-article-btn');
        if (loadArticleBtn) {
            loadArticleBtn.addEventListener('click', () => {
                this.loadSelectedArticle();
            });
        }

        // 文章下拉框选择后自动加载
        const referenceArticlesSelect = document.getElementById('reference-articles');
        if (referenceArticlesSelect) {
            referenceArticlesSelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.loadSelectedArticle();
                }
            });
        }

        const categorySelect = document.getElementById('workshop-template-category');
        if (categorySelect) {
            categorySelect.addEventListener('change', async (e) => {
                const category = e.target.value;
                if (!category) {
                    this.populateTemplateOptions([]);
                } else {
                    const templates = await this.loadTemplatesByCategory(category);
                    this.populateTemplateOptions(templates);
                }
            });
        }

        // AI 自动美化开关 → 同步工作流节点可见性 + localStorage 持久化
        const autoReTemplateSwitch = document.getElementById('auto-retemplate-switch');
        if (autoReTemplateSwitch) {
            // 从 localStorage 恢复用户的选择
            const savedState = localStorage.getItem('aiwritex_auto_retemplate');
            if (savedState !== null) {
                autoReTemplateSwitch.checked = savedState === 'true';
            }
            // 初始化时同步工作流节点显隐
            const initShow = autoReTemplateSwitch.checked ? '' : 'none';
            const initNode = document.getElementById('wf-node-retemplate');
            const initLine = document.getElementById('wf-line-retemplate');
            if (initNode) initNode.style.display = initShow;
            if (initLine) initLine.style.display = initShow;

            autoReTemplateSwitch.addEventListener('change', (e) => {
                const node = document.getElementById('wf-node-retemplate');
                const line = document.getElementById('wf-line-retemplate');
                const show = e.target.checked ? '' : 'none';
                if (node) node.style.display = show;
                if (line) line.style.display = show;
                // 持久化到 localStorage
                localStorage.setItem('aiwritex_auto_retemplate', e.target.checked);
            });
        }
    }

    // ========== 借鉴模式管理 ==========      

    toggleReferenceMode() {
        const panel = document.getElementById('reference-mode-panel');
        const referenceModeBtn = document.getElementById('reference-mode-btn');
        const logPanel = document.getElementById('generation-progress');  // 新增  

        if (!panel || !referenceModeBtn) return;

        if (this.isGenerating) {
            window.app?.showNotification('生成过程中无法切换借鉴模式', 'warning');
            return;
        }

        if (panel.classList.contains('collapsed')) {
            // 展开借鉴面板前,先关闭日志面板  
            if (logPanel && !logPanel.classList.contains('collapsed')) {
                logPanel.classList.add('collapsed');
            }

            panel.classList.remove('collapsed');
            referenceModeBtn.classList.add('active');
            this.resetReferenceForm();
            this.setReferenceFormState(false);

            setTimeout(() => {
                panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        } else {
            panel.classList.add('collapsed');
            referenceModeBtn.classList.remove('active');
            this.setReferenceFormState(true);
        }
    }

    async resetReferenceForm() {
        const categorySelect = document.getElementById('workshop-template-category');
        if (categorySelect) {
            categorySelect.value = '';
        }

        this.populateTemplateOptions([]);

        const urlsTextarea = document.getElementById('reference-urls');
        if (urlsTextarea) {
            urlsTextarea.value = '';
        }

        const ratioSelect = document.getElementById('reference-ratio');
        if (ratioSelect) {
            ratioSelect.value = '30';
        }
    }

    setReferenceFormState(disabled) {
        const formElements = [
            'workshop-template-category',
            'workshop-template-name',
            'reference-urls',
            'reference-ratio'
        ];

        formElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.disabled = disabled;
            }
        });
    }

    getReferenceConfig() {
        const panel = document.getElementById('reference-mode-panel');
        const isEnabled = panel && !panel.classList.contains('collapsed');

        if (!isEnabled) {
            return null;
        }

        // 获取选中的文章ID
        const articleSelect = document.getElementById('reference-articles');
        const selectedArticleId = articleSelect?.value || '';

        return {
            template_category: document.getElementById('workshop-template-category')?.value || '',
            template_name: document.getElementById('workshop-template-name')?.value || '',
            reference_urls: document.getElementById('reference-urls')?.value || '',
            reference_ratio: parseInt(document.getElementById('reference-ratio')?.value || '30'),
            reference_article_id: selectedArticleId
        };
    }

    // ========== 内容生成流程 ==========      

    async startGeneration() {
        // ========== 阶段 1: 前置检查 ==========  
        if (this.isGenerating) return;

        this._hotSearchPlatform = '';
        this.messageQueue = [];
        this.isProcessingQueue = false;

        try {
            const statusResponse = await fetch('/api/generate/status');
            if (statusResponse.ok) {
                const status = await statusResponse.json();
                if (status.status === 'running') {
                    window.app?.showNotification('已有任务正在运行,请稍后再试', 'warning');
                    return;
                }
            }
        } catch (error) {
            console.error('检查任务状态失败:', error);
        }

        // ========== 阶段 2: 系统配置校验 ==========  
        try {
            const configResponse = await fetch('/api/config/validate');
            if (!configResponse.ok) {
                const error = await configResponse.json();
                this.showConfigErrorDialog(error.detail || '系统配置错误,请检查配置');
                return;
            }
        } catch (error) {
            console.error('配置验证失败:', error);
            this.showConfigErrorDialog('无法验证配置,请检查系统设置');
            return;
        }

        // ========== 阶段 3: 获取话题 ==========  
        let topic = this.currentTopic.trim();
        let referenceConfig = this.getReferenceConfig();

        // 借鉴模式参数校验  
        if (referenceConfig) {
            // 检查是否有参考内容（文章ID或URL）
            const hasReferenceContent = referenceConfig.reference_article_id || referenceConfig.reference_urls;

            // 如果没有话题也没有参考内容，则提示错误
            if (!topic && !hasReferenceContent) {
                window.app?.showNotification('借鉴模式下请输入话题，或选择已有文章/填写参考链接', 'error');
                return;
            }

            // 有参考内容但没有话题，会自动从参考内容提取话题
            if (!topic && hasReferenceContent) {
                window.app?.showNotification('将根据参考内容自动生成话题...', 'info');
            }

            if (referenceConfig.reference_urls) {
                const urls = referenceConfig.reference_urls.split('|')
                    .map(u => u.trim())
                    .filter(u => u);

                const invalidUrls = urls.filter(url => !this.isValidUrl(url));
                if (invalidUrls.length > 0) {
                    window.app?.showNotification(
                        '存在无效的URL,请检查输入(确保使用http://或https://)',
                        'error'
                    );
                    return;
                }
            }
        }

        // ========== 阶段 4: 所有校验通过,启动生成 ==========  

        // 提前设置生成状态, 让UI立即响应
        this.isGenerating = true;
        this.updateGenerationUI(true);

        // 启动进度条  
        if (this.bottomProgress) {
            this.bottomProgress.start('init');
            const progressEl = document.getElementById('bottom-progress');
            if (progressEl) {
                progressEl.classList.remove('hidden');
            }
        }

        // 初始化日志按钮显示  
        this.updateLogButtonProgress('init', 0);

        // 清空消息队列,准备新任务  
        this.clearMessageQueue();

        // 记录日志 - 根据模式显示不同信息
        let taskMode = referenceConfig ? '借鉴模式' : '热搜模式';
        let logMessage = `🚀 开始生成任务`;

        if (referenceConfig) {
            if (referenceConfig.reference_article_id && this._selectedArticle) {
                const articleTitle = this._selectedArticle.title || '未知文章';
                const articleSource = this._selectedArticle.source || '热点';
                logMessage = `🚀 开始生成任务 (借鉴模式)`;
                this.appendLog(logMessage, 'status', false, Date.now() / 1000);
                this.appendLog(`📰 参考文章: [${articleSource}] ${articleTitle}`, 'info', false, Date.now() / 1000);
            } else if (referenceConfig.reference_urls) {
                logMessage = `🚀 开始生成任务 (借鉴模式 - 参考链接)`;
                this.appendLog(logMessage, 'status', false, Date.now() / 1000);
            } else {
                this.appendLog(`🚀 开始生成任务 (${taskMode})`, 'status', false, Date.now() / 1000);
            }
        } else {
            this.appendLog(`🚀 开始生成任务 (${taskMode})`, 'status', false, Date.now() / 1000);
        }

        // 自动获取热搜  
        if (!topic && !referenceConfig) {
            window.app?.showNotification('正在自动获取热搜...', 'info');
            this.appendLog('🌍 正在自动跨平台抓取、获取热点信息...', 'info', false, Date.now() / 1000);

            try {
                const response = await fetch('/api/hot-topics');
                if (response.ok) {
                    const data = await response.json();
                    topic = data.topic || '';
                    this._hotSearchPlatform = data.platform || '';

                    if (!topic) {
                        window.app?.showNotification('获取热搜失败,请手动输入话题', 'warning');
                        this.cleanupProgress();
                        this.resetLogButton();
                        this.isGenerating = false;
                        this.updateGenerationUI(false);
                        return;
                    }

                    const topicInput = document.getElementById('topic-input');
                    if (topicInput) {
                        topicInput.value = topic;
                        this.currentTopic = topic;
                    }

                    // NEW: 如果获取到了 article_id，直接无缝切换到借鉴模式
                    // 避免后端再次使用 web_search_tool，强制保留已抓取的全量上下文和视觉解析标签
                    if (data.article_id) {
                        referenceConfig = {
                            reference_article_id: data.article_id,
                            reference_ratio: 100, // 高度参考
                            reference_urls: ''
                        };
                        this._selectedArticle = { id: data.article_id, title: topic, source: data.platform };
                    }
                    this.appendLog(`✨ AI主编甄选话题: [${data.platform || '未知平台'}] ${topic}`, 'success', false, Date.now() / 1000);

                } else {
                    throw new Error('获取热搜失败');
                }
            } catch (error) {
                console.error('获取热搜失败:', error);
                window.app?.showNotification('获取热搜失败,请手动输入话题', 'error');
                this.appendLog(`❌ 获取热点信息失败: ${error.message}`, 'error', false, Date.now() / 1000);
                this.cleanupProgress();
                this.resetLogButton();
                this.isGenerating = false;
                this.updateGenerationUI(false);
                return;
            }
        }

        // 添加到历史记录  
        this.addToHistory(topic);

        // ========== 阶段 5: 发起生成请求 ==========  
        try {
            // 获取批量生成配置
            const articleCount = parseInt(document.getElementById('article-count')?.value || '1', 10);
            const postAction = document.getElementById('post-action')?.value || 'none';

            const autoReTemplateSwitch = document.getElementById('auto-retemplate-switch');
            const isBeautifyOn = autoReTemplateSwitch ? autoReTemplateSwitch.checked : false;

            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    topic: topic,
                    platform: this._hotSearchPlatform || '',
                    reference: referenceConfig,
                    article_count: articleCount,
                    post_action: postAction,
                    ai_beautify: isBeautifyOn
                })
            });

            if (!response.ok) {
                const error = await response.json();

                // 请求失败:清理进度条和队列  
                this.cleanupProgress();
                this.resetLogButton();
                this.clearMessageQueue();

                if (response.status === 400 && error.detail &&
                    (error.detail.includes('API KEY') ||
                        error.detail.includes('Model') ||
                        error.detail.includes('配置错误'))) {
                    this.showConfigErrorDialog(error.detail);
                } else {
                    window.app?.showNotification('生成失败: ' + (error.detail || '未知错误'), 'error');
                }

                this.isGenerating = false;
                this.updateGenerationUI(false);
                return;
            }

            const result = await response.json();
            window.app?.showNotification(result.message || '内容生成已开始', 'success');

            // 【新增】注册到全局后台任务管理器
            if (window.articleManager) {
                window.articleManager.addTask('article-generation', {
                    name: `AI 创作: ${topic.substring(0, 15)}${topic.length > 15 ? '...' : ''}`,
                    type: 'generation'
                });
            }

            // 连接 WebSocket 接收实时日志  
            this.connectLogWebSocket();

            // 开始轮询任务状态  
            this.startStatusPolling();

        } catch (error) {
            console.error('生成失败:', error);

            // 异常:清理进度条和队列  
            this.cleanupProgress();
            this.resetLogButton();  // 重置日志按钮  
            this.clearMessageQueue();

            window.app?.showNotification('生成失败: ' + error.message, 'error');
            this.isGenerating = false;
            this.updateGenerationUI(false);
        }
    }

    // 清理进度条的辅助方法    
    cleanupProgress() {
        if (this.bottomProgress) {
            this.bottomProgress.stop();
            const progressEl = document.getElementById('bottom-progress');
            if (progressEl) {
                progressEl.classList.add('hidden');
            }
            this.bottomProgress.reset();
        }
    }

    isValidUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
        } catch {
            return false;
        }
    }

    showConfigErrorDialog(errorMessage) {
        const dialogHtml = `      
            <div class="modal-overlay" id="config-error-dialog">      
                <div class="modal-content" style="max-width: 500px;">      
                    <div class="modal-header">      
                        <h3>配置错误</h3>      
                        <button class="modal-close" onclick="window.creativeWorkshopManager.closeConfigErrorDialog()">×</button>      
                    </div>      
                    <div class="modal-body">      
                        <div class="error-icon" style="text-align: center; margin-bottom: 20px;">      
                            <svg viewBox="0 0 24 24" width="64" height="64" fill="none" stroke="#ef4444" stroke-width="2">      
                                <circle cx="12" cy="12" r="10"/>      
                                <line x1="12" y1="8" x2="12" y2="12"/>      
                                <line x1="12" y1="16" x2="12.01" y2="16"/>      
                            </svg>      
                        </div>      
                        <p style="text-align: center; color: var(--text-secondary); margin-bottom: 20px;">      
                            ${this.escapeHtml(errorMessage)}      
                        </p>      
                    </div>      
                    <div class="modal-footer">      
                        <button class="btn btn-secondary" onclick="window.creativeWorkshopManager.closeConfigErrorDialog()">取消</button>      
                        <button class="btn btn-primary" onclick="window.creativeWorkshopManager.goToConfig('${this.getConfigPanelFromError(errorMessage)}')">前往配置</button>      
                    </div>      
                </div>      
            </div>      
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);
    }

    getConfigPanelFromError(errorMessage) {
        if (errorMessage.includes('微信公众号') || errorMessage.includes('appid') || errorMessage.includes('appsecret')) {
            return 'wechat';
        } else if (errorMessage.includes('API KEY') || errorMessage.includes('Model') || errorMessage.includes('api_key') || errorMessage.includes('model')) {
            return 'api';
        } else if (errorMessage.includes('图片生成')) {
            return 'img-api';
        } else {
            return 'api';
        }
    }

    goToConfig(panelId = 'api') {
        this.closeConfigErrorDialog();

        const configLink = document.querySelector('[data-view="config-manager"]');
        if (configLink) {
            configLink.click();

            setTimeout(() => {
                const targetPanel = document.querySelector(`[data-config="${panelId}"]`);
                if (targetPanel) {
                    targetPanel.click();
                }
            }, 100);
        }
    }

    closeConfigErrorDialog() {
        const dialog = document.getElementById('config-error-dialog');
        if (dialog) dialog.remove();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async stopGeneration() {
        if (!this.isGenerating) return;

        try {
            const response = await fetch('/api/generate/stop', {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();

                // 等待队列处理完毕  
                while (this.isProcessingQueue) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }

                // 清空队列  
                this.clearMessageQueue();

                // 清理进度条  
                this.cleanupProgress();

                // 【新增】重置日志按钮  
                this.resetLogButton();

                this.disconnectLogWebSocket();
                this.stopStatusPolling();

                this._hotSearchPlatform = '';
                const topicInput = document.getElementById('topic-input');
                if (topicInput) {
                    topicInput.value = '';
                    this.currentTopic = '';
                }

                window.app?.showNotification(result.message || '已停止生成', 'info');
            }
        } catch (error) {
            console.error('停止生成失败:', error);
            window.app?.showNotification('停止失败', 'error');
        } finally {
            this.isGenerating = false;
            this.updateGenerationUI(false);

            // 【新增】从全局任务管理器移除
            if (window.articleManager) {
                window.articleManager.removeTask('article-generation');
            }
        }
    }

    resetLogButton() {
        const progressText = document.getElementById('progress-text');
        const btnIcon = document.querySelector('#log-progress-btn .btn-icon');

        if (progressText) {
            progressText.textContent = '日志';
        }

        if (btnIcon) {
            // 恢复默认图标  
            btnIcon.innerHTML = '<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>';
            btnIcon.classList.remove('rotating');
        }
    }
    // ========== WebSocket 日志流式传输 ==========      

    connectLogWebSocket() {
        if (this.logWebSocket) {
            this.logWebSocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/generate/logs`;

        try {
            this.logWebSocket = new WebSocket(wsUrl);

            this.logWebSocket.onopen = () => {
                console.log('日志 WebSocket 已连接');
            };

            this.logWebSocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.message && data.message.includes('[PROGRESS:')) {
                        // 提取所有进度标记  
                        const progressMarkers = data.message.match(/\[PROGRESS:[^\]]+\]/g);
                    }
                    // 将消息加入队列而不是直接处理  
                    this.messageQueue.push(data);

                    // 如果没有在处理队列,启动处理  
                    if (!this.isProcessingQueue) {
                        this.processMessageQueue();
                    }

                    // 转发到全局日志面板      
                    this.appendLog(data.message, data.type, false, data.timestamp);

                    // 实时预览：截取 AI 输出内容（status 类型 = AI 内容块）
                    if (data.message) {
                        this.updateLivePreview(data.message, data.type);
                    }

                    // 检查完成状态      
                    if (data.type === 'completed' || data.type === 'failed') {
                        this.handleGenerationComplete(data);
                    }
                } catch (error) {
                    console.error('解析日志消息失败:', error);
                }
            };

            this.logWebSocket.onerror = (error) => {
                console.error('WebSocket 错误:', error);
            };

            this.logWebSocket.onclose = () => {
                this.logWebSocket = null;
            };
        } catch (error) {
            console.error('创建 WebSocket 连接失败:', error);
        }
    }

    // 处理消息队列  
    async processMessageQueue() {
        if (this.isProcessingQueue) return;
        this.isProcessingQueue = true;

        try {
            while (this.messageQueue.length > 0) {
                const data = this.messageQueue.shift();
                const markers = this.extractProgressMarkers(data.message);

                for (const marker of markers) {
                    const { stage, progress } = this.mapMarkerToProgress(marker);

                    if (stage) {
                        if (marker.status === 'DETAIL') {
                            if (this.bottomProgress && typeof this.bottomProgress.setNodeDetail === 'function') {
                                this.bottomProgress.setNodeDetail(stage, marker.detail);
                            }
                        } else if (progress !== null) {
                            if (this.bottomProgress) {
                                this.bottomProgress.updateProgress(stage, progress);
                                this.updateLogButtonProgress(stage, progress);

                                // 【新增】同步更新全局任务管理器
                                if (window.articleManager) {
                                    window.articleManager.updateTask('article-generation', { progress });
                                }
                            }
                        }
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                }
            }
        } catch (error) {
            console.error("处理消息队列出错:", error);
        } finally {
            this.isProcessingQueue = false;
        }
    }

    updateLogButtonProgress(stage, progress) {
        const progressText = document.getElementById('progress-text');
        const btnIcon = document.querySelector('#log-progress-btn .btn-icon');

        if (!progressText || !btnIcon || !this.bottomProgress) return;

        const stageConfig = this.bottomProgress.stages[stage];
        if (!stageConfig) return;

        const currentProgress = Math.round(this.bottomProgress.currentProgress);
        progressText.textContent = `${stageConfig.name} ${currentProgress}%`;

        // 更新SVG图标并添加旋转动画  
        btnIcon.innerHTML = stageConfig.icon;
        btnIcon.classList.add('rotating');
    }

    // 从消息中提取所有进度标记  
    extractProgressMarkers(message) {
        if (!message) return [];
        const markers = [];
        const progressRegex = /\[PROGRESS:(\w+):(START|END)\]/g;
        let match;

        while ((match = progressRegex.exec(message)) !== null) {
            markers.push({
                stage: match[1],
                status: match[2]
            });
        }

        // 捕获 DETAIL 标记
        const detailRegex = /\[PROGRESS:(\w+):DETAIL\]\s*(.+)/g;
        while ((match = detailRegex.exec(message)) !== null) {
            markers.push({
                stage: match[1],
                status: 'DETAIL',
                detail: match[2].trim()
            });
        }

        // 特殊处理完成标记  
        if (message.includes('任务执行完成')) {
            markers.push({
                stage: 'COMPLETE',
                status: 'END'
            });
        }

        return markers;
    }

    mapMarkerToProgress(marker) {
        const stageMap = {
            'INIT': { stage: 'init', start: 0, end: 15 },
            'SPIDER': { stage: 'spider', start: 15, end: 30 },
            'CREATIVE': { stage: 'planning', start: 30, end: 45 },
            'WRITING': { stage: 'writing', start: 45, end: 70 },
            'REVIEW': { stage: 'review', start: 70, end: 85 },
            'VISUAL': { stage: 'visual', start: 85, end: 95 },
            'SAVE': { stage: 'done', start: 95, end: 99 },
            'COMPLETE': { stage: 'done', start: 100, end: 100 }
        };

        const config = stageMap[marker.stage];
        if (!config) {
            return { stage: null, progress: null };
        }

        const progress = marker.status === 'START' ? config.start : config.end;
        return { stage: config.stage, progress };
    }

    // 清空消息队列  
    clearMessageQueue() {
        this.messageQueue = [];
        this.isProcessingQueue = false;
    }

    disconnectLogWebSocket() {
        if (this.logWebSocket) {
            this.logWebSocket.close();
            this.logWebSocket = null;
        }
    }

    /**      
     * 处理生成完成      
     */
    async handleGenerationComplete(data) {
        // 等待队列处理完毕  
        while (this.isProcessingQueue) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        this.isGenerating = false;

        // 【新增】标记全局任务为完成
        if (window.articleManager) {
            window.articleManager.updateTask('article-generation', {
                progress: 100,
                status: data.type === 'completed' ? 'done' : 'failed'
            });
            setTimeout(() => window.articleManager.removeTask('article-generation'), 3000);
        }

        // 智能恢复借鉴按钮状态  
        const refPanel = document.getElementById('reference-mode-panel');
        const logPanel = document.getElementById('generation-progress');
        const referenceModeBtn = document.getElementById('reference-mode-btn');

        if (refPanel && logPanel && referenceModeBtn) {
            const refPanelCollapsed = refPanel.classList.contains('collapsed');
            const logPanelCollapsed = logPanel.classList.contains('collapsed');

            // 情况1: 借鉴面板折叠 + 日志面板展开 → 用户切换到了日志视图,移除 active  
            // 情况2: 两个面板都折叠 → 用户关闭了所有面板,移除 active  
            // 情况3: 借鉴面板展开 → 保持 active 状态  
            if (refPanelCollapsed) {
                referenceModeBtn.classList.remove('active');
            }
        }

        if (data.type === 'completed') {
            if (this.bottomProgress) {
                this.bottomProgress.complete();
            }

            // 等待进度条动画到达100%后再停止  
            setTimeout(() => {
                if (this.bottomProgress) {
                    this.bottomProgress.stop();
                }

                // 【新增】重置日志按钮  
                this.resetLogButton();

                setTimeout(() => {
                    const progressEl = document.getElementById('bottom-progress');
                    if (progressEl) {
                        progressEl.classList.add('hidden');
                    }
                    if (this.bottomProgress) {
                        this.bottomProgress.reset();
                    }

                    this.autoPreviewGeneratedArticle();
                }, 1000);
            }, 1000);

        } else if (data.type === 'failed') {
            if (this.bottomProgress) {
                this.bottomProgress.showError(data.error || '未知错误');
            }

            // 【新增】重置日志按钮  
            this.resetLogButton();

            setTimeout(() => {
                const progressEl = document.getElementById('bottom-progress');
                if (progressEl) {
                    progressEl.classList.add('hidden');
                }
                if (this.bottomProgress) {
                    this.bottomProgress.reset();
                }
            }, 1000);

        } else if (data.type === 'stopped') {
            const progressEl = document.getElementById('bottom-progress');
            if (progressEl) {
                progressEl.classList.add('hidden');
            }
            if (this.bottomProgress) {
                this.bottomProgress.reset();
            }

            // 【新增】重置日志按钮  
            this.resetLogButton();
        }

        this.updateGenerationUI(false);
        this.stopStatusPolling();

        if (data.type === 'completed') {
            window.app?.showNotification('生成完成', 'success');

            // 自动刷新文章列表 + 侧栏状态计数
            if (window.articleManager) {
                await window.articleManager.loadArticles();
                window.articleManager.renderStatusTree();
            }

            // 成功后删除被借鉴的文章
            if (this._selectedArticle?.id) {
                this.deleteReferenceArticle(this._selectedArticle.id);
            }

            // ===== AI 自动美化 =====
            const autoReTemplateSwitch = document.getElementById('auto-retemplate-switch');
            if (autoReTemplateSwitch?.checked) {
                this.appendLog('🎨 AI 自动美化已开启，正在获取最新文章...', 'info', false, Date.now() / 1000);

                // 等待文章列表刷新完成
                setTimeout(async () => {
                    try {
                        const res = await fetch('/api/articles');
                        if (res.ok) {
                            const result = await res.json();
                            const articles = result.data || [];
                            if (articles.length > 0) {
                                const latestArticle = articles[0];
                                this.appendLog(`🎨 开始自动美化: ${latestArticle.title}`, 'status', false, Date.now() / 1000);

                                if (window.articleManager?.triggerAutoReTemplate) {
                                    window.articleManager.triggerAutoReTemplate(latestArticle);
                                } else {
                                    this.appendLog('⚠️ 文章管理器未就绪，无法执行自动美化', 'warning', false, Date.now() / 1000);
                                }
                            } else {
                                this.appendLog('⚠️ 未找到可美化的文章', 'warning', false, Date.now() / 1000);
                            }
                        }
                    } catch (err) {
                        console.error('自动美化失败:', err);
                        this.appendLog(`❌ 自动美化失败: ${err.message}`, 'error', false, Date.now() / 1000);
                    }
                }, 2000);
            }

        } else if (data.type === 'failed') {
            window.app?.showNotification('生成失败: ' + (data.error || '未知错误'), 'error');
        } else if (data.type === 'stopped') {
            window.app?.showNotification('生成已停止', 'info');
        }

        this._hotSearchPlatform = '';

        const topicInput = document.getElementById('topic-input');
        if (topicInput) {
            topicInput.value = '';
            this.currentTopic = '';
        }

        if (this.logWebSocket) {
            this.logWebSocket.close();
        }
    }

    /**  
     * 自动预览最新生成的文章  
     */
    async autoPreviewGeneratedArticle() {
        try {
            const response = await fetch('/api/articles');
            if (!response.ok) {
                console.error('获取文章列表失败');
                return;
            }

            const result = await response.json();
            if (result.status === 'success' && result.data && result.data.length > 0) {
                const articles = result.data.sort((a, b) => {
                    return new Date(b.create_time) - new Date(a.create_time);
                });

                // 【新增】保存刚刚生成的批量文章信息供对比模式翻页使用
                const articleCount = parseInt(document.getElementById('article-count')?.value || '1', 10);
                window._comparisonArticles = articles.slice(0, articleCount);
                window._currentComparisonIndex = 0;

                const latestArticle = articles[0];

                const contentResponse = await fetch(
                    `/api/articles/content?path=${encodeURIComponent(latestArticle.path)}`
                );
                if (contentResponse.ok) {
                    const content = await contentResponse.text();

                    const ext = latestArticle.path.toLowerCase().split('.').pop();
                    let htmlContent = content;

                    if ((ext === 'md' || ext === 'markdown') && window.markdownRenderer) {
                        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                        htmlContent = window.markdownRenderer.renderWithStyles(content, isDark);
                    }

                    // 【关键修改】使用 showWithActions 并传递文章信息  
                    if (window.previewPanelManager) {
                        window.previewPanelManager.showWithActions(htmlContent, {
                            path: latestArticle.path,
                            title: latestArticle.title
                        });
                    }

                    // 【新增】自动触发质量分析
                    this.showQualityAnalysis(content, latestArticle.title);
                }
            }
        } catch (error) {
            console.error('自动预览失败:', error);
        }
    }

    /**
     * 显示质量分析面板
     */
    showQualityAnalysis(content, title = '') {
        // 延迟显示，让用户先看到预览内容
        setTimeout(() => {
            if (window.qualityManager) {
                window.qualityManager.show(content);

                // 添加日志提示
                this.appendLog('📊 正在分析内容质量...', 'info', false, Date.now() / 1000);
            }
        }, 500);
    }

    appendLog(message, type = 'info', skipGlobal = false, timestamp = null) {
        // 过滤 internal 类型  
        if (type === 'internal') {
            const progressOnlyPattern = /^\[PROGRESS:\w+:(START|END)\]$/;
            if (progressOnlyPattern.test(message.trim())) {
                return;
            }

            if (message.includes('任务执行完成')) {
                return;
            }
        }

        // 【步骤2】过滤合并消息中的纯进度标记行  
        if (message.includes('\n')) {
            const lines = message.split('\n');
            const filteredLines = lines.filter(line => {
                const trimmedLine = line.trim();
                if (!trimmedLine) return false;
                const progressOnlyPattern = /^\[PROGRESS:\w+:(START|END)\]$/;
                const internalPattern = /^\[\d{2}:\d{2}:\d{2}\] \[INTERNAL\]: \[PROGRESS:\w+:(START|END)\]$/;
                return !progressOnlyPattern.test(trimmedLine) && !internalPattern.test(trimmedLine);
            });

            if (filteredLines.length === 0) {
                return;
            }

            // 【关键修改】将过滤后的行重新组合,移除空行  
            message = filteredLines.filter(line => line.trim()).join('\n');
        }

        // 添加到日志详情面板  
        const logsOutput = document.getElementById('logs-output');
        if (logsOutput) {
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;

            // 检测时间戳  
            const hasTimestamp = /^\[\d{2}:\d{2}:\d{2}\]/.test(message);

            let finalMessage = message;
            if (!hasTimestamp && timestamp) {
                const time = new Date(timestamp * 1000);
                const timeStr = time.toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false
                });
                finalMessage = `[${timeStr}] ${message}`;
            }

            // 【关键修改】清理多余空格和多个连续换行符  
            const cleanedMessage = finalMessage
                .replace(/[ \t]+/g, ' ')  // 压缩空格和制表符  
                .replace(/\n{2,}/g, '\n')  // 将多个连续换行符压缩为单个  
                .trimEnd();  // 移除末尾空白  

            entry.innerHTML = `<span class="log-message">${this.escapeHtml(cleanedMessage)}</span>`;

            logsOutput.appendChild(entry);

            const logsContainer = logsOutput.parentElement;
            if (logsContainer) {
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        }
    }

    // ========== 状态轮询 ==========  

    startStatusPolling() {
        this.stopStatusPolling();

        this.statusPollInterval = setInterval(async () => {
            if (!this.isGenerating) {
                this.stopStatusPolling();
                return;
            }

            try {
                const response = await fetch('/api/generate/status');
                if (response.ok) {
                    const result = await response.json();

                    if (result.status === 'completed' || result.status === 'failed' || result.status === 'stopped') {
                        this.stopStatusPolling();

                        this.handleGenerationComplete({
                            type: result.status,
                            error: result.error
                        });

                        // 关闭 WebSocket  
                        this.disconnectLogWebSocket();
                    }
                }
            } catch (error) {
                console.error('轮询状态失败:', error);
            }
        }, 2000);
    }

    stopStatusPolling() {
        if (this.statusPollInterval) {
            clearInterval(this.statusPollInterval);
            this.statusPollInterval = null;
        }
    }

    // ========== 按钮状态管理 ==========  

    updateGenerationUI(isGenerating) {
        const generateBtn = document.getElementById('generate-btn');
        const topicInput = document.getElementById('topic-input');
        const referenceModeBtn = document.getElementById('reference-mode-btn');

        if (generateBtn) {
            const btnText = generateBtn.querySelector('span');
            if (btnText) {
                btnText.textContent = isGenerating ? '停止生成' : '开始生成';
            }

            // 切换按钮样式  
            if (isGenerating) {
                generateBtn.classList.remove('btn-generate');
                generateBtn.classList.add('btn-stop');
            } else {
                generateBtn.classList.remove('btn-stop');
                generateBtn.classList.add('btn-generate');
            }

            // 图标切换逻辑  
            const btnIcon = generateBtn.querySelector('svg.btn-icon') || generateBtn.querySelector('.btn-icon');
            if (btnIcon) {
                if (isGenerating) {
                    // 停止状态:显示等待微动画和停止图标
                    btnIcon.outerHTML = `  
                        <svg class="btn-icon" viewBox="0 0 24 24" style="animation: rotate 2s linear infinite;">  
                            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>  
                    `;
                } else {
                    // 开始状态:显示闪电图标  
                    btnIcon.outerHTML = `  
                        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">  
                            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>  
                        </svg>  
                    `;
                }
            }
        }

        if (topicInput) {
            topicInput.disabled = isGenerating;
            topicInput.style.opacity = isGenerating ? '0.6' : '1';
            topicInput.style.cursor = isGenerating ? 'not-allowed' : 'text';
        }

        // 禁用/启用借鉴按钮  
        if (referenceModeBtn) {
            referenceModeBtn.disabled = isGenerating;
            referenceModeBtn.style.opacity = isGenerating ? '0.5' : '1';
            referenceModeBtn.style.cursor = isGenerating ? 'not-allowed' : 'pointer';

            this.setReferenceFormState(isGenerating);
        }
    }

    // 加载已有文章列表
    async loadArticleList() {
        try {
            const response = await fetch('/api/spider/articles?limit=100');
            if (response.ok) {
                const result = await response.json();
                const articles = result.articles || [];
                this.populateArticleSelect(articles);
            }
        } catch (error) {
            console.error('加载文章列表失败:', error);
        }
    }

    // 填充文章选择下拉框
    populateArticleSelect(articles) {
        const select = document.getElementById('reference-articles');
        if (!select) return;

        select.innerHTML = '<option value="">-- 选择抓取的热点文章 --</option>';

        articles.forEach(article => {
            const option = document.createElement('option');
            option.value = article.id;

            // 显示格式: [来源] 标题 (日期)
            const source = article.source || '热点';
            const title = article.title || `文章 ${article.id}`;
            const date = article.save_date ? article.save_date.slice(5) : ''; // 只取 MM-DD

            option.textContent = `[${source}] ${title} ${date ? '(' + date + ')' : ''}`;
            select.appendChild(option);
        });
    }

    // 加载选中的文章内容
    async loadSelectedArticle() {
        const select = document.getElementById('reference-articles');
        const articleId = select?.value;

        if (!articleId) {
            window.app?.showNotification('请先选择一篇热点文章', 'warning');
            return;
        }

        try {
            // 先尝试获取所有文章，然后找到对应ID的文章
            const response = await fetch('/api/spider/articles?limit=1000');
            if (response.ok) {
                const result = await response.json();
                const articles = result.articles || [];
                const article = articles.find(a => a.id == articleId);

                if (article) {
                    // 保存选中的文章信息
                    this._selectedArticle = article;

                    // 如果有外部链接则填入参考链接
                    const referenceUrls = document.getElementById('reference-urls');
                    if (article.article_url && referenceUrls) {
                        referenceUrls.value = article.article_url;
                    }

                    // 显示文章标题预览（不强制填入话题输入框）
                    const topicInput = document.getElementById('topic-input');
                    if (topicInput) {
                        // 如果话题输入框为空，则预填文章标题
                        if (!topicInput.value.trim()) {
                            topicInput.value = article.title;
                            this.currentTopic = article.title;
                        }
                    }

                    // 显示提示
                    const sourceInfo = article.source ? `(${article.source})` : '';
                    const dateInfo = article.save_date ? ` ${article.save_date}` : '';
                    window.app?.showNotification(`✅ 已加载热点文章${sourceInfo}: ${article.title}`, 'success');
                } else {
                    window.app?.showNotification('未找到该文章，请刷新重试', 'error');
                }
            } else {
                window.app?.showNotification('加载文章失败', 'error');
            }
        } catch (error) {
            console.error('加载文章失败:', error);
            window.app?.showNotification('加载文章失败: ' + error.message, 'error');
        }
    }

    // 删除被借鉴的文章（成功创作后调用）
    async deleteReferenceArticle(articleId) {
        if (!articleId) return;

        try {
            const response = await fetch(`/api/spider/articles/by-id/${articleId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    console.log('已删除被借鉴的文章:', articleId);
                    // 清空选中的文章
                    this._selectedArticle = null;
                    // 刷新文章列表
                    await this.loadArticleList();
                }
            }
        } catch (error) {
            console.error('删除被借鉴文章失败:', error);
        }
    }

    loadHistory() {
        const saved = localStorage.getItem('generation_history');
        if (saved) {
            try {
                this.generationHistory = JSON.parse(saved);
            } catch (e) {
                console.error('加载历史记录失败:', e);
            }
        }
    }

    addToHistory(topic) {
        const entry = {
            topic: topic,
            timestamp: new Date().toISOString()
        };

        this.generationHistory.unshift(entry);

        if (this.generationHistory.length > 50) {
            this.generationHistory = this.generationHistory.slice(0, 50);
        }

        localStorage.setItem('generation_history', JSON.stringify(this.generationHistory));
    }

    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter: 快速生成  
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                if (!this.isGenerating) {
                    this.startGeneration();
                }
            }

            // Ctrl/Cmd + K: 聚焦输入框  
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                document.getElementById('topic-input')?.focus();
            }

            // Esc: 停止生成  
            if (e.key === 'Escape' && this.isGenerating) {
                this.stopGeneration();
            }
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async exportLogs() {
        try {
            // 从后端获取日志文件  
            const response = await fetch('/api/logs/latest');
            if (!response.ok) {
                throw new Error('获取日志失败');
            }

            const blob = await response.blob();
            const filename = `generation_log_${new Date().toISOString().slice(0, 10)}.log`;

            // 使用 File System Access API 让用户选择保存位置  
            if ('showSaveFilePicker' in window) {
                const handle = await window.showSaveFilePicker({
                    suggestedName: filename,
                    types: [{
                        description: '日志文件',
                        accept: { 'text/plain': ['.log'] },
                    }],
                });

                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();

                window.app?.showNotification('日志导出成功', 'success');
            } else {
                // 降级方案:使用传统下载方式  
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                window.app?.showNotification('日志已下载到默认下载目录', 'success');
            }
        } catch (error) {
            window.app?.showNotification('导出日志失败: ' + error.message, 'error');
        }
    }

    // ==================== 实时预览 ====================

    // 切换实时预览面板
    toggleLivePreview() {
        const panel = document.getElementById('live-preview-panel');
        const btn = document.getElementById('live-preview-btn');
        const logPanel = document.getElementById('generation-progress');
        const refPanel = document.getElementById('reference-mode-panel');

        if (panel) {
            // 展开预览前关闭其他面板
            if (panel.classList.contains('collapsed')) {
                if (logPanel && !logPanel.classList.contains('collapsed')) {
                    logPanel.classList.add('collapsed');
                }
                if (refPanel && !refPanel.classList.contains('collapsed')) {
                    refPanel.classList.add('collapsed');
                }
            }
            panel.classList.toggle('collapsed');
            if (btn) btn.classList.toggle('active');
        }
    }

    // 从 WebSocket 消息中截取 AI 输出内容并实时渲染
    updateLivePreview(message, type) {
        // [新增] 处理 chunk 类型 (来自 Master Drafting 的内容块)
        if (type === 'chunk' || type === 'status') {
            if (!this.isCapturingContent) {
                this.isCapturingContent = true;
                this.livePreviewContent = '';
                // 自动打开预览面板
                const panel = document.getElementById('live-preview-panel');
                if (panel && panel.classList.contains('collapsed')) {
                    this.toggleLivePreview();
                }
                const contentEl = document.getElementById('live-preview-content');
                if (contentEl) {
                    contentEl.innerHTML = '';
                    this._liveChars = 0;
                }
            }
            if (message && message.trim()) {
                this._processAndRenderChunk(message);
            }
            return;
        }

        // 检测内容捕获边界
        if (message.includes('[PROGRESS:WRITING:START]')) {
            this.isCapturingContent = true;
            this.livePreviewContent = '';
            // 自动打开预览面板
            const panel = document.getElementById('live-preview-panel');
            if (panel && panel.classList.contains('collapsed')) {
                this.toggleLivePreview();
            }
            // 更新状态
            const statusEl = document.getElementById('live-preview-status');
            if (statusEl) {
                statusEl.textContent = '✍️ AI 写作中...';
                statusEl.style.background = 'rgba(108,92,231,.15)';
                statusEl.style.color = 'var(--primary-color, #6c5ce7)';
            }
            // 清空旧内容，插入 V3 Skeleton 占位动画
            const contentEl = document.getElementById('live-preview-content');
            if (contentEl) {
                contentEl.innerHTML = `
                    <div class="skeleton-wrapper" style="padding: 20px;">
                        <div class="skeleton-title" style="width: 60%; height: 28px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; border-radius: 4px; margin-bottom: 24px; animation: skeleton-loading 1.5s infinite;"></div>
                        <div class="skeleton-line" style="width: 100%; height: 16px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; border-radius: 4px; margin-bottom: 12px; animation: skeleton-loading 1.5s infinite;"></div>
                        <div class="skeleton-line" style="width: 90%; height: 16px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; border-radius: 4px; margin-bottom: 12px; animation: skeleton-loading 1.5s infinite;"></div>
                        <div class="skeleton-line" style="width: 95%; height: 16px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; border-radius: 4px; margin-bottom: 12px; animation: skeleton-loading 1.5s infinite;"></div>
                        <div class="skeleton-line" style="width: 70%; height: 16px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; border-radius: 4px; margin-bottom: 24px; animation: skeleton-loading 1.5s infinite;"></div>
                    </div>
                    <style>
                        @keyframes skeleton-loading {
                            0% { background-position: 200% 0; }
                            100% { background-position: -200% 0; }
                        }
                        [data-theme='dark'] .skeleton-title, [data-theme='dark'] .skeleton-line {
                            background: linear-gradient(90deg, #2a2f3d 25%, #3a4154 50%, #2a2f3d 75%) !important;
                            background-size: 200% 100% !important;
                        }
                    </style>
                `;
                this._liveChars = 0;
            }
            return;
        }

        if (message.includes('[PROGRESS:WRITING:END]') ||
            message.includes('[PROGRESS:REVIEW:START]') ||
            message.includes('[PROGRESS:VISUAL:START]')) {
            // 注意：视觉集成时可能也会发 chunk，所以这里不强制关闭 isCapturingContent
            // 只是更新个状态
            const statusEl = document.getElementById('live-preview-status');
            if (statusEl) {
                if (message.includes('REVIEW')) {
                    statusEl.textContent = '👁️ 终审打磨中...';
                } else if (message.includes('VISUAL')) {
                    statusEl.textContent = '🖼️ 视觉集成中...';
                } else {
                    statusEl.textContent = '⏳ 处理中...';
                }
            }
            return;
        }

        // 生成完成标记
        if (message.includes('任务执行完成') || type === 'completed' || message.includes('[PROGRESS:COMPLETE:START]')) {
            this.isCapturingContent = false;
            const statusEl = document.getElementById('live-preview-status');
            if (statusEl) {
                statusEl.textContent = '✅ 生成完成';
                statusEl.style.background = 'rgba(46,213,115,.15)';
                statusEl.style.color = '#2ed573';
            }
            return;
        }

        if (type === 'failed') {
            this.isCapturingContent = false;
            const statusEl = document.getElementById('live-preview-status');
            if (statusEl) {
                statusEl.textContent = '❌ 生成失败';
                statusEl.style.background = 'rgba(239,68,68,.15)';
                statusEl.style.color = '#ef4444';
            }
            return;
        }

        // 只在写作阶段捕获内容
        if (!this.isCapturingContent) return;

        // 过滤掉非内容消息
        if (message.includes('[PROGRESS:') || message.includes('[INTERNAL]') ||
            type === 'internal' || type === 'system') return;

        // 过滤时间戳前缀的系统消息
        let cleaned = message.trim();
        // 移除 [HH:MM:SS] 前缀
        cleaned = cleaned.replace(/^\[\d{2}:\d{2}:\d{2}\]\s*/, '');
        // 移除 [INFO]:, [DEBUG]: 等日志前缀
        cleaned = cleaned.replace(/^\[.*?\]\s*:?\s*/, '').trim();

        if (!cleaned || cleaned.length < 2) return;

        // 过滤明显不是文章正文的系统提示词或CrewAI特定的中间输出
        const skipPatterns = [
            /^AI生成/, /^开始/, /^调用/, /^正在/, /^INFO:/, /^WARNING:/, /^ERROR:/, /^DEBUG:/,
            /^\> Entering new/, /^Thought:/, /^Action:/, /^Action Input:/, /^Observation:/,
            /^Finished chain/, /^Working on task/, /^Starting task/, /== Working Agent:/,
            /\[.*\]/ // 匹配只包含在括号内的行（通常是日志提示）
        ];

        for (const pattern of skipPatterns) {
            if (pattern.test(cleaned)) return;
        }

        // [新增] 智能全量内容替换检测（如果接收到的是已经排版过的大段HTML，则直接覆盖）
        if (cleaned.includes('<div') || cleaned.includes('<p')) {
            this.livePreviewContent = cleaned;
        } else {
            // 普通文本增量追加
            this.livePreviewContent += cleaned + '\n';
        }

        this._liveChars = this.livePreviewContent.replace(/<[^>]+>/g, '').length;

        // 实时更新状态栏显示字数
        const statusEl = document.getElementById('live-preview-status');
        if (statusEl) {
            statusEl.textContent = `✍️ AI 写作中... (${this._liveChars} 字)`;
        }

        // 渲染到预览面板
        const contentEl = document.getElementById('live-preview-content');
        if (contentEl) {
            // 如果内容已经包含 HTML，直接渲染；否则进行简单 Markdown 渲染
            if (this.livePreviewContent.includes('<')) {
                contentEl.innerHTML = this.livePreviewContent;
            } else {
                const formatted = this.livePreviewContent
                    .replace(/^#{1,3}\s+(.+)$/gm, '<h3 style="color:var(--primary-color);margin:16px 0 8px;font-size:16px;border-bottom:1px solid var(--border-color);padding-bottom:6px">$1</h3>')
                    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.+?)\*/g, '<em>$1</em>')
                    .replace(/^[-*]\s+(.+)$/gm, '<li style="margin:4px 0 4px 20px">$1</li>')
                    .replace(/\n\n+/g, '</p><p style="margin:8px 0">')
                    .replace(/\n/g, '<br>');
                contentEl.innerHTML = `<div style="padding:4px 0"><p style="margin:8px 0">${formatted}</p></div>`;
            }

            // 自动滚动到底部
            const container = contentEl.parentElement;
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }
    }
}