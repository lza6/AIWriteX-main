/**
 * DatabaseManager - 数据库与资源智理逻辑
 */
class DatabaseManager {
    constructor() {
        this.initialized = false;
        this.stats = null;
        this.profile = null;
        this.init();
    }

    init() {
        if (this.initialized) return;
        this.refreshAll();
        this.initialized = true;
        console.log('DatabaseManager Initialized');
    }

    // 刷新所有数据
    async refreshAll() {
        await this.loadStorageStats();
        await this.loadAestheticProfile();
        await this.loadVotedArticles();
    }

    // 从 API 获取存储统计
    async loadStorageStats() {
        try {
            const response = await fetch('/api/articles/system/storage-stats');
            if (response.ok) {
                const result = await response.json();
                this.stats = result.data;
                this.renderStats(this.stats);
            } else {
                window.app?.showNotification('获取存储统计失败', 'error');
            }
        } catch (error) {
            console.error('Load storage stats failed:', error);
        }
    }

    // 从 API 获取审美DNA Profile
    async loadAestheticProfile() {
        try {
            const response = await fetch('/api/articles/system/aesthetic-profile');
            if (response.ok) {
                const result = await response.json();
                if (result.status === 'success' && result.data) {
                    this.profile = result.data;
                    this.renderProfile(this.profile);
                } else {
                    this.renderNoProfile();
                }
            }
        } catch (error) {
            console.error('Load aesthetic profile failed:', error);
        }
    }

    // 渲染统计信息到界面
    renderStats(data) {
        if (!data) return;

        // 格式化总大小（MB/GB）
        let totalSize = data.total_size_formatted || data.total_size;
        const totalSizeEl = document.getElementById('db-total-size');
        const articlesSizeEl = document.getElementById('db-articles-size');
        const imagesSizeEl = document.getElementById('db-images-size');
        const sqliteSizeEl = document.getElementById('db-sqlite-size');
        const rootPathEl = document.getElementById('db-root-path');

        if (totalSizeEl) totalSizeEl.textContent = totalSize;
        if (articlesSizeEl) articlesSizeEl.textContent = data.articles_size;
        if (imagesSizeEl) imagesSizeEl.textContent = data.images_size;
        if (sqliteSizeEl) sqliteSizeEl.textContent = data.db_size;

        if (rootPathEl) {
            rootPathEl.textContent = data.root_path;
            rootPathEl.title = `详细路径:\n文章: ${data.articles_path}\n图片: ${data.images_path}\n数据库: ${data.db_path}`;
        }
    }

    // 渲染审美DNA Profile信息
    renderProfile(profile) {
        const dnaUpdateEl = document.getElementById('dna-last-update');
        const dnaLayoutEl = document.getElementById('dna-layout');
        const dnaColorEl = document.getElementById('dna-color');
        const dnaKeywordsEl = document.getElementById('dna-keywords');
        const dnaVotesEl = document.getElementById('dna-votes');
        
        // 最后更新时间
        if (dnaUpdateEl) {
            const lastSummary = profile.last_summary_time || profile.last_updated;
            if (lastSummary) {
                const date = new Date(lastSummary);
                dnaUpdateEl.textContent = `最后进化同步: ${date.toLocaleString()}`;
            } else {
                dnaUpdateEl.textContent = '尚未同步您的审美偏好';
            }
        }
        
        // 布局偏好
        if (dnaLayoutEl) {
            dnaLayoutEl.textContent = profile.layout_preferences || '默认';
        }
        
        // 配色风格
        if (dnaColorEl) {
            dnaColorEl.textContent = profile.color_style || '默认';
        }
        
        // 氛围关键词
        if (dnaKeywordsEl) {
            const keywords = profile.vibe_keywords || [];
            dnaKeywordsEl.innerHTML = keywords.length > 0 
                ? keywords.map(k => `<span class="keyword-tag">${k}</span>`).join('')
                : '暂无';
        }
        
        // 投票统计
        if (dnaVotesEl) {
            const votes = profile.total_votes_analyzed || 0;
            dnaVotesEl.textContent = `已分析 ${votes} 次投票`;
        }
    }

    // 渲染无Profile状态
    renderNoProfile() {
        const dnaUpdateEl = document.getElementById('dna-last-update');
        const dnaLayoutEl = document.getElementById('dna-layout');
        const dnaColorEl = document.getElementById('dna-color');
        const dnaKeywordsEl = document.getElementById('dna-keywords');
        const dnaVotesEl = document.getElementById('dna-votes');
        
        if (dnaUpdateEl) dnaUpdateEl.textContent = '尚未同步您的审美偏好';
        if (dnaLayoutEl) dnaLayoutEl.textContent = '等待AI学习';
        if (dnaColorEl) dnaColorEl.textContent = '等待AI学习';
        if (dnaKeywordsEl) dnaKeywordsEl.textContent = '暂无';
        if (dnaVotesEl) dnaVotesEl.textContent = '请先进行审美投票';
    }

