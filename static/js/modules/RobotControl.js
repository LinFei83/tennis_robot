// 机器人控制模块
(function(global) {
    'use strict';

    class RobotControl {
    constructor(socketManager, messageHandler) {
        this.socketManager = socketManager;
        this.messageHandler = messageHandler;
        this.robotRunning = false;
        this.speedMultiplier = 1.0;
    }
    
    // 切换机器人状态
    async toggleRobot() {
        if (this.robotRunning) {
            return await this.stopRobot();
        } else {
            return await this.startRobot();
        }
    }
    
    // 启动机器人
    async startRobot() {
        try {
            const response = await fetch('/api/robot/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                this.robotRunning = true;
                this.messageHandler.showMessage(result.message, 'success');
                return { success: true, running: true };
            } else {
                this.messageHandler.showMessage(result.message, 'error');
                return { success: false, message: result.message };
            }
        } catch (error) {
            const errorMsg = `启动机器人失败: ${error.message}`;
            this.messageHandler.showMessage(errorMsg, 'error');
            return { success: false, message: errorMsg };
        }
    }
    
    // 停止机器人
    async stopRobot() {
        try {
            const response = await fetch('/api/robot/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                this.robotRunning = false;
                this.messageHandler.showMessage(result.message, 'success');
                return { success: true, running: false };
            } else {
                this.messageHandler.showMessage(result.message, 'error');
                return { success: false, message: result.message };
            }
        } catch (error) {
            const errorMsg = `停止机器人失败: ${error.message}`;
            this.messageHandler.showMessage(errorMsg, 'error');
            return { success: false, message: errorMsg };
        }
    }
    
    // 发送机器人控制命令
    sendControlCommand(command) {
        if (this.robotRunning && this.socketManager.getConnectionStatus()) {
            this.socketManager.sendRobotControl(command);
        }
    }
    
    // 更新机器人状态
    updateStatus(running) {
        this.robotRunning = running;
    }
    
    // 更新速度倍数
    updateSpeedMultiplier(multiplier) {
        this.speedMultiplier = multiplier;
    }
    
    // 获取机器人状态
    isRunning() {
        return this.robotRunning;
    }
    
    // 获取速度倍数
    getSpeedMultiplier() {
        return this.speedMultiplier;
    }
}

    // 将RobotControl暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.RobotControl = RobotControl;

})(window);
