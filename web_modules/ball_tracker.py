#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网球跟踪Web模块
负责网页交互、状态管理和WebSocket通信
调用BallController进行实际的控制逻辑
"""

import time
import threading
import numpy as np
from typing import List, Tuple, Optional
from .ball_controller import BallController


class BallTracker:
    """网球跟踪器 - Web界面和状态管理"""
    
    def __init__(self, robot_controller=None, socketio=None):
        """
        初始化网球跟踪器
        
        Args:
            robot_controller: 机器人控制器实例
            socketio: WebSocket对象，用于发送状态更新
        """
        self.socketio = socketio
        
        # 初始化控制器
        self.ball_controller = BallController(robot_controller)
        
        # 拾取模式状态
        self.pickup_mode = False
        self.tracking_active = False
        
        # 跟踪状态
        self.target_ball = None
        self.last_detection_time = 0
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
            self.ball_controller.reset_pid()
            self.center_message_shown = False  # 重置对准消息标志
            message = "拾取模式已开启"
        else:
            self.tracking_active = False
            self.ball_controller.stop_robot()
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
        
        # 更新控制器的屏幕尺寸
        self.ball_controller.update_screen_size(frame_shape)
        
        # 使用控制器过滤有效检测
        valid_balls = self.ball_controller.filter_valid_detections(boxes, scores)
        
        if valid_balls:
            self.last_detection_time = time.time()
            self.tracking_stats['total_detections'] += len(valid_balls)
            
            # 使用控制器选择目标球
            target_ball = self.ball_controller.select_target_ball(valid_balls)
            
            if target_ball:
                self.target_ball = target_ball
                self._track_ball(target_ball)
                self.tracking_stats['successful_tracks'] += 1
        else:
            # 没有检测到球，检查是否超时
            detection_timeout = self.ball_controller.detection_timeout
            if time.time() - self.last_detection_time > detection_timeout:
                self._handle_no_detection()
    
    def _track_ball(self, target_ball: dict):
        """
        跟踪目标球并控制机器人旋转
        
        Args:
            target_ball: 目标球信息
        """
        distance_to_center = target_ball['distance_to_center']
        
        # 更新统计信息
        self.tracking_stats['last_target_distance'] = float(distance_to_center)
        
        # 使用控制器检查是否已经在中心区域
        if self.ball_controller.is_ball_centered(target_ball):
            self.ball_controller.stop_robot()
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
        
        # 使用控制器计算控制输出
        control_output = self.ball_controller.calculate_control_output(target_ball)
        
        # 发送控制命令
        self.ball_controller.send_rotation_command(control_output['angular_velocity'])
        
        # 发送跟踪状态更新
        if self.socketio:
            self.socketio.emit('ball_tracking_update', {
                'target_ball': {
                    'center': [float(target_ball['center'][0]), float(target_ball['center'][1])],
                    'score': float(target_ball['score']),
                    'distance_to_center': float(distance_to_center)
                },
                'control': {
                    'error': float(control_output['error']),
                    'angular_velocity': float(control_output['angular_velocity'])
                },
                'stats': self.tracking_stats
            })
    
    def _handle_no_detection(self):
        """处理没有检测到球的情况"""
        self.ball_controller.stop_robot()
        self.target_ball = None
        self.center_message_shown = False  # 重置对准消息标志
        
        # 发送无检测状态
        if self.socketio:
            self.socketio.emit('no_ball_detected', {
                'message': '未检测到网球',
                'timeout': self.ball_controller.detection_timeout
            })
    
    def update_parameters(self, params: dict):
        """
        更新控制参数
        
        Args:
            params: 参数字典
        """
        # 委托给控制器更新参数
        return self.ball_controller.update_parameters(params)
    
    def get_current_parameters(self):
        """获取当前参数"""
        # 委托给控制器获取参数
        return self.ball_controller.get_current_parameters()
    
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
