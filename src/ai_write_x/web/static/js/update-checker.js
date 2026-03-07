class UpdateChecker {
    constructor() {
        this.updateInfo = null;
        this.checked = true;  // 直接标记为已检查，不显示更新
        this.init();
    }

    async init() {
        // 本地开发版，不检查更新
    }

    async checkForUpdatesOnce() {
        try {
            const response = await fetch('/api/config/check-updates');
            if (response.ok) {
                const data = await response.json();
                window.app?.showNotification(
                    `当前版本: ${data.current_version}。${data.release_notes || '已是最新版本'}`,
                    'info'
                );
            } else {
                throw new Error('更新服务器连接失败');
            }
        } catch (error) {
            window.app?.showNotification('检查更新失败: ' + error.message, 'error');
        }
    }
}

// 初始化更新检查器
window.updateChecker = new UpdateChecker();
