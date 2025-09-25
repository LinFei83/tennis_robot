#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WheelTec机器人控制类
将ROS C++节点转换为普通Python程序
"""

import math
import time
import struct
import threading
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
import serial

from .wheeltec_robot_config import WheelTecRobotConfig, CallbackConfig, Constants


@dataclass
class VelPosData:
    """速度、位置数据结构"""
    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0


@dataclass
class IMUData:
    """IMU数据结构"""
    accele_x_data: int = 0
    accele_y_data: int = 0
    accele_z_data: int = 0
    gyros_x_data: int = 0
    gyros_y_data: int = 0
    gyros_z_data: int = 0


@dataclass
class QuaternionData:
    """四元数数据结构"""
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class IMUSensorData:
    """IMU传感器数据结构"""
    orientation: QuaternionData = field(default_factory=QuaternionData)
    angular_velocity: VelPosData = field(default_factory=VelPosData)
    linear_acceleration: VelPosData = field(default_factory=VelPosData)


@dataclass
class OdomData:
    """里程计数据结构"""
    position: VelPosData = field(default_factory=VelPosData)
    orientation: QuaternionData = field(default_factory=QuaternionData)
    linear_velocity: VelPosData = field(default_factory=VelPosData)
    angular_velocity: VelPosData = field(default_factory=VelPosData)
    timestamp: float = 0.0


class QuaternionSolution:
    """四元数解算类"""
    
    def __init__(self, sampling_freq: float = 20.0):
        self.sampling_freq = sampling_freq
        self.two_kp = Constants.TWO_KP
        self.two_ki = Constants.TWO_KI
        self.q0 = 1.0
        self.q1 = 0.0
        self.q2 = 0.0
        self.q3 = 0.0
        self.integral_fbx = 0.0
        self.integral_fby = 0.0
        self.integral_fbz = 0.0
    
    @staticmethod
    def inv_sqrt(number: float) -> float:
        """平方根倒数计算"""
        if number <= 0:
            return 0.0
        return 1.0 / math.sqrt(number)
    
    def update(self, gx: float, gy: float, gz: float, 
               ax: float, ay: float, az: float) -> QuaternionData:
        """四元数解算更新"""
        # 检查加速度计数据有效性
        if ax == 0.0 and ay == 0.0 and az == 0.0:
            pass
        else:
            # 加速度计数据归一化
            recip_norm = self.inv_sqrt(ax * ax + ay * ay + az * az)
            ax *= recip_norm
            ay *= recip_norm
            az *= recip_norm
            
            # 四元数转换为方向余弦矩阵第三行
            halfvx = self.q1 * self.q3 - self.q0 * self.q2
            halfvy = self.q0 * self.q1 + self.q2 * self.q3
            halfvz = self.q0 * self.q0 - 0.5 + self.q3 * self.q3
            
            # 计算误差
            halfex = ay * halfvz - az * halfvy
            halfey = az * halfvx - ax * halfvz
            halfez = ax * halfvy - ay * halfvx
            
            # 积分反馈
            if self.two_ki > 0.0:
                self.integral_fbx += self.two_ki * halfex * (1.0 / self.sampling_freq)
                self.integral_fby += self.two_ki * halfey * (1.0 / self.sampling_freq)
                self.integral_fbz += self.two_ki * halfez * (1.0 / self.sampling_freq)
                gx += self.integral_fbx
                gy += self.integral_fby
                gz += self.integral_fbz
            else:
                self.integral_fbx = 0.0
                self.integral_fby = 0.0
                self.integral_fbz = 0.0
            
            # 比例反馈
            gx += self.two_kp * halfex
            gy += self.two_kp * halfey
            gz += self.two_kp * halfez
        
        # 积分四元数变化率
        gx *= 0.5 * (1.0 / self.sampling_freq)
        gy *= 0.5 * (1.0 / self.sampling_freq)
        gz *= 0.5 * (1.0 / self.sampling_freq)
        
        qa = self.q0
        qb = self.q1
        qc = self.q2
        
        self.q0 += (-qb * gx - qc * gy - self.q3 * gz)
        self.q1 += (qa * gx + qc * gz - self.q3 * gy)
        self.q2 += (qa * gy - qb * gz + self.q3 * gx)
        self.q3 += (qa * gz + qb * gy - qc * gx)
        
        # 四元数归一化
        recip_norm = self.inv_sqrt(self.q0 * self.q0 + self.q1 * self.q1 + 
                                  self.q2 * self.q2 + self.q3 * self.q3)
        self.q0 *= recip_norm
        self.q1 *= recip_norm
        self.q2 *= recip_norm
        self.q3 *= recip_norm
        
        return QuaternionData(w=self.q0, x=self.q1, y=self.q2, z=self.q3)


class WheelTecRobot:
    """WheelTec机器人控制类"""
    
    def __init__(self, config: WheelTecRobotConfig, callbacks: CallbackConfig):
        self.config = config
        self.callbacks = callbacks
        
        # 初始化数据结构
        self.robot_pos = VelPosData()
        self.robot_vel = VelPosData()
        self.imu_data = IMUData()
        self.imu_sensor = IMUSensorData()
        self.power_voltage = 0.0
        
        # 时间相关
        self.last_time = 0.0
        self.sampling_time = 0.0
        
        # 串口对象
        self.serial_port: Optional[serial.Serial] = None
        
        # 四元数解算器
        self.quaternion_solver = QuaternionSolution(config.sampling_freq)
        
        # 控制标志
        self.running = False
        self.control_thread: Optional[threading.Thread] = None
        
        # 数据缓冲区
        self.receive_buffer = bytearray(Constants.RECEIVE_DATA_SIZE)
        self.send_buffer = bytearray(Constants.SEND_DATA_SIZE)
        
        self._init_serial()
    
    def _init_serial(self):
        """初始化串口"""
        try:
            self.serial_port = serial.Serial(
                port=self.config.usart_port_name,
                baudrate=self.config.serial_baud_rate,
                timeout=2.0
            )
            self.serial_port.flushInput()
            self._log_info("串口开启成功")
        except Exception as e:
            self._log_error(f"无法打开串口: {e}")
    
    def _log_info(self, message: str):
        """记录信息"""
        if self.callbacks.info_callback:
            self.callbacks.info_callback(message)
        else:
            print(f"[INFO] {message}")
    
    def _log_error(self, message: str):
        """记录错误"""
        if self.callbacks.error_callback:
            self.callbacks.error_callback(message)
        else:
            print(f"[ERROR] {message}")
    
    def set_velocity(self, linear_x: float, linear_y: float, angular_z: float):
        """设置机器人速度"""
        if not self.serial_port or not self.serial_port.is_open:
            self._log_error("串口未打开")
            return
        
        # 构造发送数据包
        self.send_buffer[0] = Constants.FRAME_HEADER
        self.send_buffer[1] = 0  # 预留位
        self.send_buffer[2] = 0  # 预留位
        
        # X轴线速度
        x_vel_int = int(linear_x * 1000)
        self.send_buffer[3] = (x_vel_int >> 8) & 0xFF
        self.send_buffer[4] = x_vel_int & 0xFF
        
        # Y轴线速度
        y_vel_int = int(linear_y * 1000)
        self.send_buffer[5] = (y_vel_int >> 8) & 0xFF
        self.send_buffer[6] = y_vel_int & 0xFF
        
        # Z轴角速度
        z_vel_int = int(angular_z * 1000)
        self.send_buffer[7] = (z_vel_int >> 8) & 0xFF
        self.send_buffer[8] = z_vel_int & 0xFF
        
        # BCC校验
        self.send_buffer[9] = self._calculate_checksum(9, True)
        self.send_buffer[10] = Constants.FRAME_TAIL
        
        try:
            self.serial_port.write(self.send_buffer)
        except Exception as e:
            self._log_error(f"发送数据失败: {e}")
    
    def _calculate_checksum(self, count: int, is_send: bool) -> int:
        """计算BCC校验"""
        checksum = 0
        buffer = self.send_buffer if is_send else self.receive_buffer
        
        for i in range(count):
            checksum ^= buffer[i]
        
        return checksum
    
    def _imu_trans(self, data_high: int, data_low: int) -> int:
        """IMU数据转换"""
        return (data_high << 8) | data_low
    
    def _odom_trans(self, data_high: int, data_low: int) -> float:
        """里程计数据转换"""
        transition_16 = (data_high << 8) | data_low
        return (transition_16 // 1000) + (transition_16 % 1000) * 0.001
    
    def _get_sensor_data(self) -> bool:
        """获取传感器数据"""
        if not self.serial_port or not self.serial_port.is_open:
            return False
        
        try:
            # 逐字节读取数据
            data = self.serial_port.read(1)
            if not data:
                return False
            
            byte_data = data[0]
            
            # 简化的帧同步逻辑
            if byte_data == Constants.FRAME_HEADER:
                # 读取完整数据包
                remaining_data = self.serial_port.read(Constants.RECEIVE_DATA_SIZE - 1)
                if len(remaining_data) != Constants.RECEIVE_DATA_SIZE - 1:
                    return False
                
                self.receive_buffer[0] = byte_data
                self.receive_buffer[1:] = remaining_data
                
                # 验证帧尾
                if self.receive_buffer[23] != Constants.FRAME_TAIL:
                    return False
                
                # BCC校验
                if self.receive_buffer[22] != self._calculate_checksum(22, False):
                    return False
                
                # 解析数据
                self._parse_sensor_data()
                return True
        
        except Exception as e:
            self._log_error(f"读取传感器数据失败: {e}")
        
        return False
    
    def _parse_sensor_data(self):
        """解析传感器数据"""
        # 解析速度数据
        self.robot_vel.X = self._odom_trans(self.receive_buffer[2], self.receive_buffer[3])
        self.robot_vel.Y = self._odom_trans(self.receive_buffer[4], self.receive_buffer[5])
        self.robot_vel.Z = self._odom_trans(self.receive_buffer[6], self.receive_buffer[7])
        
        # 解析IMU数据
        self.imu_data.accele_x_data = self._imu_trans(self.receive_buffer[8], self.receive_buffer[9])
        self.imu_data.accele_y_data = self._imu_trans(self.receive_buffer[10], self.receive_buffer[11])
        self.imu_data.accele_z_data = self._imu_trans(self.receive_buffer[12], self.receive_buffer[13])
        self.imu_data.gyros_x_data = self._imu_trans(self.receive_buffer[14], self.receive_buffer[15])
        self.imu_data.gyros_y_data = self._imu_trans(self.receive_buffer[16], self.receive_buffer[17])
        self.imu_data.gyros_z_data = self._imu_trans(self.receive_buffer[18], self.receive_buffer[19])
        
        # 转换IMU数据为国际单位
        self.imu_sensor.linear_acceleration.X = self.imu_data.accele_x_data / Constants.ACCEL_RATIO
        self.imu_sensor.linear_acceleration.Y = self.imu_data.accele_y_data / Constants.ACCEL_RATIO
        self.imu_sensor.linear_acceleration.Z = self.imu_data.accele_z_data / Constants.ACCEL_RATIO
        
        self.imu_sensor.angular_velocity.X = self.imu_data.gyros_x_data * Constants.GYROSCOPE_RATIO
        self.imu_sensor.angular_velocity.Y = self.imu_data.gyros_y_data * Constants.GYROSCOPE_RATIO
        self.imu_sensor.angular_velocity.Z = self.imu_data.gyros_z_data * Constants.GYROSCOPE_RATIO
        
        # 解析电压数据
        voltage_raw = (self.receive_buffer[20] << 8) | self.receive_buffer[21]
        self.power_voltage = (voltage_raw // 1000) + (voltage_raw % 1000) * 0.001
    
    def _update_odometry(self):
        """更新里程计"""
        current_time = time.time()
        if self.last_time == 0:
            self.last_time = current_time
            return
        
        self.sampling_time = current_time - self.last_time
        
        # 里程计误差修正
        corrected_vel_x = self.robot_vel.X * self.config.odom_x_scale
        corrected_vel_y = self.robot_vel.Y * self.config.odom_y_scale
        
        if self.robot_vel.Z >= 0:
            corrected_vel_z = self.robot_vel.Z * self.config.odom_z_scale_positive
        else:
            corrected_vel_z = self.robot_vel.Z * self.config.odom_z_scale_negative
        
        # 计算位移（里程计积分）
        cos_z = math.cos(self.robot_pos.Z)
        sin_z = math.sin(self.robot_pos.Z)
        
        self.robot_pos.X += (corrected_vel_x * cos_z - corrected_vel_y * sin_z) * self.sampling_time
        self.robot_pos.Y += (corrected_vel_x * sin_z + corrected_vel_y * cos_z) * self.sampling_time
        self.robot_pos.Z += corrected_vel_z * self.sampling_time
        
        self.last_time = current_time
    
    def _update_quaternion(self):
        """更新四元数"""
        self.imu_sensor.orientation = self.quaternion_solver.update(
            self.imu_sensor.angular_velocity.X,
            self.imu_sensor.angular_velocity.Y,
            self.imu_sensor.angular_velocity.Z,
            self.imu_sensor.linear_acceleration.X,
            self.imu_sensor.linear_acceleration.Y,
            self.imu_sensor.linear_acceleration.Z
        )
    
    def get_odometry(self) -> OdomData:
        """获取里程计数据（相对于起点的位置和姿态）"""
        # 将Z轴角度转换为四元数
        odom_quat = self._yaw_to_quaternion(self.robot_pos.Z)
        
        return OdomData(
            position=VelPosData(X=self.robot_pos.X, Y=self.robot_pos.Y, Z=0.0),
            orientation=odom_quat,
            linear_velocity=VelPosData(X=self.robot_vel.X, Y=self.robot_vel.Y, Z=0.0),
            angular_velocity=VelPosData(X=0.0, Y=0.0, Z=self.robot_vel.Z),
            timestamp=time.time()
        )
    
    def get_imu_data(self) -> IMUSensorData:
        """获取IMU数据"""
        return IMUSensorData(
            orientation=self.imu_sensor.orientation,
            angular_velocity=self.imu_sensor.angular_velocity,
            linear_acceleration=self.imu_sensor.linear_acceleration
        )
    
    def get_voltage(self) -> float:
        """获取电压数据"""
        return self.power_voltage
    
    @staticmethod
    def _yaw_to_quaternion(yaw: float) -> QuaternionData:
        """将偏航角转换为四元数"""
        half_yaw = yaw * 0.5
        return QuaternionData(
            w=math.cos(half_yaw),
            x=0.0,
            y=0.0,
            z=math.sin(half_yaw)
        )
    
    def _publish_data(self):
        """发布数据到回调函数"""
        # 发布里程计数据
        if self.callbacks.odom_callback:
            odom_data = self.get_odometry()
            odom_dict = {
                'position': {'x': odom_data.position.X, 'y': odom_data.position.Y, 'z': odom_data.position.Z},
                'orientation': {'w': odom_data.orientation.w, 'x': odom_data.orientation.x, 
                              'y': odom_data.orientation.y, 'z': odom_data.orientation.z},
                'linear_velocity': {'x': odom_data.linear_velocity.X, 'y': odom_data.linear_velocity.Y, 'z': odom_data.linear_velocity.Z},
                'angular_velocity': {'x': odom_data.angular_velocity.X, 'y': odom_data.angular_velocity.Y, 'z': odom_data.angular_velocity.Z},
                'timestamp': odom_data.timestamp
            }
            self.callbacks.odom_callback(odom_dict)
        
        # 发布IMU数据
        if self.callbacks.imu_callback:
            imu_data = self.get_imu_data()
            imu_dict = {
                'orientation': {'w': imu_data.orientation.w, 'x': imu_data.orientation.x,
                              'y': imu_data.orientation.y, 'z': imu_data.orientation.z},
                'angular_velocity': {'x': imu_data.angular_velocity.X, 'y': imu_data.angular_velocity.Y, 'z': imu_data.angular_velocity.Z},
                'linear_acceleration': {'x': imu_data.linear_acceleration.X, 'y': imu_data.linear_acceleration.Y, 'z': imu_data.linear_acceleration.Z}
            }
            self.callbacks.imu_callback(imu_dict)
        
        # 发布电压数据
        if self.callbacks.voltage_callback:
            self.callbacks.voltage_callback(self.get_voltage())
    
    def _control_loop(self):
        """控制循环"""
        while self.running:
            if self._get_sensor_data():
                self._update_odometry()
                self._update_quaternion()
                self._publish_data()
            
            time.sleep(0.01)  # 100Hz控制频率
    
    def start(self):
        """启动机器人控制"""
        if self.running:
            self._log_error("机器人已在运行中")
            return
        
        # 检查串口状态，如果未打开则重新初始化
        if not self.serial_port or not self.serial_port.is_open:
            self._log_info("串口未打开，正在重新初始化...")
            self._init_serial()
            
            # 再次检查串口是否成功打开
            if not self.serial_port or not self.serial_port.is_open:
                self._log_error("串口初始化失败，无法启动")
                return
        
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        self._log_info("机器人控制已启动")
    
    def stop(self):
        """停止机器人控制"""
        if not self.running:
            return
        
        self.running = False
        
        # 发送停止命令
        self.set_velocity(0.0, 0.0, 0.0)
        
        if self.control_thread:
            self.control_thread.join(timeout=1.0)
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self._log_info("机器人控制已停止")
    
    def reset_odometry(self):
        """重置里程计"""
        self.robot_pos = VelPosData()
        self.last_time = 0.0
        self._log_info("里程计已重置")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
