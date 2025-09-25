#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器人控制模块
负责机器人的初始化、控制和状态管理
"""

from base_robot.wheeltec_robot import WheelTecRobot
from base_robot.wheeltec_robot_config import WheelTecRobotConfig, CallbackConfig


class RobotController:
    """机器人控制器"""
    
    def __init__(self, socketio=None):
        """
        初始化机器人控制器
        
        Args:
            socketio: WebSocket对象，用于发送状态更新
        """
        self.socketio = socketio
        
        # 机器人相关
        self.robot = None
        self.robot_config = None
        self.robot_callbacks = None
        self.robot_running = False
        
        # 当前速度状态
        self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        
        # 速度设置
        self.base_speed_linear = 0.3  # 基础线速度 m/s
        self.base_speed_angular = 0.3  # 基础角速度 rad/s
        self.speed_multiplier = 1.0  # 速度倍数
        self.min_speed_multiplier = 0.1  # 最小速度倍数
        self.max_speed_multiplier = 3.0  # 最大速度倍数
        self.speed_step = 0.1  # 速度调节步长
        
        # 初始化机器人
        self._init_robot()
    
    def _init_robot(self):
        """初始化机器人控制"""
        try:
            self.robot_config = WheelTecRobotConfig(
                usart_port_name="/dev/stm32_base",
                serial_baud_rate=115200
            )
            
            self.robot_callbacks = CallbackConfig(
                odom_callback=self._odom_callback,
                imu_callback=self._imu_callback,
                voltage_callback=self._voltage_callback,
                error_callback=self._error_callback,
                info_callback=self._info_callback
            )
            
            self.robot = WheelTecRobot(self.robot_config, self.robot_callbacks)
            print("机器人控制器初始化成功")
            
            # 自动启动机器人
            try:
                self.robot.start()
                self.robot_running = True
                print("机器人自动启动成功")
            except Exception as start_e:
                print(f"机器人自动启动失败: {start_e}")
        except Exception as e:
            print(f"机器人初始化失败: {e}")
    
    def start_robot(self):
        """启动机器人"""
        try:
            if self.robot_running:
                return {'status': 'error', 'message': '机器人已在运行中'}
            
            if not self.robot:
                return {'status': 'error', 'message': '机器人未初始化'}
            
            # 启动机器人（内部会自动处理串口重连）
            self.robot.start()
            self.robot_running = True
            return {'status': 'success', 'message': '机器人已启动'}
            
        except Exception as e:
            self.robot_running = False  # 确保状态一致
            return {'status': 'error', 'message': f'机器人启动失败: {str(e)}'}
    
    def stop_robot(self):
        """停止机器人"""
        try:
            if not self.robot_running:
                return {'status': 'error', 'message': '机器人未运行'}
            
            if not self.robot:
                self.robot_running = False
                return {'status': 'error', 'message': '机器人未初始化'}
            
            # 先停止运动
            try:
                self.robot.set_velocity(0.0, 0.0, 0.0)
            except Exception as vel_e:
                print(f"停止运动失败: {vel_e}")
            
            # 停止机器人控制
            self.robot.stop()
            self.robot_running = False
            self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
            
            return {'status': 'success', 'message': '机器人已停止'}
            
        except Exception as e:
            self.robot_running = False  # 确保状态一致
            self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
            return {'status': 'error', 'message': f'机器人停止失败: {str(e)}'}
    
    def set_velocity(self, linear_x=0.0, linear_y=0.0, angular_z=0.0):
        """设置机器人速度"""
        try:
            if self.robot_running and self.robot:
                self.robot.set_velocity(linear_x, linear_y, angular_z)
                self.current_velocity = {'x': linear_x, 'y': linear_y, 'z': angular_z}
                return {'status': 'success', 'velocity': self.current_velocity}
            else:
                return {'status': 'error', 'message': '机器人未运行'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def handle_control_command(self, command):
        """处理机器人控制命令"""
        try:
            if not (self.robot_running and self.robot):
                return {'status': 'error', 'message': '机器人未运行'}
            
            # 计算当前实际速度值
            speed_linear = self.base_speed_linear * self.speed_multiplier
            speed_angular = self.base_speed_angular * self.speed_multiplier
            
            if command == 'forward':
                self.robot.set_velocity(speed_linear, 0.0, 0.0)
                self.current_velocity = {'x': speed_linear, 'y': 0.0, 'z': 0.0}
            elif command == 'backward':
                self.robot.set_velocity(-speed_linear, 0.0, 0.0)
                self.current_velocity = {'x': -speed_linear, 'y': 0.0, 'z': 0.0}
            elif command == 'left_translate':  # A键：左平移
                self.robot.set_velocity(0.0, speed_linear, 0.0)
                self.current_velocity = {'x': 0.0, 'y': speed_linear, 'z': 0.0}
            elif command == 'right_translate':  # D键：右平移
                self.robot.set_velocity(0.0, -speed_linear, 0.0)
                self.current_velocity = {'x': 0.0, 'y': -speed_linear, 'z': 0.0}
            elif command == 'rotate_left':  # Q键：逆时针旋转
                self.robot.set_velocity(0.0, 0.0, speed_angular)
                self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': speed_angular}
            elif command == 'rotate_right':  # E键：顺时针旋转
                self.robot.set_velocity(0.0, 0.0, -speed_angular)
                self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': -speed_angular}
            elif command == 'speed_up':  # C键：加速
                return self.increase_speed()
            elif command == 'speed_down':  # Z键：减速
                return self.decrease_speed()
            elif command == 'stop':
                self.robot.set_velocity(0.0, 0.0, 0.0)
                self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
            
            return {'status': 'success', 'velocity': self.current_velocity, 'speed_multiplier': self.speed_multiplier}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def increase_speed(self):
        """增加速度"""
        old_multiplier = self.speed_multiplier
        self.speed_multiplier = min(self.speed_multiplier + self.speed_step, self.max_speed_multiplier)
        
        if self.speed_multiplier != old_multiplier:
            message = f'速度增加到 {self.speed_multiplier:.1f}x'
        else:
            message = f'已达到最大速度 {self.max_speed_multiplier:.1f}x'
        
        return {
            'status': 'success',
            'message': message,
            'speed_multiplier': self.speed_multiplier,
            'velocity': self.current_velocity
        }
    
    def decrease_speed(self):
        """减少速度"""
        old_multiplier = self.speed_multiplier
        self.speed_multiplier = max(self.speed_multiplier - self.speed_step, self.min_speed_multiplier)
        
        if self.speed_multiplier != old_multiplier:
            message = f'速度减少到 {self.speed_multiplier:.1f}x'
        else:
            message = f'已达到最小速度 {self.min_speed_multiplier:.1f}x'
        
        return {
            'status': 'success',
            'message': message,
            'speed_multiplier': self.speed_multiplier,
            'velocity': self.current_velocity
        }
    
    def get_status(self):
        """获取机器人状态"""
        return {
            'running': self.robot_running,
            'velocity': self.current_velocity,
            'speed_multiplier': self.speed_multiplier
        }
    
    def cleanup(self):
        """清理机器人资源"""
        try:
            if self.robot_running and self.robot:
                self.robot.set_velocity(0.0, 0.0, 0.0)
                self.robot.stop()
            print("机器人资源清理完成")
        except Exception as e:
            print(f"机器人资源清理错误: {e}")
    
    # 机器人回调函数
    def _odom_callback(self, data):
        """里程计回调"""
        if self.socketio:
            self.socketio.emit('odom_update', data)
    
    def _imu_callback(self, data):
        """IMU回调"""
        if self.socketio:
            self.socketio.emit('imu_update', data)
    
    def _voltage_callback(self, voltage):
        """电压回调"""
        if self.socketio:
            self.socketio.emit('voltage_update', {'voltage': voltage})
    
    def _error_callback(self, error_msg):
        """错误回调"""
        print(f"机器人错误: {error_msg}")
        if self.socketio:
            self.socketio.emit('robot_error', {'message': error_msg})
    
    def _info_callback(self, info_msg):
        """信息回调"""
        print(f"机器人信息: {info_msg}")
