class ThemeManager {    
    constructor() {    
        this.themes = {    
            LIGHT: { name: "亮色模式", value: "light" },    
            DARK: { name: "暗色模式", value: "dark" }    
        };    
            
        this.waitForConfigManager();    
    }    
        
    init() {    
        this.currentTheme = this.loadSavedTheme();    
        this.applyTheme(this.currentTheme, false);   
        this.bindThemeSelector();    
        this.bindSystemThemeChange();    
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
        
    loadSavedTheme() {    
        try {    
            // 必须从配置管理器获取，无回退  
            if (this.configManager && this.configManager.getUIConfig) {    
                const uiConfig = this.configManager.getUIConfig();    
                return uiConfig.theme || 'light';    
            }    
            return 'light';    
        } catch (e) {    
            return 'light';    
        }    
    }    
        
    async saveTheme(theme) {    
        try {    
            // 只保存到配置管理器，无备份  
            if (this.configManager && this.configManager.saveUIConfig) {    
                return await this.configManager.saveUIConfig({ theme: theme });    
            }    
            return false;    
        } catch (e) {    
            return false;    
        }    
    }    
        
    async applyTheme(theme, shouldSave = true) {                
        if (shouldSave) {    
            await this.saveTheme(theme);    
        }    
              
        document.documentElement.setAttribute('data-theme', theme);    
        this.currentTheme = theme;    
        this.updateThemeSelector();    
    }  
        
    bindThemeSelector() {  
        try {  
            const selector = document.getElementById('theme-selector');  
            if (!selector) return;  
            
            selector.value = this.currentTheme;  
            
            selector.addEventListener('change', async (e) => {  
                const newTheme = e.target.value;  
                // 只应用主题,不保存  
                await this.applyTheme(newTheme, false);  
            });  
        } catch (error) {  
            console.error('绑定主题选择器失败:', error);  
        }  
    }  
    
    // 添加手动保存方法  
    async saveCurrentTheme() {  
        return await this.saveTheme(this.currentTheme);  
    }  
        
    updateThemeSelector() {    
        const selector = document.getElementById('theme-selector');    
        if (selector) {    
            selector.value = this.currentTheme;    
        }    
    }    
        
    bindSystemThemeChange() {    
        if (window.matchMedia) {    
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');    
            mediaQuery.addEventListener('change', async (e) => {    
                // 只有在用户没有手动设置主题时才跟随系统    
                const uiConfig = this.configManager.getUIConfig();    
                if (!uiConfig.theme) {    
                    await this.applyTheme(e.matches ? 'dark' : 'light');    
                }    
            });    
        }    
    }    
        
    async toggleTheme() {    
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';    
        await this.applyTheme(newTheme);    
    }    
}    
    
document.addEventListener('DOMContentLoaded', () => {    
    window.themeManager = new ThemeManager();    
});