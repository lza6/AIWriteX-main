/**
 * Aesthetic Voting Manager (V13.0)
 * Handles the multi-option popup for aesthetic feedback on articles and templates.
 */
class AestheticVotingManager {
    constructor() {
        this.currentVoteData = null; // { type: 'article'|'template', path: string, title: string }
        this.selectedRating = 5;
    }

    /**
     * Open voting dialog
     * @param {Object} data - { type, path, title }
     */
    async open(data) {
        this.currentVoteData = data;
        this.selectedRating = 5;
        this.renderDialog();
    }

    renderDialog() {
        // Remove existing dialog if any
        const existing = document.getElementById('aesthetic-vote-modal');
        if (existing) existing.remove();

        const dialogHtml = `
            <div class="modal-overlay" id="aesthetic-vote-modal">
                <div class="modal-content aesthetic-vote-content" style="max-width: 500px; border-radius: 20px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.3); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);">
                    <div class="modal-header" style="border-bottom: none; padding: 25px 30px 10px;">
                        <h3 style="display: flex; align-items: center; gap: 10px; font-size: 1.25rem;">
                            <span style="font-size: 24px;">✨</span> 
                            进化 AI 审美 DNA
                        </h3>
                        <button class="modal-close" onclick="window.aestheticVotingManager.close()">×</button>
                    </div>
                    
                    <div class="modal-body" style="padding: 10px 30px 30px;">
                        <p style="color: #64748b; font-size: 14px; margin-bottom: 20px;">
                            目标: <span style="color: #1e293b; font-weight: 600;">${this.currentVoteData.title}</span><br>
                            您的评价将直接影响 AI 未来生成内容的排版、配色与整体质感。
                        </p>

                        <div class="vote-section" style="margin-bottom: 25px;">
                            <label style="display: block; font-weight: 600; margin-bottom: 12px; font-size: 15px;">总体外观评分</label>
                            <div class="star-rating" style="display: flex; gap: 8px; font-size: 28px; cursor: pointer;">
                                ${[1, 2, 3, 4, 5].map(i => `
                                    <span class="star" data-rating="${i}" style="color: ${i <= this.selectedRating ? '#ffb800' : '#e2e8f0'}; transition: transform 0.2s;">★</span>
                                `).join('')}
                            </div>
                        </div>

                        <div class="vote-section" style="margin-bottom: 25px;">
                            <label style="display: block; font-weight: 600; margin-bottom: 12px; font-size: 15px;">哪些地方做得好？(多选)</label>
                            <div class="tag-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                ${['排版布局专业', '配色方案高级', 'UI样式美观', '结构层次分明', '字体选择得当', '图文衔接自然'].map(tag => `
                                    <div class="vote-tag positive" data-tag="${tag}" style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 13px; cursor: pointer; text-align: center; transition: all 0.2s;">
                                        ${tag}
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <div class="vote-section" style="margin-bottom: 25px;">
                            <label style="display: block; font-weight: 600; margin-bottom: 12px; font-size: 15px;">哪里还需要改进？(多选)</label>
                            <div class="tag-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                ${['排版太拥挤', '颜色不够协调', '样式过于陈旧', '内容重点不突出', '间距控制不好', '缺乏视觉冲击力'].map(tag => `
                                    <div class="vote-tag negative" data-tag="${tag}" style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 13px; cursor: pointer; text-align: center; transition: all 0.2s;">
                                        ${tag}
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <div class="vote-section">
                            <label style="display: block; font-weight: 600; margin-bottom: 12px; font-size: 15px;">补充建议 (选填)</label>
                            <textarea id="vote-comment" placeholder="输入您的想法，例如：希望配色更活泼一点..." style="width: 100%; height: 80px; padding: 12px; border: 1px solid #e2e8f0; border-radius: 12px; font-size: 13px; resize: none; background: #f8fafc;"></textarea>
                        </div>
                    </div>

                    <div class="modal-footer" style="padding: 20px 30px 30px; border-top: none;">
                        <button class="btn btn-primary" id="submit-vote-btn" style="width: 100%; height: 48px; border-radius: 14px; font-weight: 600; font-size: 16px; background: linear-gradient(135deg, #6366f1, #a855f7); box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);">
                            确定提交并同步 DNA
                        </button>
                    </div>
                </div>
            </div>

            <style>
                .star:hover { transform: scale(1.2); }
                .vote-tag.active {
                    background: rgba(99, 102, 241, 0.1);
                    border-color: #6366f1 !important;
                    color: #6366f1;
                    font-weight: 600;
                }
                .vote-tag:hover { background: #f1f5f9; }
            </style>
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        this.bindEvents();
    }

    bindEvents() {
        const modal = document.getElementById('aesthetic-vote-modal');
        if (!modal) return;

        // Star rating
        modal.querySelectorAll('.star').forEach(star => {
            star.addEventListener('click', () => {
                this.selectedRating = parseInt(star.dataset.rating);
                modal.querySelectorAll('.star').forEach(s => {
                    s.style.color = parseInt(s.dataset.rating) <= this.selectedRating ? '#ffb800' : '#e2e8f0';
                });
            });
        });

        // Tags toggle
        modal.querySelectorAll('.vote-tag').forEach(tag => {
            tag.addEventListener('click', () => {
                tag.classList.toggle('active');
            });
        });

        // Submit
        document.getElementById('submit-vote-btn').addEventListener('click', () => this.submit());
    }

    async submit() {
        const modal = document.getElementById('aesthetic-vote-modal');
        const positiveTags = Array.from(modal.querySelectorAll('.vote-tag.positive.active')).map(t => t.dataset.tag);
        const negativeTags = Array.from(modal.querySelectorAll('.vote-tag.negative.active')).map(t => t.dataset.tag);
        const comment = document.getElementById('vote-comment').value;

        const submitBtn = document.getElementById('submit-vote-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = '正在同步 AI DNA...';

        try {
            const res = await fetch('/api/articles/vote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    article_path: this.currentVoteData.path,
                    rating: this.selectedRating,
                    positive_tags: positiveTags,
                    negative_tags: negativeTags,
                    comment: comment,
                    vote_type: this.currentVoteData.type // 'article' or 'template'
                })
            });

            const result = await res.json();

            if (result.status === 'success') {
                window.app?.showNotification('提交成功！AI 已吸收您的审美反馈 ✨', 'success');
                this.close();
                // Optionally refresh DNA list if in Database Manager
                if (window.databaseManager) window.databaseManager.refreshAll();
            } else if (result.status === 'already_voted') {
                // 已投票情况
                window.app?.showNotification('您已经为这篇文章投过票了噢～如需重新投票，请先撤销现有投票。', 'warning');
                submitBtn.disabled = false;
                submitBtn.textContent = '确定提交并同步 DNA';
            } else {
                throw new Error(result.message || '未知错误');
            }
        } catch (e) {
            window.app?.showNotification('提交失败: ' + e.message, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = '确定提交并同步 DNA';
        }
    }

    close() {
        const modal = document.getElementById('aesthetic-vote-modal');
        if (modal) modal.remove();
        this.currentVoteData = null;
    }
}

// Global instance
window.aestheticVotingManager = new AestheticVotingManager();
