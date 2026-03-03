class WindowModeManager {    
    constructor() {    
        this.modes = {    
            STANDARD: { width: 1400, height: 900, name: "标准模式" },    
            MAXIMIZED: { maximized: true, name: "最大化模式" }    
        };              
        this.waitForConfigManager();    
    }    
        
    init() {    
        this.currentMode = this.loadSavedMode();    
        this.bindModeSelector();    
        this.applyMode(this.currentMode);    
    }    
        
    waitForConfigManager() {  
        if (window.configManager) {  
            this.configManager = window.configManager;  
            // 不立即初始化,等待 onConfigLoaded 回调  
        } else {  
            setTimeout(() => this.waitForConfigManager(), 50);  
        }  
    }  
    
    onConfigLoaded() {  
        // 配置加载完成后才初始化  
        this.init();  
    }    
        
    loadSavedMode() {              
        try {    
            // 必须从配置管理器获取，无回退  
            if (this.configManager && this.configManager.getUIConfig) {    
                const uiConfig = this.configManager.getUIConfig();    
                return uiConfig.windowMode || 'STANDARD';    
            }    
            return 'STANDARD';    
        } catch (e) {    
            console.error('加载窗口模式失败:', e);    
            return 'STANDARD';    
        }    
    }    
        
    async saveMode(mode) {    
        try {    
            // 只保存到配置管理器，无备份  
            if (this.configManager && this.configManager.saveUIConfig) {    
                return await this.configManager.saveUIConfig({ windowMode: mode });    
            }    
            return false;    
        } catch (e) {    
            console.error('保存窗口模式失败:', e);    
            return false;    
        }    
    }    
            
    applyMode(mode) {  
        document.body.className = document.body.className.replace(/window-mode-\w+/g, '');  
        document.body.classList.add(`window-mode-${mode.toLowerCase()}`);  
        document.body.setAttribute('data-window-mode', mode.toLowerCase());  
        this.currentMode = mode;  
    }
                
    bindModeSelector() {  
        try {  
            const selector = document.getElementById('window-mode-selector');  
            if (!selector) return;  
            
            selector.value = this.currentMode;  
            
            selector.addEventListener('change', async (e) => {  
                const newMode = e.target.value;  
                // 只应用模式,不保存  
                this.applyMode(newMode);  
                // 立即显示重启提示  
                this.showRestartNotification();  
            });  
        } catch (error) {  
            console.error('绑定窗口模式选择器失败:', error);  
        }  
    }
        
    // 添加手动保存方法  
    async saveCurrentMode() {  
        const success = await this.saveMode(this.currentMode);  
        if (success) {  
            this.showRestartNotification();  
        }  
        return success;  
    }    
        
    showRestartNotification() {  
        // 直接使用统一的通知系统,警告样式  
        if (window.app && window.app.showNotification) {  
            window.app.showNotification('窗口模式已修改，请保存后重启生效', 'warning');  
        } 
    }  
}    
    
document.addEventListener('DOMContentLoaded', () => {    
    window.windowModeManager = new WindowModeManager();    
});