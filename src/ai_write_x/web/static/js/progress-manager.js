class BottomProgressManager {
    constructor() {
        this.stages = {
            init: { id: 'init', name: '正在初始化', icon: '⚽' },
            spider: { id: 'spider', name: '抓取与解析', icon: '🕷️' },
            planning: { id: 'planning', name: '策划大纲', icon: '📝' },
            writing: { id: 'writing', name: '文章撰写', icon: '✍️' },
            review: { id: 'review', name: '终审查对', icon: '👁️' },
            reflexion: { id: 'reflexion', name: '重写提升', icon: '🔄' },
            visual: { id: 'visual', name: '视觉排版', icon: '🖼️' },
            done: { id: 'done', name: '生成完成', icon: '✅' }
        };

        this.currentStage = null;
        this.isRunning = false;

        // DOM elements
        this.progressEl = document.getElementById('workflow-nodes');
        this.progressTextEl = document.getElementById('progress-text');

        // ComfyUI nodes logic
        this.nodes = Array.from(document.querySelectorAll('.wf-node'));
        this.lines = Array.from(document.querySelectorAll('.wf-line'));
    }

    start(stage) {
        if (this.progressEl) {
            this.progressEl.classList.remove('hidden');
            const inputGroup = document.querySelector('.topic-input-group');
            if (inputGroup) inputGroup.classList.add('showing-progress');
        }

        this.currentStage = stage;
        this.isRunning = true;

        // Reset all nodes
        this.nodes.forEach(n => {
            n.classList.remove('active', 'done');
        });
        this.lines.forEach(l => {
            l.classList.remove('active', 'done');
        });

        this.activateStage(stage);
    }

    async updateProgress(stage, progress) {
        if (!this.stages[stage]) return;
        if (stage !== this.currentStage) {
            this.markStageDone(this.currentStage);
            this.currentStage = stage;
            this.activateStage(stage);
        }
    }

    activateStage(stageId) {
        let foundNode = false;
        let lineIdx = 0;

        for (let i = 0; i < this.nodes.length; i++) {
            const node = this.nodes[i];
            const nid = node.getAttribute('data-stage');

            if (foundNode) {
                // Future nodes
            } else if (nid === stageId) {
                node.classList.add('active');
                node.classList.remove('done');
                if (i > 0 && this.lines[i - 1]) {
                    this.lines[i - 1].classList.add('active');
                }
                foundNode = true;
            } else {
                node.classList.add('done');
                node.classList.remove('active');
                if (i > 0 && this.lines[i - 1]) {
                    this.lines[i - 1].classList.add('done');
                    this.lines[i - 1].classList.remove('active');
                }
            }
        }
    }

    markStageDone(stageId) {
        this.nodes.forEach((node, i) => {
            if (node.getAttribute('data-stage') === stageId) {
                node.classList.remove('active');
                node.classList.add('done');
                if (i < this.lines.length && this.lines[i]) {
                    this.lines[i].classList.remove('active');
                    this.lines[i].classList.add('done');
                }
            }
        });
    }

    setNodeDetail(stageId, detailText) {
        const node = this.nodes.find(n => n.getAttribute('data-stage') === stageId);
        if (node) {
            let detailEl = node.querySelector('.node-detail');
            if (!detailEl) {
                detailEl = document.createElement('div');
                detailEl.className = 'node-detail';
                detailEl.style.fontSize = '10px';
                detailEl.style.color = 'var(--text-tertiary)';
                detailEl.style.marginTop = '4px';
                detailEl.style.lineHeight = '1.2';
                const labelWrapper = node.querySelector('.node-label');
                if (labelWrapper) labelWrapper.appendChild(detailEl);
            }
            detailEl.innerHTML = detailText;
        }
    }

    reset() {
        this.isRunning = false;
        this.currentStage = null;
        if (this.progressEl) {
            setTimeout(() => {
                this.progressEl.classList.add('hidden');
                this.nodes.forEach(n => {
                    n.classList.remove('active', 'done');
                    const detailEl = n.querySelector('.node-detail');
                    if (detailEl) detailEl.remove();
                });
                this.lines.forEach(l => l.classList.remove('active', 'done'));
            }, 500);
        }
    }
}