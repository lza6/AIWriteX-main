class TaskQueueManager {
    constructor() {
        this.queue = [];
        this.isProcessing = false;
        this.currentTask = null;
    }

    /**
     * 加入队列
     * @param {Object} task 任务对象 { type: 're-template'|'image-gen', data: any, id: string, title: string }
     */
    enqueue(task) {
        if (!task.id) {
            task.id = 'task_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
        }

        this.queue.push(task);
        window.app?.showNotification(`任务已加入队列: ${task.title}`, 'info');

        // 更新 UI
        if (window.articleManager) {
            window.articleManager.updateQueueUI();
        }

        // 尝试执行
        this.processNext();
        return task.id;
    }

    /**
     * 停止/取消任务
     */
    abort(taskId) {
        // 如果在队列中，直接移除
        const index = this.queue.findIndex(t => t.id === taskId);
        if (index > -1) {
            this.queue.splice(index, 1);
            if (window.articleManager) window.articleManager.updateQueueUI();
            return;
        }

        // 如果正在执行，让负责的模块中止
        if (this.currentTask && this.currentTask.id === taskId) {
            if (this.currentTask.type === 're-template' && window.articleManager) {
                window.articleManager.stopReTemplate();
            } else if (this.currentTask.type === 'image-gen' && window.articleManager) {
                window.articleManager.stopGenerateImage();
            }
            // 模块内部中止后应调用 taskComplete
        }
    }

    /**
     * 执行下一个任务
     */
    async processNext() {
        if (this.isProcessing || this.queue.length === 0) {
            return;
        }

        this.isProcessing = true;
        this.currentTask = this.queue.shift();

        if (window.articleManager) {
            window.articleManager.updateQueueUI();
        }

        try {
            if (this.currentTask.type === 're-template') {
                if (window.articleManager) {
                    // 后台静默执行，传 true 表示后台模式
                    await window.articleManager.openReTemplateModal(true, this.currentTask.data);
                }
            } else if (this.currentTask.type === 'image-gen') {
                if (window.articleManager) {
                    await window.articleManager.generateImages(this.currentTask.data);
                }
            }
        } catch (e) {
            console.error('队列任务执行失败:', e);
            window.app?.showNotification(`任务失败: ${this.currentTask.title}`, 'error');
            this.taskComplete(this.currentTask.id);
        }
    }

    /**
     * 任务完成回调
     */
    taskComplete(taskId) {
        if (this.currentTask && this.currentTask.id === taskId) {
            this.currentTask = null;
            this.isProcessing = false;

            if (window.articleManager) {
                window.articleManager.updateQueueUI();
            }

            // 短暂延迟后执行下一个
            setTimeout(() => this.processNext(), 1000);
        }
    }
}

// 供全局访问
window.TaskQueueManager = TaskQueueManager;
