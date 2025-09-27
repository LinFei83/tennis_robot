#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网球控制器模块
负责网球检测处理、跟踪算法和机器人控制逻辑
"""

import time
import math
import numpy as np
from typing import List, Tuple, Optional


class BallController:
    """网球控制器 - 负责核心控制逻辑"""
    
    def __init__(self, robot_controller=None):
        """
        初始化网球控制器
        
        Args:
            robot_controller: 机器人控制器实例
        """
        self.robot_controller = robot_controller
        
        # 屏幕参数
        self.screen_width = 640
        self.screen_height = 480
        self.screen_center_x = self.screen_width // 2
        self.screen_center_y = self.screen_height // 2
        
        # 控制参数
        self.center_tolerance = 30  # 中心区域容差（像素）
        self.min_confidence = 0.6   # 最小置信度
        self.angular_speed_base = 0.05  # 基础角速度 rad/s
        self.max_angular_speed = 0.15   # 最大角速度 rad/s
        
        # 前进控制参数
        self.forward_speed = 0.2  # 前进速度 m/s
        
        # PID控制参数
        self.kp = 0.003  # 比例系数
        self.ki = 0.0001  # 积分系数
        self.kd = 0.001   # 微分系数
        
        # PID控制变量
        self.prev_error = 0
        self.integral = 0
        self.last_time = time.time()
        
        # 检测超时参数
        self.detection_timeout = 2.0  # 检测超时时间（秒）
    
    def update_screen_size(self, frame_shape: Tuple[int, int, int]):
        """
        更新屏幕尺寸
        
        Args:
            frame_shape: 帧尺寸 (height, width, channels)
        """
        if frame_shape:
            self.screen_height, self.screen_width = frame_shape[:2]
            self.screen_center_x = self.screen_width // 2
            self.screen_center_y = self.screen_height // 2
    
    def filter_valid_detections(self, boxes: List, scores: List) -> List[dict]:
        """
        过滤有效的检测结果
        
        Args:
            boxes: 检测框列表 [[x1, y1, x2, y2], ...]
            scores: 置信度列表
            
        Returns:
            有效球的信息列表
        """
        valid_balls = []
        
        for i, (box, score) in enumerate(zip(boxes, scores)):
            if score >= self.min_confidence:
                # 计算球的中心点
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                # 计算球的尺寸
                width = x2 - x1
                height = y2 - y1
                area = width * height
                
                # 计算到屏幕中心的距离
                distance_to_center = math.sqrt(
                    (center_x - self.screen_center_x) ** 2 + 
                    (center_y - self.screen_center_y) ** 2
                )
                
                ball_info = {
                    'id': i,
                    'box': [float(x) for x in box],
                    'center': (float(center_x), float(center_y)),
                    'score': float(score),
                    'area': float(area),
                    'distance_to_center': float(distance_to_center)
                }
                
                valid_balls.append(ball_info)
        
        return valid_balls
    
    def select_target_ball(self, valid_balls: List[dict], selection_mode: str = 'largest') -> Optional[dict]:
        """
        选择目标球
        
        Args:
            valid_balls: 有效检测球列表
            selection_mode: 选择模式 'largest'(最大检测框) 或 'nearest'(最近中心)
            
        Returns:
            目标球信息或None
        """
        if not valid_balls:
            return None
        
        if selection_mode == 'largest':
            # 选择检测框最大的球（最近的球）
            target_ball = max(valid_balls, key=lambda ball: ball['area'])
        else:  # nearest
            # 按到屏幕中心的距离排序，选择最近的
            target_ball = min(valid_balls, key=lambda ball: ball['distance_to_center'])
        
        return target_ball
    
    def is_ball_centered(self, target_ball: dict) -> bool:
        """
        检查球是否已经在中心区域
        
        Args:
            target_ball: 目标球信息
            
        Returns:
            True如果球在中心区域
        """
        distance_to_center = target_ball['distance_to_center']
        return distance_to_center <= self.center_tolerance
    
    
    def calculate_control_output(self, target_ball: dict) -> dict:
        """
        计算控制输出
        
        Args:
            target_ball: 目标球信息
            
        Returns:
            控制信息字典
        """
        center_x, center_y = target_ball['center']
        distance_to_center = target_ball['distance_to_center']
        
        # 计算控制误差（水平方向）
        error = center_x - self.screen_center_x
        
        # PID控制计算
        angular_velocity = self._calculate_pid_control(error)
        
        # 限制最大角速度
        angular_velocity = max(-self.max_angular_speed, 
                             min(self.max_angular_speed, angular_velocity))
        
        return {
            'error': float(error),
            'angular_velocity': float(angular_velocity),
            'distance_to_center': float(distance_to_center)
        }
    
    def _calculate_pid_control(self, error: float) -> float:
        """
        PID控制计算
        
        Args:
            error: 控制误差
            
        Returns:
            控制输出（角速度）
        """
        current_time = time.time()
        dt = current_time - self.last_time
        
        if dt <= 0:
            dt = 0.01
        
        # 比例项
        proportional = self.kp * error
        
        # 积分项
        self.integral += error * dt
        # 限制积分项防止积分饱和
        self.integral = max(-100, min(100, self.integral))
        integral_term = self.ki * self.integral
        
        # 微分项
        derivative = (error - self.prev_error) / dt
        derivative_term = self.kd * derivative
        
        # PID输出
        output = proportional + integral_term + derivative_term
        
        # 更新历史值
        self.prev_error = error
        self.last_time = current_time
        
        return output
    
    def send_rotation_command(self, angular_velocity: float) -> bool:
        """
        发送旋转控制命令
        
        Args:
            angular_velocity: 角速度 (rad/s)
            
        Returns:
            True如果命令发送成功
        """
        if self.robot_controller and hasattr(self.robot_controller, 'robot_running') and self.robot_controller.robot_running:
            try:
                # 只进行旋转，不移动
                result = self.robot_controller.set_velocity(0.0, 0.0, -angular_velocity)
                if result.get('status') != 'success':
                    print(f"旋转命令执行失败: {result.get('message', '未知错误')}")
                    return False
                return True
            except Exception as e:
                print(f"发送旋转命令失败: {e}")
                return False
        return False
    
    def stop_robot(self) -> bool:
        """
        停止机器人运动
        
        Returns:
            True如果停止成功
        """
        if self.robot_controller and hasattr(self.robot_controller, 'robot_running') and self.robot_controller.robot_running:
            try:
                result = self.robot_controller.set_velocity(0.0, 0.0, 0.0)
                if result.get('status') != 'success':
                    print(f"停止机器人失败: {result.get('message', '未知错误')}")
                    return False
                return True
            except Exception as e:
                print(f"停止机器人失败: {e}")
                return False
        return False
    
    def send_forward_command(self, speed: float = None) -> bool:
        """
        发送前进控制命令
        
        Args:
            speed: 前进速度，如果为None则使用默认速度
            
        Returns:
            True如果命令发送成功
        """
        if speed is None:
            speed = self.forward_speed
            
        if self.robot_controller and hasattr(self.robot_controller, 'robot_running') and self.robot_controller.robot_running:
            try:
                result = self.robot_controller.set_velocity(speed, 0.0, 0.0)
                if result.get('status') != 'success':
                    print(f"前进命令执行失败: {result.get('message', '未知错误')}")
                    return False
                return True
            except Exception as e:
                print(f"发送前进命令失败: {e}")
                return False
        return False
    
    def send_backward_command(self, speed: float = None, duration: float = 1.0) -> bool:
        """
        发送后退控制命令
        
        Args:
            speed: 后退速度，如果为None则使用默认速度
            duration: 后退持续时间（秒）
            
        Returns:
            True如果命令发送成功
        """
        if speed is None:
            speed = self.forward_speed
            
        if self.robot_controller and hasattr(self.robot_controller, 'robot_running') and self.robot_controller.robot_running:
            try:
                result = self.robot_controller.set_velocity(-speed, 0.0, 0.0)
                if result.get('status') != 'success':
                    print(f"后退命令执行失败: {result.get('message', '未知错误')}")
                    return False
                return True
            except Exception as e:
                print(f"发送后退命令失败: {e}")
                return False
        return False
    
    def send_search_rotation_command(self, angular_velocity: float = None) -> bool:
        """
        发送搜索旋转命令
        
        Args:
            angular_velocity: 角速度，如果为None则使用默认值
            
        Returns:
            True如果命令发送成功
        """
        if angular_velocity is None:
            angular_velocity = self.angular_speed_base
            
        if self.robot_controller and hasattr(self.robot_controller, 'robot_running') and self.robot_controller.robot_running:
            try:
                result = self.robot_controller.set_velocity(0.0, 0.0, angular_velocity)
                if result.get('status') != 'success':
                    print(f"搜索旋转命令执行失败: {result.get('message', '未知错误')}")
                    return False
                return True
            except Exception as e:
                print(f"发送搜索旋转命令失败: {e}")
                return False
        return False
    
    def reset_pid(self):
        """重置PID控制器"""
        self.prev_error = 0
        self.integral = 0
        self.last_time = time.time()
    
    def update_parameters(self, params: dict):
        """
        更新控制参数
        
        Args:
            params: 参数字典
            
        Returns:
            更新结果和当前参数
        """
        if 'center_tolerance' in params:
            self.center_tolerance = max(10, min(100, params['center_tolerance']))
        
        if 'min_confidence' in params:
            self.min_confidence = max(0.1, min(1.0, params['min_confidence']))
        
        if 'max_angular_speed' in params:
            self.max_angular_speed = max(0.1, min(2.0, params['max_angular_speed']))
        
        if 'kp' in params:
            self.kp = max(0.0001, min(0.01, params['kp']))
        
        if 'ki' in params:
            self.ki = max(0, min(0.001, params['ki']))
        
        if 'kd' in params:
            self.kd = max(0, min(0.01, params['kd']))
        
        if 'forward_speed' in params:
            self.forward_speed = max(0.1, min(1.0, params['forward_speed']))
        
        # 重置PID控制器
        self.reset_pid()
        
        return {
            'status': 'success',
            'message': '参数更新成功',
            'current_params': self.get_current_parameters()
        }
    
    def get_current_parameters(self):
        """获取当前参数"""
        return {
            'center_tolerance': self.center_tolerance,
            'min_confidence': self.min_confidence,
            'max_angular_speed': self.max_angular_speed,
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'detection_timeout': self.detection_timeout,
            'forward_speed': self.forward_speed
        }
