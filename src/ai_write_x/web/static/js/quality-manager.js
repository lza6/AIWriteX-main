/**
 * 内容质量检测管理器
 * 处理内容分析、优化建议、自动优化等功能
 */

class QualityManager {
    constructor() {
        this.panelVisible = false;
        this.currentContent = '';
        this.optimizedContent = '';
        this.currentAnalysis = null;
        this.isOptimizing = false;
        this.selectedSuggestions = new Set(); // 选中的优化建议
        this.currentSuggestions = []; // 当前所有建议

        this.metricsInfo = {
            originality: { name: '原创性', icon: '⭐', weight: 0.20 },
            readability: { name: '可读性', icon: '📖', weight: 0.15 },
            coherence: { name: '连贯性', icon: '🔗', weight: 0.15 },
            vocabulary: { name: '词汇丰富度', icon: '📚', weight: 0.10 },
            sentence_variety: { name: '句式多样性', icon: '📝', weight: 0.10 },
            ai_likelihood: { name: 'AI检测概率', icon: '🤖', weight: 0.20, inverse: true },
            semantic_depth: { name: '语义深度', icon: '💡', weight: 0.10 }
        };

        this.init();
    }

    init() {
        this.createPanel();
        this.bindEvents();
    }

    createPanel() {
        // 面板已经通过HTML模板加载
        this.panel = document.getElementById('quality-panel');
        if (!this.panel) {
            console.warn('Quality panel not found');
        }
    }

