// WebSocket通信管理模块
(function(global) {
    'use strict';

    class SocketManager {
    constructor(eventHandlers = {}) {
        this.socket = io();
        this.isConnected = false;
        this.eventHandlers = eventHandlers;
        
        this.init();
    }
    
    init() {
        this.setupSocketEvents();
    }
    
    // WebSocket事件设置
    setupSocketEvents() {
        this.socket.on('connect', () => {
            console.log('已连接到服务器');
            this.isConnected = true;
            this.handleEvent('connect', { message: '已连接到服务器' });
        });
        
        this.socket.on('disconnect', () => {
            console.log('与服务器断开连接');
            this.isConnected = false;
            this.handleEvent('disconnect', { message: '与服务器断开连接' });
        });
        
        // 状态更新事件
        this.socket.on('status', (data) => {
            this.handleEvent('status', data);
        });
        
        this.socket.on('system_stats', (data) => {
            this.handleEvent('system_stats', data);
        });
        
        this.socket.on('velocity_update', (data) => {
            this.handleEvent('velocity_update', data);
        });
        
        this.socket.on('detection_update', (data) => {
            this.handleEvent('detection_update', data);
        });
        
        this.socket.on('odom_update', (data) => {
            this.handleEvent('odom_update', data);
        });
        
        this.socket.on('voltage_update', (data) => {
            this.handleEvent('voltage_update', data);
        });
        
        // 错误和信息事件
        this.socket.on('robot_error', (data) => {
            this.handleEvent('robot_error', data);
        });
        
        this.socket.on('info', (data) => {
            this.handleEvent('info', data);
        });
        
        this.socket.on('error', (data) => {
            this.handleEvent('error', data);
        });
        
        // 拾取模式相关事件
        this.socket.on('pickup_mode_update', (data) => {
            console.log('收到拾取模式更新事件:', data);
            this.handleEvent('pickup_mode_update', data);
        });
        
        this.socket.on('ball_tracking_update', (data) => {
            console.log('收到球跟踪更新事件:', data);
            this.handleEvent('ball_tracking_update', data);
        });
        
        this.socket.on('ball_centered', (data) => {
            console.log('收到球对准中心事件:', data);
            this.handleEvent('ball_centered', data);
        });
        
        this.socket.on('no_ball_detected', (data) => {
            console.log('收到无球检测事件:', data);
            this.handleEvent('no_ball_detected', data);
        });
    }
    
    // 事件处理器
    handleEvent(eventType, data) {
        if (this.eventHandlers[eventType]) {
            this.eventHandlers[eventType](data);
        }
    }
    
    // 发送机器人控制命令
    sendRobotControl(command) {
        if (this.isConnected) {
            this.socket.emit('robot_control', { command: command });
        }
    }
    
    // 设置事件处理器
    setEventHandler(eventType, handler) {
        this.eventHandlers[eventType] = handler;
    }
    
    // 获取连接状态
    getConnectionStatus() {
        return this.isConnected;
    }
}

    // 将SocketManager暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.SocketManager = SocketManager;

})(window);
