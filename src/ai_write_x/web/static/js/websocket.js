// WebSocket连接管理  
class WebSocketManager {  
    constructor() {  
        this.ws = null;  
        this.reconnectAttempts = 0;  
        this.maxReconnectAttempts = 5;  
        this.reconnectInterval = 3000;  
        this.callbacks = {  
            onMessage: [],  
            onOpen: [],  
            onClose: [],  
            onError: []  
        };  
    }  
      
    connect() {  
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';  
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;  
          
        try {  
            this.ws = new WebSocket(wsUrl);  
            this.setupEventListeners();  
        } catch (error) {  
            console.error('WebSocket连接失败:', error);  
            this.handleReconnect();  
        }  
    }  
      
    setupEventListeners() {  
        this.ws.onopen = (event) => {  
            this.reconnectAttempts = 0;  
            this.callbacks.onOpen.forEach(callback => callback(event));  
        };  
          
        this.ws.onmessage = (event) => {  
            try {  
                const data = JSON.parse(event.data);  
                this.callbacks.onMessage.forEach(callback => callback(data));  
            } catch (error) {  
            }  
        };  
          
        this.ws.onclose = (event) => {  
            this.callbacks.onClose.forEach(callback => callback(event));  
            this.handleReconnect();  
        };  
          
        this.ws.onerror = (error) => {  
            this.callbacks.onError.forEach(callback => callback(error));  
        };  
    }  
      
    handleReconnect() {  
        if (this.reconnectAttempts < this.maxReconnectAttempts) {  
            this.reconnectAttempts++;  
              
            setTimeout(() => {  
                this.connect();  
            }, this.reconnectInterval);  
        } else {  
        }  
    }  
      
    send(message) {  
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {  
            this.ws.send(message);  
        } else {  
        }  
    }  
      
    on(event, callback) {  
        if (this.callbacks[event]) {  
            this.callbacks[event].push(callback);  
        }  
    }  
      
    off(event, callback) {  
        if (this.callbacks[event]) {  
            const index = this.callbacks[event].indexOf(callback);  
            if (index > -1) {  
                this.callbacks[event].splice(index, 1);  
            }  
        }  
    }  
      
    close() {  
        if (this.ws) {  
            this.ws.close();  
        }  
    }  
}