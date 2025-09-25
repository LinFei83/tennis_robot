// 网球机器人控制台JavaScript

class RobotController {
    constructor() {
        this.socket = io();
        this.isConnected = false;
        this.robotRunning = false;
        this.visionRunning = false;
        this.keyPressed = new Set();
        this.speedMultiplier = 1.0;
        
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
            if (data.speed_multiplier !== undefined) {
                this.speedMultiplier = data.speed_multiplier;
                this.updateSpeedDisplay();
            }
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
        
        this.socket.on('info', (data) => {
            this.showMessage(data.message, 'info');
        });
        
        this.socket.on('error', (data) => {
            this.showMessage(data.message, 'error');
        });
    }
    
    // UI事件设置
    setupUIEvents() {
        // 系统控制按钮
        document.getElementById('toggle-robot').addEventListener('click', () => {
            this.toggleRobot();
        });
        
        document.getElementById('toggle-vision').addEventListener('click', () => {
            this.toggleVision();
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
                    this.sendRobotControl('left_translate');
                    break;
                case 'KeyD':
                    this.sendRobotControl('right_translate');
                    break;
                case 'KeyQ':
                    this.sendRobotControl('rotate_left');
                    break;
                case 'KeyE':
                    this.sendRobotControl('rotate_right');
                    break;
                case 'KeyC':
                    this.sendRobotControl('speed_up');
                    break;
                case 'KeyZ':
                    this.sendRobotControl('speed_down');
                    break;
                case 'Space':
                    event.preventDefault();
                    this.sendRobotControl('stop');
                    break;
                case 'KeyP':
                    event.preventDefault();
                    this.captureOriginalImage();
                    break;
                case 'KeyO':
                    event.preventDefault();
                    this.captureDetectionImage();
                    break;
            }
        });
        
        document.addEventListener('keyup', (event) => {
            this.keyPressed.delete(event.code);
            
            if (!this.robotRunning) return;
            
            // 当按键释放时停止机器人
            if (['KeyW', 'KeyS', 'KeyA', 'KeyD', 'KeyQ', 'KeyE'].includes(event.code)) {
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
    async toggleRobot() {
        if (this.robotRunning) {
            await this.stopRobot();
        } else {
            await this.startRobot();
        }
    }

    async toggleVision() {
        if (this.visionRunning) {
            await this.stopVision();
        } else {
            await this.startVision();
        }
    }

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
        const buttonElement = document.getElementById('toggle-robot');
        
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
    
    updateVisionStatus(running) {
        const statusElement = document.getElementById('vision-status');
        const buttonElement = document.getElementById('toggle-vision');
        
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
    
    updateSpeedDisplay() {
        const speedElement = document.getElementById('speed-multiplier');
        if (speedElement) {
            speedElement.textContent = this.speedMultiplier.toFixed(1);
        }
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
    
    // 截图功能
    async captureOriginalImage() {
        try {
            const response = await fetch('/api/vision/capture_original', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                // 获取文件名
                const contentDisposition = response.headers.get('content-disposition');
                let filename = 'original_image.jpg';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }
                
                // 下载文件
                const blob = await response.blob();
                this.downloadFile(blob, filename);
                this.showMessage('原始图像截取成功', 'success');
            } else {
                const result = await response.json();
                this.showMessage(`截取失败: ${result.message}`, 'error');
            }
        } catch (error) {
            this.showMessage(`截取原始图像失败: ${error.message}`, 'error');
        }
    }
    
    async captureDetectionImage() {
        try {
            const response = await fetch('/api/vision/capture_detection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                // 获取文件名
                const contentDisposition = response.headers.get('content-disposition');
                let filename = 'detection_image.jpg';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }
                
                // 下载文件
                const blob = await response.blob();
                this.downloadFile(blob, filename);
                this.showMessage('检测画面截取成功', 'success');
            } else {
                const result = await response.json();
                this.showMessage(`截取失败: ${result.message}`, 'error');
            }
        } catch (error) {
            this.showMessage(`截取检测画面失败: ${error.message}`, 'error');
        }
    }
    
    // 文件下载功能
    downloadFile(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
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

// 键盘帮助折叠/展开功能
function toggleKeyboardHelp() {
    const content = document.getElementById('keyboard-help-content');
    const toggleIcon = document.getElementById('keyboard-toggle');
    
    if (content.classList.contains('collapsed')) {
        // 展开
        content.classList.remove('collapsed');
        toggleIcon.textContent = '▲';
        toggleIcon.style.transform = 'rotate(180deg)';
    } else {
        // 折叠
        content.classList.add('collapsed');
        toggleIcon.textContent = '▼';
        toggleIcon.style.transform = 'rotate(0deg)';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.robotController = new RobotController();
});
