// UI更新管理模块
(function(global) {
    'use strict';

    class UIManager {
    constructor() {
        this.init();
    }
    
    init() {
        this.updateTime();
    }
    
    // 更新系统状态
    updateStatus(data) {
        this.updateRobotStatus(data.robot);
        this.updateVisionStatus(data.vision);
    }
    
    // 更新机器人状态显示
    updateRobotStatus(running) {
        const statusElement = document.getElementById('robot-status');
        const buttonElement = document.getElementById('toggle-robot');
        
        if (!statusElement || !buttonElement) return;
        
        if (running) {
            statusElement.textContent = '在线';
            statusElement.className = 'status-value online';
            buttonElement.textContent = '停止机器人';
            buttonElement.className = 'btn btn-danger';
        } else {
            statusElement.textContent = '离线';
            statusElement.className = 'status-value offline';
            buttonElement.textContent = '启动机器人';
            buttonElement.className = 'btn btn-success';
        }
    }
    
    // 更新视觉系统状态显示
    updateVisionStatus(running) {
        const statusElement = document.getElementById('vision-status');
        const buttonElement = document.getElementById('toggle-vision');
        
        if (!statusElement || !buttonElement) return;
        
        if (running) {
            statusElement.textContent = '在线';
            statusElement.className = 'status-value online';
            buttonElement.textContent = '停止视觉';
            buttonElement.className = 'btn btn-warning';
        } else {
            statusElement.textContent = '离线';
            statusElement.className = 'status-value offline';
            buttonElement.textContent = '启动视觉';
            buttonElement.className = 'btn btn-primary';
        }
    }
    
    // 更新系统统计信息
    updateSystemStats(data) {
        this.updateCPUStats(data);
        this.updateMemoryStats(data);
    }
    
    // 更新CPU使用率
    updateCPUStats(data) {
        const cpuProgress = document.getElementById('cpu-progress');
        const cpuPercent = document.getElementById('cpu-percent');
        
        if (!cpuProgress || !cpuPercent) return;
        
        cpuProgress.style.width = `${data.cpu_percent}%`;
        cpuPercent.textContent = `${data.cpu_percent.toFixed(1)}%`;
        
        // 根据使用率设置颜色
        if (data.cpu_percent > 80) {
            cpuProgress.className = 'progress-fill danger';
        } else if (data.cpu_percent > 60) {
            cpuProgress.className = 'progress-fill warning';
        } else {
            cpuProgress.className = 'progress-fill';
        }
    }
    
    // 更新内存使用率
    updateMemoryStats(data) {
        const memoryProgress = document.getElementById('memory-progress');
        const memoryPercent = document.getElementById('memory-percent');
        const memoryUsed = document.getElementById('memory-used');
        const memoryTotal = document.getElementById('memory-total');
        
        if (!memoryProgress || !memoryPercent || !memoryUsed || !memoryTotal) return;
        
        memoryProgress.style.width = `${data.memory_percent}%`;
        memoryPercent.textContent = `${data.memory_percent.toFixed(1)}%`;
        memoryUsed.textContent = data.memory_used.toFixed(1);
        memoryTotal.textContent = data.memory_total.toFixed(1);
        
        // 根据使用率设置颜色
        if (data.memory_percent > 85) {
            memoryProgress.className = 'progress-fill danger';
        } else if (data.memory_percent > 70) {
            memoryProgress.className = 'progress-fill warning';
        } else {
            memoryProgress.className = 'progress-fill';
        }
    }
    
    // 更新速度显示
    updateVelocityDisplay(data) {
        const velocityX = document.getElementById('velocity-x');
        const velocityY = document.getElementById('velocity-y');
        const velocityZ = document.getElementById('velocity-z');
        
        if (velocityX) velocityX.textContent = data.x.toFixed(2);
        if (velocityY) velocityY.textContent = data.y.toFixed(2);
        if (velocityZ) velocityZ.textContent = data.z.toFixed(2);
    }
    
    // 更新速度倍数显示
    updateSpeedDisplay(speedMultiplier) {
        const speedElement = document.getElementById('speed-multiplier');
        if (speedElement) {
            speedElement.textContent = speedMultiplier.toFixed(1);
        }
    }
    
    // 更新检测统计信息
    updateDetectionStats(data) {
        const detectionCount = document.getElementById('detection-count');
        const fpsDisplay = document.getElementById('fps-display');
        const detectionTime = document.getElementById('detection-time');
        
        if (detectionCount) detectionCount.textContent = `检测: ${data.boxes}`;
        if (fpsDisplay) fpsDisplay.textContent = `FPS: ${data.fps.toFixed(1)}`;
        if (detectionTime) detectionTime.textContent = `耗时: ${data.detection_time.toFixed(0)}ms`;
    }
    
    // 更新里程计显示
    updateOdometryDisplay(data) {
        if (!data.position) return;
        
        const positionX = document.getElementById('position-x');
        const positionY = document.getElementById('position-y');
        
        if (positionX) positionX.textContent = data.position.x.toFixed(2);
        if (positionY) positionY.textContent = data.position.y.toFixed(2);
    }
    
    // 更新电压显示
    updateVoltageDisplay(data) {
        const voltageElement = document.getElementById('battery-voltage');
        const statusElement = document.getElementById('voltage-status');
        
        if (!voltageElement || !statusElement) return;
        
        voltageElement.textContent = data.voltage.toFixed(2);
        
        // 根据电压设置状态
        if (data.voltage < 11.0) {
            statusElement.textContent = '电压过低';
            statusElement.className = 'voltage-status danger';
        } else if (data.voltage < 11.5) {
            statusElement.textContent = '电压偏低';
            statusElement.className = 'voltage-status warning';
        } else {
            statusElement.textContent = '正常';
            statusElement.className = 'voltage-status';
        }
    }
    
    // 时间更新
    updateTime() {
        const updateClock = () => {
            const now = new Date();
            const timeString = now.toLocaleTimeString('zh-CN', { hour12: false });
            const timeElement = document.getElementById('current-time');
            if (timeElement) {
                timeElement.textContent = timeString;
            }
        };
        
        updateClock();
        setInterval(updateClock, 1000);
    }
    
    // 设置UI事件监听器
    setupUIEvents(robotControl, visionControl) {
        // 系统控制按钮
        const robotButton = document.getElementById('toggle-robot');
        const visionButton = document.getElementById('toggle-vision');
        
        if (robotButton) {
            robotButton.addEventListener('click', async () => {
                const result = await robotControl.toggleRobot();
                if (result && result.success !== undefined) {
                    this.updateRobotStatus(result.running);
                } else {
                    // 如果操作失败，确保UI状态与实际状态一致
                    this.updateRobotStatus(robotControl.isRunning());
                }
            });
        }
        
        if (visionButton) {
            visionButton.addEventListener('click', async () => {
                const result = await visionControl.toggleVision();
                if (result && result.success !== undefined) {
                    this.updateVisionStatus(result.running);
                } else {
                    // 如果操作失败，确保UI状态与实际状态一致
                    this.updateVisionStatus(visionControl.isRunning());
                }
            });
        }
    }
}

    // 将UIManager暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.UIManager = UIManager;

})(window);
