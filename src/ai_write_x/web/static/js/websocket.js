// WebSocket连接管理带着V3心跳与无限重连外挂
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = Infinity; // V3: 无限重连 
        this.baseReconnectInterval = 2000;
        this.maxInterval = 10000;
        this.heartbeatTimer = null;
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
            if (this.reconnectAttempts > 0) {
                window.app?.showNotification('✓ 系统连接已恢复，实时日志继续输出', 'success');
            }
            this.reconnectAttempts = 0;
            this.callbacks.onOpen.forEach(callback => callback(event));
            this.startHeartbeat();
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // 如果是心跳响应，忽略
                if (data.type === 'pong') return;
                this.callbacks.onMessage.forEach(callback => callback(data));
            } catch (error) {
            }
        };

        this.ws.onclose = (event) => {
            this.stopHeartbeat();
            this.callbacks.onClose.forEach(callback => callback(event));
            this.handleReconnect();
        };

        this.ws.onerror = (error) => {
            this.callbacks.onError.forEach(callback => callback(error));
        };
    }

    // V3: 心跳保活机制
    startHeartbeat() {
        this.stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // 30s 发送一次 ping
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    }

    handleReconnect() {
        if (this.reconnectAttempts === 0) {
            window.app?.showNotification('⚠️ 与后端连接断开，正在自动尝试重连...', 'warning');
        }

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;

            // 指数退避 (Exponential Backoff)
            const delay = Math.min(this.baseReconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1), this.maxInterval);

            setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            window.app?.showNotification('❌ 系统离线：连续重连失败，请刷新页面恢复服务。', 'error');
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