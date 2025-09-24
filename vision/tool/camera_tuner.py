#!/usr/bin/env python3
"""
摄像头参数调整工具
用于实时调整摄像头的各种参数，并将配置保存到文件
"""

import cv2
import json
import numpy as np
import os
from datetime import datetime

class CameraTuner:
    def __init__(self, camera_index=0, config_path="vision/config/camera_config.json"):
        """
        初始化摄像头调整工具
        
        Args:
            camera_index: 摄像头索引
            config_path: 配置文件路径
        """
        self.camera_index = camera_index
        self.config_path = config_path
        self.cap = None
        
        # 加载现有配置
        self.config = self.load_config()
        
        # 参数范围定义（基于实际摄像头支持的属性）
        self.param_ranges = {
            'fps': {'min': 1, 'max': 60, 'default': 30},
            'brightness': {'min': 0, 'max': 100, 'default': 30},      # 根据实际范围调整
            'contrast': {'min': 0, 'max': 100, 'default': 29},        # 根据实际范围调整
            'saturation': {'min': 0, 'max': 255, 'default': 128},
            'gain': {'min': 0, 'max': 100, 'default': 0},             # 增益可以替代曝光控制
            'buffer_size': {'min': 1, 'max': 10, 'default': 5}
        }
        
        # 参数显示名称映射（用于滑条显示）
        self.param_display_names = {
            'fps': 'zhenshu',           # 帧数
            'brightness': 'liangdu',    # 亮度
            'contrast': 'duibidu',      # 对比度
            'saturation': 'baohedu',    # 饱和度
            'gain': 'zengyi',           # 增益（替代曝光）
            'buffer_size': 'huanchong'  # 缓冲
        }
        
        # 当前参数值
        self.current_params = {
            'fps': self.config['camera'].get('fps', 30),
            'brightness': self.config['image_settings'].get('brightness', 30),
            'contrast': self.config['image_settings'].get('contrast', 29),
            'saturation': self.config['image_settings'].get('saturation', 128),
            'gain': self.config['image_settings'].get('gain', 0),
            'buffer_size': self.config['camera'].get('buffer_size', 5)
        }
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"成功加载配置文件: {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"配置文件不存在，使用默认配置")
            return {
                "camera": {"index": 0, "fps": 30, "buffer_size": 5},
                "image_settings": {"brightness": 30, "contrast": 29, "saturation": 128, "gain": 0},
                "detection": {"confidence_threshold": 0.6, "iou_threshold": 0.5}
            }
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {e}，使用默认配置")
            return {
                "camera": {"index": 0, "fps": 30, "buffer_size": 5},
                "image_settings": {"brightness": 30, "contrast": 29, "saturation": 128, "gain": 0},
                "detection": {"confidence_threshold": 0.6, "iou_threshold": 0.5}
            }
    
    def save_config(self):
        """保存当前配置到文件"""
        # 更新配置
        self.config['camera']['fps'] = self.current_params['fps']
        self.config['camera']['buffer_size'] = self.current_params['buffer_size']
        self.config['image_settings']['brightness'] = self.current_params['brightness']
        self.config['image_settings']['contrast'] = self.current_params['contrast']
        self.config['image_settings']['saturation'] = self.current_params['saturation']
        self.config['image_settings']['gain'] = self.current_params['gain']
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"配置已保存到: {self.config_path}")
            
            # 创建备份
            backup_path = f"{self.config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"备份已创建: {backup_path}")
            
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def init_camera(self):
        """初始化摄像头"""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"错误: 无法打开摄像头 {self.camera_index}")
            return False
        
        # 设置基本参数
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        return True
    
    def apply_params(self):
        """应用当前参数到摄像头"""
        if self.cap is None:
            return
        
        try:
            # 应用参数
            self.cap.set(cv2.CAP_PROP_FPS, self.current_params['fps'])
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.current_params['buffer_size'])
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.current_params['brightness'])
            self.cap.set(cv2.CAP_PROP_CONTRAST, self.current_params['contrast'])
            self.cap.set(cv2.CAP_PROP_SATURATION, self.current_params['saturation'])
            
            # 使用增益控制替代曝光（如果摄像头支持）
            self.cap.set(cv2.CAP_PROP_GAIN, self.current_params['gain'])
            
        except Exception as e:
            print(f"应用参数时出错: {e}")
    
    def on_trackbar_change(self, val, param_name):
        """滑条变化回调函数"""
        self.current_params[param_name] = val
        self.apply_params()
    
    def create_trackbars(self):
        """创建参数调整滑条"""
        cv2.namedWindow('Camera Tuner', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Camera Tuner', 400, 300)
        
        # 为每个参数创建滑条
        for param_name, param_info in self.param_ranges.items():
            display_name = self.param_display_names[param_name]
            cv2.createTrackbar(
                display_name,
                'Camera Tuner',
                self.current_params[param_name],
                param_info['max'] - param_info['min'],
                lambda val, name=param_name: self.on_trackbar_change(val + self.param_ranges[name]['min'], name)
            )
            # 设置初始值
            cv2.setTrackbarPos(display_name, 'Camera Tuner', 
                             self.current_params[param_name] - param_info['min'])
    
    def display_info(self, frame):
        """显示纯净的图像，不添加任何文字信息"""
        # 不在图像上绘制任何文字，保持图像纯净
        pass
    
    def reset_to_defaults(self):
        """重置为默认值"""
        for param_name, param_info in self.param_ranges.items():
            self.current_params[param_name] = param_info['default']
            display_name = self.param_display_names[param_name]
            cv2.setTrackbarPos(display_name, 'Camera Tuner', 
                             param_info['default'] - param_info['min'])
        self.apply_params()
        print("参数已重置为默认值")
    
    def run(self):
        """运行调整工具"""
        if not self.init_camera():
            return
        
        print("摄像头参数调整工具启动")
        print("操作说明:")
        print("  使用滑条调整参数")
        print("  's' - 保存配置")
        print("  'r' - 重置为默认值")
        print("  'q' - 退出")
        
        # 创建控制面板
        self.create_trackbars()
        
        # 应用初始参数
        self.apply_params()
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("无法读取摄像头画面")
                    break
                
                # 显示参数信息
                self.display_info(frame)
                
                # 显示图像
                cv2.imshow('Camera Feed', frame)
                
                # 检查按键
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    self.save_config()
                elif key == ord('r'):
                    self.reset_to_defaults()
        
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        
        finally:
            # 清理资源
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            print("摄像头参数调整工具已退出")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='摄像头参数调整工具')
    parser.add_argument('--camera', '-c', type=int, default=0, help='摄像头索引 (默认: 0)')
    parser.add_argument('--config', type=str, default='vision/config/camera_config.json', help='配置文件路径')
    
    args = parser.parse_args()
    
    tuner = CameraTuner(args.camera, args.config)
    tuner.run()


if __name__ == "__main__":
    main()
