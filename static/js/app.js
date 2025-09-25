// 网球机器人控制台JavaScript

class RobotController {
    constructor() {
        this.socket = io();
        this.isConnected = false;
        this.robotRunning = false;
        this.visionRunning = false;
        this.keyPressed = new Set();
        
        this.init();
    }
    
    init() {
        this.setupSocketEvents();
        this.setupUIEvents();
        this.setupKeyboardControl();
        this.updateTime();
        this.hideVideoOverlay();
    }
    
    // WebSocket事件设置
    setupSocketEvents() {
        this.socket.on('connect', () => {
            console.log('已连接到服务器');
            this.isConnected = true;
            this.showMessage('已连接到服务器', 'success');
        });
        
        this.socket.on('disconnect', () => {
            console.log('与服务器断开连接');
            this.isConnected = false;
            this.showMessage('与服务器断开连接', 'error');
        });
        
        this.socket.on('status', (data) => {
            this.updateStatus(data);
        });
        
        this.socket.on('system_stats', (data) => {
            this.updateSystemStats(data);
        });
        
        this.socket.on('velocity_update', (data) => {
            this.updateVelocityDisplay(data);
        });
        
        this.socket.on('detection_update', (data) => {
            this.updateDetectionStats(data);
        });
        
        this.socket.on('odom_update', (data) => {
            this.updateOdometryDisplay(data);
        });
        
        this.socket.on('voltage_update', (data) => {
            this.updateVoltageDisplay(data);
        });
        
        this.socket.on('robot_error', (data) => {
            this.showMessage(`机器人错误: ${data.message}`, 'error');
        });
    }
    
    // UI事件设置
    setupUIEvents() {
        // 系统控制按钮
        document.getElementById('start-robot').addEventListener('click', () => {
            this.startRobot();
        });
        
        document.getElementById('stop-robot').addEventListener('click', () => {
            this.stopRobot();
        });
        
        document.getElementById('start-vision').addEventListener('click', () => {
            this.startVision();
        });
        
        document.getElementById('stop-vision').addEventListener('click', () => {
            this.stopVision();
        });
        
        // 视频流加载事件
        const videoStream = document.getElementById('video-stream');
        
        // 对于MJPEG流，使用onload可能不可靠，改用定时检查
        let videoCheckInterval;
        
        const checkVideoStream = () => {
            if (videoStream.naturalWidth > 0 && videoStream.naturalHeight > 0) {
                this.hideVideoOverlay();
                if (videoCheckInterval) {
                    clearInterval(videoCheckInterval);
                    videoCheckInterval = null;
                }
            }
        };
        
        videoStream.addEventListener('load', () => {
            this.hideVideoOverlay();
        });
        
        videoStream.addEventListener('error', () => {
            this.showVideoOverlay();
        });
        
        // 定时检查视频流是否加载成功
        videoCheckInterval = setInterval(checkVideoStream, 1000);
    }
    
    // 键盘控制设置
    setupKeyboardControl() {
        document.addEventListener('keydown', (event) => {
            if (this.keyPressed.has(event.code)) return;
            this.keyPressed.add(event.code);
            
            if (!this.robotRunning) return;
            
            switch(event.code) {
                case 'KeyW':
                    this.sendRobotControl('forward');
                    break;
                case 'KeyS':
                    this.sendRobotControl('backward');
                    break;
                case 'KeyA':
                    this.sendRobotControl('left');
                    break;
                case 'KeyD':
                    this.sendRobotControl('right');
                    break;
                case 'Space':
                    event.preventDefault();
                    this.sendRobotControl('stop');
                    break;
            }
        });
        
        document.addEventListener('keyup', (event) => {
            this.keyPressed.delete(event.code);
            
            if (!this.robotRunning) return;
            
            // 当按键释放时停止机器人
            if (['KeyW', 'KeyS', 'KeyA', 'KeyD'].includes(event.code)) {
                this.sendRobotControl('stop');
            }
        });
        
        // 防止页面失去焦点时按键卡住
        window.addEventListener('blur', () => {
            this.keyPressed.clear();
            if (this.robotRunning) {
                this.sendRobotControl('stop');
            }
        });
    }
    
    // 发送机器人控制命令
    sendRobotControl(command) {
        if (this.isConnected) {
            this.socket.emit('robot_control', { command: command });
        }
    }
    
