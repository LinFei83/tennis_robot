// 视觉系统控制模块
(function(global) {
    'use strict';

    class VisionControl {
    constructor(messageHandler) {
        this.messageHandler = messageHandler;
        this.visionRunning = false;
        
        this.init();
    }
    
    init() {
        this.setupVideoEvents();
    }
    
    // 设置视频流事件
    setupVideoEvents() {
        const videoStream = document.getElementById('video-stream');
        if (!videoStream) return;
        
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
    
    // 切换视觉系统状态
    async toggleVision() {
        if (this.visionRunning) {
            return await this.stopVision();
        } else {
            return await this.startVision();
        }
    }
    
    // 启动视觉系统
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
                this.messageHandler.showMessage(result.message, 'success');
                this.hideVideoOverlay();
                return { success: true, running: true };
            } else {
                this.messageHandler.showMessage(result.message, 'error');
                return { success: false, message: result.message };
            }
        } catch (error) {
            const errorMsg = `启动视觉系统失败: ${error.message}`;
            this.messageHandler.showMessage(errorMsg, 'error');
            return { success: false, message: errorMsg };
        }
    }
    
    // 停止视觉系统
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
                this.messageHandler.showMessage(result.message, 'success');
                this.showVideoOverlay();
                return { success: true, running: false };
            } else {
                this.messageHandler.showMessage(result.message, 'error');
                return { success: false, message: result.message };
            }
        } catch (error) {
            const errorMsg = `停止视觉系统失败: ${error.message}`;
            this.messageHandler.showMessage(errorMsg, 'error');
            return { success: false, message: errorMsg };
        }
    }
    
    // 生成带时间戳的文件名
    generateTimestampedFilename(baseName, extension) {
        const now = new Date();
        const timestamp = now.getFullYear() +
                         String(now.getMonth() + 1).padStart(2, '0') +
                         String(now.getDate()).padStart(2, '0') + '_' +
                         String(now.getHours()).padStart(2, '0') +
                         String(now.getMinutes()).padStart(2, '0') +
                         String(now.getSeconds()).padStart(2, '0');
        return `${baseName}_${timestamp}.${extension}`;
    }
    
    // 截取原始图像
    async captureOriginalImage() {
        try {
            const response = await fetch('/api/vision/capture_original', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const filename = this.generateTimestampedFilename('original_image', 'jpg');
                const result = await this.handleImageDownload(response, filename);
                if (result.success) {
                    this.messageHandler.showMessage('原始图像截取成功', 'success');
                }
                return result;
            } else {
                const result = await response.json();
                const errorMsg = `截取失败: ${result.message}`;
                this.messageHandler.showMessage(errorMsg, 'error');
                return { success: false, message: errorMsg };
            }
        } catch (error) {
            const errorMsg = `截取原始图像失败: ${error.message}`;
            this.messageHandler.showMessage(errorMsg, 'error');
            return { success: false, message: errorMsg };
        }
    }
    
    // 截取检测画面
    async captureDetectionImage() {
        try {
            const response = await fetch('/api/vision/capture_detection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                const filename = this.generateTimestampedFilename('detection_image', 'jpg');
                const result = await this.handleImageDownload(response, filename);
                if (result.success) {
                    this.messageHandler.showMessage('检测画面截取成功', 'success');
                }
                return result;
            } else {
                const result = await response.json();
                const errorMsg = `截取失败: ${result.message}`;
                this.messageHandler.showMessage(errorMsg, 'error');
                return { success: false, message: errorMsg };
            }
        } catch (error) {
            const errorMsg = `截取检测画面失败: ${error.message}`;
            this.messageHandler.showMessage(errorMsg, 'error');
            return { success: false, message: errorMsg };
        }
    }
    
    // 处理图像下载
    async handleImageDownload(response, defaultFilename) {
        try {
            // 获取文件名
            const contentDisposition = response.headers.get('content-disposition');
            let filename = defaultFilename;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            
            // 下载文件
            const blob = await response.blob();
            this.downloadFile(blob, filename);
            return { success: true, filename };
        } catch (error) {
            return { success: false, message: error.message };
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
    
    // 视频覆盖层控制
    showVideoOverlay() {
        const overlay = document.getElementById('video-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }
    
    hideVideoOverlay() {
        const overlay = document.getElementById('video-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    // 更新视觉系统状态
    updateStatus(running) {
        this.visionRunning = running;
    }
    
    // 获取视觉系统状态
    isRunning() {
        return this.visionRunning;
    }
}

    // 将VisionControl暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.VisionControl = VisionControl;

})(window);
