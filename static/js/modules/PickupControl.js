// 拾取模式控制模块
(function(global) {
    'use strict';

    class PickupControl {
        constructor(messageHandler) {
            this.messageHandler = messageHandler;
            this.pickupMode = false;
            this.currentState = 'idle';
            this.currentTarget = null;
            this.stats = {};
            
            this.init();
        }
        
        init() {
            this.setupEventListeners();
            // 初始化时获取当前状态
            this.getPickupStatus();
        }
        
        // 设置事件监听器
        setupEventListeners() {
            const pickupButton = document.getElementById('toggle-pickup');
            if (pickupButton) {
                pickupButton.addEventListener('click', () => {
                    this.togglePickupMode();
                });
            }
            
            const emergencyStopButton = document.getElementById('emergency-stop');
            if (emergencyStopButton) {
                emergencyStopButton.addEventListener('click', () => {
                    this.emergencyStop();
                });
            }
            
            const restartButton = document.getElementById('restart-pickup');
            if (restartButton) {
                restartButton.addEventListener('click', () => {
                    this.restartPickup();
                });
            }
        }
        
        // 切换拾取模式
        async togglePickupMode() {
            try {
                const response = await fetch('/api/pickup/toggle', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    this.pickupMode = result.pickup_mode;
                    this.currentState = result.current_state || 'idle';
                    this.messageHandler.showMessage(result.message, 'success');
                    this.updatePickupUI();
                    return { success: true, pickup_mode: result.pickup_mode };
                } else {
                    this.messageHandler.showMessage(result.message, 'error');
                    return { success: false, message: result.message };
                }
            } catch (error) {
                const errorMsg = `拾取模式切换失败: ${error.message}`;
                this.messageHandler.showMessage(errorMsg, 'error');
                return { success: false, message: errorMsg };
            }
        }
        
        // 获取拾取状态
        async getPickupStatus() {
            try {
                const response = await fetch('/api/pickup/status', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                const result = await response.json();
                
                if (result) {
                    this.pickupMode = result.pickup_mode;
                    this.currentState = result.current_state || 'idle';
                    this.stats = result.stats || {};
                    this.updatePickupUI();
                    return result;
                }
            } catch (error) {
                console.error('获取拾取状态失败:', error);
                return null;
            }
        }
        
        // 获取拾取参数
        async getPickupParameters() {
            try {
                const response = await fetch('/api/pickup/parameters', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    return result.parameters;
                }
            } catch (error) {
                console.error('获取拾取参数失败:', error);
                return null;
            }
        }
        
        // 更新拾取参数
        async updatePickupParameters(params) {
            try {
                const response = await fetch('/api/pickup/parameters', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(params)
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    this.messageHandler.showMessage(result.message, 'success');
                    return result;
                } else {
                    this.messageHandler.showMessage(result.message, 'error');
                    return result;
                }
            } catch (error) {
                const errorMsg = `参数更新失败: ${error.message}`;
                this.messageHandler.showMessage(errorMsg, 'error');
                return { success: false, message: errorMsg };
            }
        }
        
        // 重置统计信息
        async resetStatistics() {
            try {
                const response = await fetch('/api/pickup/reset_stats', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    this.messageHandler.showMessage(result.message, 'success');
                    return result;
                } else {
                    this.messageHandler.showMessage(result.message, 'error');
                    return result;
                }
            } catch (error) {
                const errorMsg = `重置统计失败: ${error.message}`;
                this.messageHandler.showMessage(errorMsg, 'error');
                return { success: false, message: errorMsg };
            }
        }
        
        // 紧急停止
        async emergencyStop() {
            try {
                const response = await fetch('/api/pickup/emergency_stop', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    this.pickupMode = false;
                    this.currentState = 'idle';
                    this.messageHandler.showMessage(result.message, 'warning');
                    this.updatePickupUI();
                    return result;
                } else {
                    this.messageHandler.showMessage(result.message, 'error');
                    return result;
                }
            } catch (error) {
                const errorMsg = `紧急停止失败: ${error.message}`;
                this.messageHandler.showMessage(errorMsg, 'error');
                return { success: false, message: errorMsg };
            }
        }
        
        // 重启拾取
        async restartPickup() {
            try {
                const response = await fetch('/api/pickup/restart', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    this.currentState = 'searching';
                    this.messageHandler.showMessage(result.message, 'success');
                    this.updatePickupUI();
                    return result;
                } else {
                    this.messageHandler.showMessage(result.message, 'error');
                    return result;
                }
            } catch (error) {
                const errorMsg = `重启拾取失败: ${error.message}`;
                this.messageHandler.showMessage(errorMsg, 'error');
                return { success: false, message: errorMsg };
            }
        }
        
        // 更新拾取模式UI
        updatePickupUI() {
            const pickupButton = document.getElementById('toggle-pickup');
            const pickupStatusGroup = document.getElementById('pickup-status-group');
            const pickupModeStatus = document.getElementById('pickup-mode-status');
            const currentStateElement = document.getElementById('current-state');
            const ballsPickedElement = document.getElementById('balls-picked');
            
            console.log('更新拾取UI:', { pickupMode: this.pickupMode, currentState: this.currentState, stats: this.stats });
            
            if (pickupButton) {
                if (this.pickupMode) {
                    pickupButton.textContent = '关闭拾取';
                    pickupButton.className = 'btn btn-warning';
                } else {
                    pickupButton.textContent = '开启拾取';
                    pickupButton.className = 'btn btn-secondary';
                }
            }
            
            // 只有开启拾取模式时才显示状态组
            if (pickupStatusGroup) {
                pickupStatusGroup.style.display = this.pickupMode ? 'block' : 'none';
            }
            
            // 显示/隐藏拾取控制按钮
            const pickupControlButtons = document.getElementById('pickup-control-buttons');
            if (pickupControlButtons) {
                pickupControlButtons.style.display = this.pickupMode ? 'block' : 'none';
            }
            
            if (pickupModeStatus) {
                if (this.pickupMode) {
                    pickupModeStatus.textContent = '开启';
                    pickupModeStatus.className = 'status-value online';
                } else {
                    pickupModeStatus.textContent = '关闭';
                    pickupModeStatus.className = 'status-value offline';
                }
            }
            
            // 更新当前状态显示
            if (currentStateElement) {
                const stateMap = {
                    'idle': '空闲',
                    'searching': '搜索',
                    'tracking': '追踪',
                    'approaching': '接近',
                    'backing_up': '后退',
                    'rotating_search': '360°搜索',
                    'completed': '完成'
                };
                
                const stateText = stateMap[this.currentState] || this.currentState;
                currentStateElement.textContent = stateText;
                
                // 根据状态设置不同的样式
                currentStateElement.className = 'status-value';
                if (this.currentState === 'idle' || this.currentState === 'completed') {
                    currentStateElement.classList.add('offline');
                } else if (this.currentState === 'approaching') {
                    currentStateElement.classList.add('warning');
                } else {
                    currentStateElement.classList.add('online');
                }
            }
            
            // 更新已拾取球数
            if (ballsPickedElement && this.stats) {
                ballsPickedElement.textContent = this.stats.balls_picked || 0;
            }
        }
        
        // 处理拾取模式更新事件
        handlePickupModeUpdate(data) {
            console.log('拾取模式更新:', data);
            this.pickupMode = data.enabled;
            this.currentState = data.current_state || 'idle';
            this.updatePickupUI();
            
            if (data.message) {
                this.messageHandler.showMessage(data.message, 'info');
            }
        }
        
        // 处理状态变化事件
        handleStateChange(data) {
            console.log('状态变化:', data);
            this.currentState = data.new_state;
            this.updatePickupUI();
        }
        
        // 处理拾取状态更新事件
        handlePickupStatusUpdate(data) {
            console.log('拾取状态更新:', data);
            this.currentState = data.state;
            this.stats = data.stats || {};
            this.updatePickupUI();
            
            if (data.message) {
                this.messageHandler.showMessage(data.message, 'info');
            }
        }
        
        // 处理球跟踪更新事件
        handleBallTrackingUpdate(data) {
            console.log('球跟踪更新:', data);
            this.currentTarget = data.target_ball;
            this.currentState = data.state || this.currentState;
            this.stats = data.stats || this.stats;
            
            // 更新目标距离显示
            const targetDistance = document.getElementById('target-distance');
            if (targetDistance && data.target_ball) {
                targetDistance.textContent = Math.round(data.target_ball.distance_to_center);
            }
            
            // 更新球面积显示（用于判断接近程度）
            const ballArea = document.getElementById('ball-area');
            if (ballArea && data.target_ball) {
                ballArea.textContent = Math.round(data.target_ball.area);
            }
            
            this.updatePickupUI();
        }
        
        // 处理球对准中心事件
        handleBallCentered(data) {
            this.messageHandler.showMessage(data.message, 'success');
            
            // 更新目标距离显示
            const targetDistance = document.getElementById('target-distance');
            if (targetDistance) {
                targetDistance.textContent = Math.round(data.distance);
            }
        }
        
        // 处理无球检测事件
        handleNoBallDetected(data) {
            console.log('无球检测:', data.message);
            this.currentTarget = null;
            
            // 重置目标距离显示
            const targetDistance = document.getElementById('target-distance');
            if (targetDistance) {
                targetDistance.textContent = '--';
            }
            
            // 重置球面积显示
            const ballArea = document.getElementById('ball-area');
            if (ballArea) {
                ballArea.textContent = '--';
            }
        }
        
        // 获取拾取模式状态
        isPickupMode() {
            return this.pickupMode;
        }
        
        // 获取当前状态
        getCurrentState() {
            return this.currentState;
        }
        
        // 获取当前目标
        getCurrentTarget() {
            return this.currentTarget;
        }
        
        // 获取统计信息
        getStats() {
            return this.stats;
        }
    }

    // 将PickupControl暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.PickupControl = PickupControl;

})(window);
