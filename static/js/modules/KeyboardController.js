// 键盘控制模块
(function(global) {
    'use strict';

    class KeyboardController {
    constructor(robotControl, visionControl) {
        this.robotControl = robotControl;
        this.visionControl = visionControl;
        this.keyPressed = new Set();
        
        this.init();
    }
    
    init() {
        this.setupKeyboardEvents();
        this.setupWindowEvents();
    }
    
    // 设置键盘事件
    setupKeyboardEvents() {
        document.addEventListener('keydown', (event) => {
            if (this.keyPressed.has(event.code)) return;
            this.keyPressed.add(event.code);
            
            this.handleKeyDown(event);
        });
        
        document.addEventListener('keyup', (event) => {
            this.keyPressed.delete(event.code);
            this.handleKeyUp(event);
        });
    }
    
    // 设置窗口事件
    setupWindowEvents() {
        // 防止页面失去焦点时按键卡住
        window.addEventListener('blur', () => {
            this.keyPressed.clear();
            if (this.robotControl.isRunning()) {
                this.robotControl.sendControlCommand('stop');
            }
        });
    }
    
    // 处理按键按下事件
    handleKeyDown(event) {
        // 机器人控制按键
        if (this.robotControl.isRunning()) {
            switch(event.code) {
                case 'KeyW':
                    this.robotControl.sendControlCommand('forward');
                    break;
                case 'KeyS':
                    this.robotControl.sendControlCommand('backward');
                    break;
                case 'KeyA':
                    this.robotControl.sendControlCommand('left_translate');
                    break;
                case 'KeyD':
                    this.robotControl.sendControlCommand('right_translate');
                    break;
                case 'KeyQ':
                    this.robotControl.sendControlCommand('rotate_left');
                    break;
                case 'KeyE':
                    this.robotControl.sendControlCommand('rotate_right');
                    break;
                case 'KeyC':
                    this.robotControl.sendControlCommand('speed_up');
                    break;
                case 'KeyZ':
                    this.robotControl.sendControlCommand('speed_down');
                    break;
                case 'Space':
                    event.preventDefault();
                    this.robotControl.sendControlCommand('stop');
                    break;
            }
        }
        
        // 视觉系统控制按键
        switch(event.code) {
            case 'KeyP':
                event.preventDefault();
                this.visionControl.captureOriginalImage();
                break;
            case 'KeyO':
                event.preventDefault();
                this.visionControl.captureDetectionImage();
                break;
        }
    }
    
    // 处理按键释放事件
    handleKeyUp(event) {
        if (!this.robotControl.isRunning()) return;
        
        // 当按键释放时停止机器人
        if (['KeyW', 'KeyS', 'KeyA', 'KeyD', 'KeyQ', 'KeyE'].includes(event.code)) {
            this.robotControl.sendControlCommand('stop');
        }
    }
    
    // 清除所有按键状态
    clearKeyState() {
        this.keyPressed.clear();
    }
    
    // 检查按键是否被按下
    isKeyPressed(keyCode) {
        return this.keyPressed.has(keyCode);
    }
    
    // 获取当前按下的按键
    getPressedKeys() {
        return Array.from(this.keyPressed);
    }
}

    // 将KeyboardController暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.KeyboardController = KeyboardController;

})(window);
