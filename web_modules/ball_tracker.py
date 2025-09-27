#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网球跟踪Web模块
负责网页交互、状态管理和WebSocket通信
调用BallController进行实际的控制逻辑
实现完整的网球拾取状态机
"""

import time
import threading
import math
import numpy as np
from typing import List, Tuple, Optional
from enum import Enum
from .ball_controller import BallController


class PickupState(Enum):
    """拾取状态枚举"""
    IDLE = "idle"                    # 空闲状态
    SEARCHING = "searching"          # 搜索网球
    TRACKING = "tracking"            # 追踪网球到中心
    APPROACHING = "approaching"      # 前进接近网球
    BACKING_UP = "backing_up"        # 后退
    ROTATING_SEARCH = "rotating_search"  # 360度搜索
    COMPLETED = "completed"          # 拾取完成


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
        self.current_state = PickupState.IDLE
        
        # 跟踪状态
        self.target_ball = None
        self.last_detection_time = 0
        self.last_ball_area = 0  # 用于检测球是否消失
        
        # 连续帧检测机制
        self.detection_history = []  # 存储最近的检测结果
        self.max_history_frames = 3  # 保存最近3帧的检测结果
        self.required_consecutive_frames = 3  # 需要连续3帧确认状态变化
        
        # 状态计时器
        self.state_start_time = 0
        self.rotation_start_angle = 0
        self.total_rotation = 0
        
        # 超时和阈值设置
        self.pickup_timeout = 3.0        # 拾取超时时间
        self.backup_duration = 1.5       # 后退持续时间
        self.search_timeout = 10.0       # 搜索超时时间
        self.ball_lost_timeout = 1.0     # 球消失判定时间
        self.rotation_speed = 0.3        # 搜索旋转速度
        
        # 统计信息
        self.tracking_stats = {
            'total_detections': 0,
            'successful_tracks': 0,
            'center_hits': 0,
            'balls_picked': 0,
            'current_state': self.current_state.value,
            'last_target_distance': 0
        }
    
    def toggle_pickup_mode(self):
        """切换拾取模式"""
        self.pickup_mode = not self.pickup_mode
        
        if self.pickup_mode:
            self._change_state(PickupState.SEARCHING)
            self.ball_controller.reset_pid()
            message = "拾取模式已开启，开始搜索网球"
        else:
            self._change_state(PickupState.IDLE)
            self.ball_controller.stop_robot()
            message = "拾取模式已关闭"
        
        # 发送状态更新
        if self.socketio:
            self.socketio.emit('pickup_mode_update', {
                'enabled': self.pickup_mode,
                'current_state': self.current_state.value,
                'message': message
            })
        
        return {
            'status': 'success',
            'pickup_mode': self.pickup_mode,
            'current_state': self.current_state.value,
            'message': message
        }
    
    def _update_detection_history(self, has_ball: bool, target_ball: Optional[dict] = None):
        """
        更新检测历史记录
        
        Args:
            has_ball: 当前帧是否检测到球
            target_ball: 目标球信息（如果有的话）
        """
        # 添加当前帧的检测结果
        detection_data = {
            'has_ball': has_ball,
            'target_ball': target_ball,
            'timestamp': time.time()
        }
        
        self.detection_history.append(detection_data)
        
        # 保持历史记录长度不超过最大值
        if len(self.detection_history) > self.max_history_frames:
            self.detection_history.pop(0)
    
    def _check_consecutive_detection(self, expected_state: bool) -> bool:
        """
        检查是否有连续的检测结果
        
        Args:
            expected_state: 期望的检测状态（True=有球，False=无球）
            
        Returns:
            bool: 是否有连续required_consecutive_frames帧的期望状态
        """
        if len(self.detection_history) < self.required_consecutive_frames:
            return False
        
        # 检查最近的required_consecutive_frames帧
        recent_frames = self.detection_history[-self.required_consecutive_frames:]
        
        # 检查是否所有帧都符合期望状态
        for frame in recent_frames:
            if frame['has_ball'] != expected_state:
                return False
        
        return True
    
    def _reset_detection_history(self):
        """重置检测历史记录"""
        self.detection_history = []
    
    def _change_state(self, new_state: PickupState):
        """
        改变状态机状态
        
        Args:
            new_state: 新状态
        """
        if self.current_state != new_state:
            old_state = self.current_state
            self.current_state = new_state
            self.state_start_time = time.time()
            self.tracking_stats['current_state'] = new_state.value
            
            # 状态切换时重置检测历史，确保新状态从干净的历史开始
            self._reset_detection_history()
            
            print(f"状态变化: {old_state.value} -> {new_state.value}")
            
            # 发送状态变化通知
            if self.socketio:
                self.socketio.emit('state_change', {
                    'old_state': old_state.value,
                    'new_state': new_state.value,
                    'timestamp': time.time()
                })
    
    def get_pickup_status(self):
        """获取拾取模式状态"""
        return {
            'pickup_mode': self.pickup_mode,
            'current_state': self.current_state.value,
            'state_duration': time.time() - self.state_start_time if self.state_start_time > 0 else 0,
            'stats': self.tracking_stats.copy()
        }
    
    def process_detections(self, boxes: List, scores: List, frame_shape: Tuple[int, int, int]):
        """
        处理检测结果并执行状态机控制
        
        Args:
            boxes: 检测框列表 [[x1, y1, x2, y2], ...]
            scores: 置信度列表
            frame_shape: 帧尺寸 (height, width, channels)
        """
        if not self.pickup_mode or self.current_state == PickupState.IDLE:
            return
        
        # 更新控制器的屏幕尺寸
        self.ball_controller.update_screen_size(frame_shape)
        
        # 使用控制器过滤有效检测
        valid_balls = self.ball_controller.filter_valid_detections(boxes, scores)
        
        if valid_balls:
            self.last_detection_time = time.time()
            self.tracking_stats['total_detections'] += len(valid_balls)
            
            # 使用控制器选择目标球（选择最大的球）
            target_ball = self.ball_controller.select_target_ball(valid_balls, 'largest')
            
            if target_ball:
                # 更新检测历史：有球
                self._update_detection_history(True, target_ball)
                
                self.target_ball = target_ball
                self.last_ball_area = target_ball['area']
                self._process_state_machine(target_ball)
                self.tracking_stats['successful_tracks'] += 1
            else:
                # 更新检测历史：无球
                self._update_detection_history(False)
                self._process_state_machine(None)
        else:
            # 没有检测到球，更新检测历史
            self._update_detection_history(False)
            self._process_state_machine(None)
    
    def _process_state_machine(self, target_ball: Optional[dict]):
        """
        处理状态机逻辑
        
        Args:
            target_ball: 目标球信息，None表示没有检测到球
        """
        current_time = time.time()
        state_duration = current_time - self.state_start_time
        
        if self.current_state == PickupState.SEARCHING:
            self._handle_searching_state(target_ball)
            
        elif self.current_state == PickupState.TRACKING:
            self._handle_tracking_state(target_ball, state_duration)
            
        elif self.current_state == PickupState.APPROACHING:
            self._handle_approaching_state(target_ball, state_duration)
            
        elif self.current_state == PickupState.BACKING_UP:
            self._handle_backing_up_state(state_duration)
            
        elif self.current_state == PickupState.ROTATING_SEARCH:
            self._handle_rotating_search_state(target_ball, state_duration)
            
        elif self.current_state == PickupState.COMPLETED:
            self._handle_completed_state()
    
    def _handle_searching_state(self, target_ball: Optional[dict]):
        """处理搜索状态"""
        if target_ball:
            # 检查是否连续3帧都检测到球
            if self._check_consecutive_detection(True):
                # 连续检测到球，开始追踪
                self._change_state(PickupState.TRACKING)
                self._emit_message(f"连续检测到网球，开始追踪")
            else:
                # 还没有连续检测到，继续搜索但保持静止
                self.ball_controller.stop_robot()
        else:
            # 继续搜索，保持静止或缓慢旋转
            self.ball_controller.stop_robot()
    
    def _handle_tracking_state(self, target_ball: Optional[dict], state_duration: float):
        """处理追踪状态"""
        if not target_ball:
            # 检查是否连续3帧都没有检测到球
            if self._check_consecutive_detection(False):
                # 连续丢失球，回到搜索状态
                self._change_state(PickupState.SEARCHING)
                self.ball_controller.stop_robot()
                self._emit_message("网球连续丢失，重新搜索")
                return
            else:
                # 还没有连续丢失，继续保持当前状态但停止移动
                self.ball_controller.stop_robot()
                return
        
        # 检查是否已经对准中心
        if self.ball_controller.is_ball_centered(target_ball):
            # 球已对准中心，开始前进
            self._change_state(PickupState.APPROACHING)
            self.tracking_stats['center_hits'] += 1
            self._emit_message("网球已对准中心，开始前进")
            return
        
        # 继续追踪球到中心
        self._track_ball_to_center(target_ball)
        
        # 超时检查
        if state_duration > self.search_timeout:
            self._change_state(PickupState.SEARCHING)
            self.ball_controller.stop_robot()
            self._emit_message("追踪超时，重新搜索")
    
    def _handle_approaching_state(self, target_ball: Optional[dict], state_duration: float):
        """处理接近状态"""
        if not target_ball:
            # 检查是否连续3帧都没有检测到球（表示拾取成功）
            if self._check_consecutive_detection(False):
                # 连续没有检测到球，视野中没有球了，表示拾取成功
                self.ball_controller.stop_robot()
                self._change_state(PickupState.BACKING_UP)
                self.tracking_stats['balls_picked'] += 1
                self._emit_message("网球已拾取成功，开始后退")
                return
            else:
                # 还没有连续丢失，继续前进
                pass
        
        # # 检查球是否还在中心
        # if not self.ball_controller.is_ball_centered(target_ball):
        #     # 球偏离中心，重新追踪
        #     self._change_state(PickupState.TRACKING)
        #     self._emit_message("网球偏离中心，重新追踪")
        #     return
        
        # 继续前进
        self.ball_controller.send_forward_command()
        
        # 超时检查
        if state_duration > self.pickup_timeout * 2:
            self._change_state(PickupState.SEARCHING)
            self.ball_controller.stop_robot()
            self._emit_message("接近超时，重新搜索")
    
    
    def _handle_backing_up_state(self, state_duration: float):
        """处理后退状态"""
        if state_duration < self.backup_duration:
            # 继续后退
            self.ball_controller.send_backward_command()
        else:
            # 后退完成，开始360度搜索
            self.ball_controller.stop_robot()
            self._change_state(PickupState.ROTATING_SEARCH)
            self.rotation_start_angle = 0
            self.total_rotation = 0
            self._emit_message("后退完成，开始360度搜索")
    
    def _handle_rotating_search_state(self, target_ball: Optional[dict], state_duration: float):
        """处理360度搜索状态"""
        if target_ball:
            # 检查是否连续3帧都检测到球
            if self._check_consecutive_detection(True):
                # 连续检测到新球，停止搜索，开始追踪
                self.ball_controller.stop_robot()
                self._change_state(PickupState.TRACKING)
                self._emit_message("连续发现新网球，开始追踪")
                return
            else:
                # 还没有连续检测到，继续搜索
                pass
        
        # 继续旋转搜索
        self.ball_controller.send_search_rotation_command(self.rotation_speed)
        
        # 估算旋转角度（简单估算）
        rotation_increment = self.rotation_speed * 0.1  # 假设每100ms调用一次
        self.total_rotation += rotation_increment
        
        # 检查是否完成一圈
        if self.total_rotation >= 2 * math.pi or state_duration > self.search_timeout:
            # 完成搜索
            self.ball_controller.stop_robot()
            self._change_state(PickupState.COMPLETED)
            self._emit_message("360度搜索完成，拾取任务结束")
    
    def _handle_completed_state(self):
        """处理完成状态"""
        # 保持停止状态
        self.ball_controller.stop_robot()
        # 可以选择自动关闭拾取模式或等待用户操作
    
    def _track_ball_to_center(self, target_ball: dict):
        """
        跟踪目标球并控制机器人旋转到中心
        
        Args:
            target_ball: 目标球信息
        """
        distance_to_center = target_ball['distance_to_center']
        
        # 更新统计信息
        self.tracking_stats['last_target_distance'] = float(distance_to_center)
        
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
                    'distance_to_center': float(distance_to_center),
                    'area': float(target_ball['area'])
                },
                'control': {
                    'error': float(control_output['error']),
                    'angular_velocity': float(control_output['angular_velocity'])
                },
                'state': self.current_state.value,
                'stats': self.tracking_stats
            })
    
    def _emit_message(self, message: str):
        """
        发送消息到前端
        
        Args:
            message: 要发送的消息
        """
        print(f"[{self.current_state.value}] {message}")
        if self.socketio:
            self.socketio.emit('pickup_status_update', {
                'state': self.current_state.value,
                'message': message,
                'timestamp': time.time(),
                'stats': self.tracking_stats
            })
    
    def update_parameters(self, params: dict):
        """
        更新控制参数
        
        Args:
            params: 参数字典
        """
        # 更新状态机参数
        if 'pickup_timeout' in params:
            self.pickup_timeout = max(1.0, min(10.0, params['pickup_timeout']))
        
        if 'backup_duration' in params:
            self.backup_duration = max(0.5, min(5.0, params['backup_duration']))
        
        if 'search_timeout' in params:
            self.search_timeout = max(5.0, min(30.0, params['search_timeout']))
        
        if 'rotation_speed' in params:
            self.rotation_speed = max(0.1, min(1.0, params['rotation_speed']))
        
        # 委托给控制器更新其他参数
        return self.ball_controller.update_parameters(params)
    
    def get_current_parameters(self):
        """获取当前参数"""
        # 获取控制器参数
        controller_params = self.ball_controller.get_current_parameters()
        
        # 添加状态机参数
        controller_params.update({
            'pickup_timeout': self.pickup_timeout,
            'backup_duration': self.backup_duration,
            'search_timeout': self.search_timeout,
            'rotation_speed': self.rotation_speed,
            'ball_lost_timeout': self.ball_lost_timeout
        })
        
        return controller_params
    
    def reset_statistics(self):
        """重置统计信息"""
        self.tracking_stats = {
            'total_detections': 0,
            'successful_tracks': 0,
            'center_hits': 0,
            'balls_picked': 0,
            'current_state': self.current_state.value,
            'last_target_distance': 0
        }
        
        return {
            'status': 'success',
            'message': '统计信息已重置'
        }
    
    def emergency_stop(self):
        """紧急停止"""
        self.ball_controller.stop_robot()
        self._change_state(PickupState.IDLE)
        self.pickup_mode = False
        
        if self.socketio:
            self.socketio.emit('emergency_stop', {
                'message': '紧急停止已执行',
                'timestamp': time.time()
            })
        
        return {
            'status': 'success',
            'message': '紧急停止已执行'
        }
    
    def restart_pickup(self):
        """重启拾取过程"""
        if self.pickup_mode:
            self._change_state(PickupState.SEARCHING)
            self.ball_controller.reset_pid()
            self._emit_message("重启拾取过程，开始搜索")
            
            return {
                'status': 'success',
                'message': '拾取过程已重启'
            }
        else:
            return {
                'status': 'error',
                'message': '拾取模式未开启'
            }

