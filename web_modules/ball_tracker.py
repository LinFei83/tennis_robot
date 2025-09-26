#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网球跟踪和自动控制模块
负责网球检测、跟踪和机器人自动控制
"""

import time
import math
import threading
import numpy as np
from typing import List, Tuple, Optional


class BallTracker:
    """网球跟踪器"""
    
    def __init__(self, robot_controller=None, socketio=None):
        """
        初始化网球跟踪器
        
        Args:
            robot_controller: 机器人控制器实例
            socketio: WebSocket对象，用于发送状态更新
        """
        self.robot_controller = robot_controller
        self.socketio = socketio
        
        # 拾取模式状态
        self.pickup_mode = False
        self.tracking_active = False
        
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
        
        # PID控制参数
        self.kp = 0.003  # 比例系数
        self.ki = 0.0001  # 积分系数
        self.kd = 0.001   # 微分系数
        
        # PID控制变量
        self.prev_error = 0
        self.integral = 0
        self.last_time = time.time()
        
        # 跟踪状态
        self.target_ball = None
        self.last_detection_time = 0
        self.detection_timeout = 2.0  # 检测超时时间（秒）
        self.center_message_shown = False  # 是否已显示对准中心消息
        
        # 统计信息
        self.tracking_stats = {
            'total_detections': 0,
            'successful_tracks': 0,
            'center_hits': 0,
            'last_target_distance': 0
        }
    
    def toggle_pickup_mode(self):
        """切换拾取模式"""
        self.pickup_mode = not self.pickup_mode
        
        if self.pickup_mode:
            self.tracking_active = True
            self._reset_pid()
            self.center_message_shown = False  # 重置对准消息标志
            message = "拾取模式已开启"
        else:
            self.tracking_active = False
            self._stop_robot()
            self.center_message_shown = False  # 重置对准消息标志
            message = "拾取模式已关闭"
        
        # 发送状态更新
        if self.socketio:
            self.socketio.emit('pickup_mode_update', {
                'enabled': self.pickup_mode,
                'tracking_active': self.tracking_active,
                'message': message
            })
        
        return {
            'status': 'success',
            'pickup_mode': self.pickup_mode,
            'message': message
        }
    
    def get_pickup_status(self):
        """获取拾取模式状态"""
        return {
            'pickup_mode': self.pickup_mode,
            'tracking_active': self.tracking_active,
            'stats': self.tracking_stats.copy()
        }
    
    def process_detections(self, boxes: List, scores: List, frame_shape: Tuple[int, int, int]):
        """
        处理检测结果并执行跟踪控制
        
        Args:
            boxes: 检测框列表 [[x1, y1, x2, y2], ...]
            scores: 置信度列表
            frame_shape: 帧尺寸 (height, width, channels)
        """
        if not self.pickup_mode or not self.tracking_active:
            return
        
        # 更新屏幕尺寸
        if frame_shape:
            self.screen_height, self.screen_width = frame_shape[:2]
            self.screen_center_x = self.screen_width // 2
            self.screen_center_y = self.screen_height // 2
        
        # 过滤有效检测
        valid_balls = self._filter_valid_detections(boxes, scores)
        
        if valid_balls:
            self.last_detection_time = time.time()
            self.tracking_stats['total_detections'] += len(valid_balls)
            
            # 选择目标球
            target_ball = self._select_target_ball(valid_balls)
            
            if target_ball:
                self.target_ball = target_ball
                self._track_ball(target_ball)
                self.tracking_stats['successful_tracks'] += 1
        else:
            # 没有检测到球，检查是否超时
            if time.time() - self.last_detection_time > self.detection_timeout:
                self._handle_no_detection()
    
    def _filter_valid_detections(self, boxes: List, scores: List) -> List[dict]:
        """过滤有效的检测结果"""
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
    
    def _select_target_ball(self, valid_balls: List[dict]) -> Optional[dict]:
        """
        选择目标球（选择最近的球）
        
        Args:
            valid_balls: 有效检测球列表
            
        Returns:
            目标球信息或None
        """
        if not valid_balls:
            return None
        
        # 按到屏幕中心的距离排序，选择最近的
        target_ball = min(valid_balls, key=lambda ball: ball['distance_to_center'])
        
        return target_ball
    
    def _track_ball(self, target_ball: dict):
        """
        跟踪目标球并控制机器人旋转
        
        Args:
            target_ball: 目标球信息
        """
        center_x, center_y = target_ball['center']
        distance_to_center = target_ball['distance_to_center']
        
        # 更新统计信息
        self.tracking_stats['last_target_distance'] = float(distance_to_center)
        
        # 检查是否已经在中心区域
        if distance_to_center <= self.center_tolerance:
            self._stop_robot()
            self.tracking_stats['center_hits'] += 1
            
            # 只在第一次对准时发送消息
            if not self.center_message_shown and self.socketio:
                self.socketio.emit('ball_centered', {
                    'ball_center': [float(target_ball['center'][0]), float(target_ball['center'][1])],
                    'distance': float(distance_to_center),
                    'message': '网球已对准屏幕中心'
                })
                self.center_message_shown = True
            return
        
        # 球不在中心区域，重置对准消息标志
        self.center_message_shown = False
        
        # 计算控制误差（水平方向）
        error = center_x - self.screen_center_x
        
        # PID控制计算
        angular_velocity = self._calculate_pid_control(error)
        
        # 限制最大角速度
        angular_velocity = max(-self.max_angular_speed, 
                             min(self.max_angular_speed, angular_velocity))
        
        # 发送控制命令
        self._send_rotation_command(angular_velocity)
        
        # 发送跟踪状态更新
        if self.socketio:
            self.socketio.emit('ball_tracking_update', {
                'target_ball': {
                    'center': [float(target_ball['center'][0]), float(target_ball['center'][1])],
                    'score': float(target_ball['score']),
                    'distance_to_center': float(distance_to_center)
                },
                'control': {
                    'error': float(error),
                    'angular_velocity': float(angular_velocity)
                },
                'stats': self.tracking_stats
            })
    
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
    
    def _send_rotation_command(self, angular_velocity: float):
        """
        发送旋转控制命令
        
        Args:
            angular_velocity: 角速度 (rad/s)
        """
        if self.robot_controller and hasattr(self.robot_controller, 'robot_running') and self.robot_controller.robot_running:
            try:
                # 只进行旋转，不移动
                result = self.robot_controller.set_velocity(0.0, 0.0, -angular_velocity)
                if result.get('status') != 'success':
                    print(f"旋转命令执行失败: {result.get('message', '未知错误')}")
            except Exception as e:
                print(f"发送旋转命令失败: {e}")
    
    def _stop_robot(self):
        """停止机器人运动"""
        if self.robot_controller and hasattr(self.robot_controller, 'robot_running') and self.robot_controller.robot_running:
            try:
                result = self.robot_controller.set_velocity(0.0, 0.0, 0.0)
                if result.get('status') != 'success':
                    print(f"停止机器人失败: {result.get('message', '未知错误')}")
            except Exception as e:
                print(f"停止机器人失败: {e}")
    
    def _handle_no_detection(self):
        """处理没有检测到球的情况"""
        self._stop_robot()
        self.target_ball = None
        self.center_message_shown = False  # 重置对准消息标志
        
        # 发送无检测状态
        if self.socketio:
            self.socketio.emit('no_ball_detected', {
                'message': '未检测到网球',
                'timeout': self.detection_timeout
            })
    
    def _reset_pid(self):
        """重置PID控制器"""
        self.prev_error = 0
        self.integral = 0
        self.last_time = time.time()
    
    def update_parameters(self, params: dict):
        """
        更新控制参数
        
        Args:
            params: 参数字典
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
        
        # 重置PID控制器
        self._reset_pid()
        
        return {
            'status': 'success',
            'message': '参数更新成功',
            'current_params': {
                'center_tolerance': self.center_tolerance,
                'min_confidence': self.min_confidence,
                'max_angular_speed': self.max_angular_speed,
                'kp': self.kp,
                'ki': self.ki,
                'kd': self.kd
            }
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
            'detection_timeout': self.detection_timeout
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.tracking_stats = {
            'total_detections': 0,
            'successful_tracks': 0,
            'center_hits': 0,
            'last_target_distance': 0
        }
        
        return {
            'status': 'success',
            'message': '统计信息已重置'
        }
