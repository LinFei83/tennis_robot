// 拾取模式控制模块
(function(global) {
    'use strict';

    class PickupControl {
        constructor(messageHandler) {
            this.messageHandler = messageHandler;
            this.pickupMode = false;
            this.trackingActive = false;
            this.currentTarget = null;
            
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
                    this.trackingActive = result.tracking_active;
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
        
        // 更新拾取模式UI
        updatePickupUI() {
            const pickupButton = document.getElementById('toggle-pickup');
            const pickupStatusGroup = document.getElementById('pickup-status-group');
            const pickupModeStatus = document.getElementById('pickup-mode-status');
            const trackingStatus = document.getElementById('tracking-status');
            
            console.log('更新拾取UI:', { pickupMode: this.pickupMode, trackingActive: this.trackingActive });
            
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
            
            if (pickupModeStatus) {
                if (this.pickupMode) {
                    pickupModeStatus.textContent = '开启';
                    pickupModeStatus.className = 'status-value online';
                } else {
                    pickupModeStatus.textContent = '关闭';
                    pickupModeStatus.className = 'status-value offline';
                }
            }
            
            if (trackingStatus) {
                if (this.trackingActive && this.pickupMode) {
                    trackingStatus.textContent = '激活';
                    trackingStatus.className = 'status-value online';
                } else {
                    trackingStatus.textContent = '未激活';
                    trackingStatus.className = 'status-value offline';
                }
            }
        }
        
        // 处理拾取模式更新事件
        handlePickupModeUpdate(data) {
            console.log('拾取模式更新:', data);
            this.pickupMode = data.enabled;
            this.trackingActive = data.tracking_active;
            this.updatePickupUI();
            
            if (data.message) {
                this.messageHandler.showMessage(data.message, 'info');
            }
        }
        
        // 处理球跟踪更新事件
        handleBallTrackingUpdate(data) {
            console.log('球跟踪更新:', data);
            this.currentTarget = data.target_ball;
            
            // 更新跟踪状态
            this.trackingActive = true;
            
            // 更新目标距离显示
            const targetDistance = document.getElementById('target-distance');
            if (targetDistance && data.target_ball) {
                targetDistance.textContent = Math.round(data.target_ball.distance_to_center);
            }
            
            // 更新跟踪状态显示
            const trackingStatus = document.getElementById('tracking-status');
            if (trackingStatus) {
                trackingStatus.textContent = '跟踪中';
                trackingStatus.className = 'status-value online';
            }
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
            this.trackingActive = false;
            
            // 重置目标距离显示
            const targetDistance = document.getElementById('target-distance');
            if (targetDistance) {
                targetDistance.textContent = '--';
            }
            
            // 更新跟踪状态显示
            const trackingStatus = document.getElementById('tracking-status');
            if (trackingStatus && this.pickupMode) {
                trackingStatus.textContent = '搜索中';
                trackingStatus.className = 'status-value warning';
            }
        }
        
        // 获取拾取模式状态
        isPickupMode() {
            return this.pickupMode;
        }
        
        // 获取跟踪状态
        isTrackingActive() {
            return this.trackingActive;
        }
        
        // 获取当前目标
        getCurrentTarget() {
            return this.currentTarget;
        }
    }

    // 将PickupControl暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.PickupControl = PickupControl;

})(window);