    // 执行 AI 智能清理
    async runSmartClean() {
        const logArea = document.getElementById('db-clean-logs');
        const btn = document.getElementById('db-smart-clean-btn');

        if (!window.dialogManager) return;

        window.dialogManager.showConfirm(
            '🤖 AI 建议清理：\n确认启动 AI 智能清理吗？此操作将自动识别并删除 30 天前已成功发布的冗余文章文件，以释放磁盘空间。',
            async () => {
                btn.disabled = true;
                btn.textContent = '⏳ AI 正在治理中...';
                if (logArea) logArea.innerHTML = '<div class="log-entry">[INFO] AI 正在扫描老旧粒子...</div>';

                try {
                    const res = await fetch('/api/articles/system/smart-clean', { method: 'POST' });
                    const result = await res.json();

                    if (res.ok) {
                        this.addLog(`[SUCCESS] ${result.message}`);
                        this.addLog(`[INFO] 系统熵值已降低，空间已释放。`);
                        window.app?.showNotification('AI 智理完成', 'success');
                        await this.refreshAll();
                    } else {
                        this.addLog(`[ERROR] 清理过程中发生异常: ${result.message}`);
                    }
                } catch (err) {
                    this.addLog(`[ERROR] 网络请求失败: ${err.message}`);
                } finally {
                    btn.disabled = false;
                    btn.textContent = '执行 AI 一键智理';
                }
            }
        );
    }

    // 触发审美特征汇总（带实时进度显示）
    async runAestheticEvolution() {
        const btn = event?.target;
        const originalText = btn?.textContent || '🧬 立即触发审美特征总结';
        
        try {
            if (btn) {
                btn.disabled = true;
                btn.textContent = '🧬 AI 正在深度解析中...';
            }
            
            window.app?.showNotification('🧬 AI 正在解析您的审美 DNA...', 'info');
            
            const res = await fetch('/api/articles/system/aesthetic-summarize', { method: 'POST' });
            const result = await res.json();
            
            if (res.ok && result.status === 'success') {
                // 显示汇总结果
                const profile = result.data;
                const summary = `
✅ 审美特征已同步更新！

📊 已分析 ${profile.total_votes_analyzed || 0} 条投票记录
🎨 布局偏好: ${profile.layout_preferences}
🌈 配色风格: ${profile.color_style}
📝 结构规则: ${profile.structural_rules}
🏷️ 氛围关键词: ${(profile.vobe_keywords || []).join(', ')}
`;
                window.app?.showNotification(summary, 'success');
                
                // 刷新显示
                await this.loadAestheticProfile();
            } else {
                throw new Error(result.message || '汇总失败');
            }
        } catch (e) {
            window.app?.showNotification('同步审美 DNA 失败: ' + e.message, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }
    }

    // 辅助：添加日志行
    addLog(message) {
        const logArea = document.getElementById('db-clean-logs');
        if (!logArea) return;

        const time = new Date().toLocaleTimeString();
        const div = document.createElement('div');
        div.className = 'log-entry';
        div.textContent = `[${time}] ${message}`;

        // 如果是占位符则移除
        const placeholder = logArea.querySelector('.log-placeholder');
        if (placeholder) placeholder.remove();

        logArea.appendChild(div);
        logArea.scrollTop = logArea.scrollHeight;
    }

    // 打开根目录
    async openRootDir() {
        if (this.stats?.root_path) {
            window.open('file://' + this.stats.root_path);
        } else {
            window.app?.showNotification('无法获取根目录路径', 'error');
        }
    }

    // 加载已投票文章列表
    async loadVotedArticles() {
        const listEl = document.getElementById('voted-articles-list');
        const countEl = document.getElementById('voted-count');
        
        if (!listEl) return;
        
        try {
            listEl.innerHTML = '<div class="log-placeholder">加载中...</div>';
            
            const res = await fetch('/api/articles/voted-articles');
            const result = await res.json();
            
            if (res.ok && result.status === 'success') {
                const { total, votes } = result.data;
                
                if (countEl) countEl.textContent = total;
                
                if (!votes || votes.length === 0) {
                    listEl.innerHTML = '<div class="log-placeholder">暂无投票记录</div>';
                    return;
                }
                
                // 渲染投票列表
                listEl.innerHTML = votes.map(vote => {
                    const fileName = vote.article_path ? vote.article_path.split(/[\\/]/).pop() : '未知';
                    const date = vote.created_at ? new Date(vote.created_at).toLocaleString() : '未知';
                    const stars = '★'.repeat(vote.rating) + '☆'.repeat(5 - vote.rating);
                    
                    return `
                        <div class="voted-item" style="padding: 12px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex: 1; min-width: 0;">
                                <div style="font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    ${this.escapeHtml(fileName)}
                                </div>
                                <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">
                                    ${stars} · ${date}
                                </div>
                            </div>
                            <button class="btn btn-secondary btn-sm" style="padding: 4px 10px; font-size: 11px; margin-left: 10px; color: #ef4444; border-color: #ef4444;"
                                onclick="window.databaseManager?.deleteVote('${vote.id}', '${this.escapeHtml(fileName)}')">
                                🗑️ 撤销
                            </button>
                        </div>
                    `;
                }).join('');
                
            } else {
                throw new Error(result.message || '加载失败');
            }
        } catch (e) {
            listEl.innerHTML = '<div class="log-placeholder" style="color: #ef4444;">加载失败: ' + e.message + '</div>';
        }
    }

    // 删除/撤销投票
    async deleteVote(voteId, fileName) {
        if (!window.dialogManager) return;
        
        window.dialogManager.showConfirm(
            `确认撤销 "${fileName}" 的投票记录吗？`,
            async () => {
                try {
                    const res = await fetch(`/api/articles/vote/${voteId}`, { method: 'DELETE' });
                    const result = await res.json();
                    
                    if (res.ok && result.status === 'success') {
                        window.app?.showNotification('投票记录已撤销', 'success');
                        await this.loadVotedArticles();
                        await this.loadAestheticProfile();
                    } else {
                        throw new Error(result.message || '删除失败');
                    }
                } catch (e) {
                    window.app?.showNotification('撤销失败: ' + e.message, 'error');
                }
            }
        );
    }

    // HTML转义辅助
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 全局实例化封装
window.databaseManager = new DatabaseManager();