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
        // 本地开发版，不检查更新
    }
}

// 初始化更新检查器
window.updateChecker = new UpdateChecker();
