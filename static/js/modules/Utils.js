// 工具函数模块
(function(global) {
    'use strict';

    class Utils {
    constructor() {
        // 工具类不需要初始化
    }
    
    // 消息提示功能
    static showMessage(message, type = 'info') {
        const container = document.getElementById('message-container');
        if (!container) {
            console.warn('消息容器未找到');
            return;
        }
        
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
    
    // 格式化数字，保留指定小数位
    static formatNumber(number, decimals = 2) {
        return number.toFixed(decimals);
    }
    
    // 格式化时间
    static formatTime(date = new Date()) {
        return date.toLocaleTimeString('zh-CN', { hour12: false });
    }
    
    // 安全获取DOM元素
    static getElementById(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`元素未找到: ${id}`);
        }
        return element;
    }
    
    // 安全设置元素文本内容
    static setElementText(elementId, text) {
        const element = this.getElementById(elementId);
        if (element) {
            element.textContent = text;
            return true;
        }
        return false;
    }
    
    // 安全设置元素HTML内容
    static setElementHTML(elementId, html) {
        const element = this.getElementById(elementId);
        if (element) {
            element.innerHTML = html;
            return true;
        }
        return false;
    }
    
    // 安全设置元素样式
    static setElementStyle(elementId, property, value) {
        const element = this.getElementById(elementId);
        if (element) {
            element.style[property] = value;
            return true;
        }
        return false;
    }
    
    // 安全设置元素类名
    static setElementClass(elementId, className) {
        const element = this.getElementById(elementId);
        if (element) {
            element.className = className;
            return true;
        }
        return false;
    }
    
    // 防抖函数
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // 节流函数
    static throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    // 深拷贝对象
    static deepClone(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        
        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }
        
        if (obj instanceof Array) {
            return obj.map(item => this.deepClone(item));
        }
        
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
        
        return obj;
    }
    
    // 等待指定时间
    static sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // 检查对象是否为空
    static isEmpty(obj) {
        if (obj == null) return true;
        if (Array.isArray(obj) || typeof obj === 'string') {
            return obj.length === 0;
        }
        return Object.keys(obj).length === 0;
    }
}

// 消息处理器类
class MessageHandler {
    showMessage(message, type = 'info') {
        Utils.showMessage(message, type);
    }
}

// 键盘帮助折叠/展开功能
function toggleKeyboardHelp() {
    const content = document.getElementById('keyboard-help-content');
    const toggleIcon = document.getElementById('keyboard-toggle');
    
    if (!content || !toggleIcon) return;
    
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

    // 将工具类暴露到全局对象
    global.TennisRobot = global.TennisRobot || {};
    global.TennisRobot.Utils = Utils;
    global.TennisRobot.MessageHandler = MessageHandler;
    global.toggleKeyboardHelp = toggleKeyboardHelp;

})(window);
