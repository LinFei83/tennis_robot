#!/usr/bin/env python3
"""
摄像头管理模块 - 负责摄像头配置、初始化和帧获取
"""

import cv2
import json
import time
from typing import Dict, Tuple, Optional, Any


class CameraConfig:
    """摄像头配置管理类"""
    
    DEFAULT_CONFIG = {
        "camera": {"index": 0, "fps": 30},
        "image_settings": {"brightness": 128, "contrast": 128, "saturation": 128, "exposure": -6},
        "detection": {"confidence_threshold": 0.6, "iou_threshold": 0.5}
    }
    
    def __init__(self, config_path: str = "vision/config/camera_config.json"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载摄像头配置文件
        
        Returns:
            config: 配置字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"成功加载配置文件: {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"配置文件不存在: {self.config_path}，使用默认配置")
            return self.DEFAULT_CONFIG.copy()
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {e}，使用默认配置")
            return self.DEFAULT_CONFIG.copy()
    
    def get_camera_config(self) -> Dict[str, Any]:
        """获取摄像头配置"""
        return self.config.get("camera", {})
    
    def get_image_settings(self) -> Dict[str, Any]:
        """获取图像设置"""
        return self.config.get("image_settings", {})
    
    def get_detection_config(self) -> Dict[str, Any]:
        """获取检测配置"""
        return self.config.get("detection", {})


class CameraManager:
    """摄像头管理类，负责摄像头的初始化、设置和帧获取"""
    
    def __init__(self, config: CameraConfig, target_width: int = None, target_height: int = None):
        """
        初始化摄像头管理器
        
        Args:
            config: 摄像头配置对象
            target_width: 目标宽度（通常为模型输入宽度）
            target_height: 目标高度（通常为模型输入高度）
        """
        self.config = config
        self.target_width = target_width
        self.target_height = target_height
        self.cap = None
        
    def initialize_camera(self) -> bool:
        """
        初始化摄像头
        
        Returns:
            bool: 初始化是否成功
        """
        camera_config = self.config.get_camera_config()
        camera_index = camera_config.get("index", 0)
        
        print("正在初始化摄像头...")
        self.cap = cv2.VideoCapture(camera_index)
        
        if not self.cap.isOpened():
            print(f"错误: 无法打开摄像头 {camera_index}")
            return False
        
        # 设置摄像头分辨率
        if self.target_width and self.target_height:
            print(f"设置摄像头分辨率为: {self.target_width}x{self.target_height}")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        
        # 应用摄像头设置
        self._apply_camera_settings()
        
        # 验证实际分辨率
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"摄像头实际分辨率: {actual_width}x{actual_height}")
        
        if (self.target_width and actual_width != self.target_width or 
            self.target_height and actual_height != self.target_height):
            print("警告: 摄像头不支持目标分辨率，将使用resize调整图像尺寸")
        
        print("摄像头初始化完成")
        return True
    
    def _apply_camera_settings(self):
        """应用摄像头设置"""
        if not self.cap:
            return
            
        camera_config = self.config.get_camera_config()
        image_config = self.config.get_image_settings()
        
        # 基础摄像头参数
        self.cap.set(cv2.CAP_PROP_FPS, camera_config.get("fps", 30))
        # 设置最小缓冲区以减少延迟
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print("设置摄像头缓冲区大小: 1")
        
        # 图像质量参数
        try:
            # 如果需要设置曝光，先关闭自动曝光
            if "exposure" in image_config:
                # 关闭自动曝光 (0.25表示手动模式，0.75表示自动模式)
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                print("关闭自动曝光，切换到手动曝光模式")
            
            settings_map = {
                "brightness": cv2.CAP_PROP_BRIGHTNESS,
                "contrast": cv2.CAP_PROP_CONTRAST,
                "saturation": cv2.CAP_PROP_SATURATION,
                "exposure": cv2.CAP_PROP_EXPOSURE,
                "gain": cv2.CAP_PROP_GAIN
            }
            
            for setting_name, cv_prop in settings_map.items():
                if setting_name in image_config:
                    self.cap.set(cv_prop, image_config[setting_name])
                    print(f"设置{setting_name}: {image_config[setting_name]}")
                    
        except Exception as e:
            print(f"警告: 设置摄像头参数时出错: {e}")
    
    def get_latest_frame(self) -> Tuple[bool, Optional[any]]:
        """
        始终获取摄像头最新帧，清空缓冲区以减少延迟
        
        Returns:
            Tuple[bool, Optional[numpy.ndarray]]: (是否成功, 帧数据)
        """
        if not self.cap:
            return False, None
            
        frame = None
        ret = False
        
        # 清空缓冲区，获取最新帧
        # 由于缓冲区设置为1，读取2帧以确保获得最新帧
        for _ in range(2):
            current_ret, current_frame = self.cap.read()
            if current_ret:
                ret = current_ret
                frame = current_frame
            else:
                # 如果读取失败，停止尝试
                break
        
        return ret, frame
    
    
    def release(self):
        """释放摄像头资源"""
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()


class PerformanceMonitor:
    """性能监控类"""
    
    def __init__(self):
        """初始化性能监控器"""
        self.frame_count = 0
        self.start_time = time.time()
    
    def update_frame_count(self):
        """更新帧计数"""
        self.frame_count += 1
    
    def get_fps(self) -> float:
        """获取当前FPS"""
        elapsed_time = time.time() - self.start_time
        return self.frame_count / (elapsed_time + 1e-6)
    
    def get_stats(self) -> Dict[str, float]:
        """
        获取统计信息
        
        Returns:
            Dict: 包含总帧数、运行时间、平均FPS的字典
        """
        total_time = time.time() - self.start_time
        avg_fps = self.frame_count / total_time if total_time > 0 else 0
        
        return {
            "total_frames": self.frame_count,
            "total_time": total_time,
            "average_fps": avg_fps
        }
