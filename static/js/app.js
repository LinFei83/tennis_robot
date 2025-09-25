// 网球机器人控制台主控制器
(function(global) {
    'use strict';

class RobotController {
    constructor() {
            // 等待所有模块加载完成
            if (!this.checkModulesLoaded()) {
                setTimeout(() => new RobotController(), 100);
                return;
            }

            // 初始化消息处理器
            this.messageHandler = new global.TennisRobot.MessageHandler();
            
            // 初始化各个模块
            this.initModules();
            
            // 设置模块间的事件处理
            this.setupEventHandlers();
            
            // 初始化UI事件
            this.uiManager.setupUIEvents(this.robotControl, this.visionControl, this.pickupControl);
        }
        
        // 检查所有模块是否已加载
        checkModulesLoaded() {
            const requiredModules = [
                'SocketManager',
                'RobotControl', 
                'VisionControl',
                'PickupControl',
                'UIManager',
                'KeyboardController',
                'MessageHandler'
            ];
            
            if (!global.TennisRobot) {
                return false;
            }
            
            return requiredModules.every(module => global.TennisRobot[module]);
        }
        
        // 初始化各个模块
        initModules() {
            // 初始化Socket管理器
            this.socketManager = new global.TennisRobot.SocketManager();
            
            // 初始化机器人控制模块
            this.robotControl = new global.TennisRobot.RobotControl(this.socketManager, this.messageHandler);
            
            // 初始化视觉控制模块
            this.visionControl = new global.TennisRobot.VisionControl(this.messageHandler);
            
            // 初始化拾取控制模块
            this.pickupControl = new global.TennisRobot.PickupControl(this.messageHandler);
            
            // 初始化UI管理器
            this.uiManager = new global.TennisRobot.UIManager();
            
            // 初始化键盘控制器
            this.keyboardController = new global.TennisRobot.KeyboardController(this.robotControl, this.visionControl);
        }
        
        // 设置模块间的事件处理
        setupEventHandlers() {
            // 设置Socket事件处理器
            this.socketManager.setEventHandler('connect', (data) => {
                this.messageHandler.showMessage(data.message, 'success');
            });
            
            this.socketManager.setEventHandler('disconnect', (data) => {
                this.messageHandler.showMessage(data.message, 'error');
            });
            
            this.socketManager.setEventHandler('status', (data) => {
                this.robotControl.updateStatus(data.robot);
                this.visionControl.updateStatus(data.vision);
                this.uiManager.updateStatus(data);
            });
            
            this.socketManager.setEventHandler('system_stats', (data) => {
                this.uiManager.updateSystemStats(data);
            });
            
            this.socketManager.setEventHandler('velocity_update', (data) => {
                this.uiManager.updateVelocityDisplay(data);
                if (data.speed_multiplier !== undefined) {
                    this.robotControl.updateSpeedMultiplier(data.speed_multiplier);
                    this.uiManager.updateSpeedDisplay(data.speed_multiplier);
                }
            });
            
            this.socketManager.setEventHandler('detection_update', (data) => {
                this.uiManager.updateDetectionStats(data);
            });
            
            this.socketManager.setEventHandler('odom_update', (data) => {
                this.uiManager.updateOdometryDisplay(data);
            });
            
            this.socketManager.setEventHandler('voltage_update', (data) => {
                this.uiManager.updateVoltageDisplay(data);
            });
            
            this.socketManager.setEventHandler('robot_error', (data) => {
                this.messageHandler.showMessage(`机器人错误: ${data.message}`, 'error');
            });
            
            this.socketManager.setEventHandler('info', (data) => {
                this.messageHandler.showMessage(data.message, 'info');
            });
            
            this.socketManager.setEventHandler('error', (data) => {
                this.messageHandler.showMessage(data.message, 'error');
            });
            
            // 拾取模式相关事件
            this.socketManager.setEventHandler('pickup_mode_update', (data) => {
                this.pickupControl.handlePickupModeUpdate(data);
            });
            
            this.socketManager.setEventHandler('ball_tracking_update', (data) => {
                this.pickupControl.handleBallTrackingUpdate(data);
            });
            
            this.socketManager.setEventHandler('ball_centered', (data) => {
                this.pickupControl.handleBallCentered(data);
            });
            
            this.socketManager.setEventHandler('no_ball_detected', (data) => {
                this.pickupControl.handleNoBallDetected(data);
            });
        }
        
        // 获取模块实例（用于调试或扩展）
        getModules() {
            return {
                socketManager: this.socketManager,
                robotControl: this.robotControl,
                visionControl: this.visionControl,
                pickupControl: this.pickupControl,
                uiManager: this.uiManager,
                keyboardController: this.keyboardController,
                messageHandler: this.messageHandler
            };
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
        global.robotController = new RobotController();
});

})(window);