    bindEvents() {
        // 关闭按钮
        const closeBtn = document.getElementById('close-quality-panel');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        // 自动优化按钮
        const optimizeBtn = document.getElementById('btn-auto-optimize');
        if (optimizeBtn) {
            optimizeBtn.addEventListener('click', () => this.startAutoOptimize());
        }

        // 对比按钮
        const compareBtn = document.getElementById('btn-compare');
        if (compareBtn) {
            compareBtn.addEventListener('click', () => this.showComparison());
        }

        // 应用优化结果按钮
        const applyBtn = document.getElementById('btn-apply-optimized');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyOptimized());
        }
    }

    show(content = '') {
        this.currentContent = content;
        this.panelVisible = true;

        if (this.panel) {
            this.panel.style.display = 'flex';
        }

        if (content) {
            this.analyzeContent(content);
        }
    }

    hide() {
        this.panelVisible = false;
        if (this.panel) {
            this.panel.style.display = 'none';
        }
    }

    toggle(content = '') {
        if (this.panelVisible) {
            this.hide();
        } else {
            this.show(content);
        }
    }

    async analyzeContent(content) {
        if (!content) return;

        this.currentContent = content;

        // 显示加载状态
        this.updateScoreDisplay('--', 0);
        document.getElementById('ai-risk-value').textContent = '分析中...';
        document.getElementById('originality-value').textContent = '分析中...';

        try {
            const response = await fetch('/api/quality/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.currentAnalysis = result.data;
                this.updateDisplay(result.data);
            } else {
                throw new Error(result.message || '分析失败');
            }
        } catch (error) {
            console.error('Content analysis failed:', error);
            this.showError('内容分析失败: ' + error.message);
        }
    }

    updateDisplay(data) {
        // 更新综合评分
        this.updateScoreDisplay(data.overall_score, data.overall_score);

        // 更新AI检测概率
        const aiRisk = data.ai_detection_score;
        const aiRiskEl = document.getElementById('ai-risk-value');
        const aiStatusEl = document.getElementById('ai-risk-status');

        aiRiskEl.textContent = aiRisk.toFixed(1) + '%';

        if (aiRisk <= 30) {
            aiStatusEl.textContent = '安全';
            aiStatusEl.className = 'metric-status good';
        } else if (aiRisk <= 50) {
            aiStatusEl.textContent = '警告';
            aiStatusEl.className = 'metric-status warning';
        } else {
            aiStatusEl.textContent = '危险';
            aiStatusEl.className = 'metric-status danger';
        }

        // 更新原创性
        const originality = data.originality_score;
        const origEl = document.getElementById('originality-value');
        const origStatusEl = document.getElementById('originality-status');

        origEl.textContent = originality.toFixed(1);

        if (originality >= 75) {
            origStatusEl.textContent = '优秀';
            origStatusEl.className = 'metric-status good';
        } else if (originality >= 60) {
            origStatusEl.textContent = '一般';
            origStatusEl.className = 'metric-status warning';
        } else {
            origStatusEl.textContent = '较低';
            origStatusEl.className = 'metric-status danger';
        }

        // 更新详细指标
        this.updateMetricsGrid(data.quality_scores);

        // 更新优化建议
        this.updateSuggestions(data.suggestions);
    }

    updateScoreDisplay(score, percentage) {
        const scoreValue = document.getElementById('overall-score-value');
        const progressRing = document.getElementById('score-progress-ring');

        scoreValue.textContent = score.toFixed ? score.toFixed(1) : score;

        // 更新圆环进度
        const circumference = 283; // 2 * PI * 45
        const offset = circumference - (percentage / 100) * circumference;
        progressRing.style.strokeDashoffset = offset;

        // 根据分数改变颜色
        if (percentage >= 80) {
            progressRing.style.stroke = '#22c55e';
        } else if (percentage >= 60) {
            progressRing.style.stroke = '#eab308';
        } else {
            progressRing.style.stroke = '#ef4444';
        }
    }

    updateMetricsGrid(scores) {
        const grid = document.getElementById('metrics-grid');
        if (!grid) return;

        grid.innerHTML = '';

        for (const [key, data] of Object.entries(scores)) {
            const info = this.metricsInfo[key] || { name: key, icon: '📊' };
            // 确保分数有效，默认0
            const score = (data && typeof data.score === 'number') ? data.score : 0;
            const isInverse = info.inverse;

            // 对于AI检测概率，分数越低越好
            const displayScore = isInverse ? (100 - score) : score;
            const barColor = this.getScoreColor(displayScore, isInverse);

            const item = document.createElement('div');
            item.className = 'metric-item';
            item.innerHTML = `
                <div class="metric-item-header">
                    <span class="metric-item-name">${info.icon} ${info.name}</span>
                    <span class="metric-item-value">${score.toFixed(1)}</span>
                </div>
                <div class="metric-item-bar">
                    <div class="metric-item-bar-fill" style="width: ${score}%; background: ${barColor}"></div>
                </div>
            `;

            grid.appendChild(item);
        }
    }

    getScoreColor(score, isInverse = false) {
        if (isInverse) {
            // AI检测概率：越低越好
            if (score <= 30) return '#22c55e';
            if (score <= 50) return '#eab308';
            return '#ef4444';
        } else {
            // 其他指标：越高越好
            if (score >= 75) return '#22c55e';
            if (score >= 50) return '#eab308';
            return '#ef4444';
        }
    }

    updateSuggestions(suggestions) {
        const list = document.getElementById('suggestions-list');
        if (!list) return;

        list.innerHTML = '';
        this.currentSuggestions = suggestions || [];
        this.selectedSuggestions.clear();

        if (!suggestions || suggestions.length === 0) {
            list.innerHTML = '<div class="suggestion-item">✅ 内容质量良好，暂无优化建议</div>';
            return;
        }

        // 添加操作按钮栏
        const actionBar = document.createElement('div');
        actionBar.className = 'suggestion-action-bar';
        actionBar.innerHTML = `
            <button class="suggestion-btn-select-all" id="btn-select-all-suggestions">
                <span>☑️</span> 全选
            </button>
            <button class="suggestion-btn-optimize" id="btn-optimize-selected">
                <span>✨</span> 一键优化选中项
            </button>
        `;
        list.appendChild(actionBar);

        // 绑定按钮事件
        setTimeout(() => {
            const selectAllBtn = document.getElementById('btn-select-all-suggestions');
            const optimizeBtn = document.getElementById('btn-optimize-selected');
            if (selectAllBtn) {
                selectAllBtn.addEventListener('click', () => this.toggleSelectAll());
            }
            if (optimizeBtn) {
                optimizeBtn.addEventListener('click', () => this.optimizeSelected());
            }
        }, 0);

        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item selectable';
            item.dataset.index = index;

            const isPriority = suggestion.includes('【优先】');
            const cleanSuggestion = suggestion.replace('【优先】', '');

            item.innerHTML = `
                <label class="suggestion-checkbox">
                    <input type="checkbox" data-index="${index}">
                    <span class="checkmark"></span>
                </label>
                <span class="suggestion-icon">${isPriority ? '⚠️' : '💡'}</span>
                <span class="suggestion-text">${cleanSuggestion}</span>
            `;

            if (isPriority) {
                item.classList.add('priority');
            }

            // 点击整行切换选中
            item.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    const checkbox = item.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    this.toggleSuggestion(index, checkbox.checked);
                }
            });

            // checkbox 变化事件
            const checkbox = item.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', (e) => {
                this.toggleSuggestion(index, e.target.checked);
            });

            list.appendChild(item);
        });
    }

    toggleSuggestion(index, isSelected) {
        if (isSelected) {
            this.selectedSuggestions.add(index);
        } else {
            this.selectedSuggestions.delete(index);
        }

        // 更新UI
        const item = document.querySelector(`.suggestion-item[data-index="${index}"]`);
        if (item) {
            item.classList.toggle('selected', isSelected);
        }

        this.updateOptimizeButton();
    }

    toggleSelectAll() {
        const allChecked = this.selectedSuggestions.size === this.currentSuggestions.length;
        const checkboxes = document.querySelectorAll('.suggestion-item input[type="checkbox"]');

        if (allChecked) {
            // 取消全选
            this.selectedSuggestions.clear();
            checkboxes.forEach(cb => cb.checked = false);
            document.querySelectorAll('.suggestion-item.selectable').forEach(item => {
                item.classList.remove('selected');
            });
        } else {
            // 全选
            this.currentSuggestions.forEach((_, index) => {
                this.selectedSuggestions.add(index);
            });
            checkboxes.forEach(cb => cb.checked = true);
            document.querySelectorAll('.suggestion-item.selectable').forEach(item => {
                item.classList.add('selected');
            });
        }

        this.updateOptimizeButton();
    }

    updateOptimizeButton() {
        const btn = document.getElementById('btn-optimize-selected');
        if (btn) {
            const count = this.selectedSuggestions.size;
            btn.innerHTML = `<span>✨</span> 一键优化${count > 0 ? ` (${count}项)` : ''}`;
            btn.disabled = count === 0;
            btn.style.opacity = count === 0 ? '0.5' : '1';
        }
    }

    async optimizeSelected() {
        if (this.selectedSuggestions.size === 0 || !this.currentContent) {
            window.EditorApp.notifications.show('请先选择要优化的建议', 'warning');
            return;
        }

        this.isOptimizing = true;

        // 获取选中的建议
        const selectedTexts = Array.from(this.selectedSuggestions).map(idx => {
            let text = this.currentSuggestions[idx];
            return text.replace('【优先】', '').trim();
        });

        console.log('[Quality] 开始优化，选中建议:', selectedTexts);
        window.EditorApp.notifications.show(`正在优化 ${selectedTexts.length} 个建议，请稍候...`, 'info');

        try {
            // 调用AI优化API，添加超时控制
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 2分钟超时

            console.log('[Quality] 发送请求到 /api/quality/optimize-with-suggestions');

            const response = await fetch('/api/quality/optimize-with-suggestions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: this.currentContent,
                    suggestions: selectedTexts,
                    mode: 'agent'
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            console.log('[Quality] 收到响应:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('[Quality] 响应结果:', result);

            if (result.status === 'success' && result.data) {
                this.optimizedContent = result.data.optimized_content;

                // 显示优化结果
                this.showOptimizationResult(
                    this.currentContent,
                    this.optimizedContent,
                    result.data.changes || selectedTexts
                );

                window.EditorApp.notifications.show('优化完成！', 'success');
            } else {
                throw new Error(result.message || '优化失败');
            }
        } catch (error) {
            console.error('[Quality] 优化失败:', error);
            if (error.name === 'AbortError') {
                window.EditorApp.notifications.show('优化超时，请稍后重试', 'error');
            } else {
                window.EditorApp.notifications.show('优化失败: ' + error.message, 'error');
            }
        } finally {
            this.isOptimizing = false;
        }
    }

    showOptimizationResult(original, optimized, changes) {
        // 创建对比弹窗
        const modal = document.createElement('div');
        modal.className = 'optimization-result-modal';
        modal.innerHTML = `
            <div class="optimization-result-overlay">
                <div class="optimization-result-content">
                    <div class="result-header">
                        <h3>✨ AI智能优化结果</h3>
                        <button class="close-btn">&times;</button>
                    </div>
                    <div class="result-body">
                        <div class="changes-list">
                            <h4>优化项：</h4>
                            <ul>
                                ${changes.map(c => `<li>✓ ${c}</li>`).join('')}
                            </ul>
                        </div>
                        <div class="diff-view">
                            <div class="diff-section markdown-body" style="overflow-y: auto; max-height: 400px; padding: 10px; border: 1px solid #ddd; background: var(--bg-secondary);">
                                <h4>原文</h4>
                                <div class="diff-content original">${window.marked && window.marked.parse ? window.marked.parse(original) : original}</div>
                            </div>
                            <div class="diff-arrow" style="align-self: center; font-size: 24px; padding: 0 10px;">➜</div>
                            <div class="diff-section markdown-body" style="overflow-y: auto; max-height: 400px; padding: 10px; border: 1px solid #ddd; background: var(--bg-secondary);">
                                <h4>优化后</h4>
                                <div class="diff-content optimized">${window.marked && window.marked.parse ? window.marked.parse(optimized) : optimized}</div>
                            </div>
                        </div>
                    </div>
                    <div class="result-footer">
                        <button class="btn-cancel">取消</button>
                        <button class="btn-apply">应用优化</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 绑定事件
        modal.querySelector('.close-btn').addEventListener('click', () => modal.remove());
        modal.querySelector('.btn-cancel').addEventListener('click', () => modal.remove());
        modal.querySelector('.btn-apply').addEventListener('click', () => {
            this.applyOptimizedContent(optimized);
            modal.remove();
        });

        // 点击遮罩关闭
        modal.querySelector('.optimization-result-overlay').addEventListener('click', (e) => {
            if (e.target === modal.querySelector('.optimization-result-overlay')) {
                modal.remove();
            }
        });
    }

    applyOptimizedContent(content) {
        // 应用到编辑器
        const editor = window.editor;
        if (editor) {
            editor.setValue(content);
            this.currentContent = content;
            window.EditorApp.notifications.show('已应用优化内容', 'success');

            // 重新分析
            setTimeout(() => this.analyze(), 1000);
        }
    }

    async startAutoOptimize() {
        if (this.isOptimizing || !this.currentContent) return;

        this.isOptimizing = true;

        // 显示优化进度
        const progressEl = document.getElementById('optimization-progress');
        progressEl.style.display = 'block';

        // 禁用按钮
        document.getElementById('btn-auto-optimize').disabled = true;

        try {
            // 获取优化计划
            const planResponse = await fetch('/api/quality/auto-optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: this.currentContent,
                    target_originality: 75.0,
                    max_ai_likelihood: 30.0,
                    max_iterations: 5
                })
            });

            const planResult = await planResponse.json();

            if (planResult.status === 'success') {
                const data = planResult.data;

                if (!data.needs_optimization) {
                    this.updateProgressStatus('✅ 内容已达标，无需优化');
                    this.isOptimizing = false;
                    document.getElementById('btn-auto-optimize').disabled = false;
                    return;
                }

                // 更新初始分数
                this.updateProgressBar('overall', data.current_scores.overall);
                this.updateProgressBar('originality', data.current_scores.originality);
                this.updateProgressBar('ai', data.current_scores.ai_likelihood, true);

                // 生成优化后的内容（通过AI）
                this.updateProgressStatus('🔄 正在生成优化内容...');

                const optimizedContent = await this.generateOptimizedContent(
                    this.currentContent,
                    data.suggestions
                );

                if (optimizedContent) {
                    this.optimizedContent = optimizedContent;

                    // 分析优化后的内容
                    this.updateProgressStatus('🔍 正在分析优化结果...');
                    const analysisResult = await this.analyzeContentAsync(optimizedContent);

                    if (analysisResult) {
                        // 更新进度
                        this.updateProgressBar('overall', analysisResult.overall_score);
                        this.updateProgressBar('originality', analysisResult.originality_score);
                        this.updateProgressBar('ai', analysisResult.ai_detection_score, true);

                        // 显示对比按钮和应用按钮
                        document.getElementById('btn-compare').style.display = 'flex';
                        document.getElementById('btn-apply-optimized').style.display = 'flex';

                        // 更新显示
                        this.currentAnalysis = analysisResult;
                        this.updateDisplay(analysisResult);

                        this.updateProgressStatus('✅ 优化完成！');
                    }
                }
            }
        } catch (error) {
            console.error('Auto optimize failed:', error);
            this.updateProgressStatus('❌ 优化失败: ' + error.message);
        } finally {
            this.isOptimizing = false;
            document.getElementById('btn-auto-optimize').disabled = false;
        }
    }

    async generateOptimizedContent(content, suggestions) {
        // 调用AI生成优化内容
        try {
            const response = await fetch('/api/generate/optimize-content', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: content,
                    suggestions: suggestions,
                    optimize_type: 'quality'
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                return result.data.content;
            } else {
                throw new Error(result.message || '生成优化内容失败');
            }
        } catch (error) {
            console.error('Generate optimized content failed:', error);
            // 如果API不存在，返回模拟的优化内容
            return this.simulateOptimization(content, suggestions);
        }
    }

    simulateOptimization(content, suggestions) {
        // 简单的模拟优化
        let optimized = content;

        // 替换一些AI常用表达
        const replacements = {
            '首先，': '第一，',
            '其次，': '第二，',
            '最后，': '另外，',
            '总而言之': '总之',
            '综上所述': '整体来看',
            '不可否认': '确实',
            '毋庸置疑': '毫无疑问',
            '显而易见': '很明显',
            '众所周知': '大家都知道',
            '在当今社会': '现在',
            '随着科技的发展': '科技发展',
            '值得一提的是': '值得注意的是',
            '让我们来看看': '来看看',
            '接下来我们将讨论': '下面讨论',
        };

        for (const [from, to] of Object.entries(replacements)) {
            optimized = optimized.split(from).join(to);
        }

        return optimized;
    }

    async analyzeContentAsync(content) {
        try {
            const response = await fetch('/api/quality/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            const result = await response.json();
            return result.status === 'success' ? result.data : null;
        } catch (error) {
            console.error('Analyze content failed:', error);
            return null;
        }
    }

    updateProgressBar(type, value, isAi = false) {
        const bar = document.getElementById(`progress-${type}`);
        const valueEl = document.getElementById(`progress-${type}-value`);

        if (bar) {
            bar.style.width = value + '%';
            if (isAi) {
                bar.style.background = value <= 30 ? '#22c55e' : value <= 50 ? '#eab308' : '#ef4444';
            }
        }

        if (valueEl) {
            valueEl.textContent = value.toFixed(1);
        }
    }

    updateProgressStatus(message) {
        const statusEl = document.getElementById('progress-status');
        if (statusEl) {
            if (message.includes('✅') || message.includes('❌')) {
                statusEl.innerHTML = `<span>${message}</span>`;
            } else {
                statusEl.innerHTML = `
                    <div class="status-spinner"></div>
                    <span>${message}</span>
                `;
            }
        }
    }

    async showComparison() {
        if (!this.currentContent || !this.optimizedContent) return;

        try {
            const response = await fetch('/api/quality/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original: this.currentContent,
                    optimized: this.optimizedContent
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.renderComparison(result.data);
                document.getElementById('comparison-view').style.display = 'block';
            }
        } catch (error) {
            console.error('Comparison failed:', error);
        }
    }

    renderComparison(data) {
        const originalScores = document.getElementById('original-scores');
        const optimizedScores = document.getElementById('optimized-scores');
        const summary = document.getElementById('improvement-summary');

        if (!originalScores || !optimizedScores) return;

        // 渲染原始分数
        originalScores.innerHTML = this.renderComparisonScores(
            data.original_analysis,
            false
        );

        // 渲染优化后分数
        optimizedScores.innerHTML = this.renderComparisonScores(
            data.optimized_analysis,
            true,
            data.improvements
        );

        // 渲染改进摘要
        summary.innerHTML = `
            <div class="improvement-item">
                <div class="improvement-value">+${data.overall_improvement}</div>
                <div class="improvement-label">综合提升</div>
            </div>
            <div class="improvement-item">
                <div class="improvement-value">${data.similarity}%</div>
                <div class="improvement-label">内容相似度</div>
            </div>
        `;
    }

    renderComparisonScores(analysis, isOptimized, improvements = {}) {
        const scores = [
            { key: 'overall', label: '综合评分', value: analysis.overall_score },
            { key: 'originality', label: '原创性', value: analysis.originality_score },
            { key: 'ai', label: 'AI概率', value: analysis.ai_detection_score },
        ];

        return scores.map(score => {
            const improvement = improvements[score.key];
            const improvementText = isOptimized && improvement ?
                `<span style="color: ${improvement.improvement > 0 ? '#22c55e' : '#ef4444'}">
                    ${improvement.improvement > 0 ? '+' : ''}${improvement.improvement}
                </span>` : '';

            return `
                <div class="comparison-score-item">
                    <span class="comparison-score-name">${score.label}</span>
                    <span class="comparison-score-value ${isOptimized && improvement?.improvement > 0 ? 'improved' : ''}">
                        ${score.value.toFixed(1)} ${improvementText}
                    </span>
                </div>
            `;
        }).join('');
    }

    applyOptimized() {
        if (!this.optimizedContent) return;

        // 触发事件，让编辑器更新内容
        const event = new CustomEvent('quality:apply-optimized', {
            detail: { content: this.optimizedContent }
        });
        document.dispatchEvent(event);

        // 更新当前内容
        this.currentContent = this.optimizedContent;
        this.analyzeContent(this.currentContent);

        // 显示通知
        if (window.app?.showNotification) {
            window.app.showNotification('已应用优化后的内容', 'success');
        }
    }

    showError(message) {
        const list = document.getElementById('suggestions-list');
        if (list) {
            list.innerHTML = `<div class="suggestion-item" style="color: #ef4444;">❌ ${message}</div>`;
        }
    }
}

// 创建全局实例
let qualityManager = null;

document.addEventListener('DOMContentLoaded', () => {
    qualityManager = new QualityManager();
    window.qualityManager = qualityManager;
});