    // 系统控制方法
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
                this.updateRobotStatus(true);
                this.showMessage(result.message, 'success');
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            this.showMessage(`启动机器人失败: ${error.message}`, 'error');
        }
    }
    
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
                this.updateRobotStatus(false);
                this.showMessage(result.message, 'success');
                // 重置速度显示
                this.updateVelocityDisplay({x: 0, y: 0, z: 0});
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            this.showMessage(`停止机器人失败: ${error.message}`, 'error');
        }
    }
    
    async startVision() {
        try {
            const response = await fetch('/api/vision/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                this.visionRunning = true;
                this.updateVisionStatus(true);
                this.showMessage(result.message, 'success');
                this.hideVideoOverlay();
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            this.showMessage(`启动视觉系统失败: ${error.message}`, 'error');
        }
    }
    
    async stopVision() {
        try {
            const response = await fetch('/api/vision/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                this.visionRunning = false;
                this.updateVisionStatus(false);
                this.showMessage(result.message, 'success');
                this.showVideoOverlay();
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            this.showMessage(`停止视觉系统失败: ${error.message}`, 'error');
        }
    }
    
    // UI更新方法
    updateStatus(data) {
        this.robotRunning = data.robot;
        this.visionRunning = data.vision;
        this.updateRobotStatus(data.robot);
        this.updateVisionStatus(data.vision);
    }
    
    updateRobotStatus(running) {
        const statusElement = document.getElementById('robot-status');
        if (running) {
            statusElement.textContent = '在线';
            statusElement.className = 'status-value online';
        } else {
            statusElement.textContent = '离线';
            statusElement.className = 'status-value offline';
        }
    }
    
    updateVisionStatus(running) {
        const statusElement = document.getElementById('vision-status');
        if (running) {
            statusElement.textContent = '在线';
            statusElement.className = 'status-value online';
        } else {
            statusElement.textContent = '离线';
            statusElement.className = 'status-value offline';
        }
    }
    
    updateSystemStats(data) {
        // 更新CPU使用率
        const cpuProgress = document.getElementById('cpu-progress');
        const cpuPercent = document.getElementById('cpu-percent');
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
        
        // 更新内存使用率
        const memoryProgress = document.getElementById('memory-progress');
        const memoryPercent = document.getElementById('memory-percent');
        const memoryUsed = document.getElementById('memory-used');
        const memoryTotal = document.getElementById('memory-total');
        
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
    
    updateVelocityDisplay(data) {
        document.getElementById('velocity-x').textContent = data.x.toFixed(2);
        document.getElementById('velocity-y').textContent = data.y.toFixed(2);
        document.getElementById('velocity-z').textContent = data.z.toFixed(2);
    }
    
    updateDetectionStats(data) {
        document.getElementById('detection-count').textContent = `检测: ${data.boxes}`;
        document.getElementById('fps-display').textContent = `FPS: ${data.fps.toFixed(1)}`;
        document.getElementById('detection-time').textContent = `耗时: ${data.detection_time.toFixed(0)}ms`;
    }
    
    updateOdometryDisplay(data) {
        if (data.position) {
            document.getElementById('position-x').textContent = data.position.x.toFixed(2);
            document.getElementById('position-y').textContent = data.position.y.toFixed(2);
        }
    }
    
    updateVoltageDisplay(data) {
        const voltageElement = document.getElementById('battery-voltage');
        const statusElement = document.getElementById('voltage-status');
        
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
    
    // 视频覆盖层控制
    showVideoOverlay() {
        document.getElementById('video-overlay').style.display = 'flex';
    }
    
    hideVideoOverlay() {
        document.getElementById('video-overlay').style.display = 'none';
    }
    
    // 时间更新
    updateTime() {
        const updateClock = () => {
            const now = new Date();
            const timeString = now.toLocaleTimeString('zh-CN', { hour12: false });
            document.getElementById('current-time').textContent = timeString;
        };
        
        updateClock();
        setInterval(updateClock, 1000);
    }
    
    // 消息提示
    showMessage(message, type = 'info') {
        const container = document.getElementById('message-container');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = message;
        
        container.appendChild(messageElement);
        
        // 自动移除消息
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.parentNode.removeChild(messageElement);
            }
        }, 5000);
        
        // 限制消息数量
        while (container.children.length > 5) {
            container.removeChild(container.firstChild);
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.robotController = new RobotController();
});
