#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WheelTec机器人配置文件
基于launch/include/base_serial.launch的配置参数
"""

import dataclasses
from typing import Optional, Callable, Any


@dataclasses.dataclass
class WheelTecRobotConfig:
    """WheelTec机器人配置类"""
    
    # 串口通信配置
    usart_port_name: str = "/dev/wheeltec_controller"
    serial_baud_rate: int = 115200
    

    # 里程计修正参数
    odom_x_scale: float = 1.0
    odom_y_scale: float = 1.0
    odom_z_scale_positive: float = 1.0
    odom_z_scale_negative: float = 1.0
    
    # 功能开关
    smoother: bool = False  # 是否使用平滑算法
    
    # 采样频率
    sampling_freq: float = 20.0
    
    # 协方差矩阵（用于里程计数据）
    odom_pose_covariance: list = dataclasses.field(default_factory=lambda: [
        1e-3,    0,    0,   0,   0,    0,
           0, 1e-3,    0,   0,   0,    0,
           0,    0,  1e6,   0,   0,    0,
           0,    0,    0, 1e6,   0,    0,
           0,    0,    0,   0, 1e6,    0,
           0,    0,    0,   0,   0,  1e3
    ])
    
    odom_pose_covariance2: list = dataclasses.field(default_factory=lambda: [
        1e-9,    0,    0,   0,   0,    0,
           0, 1e-3, 1e-9,   0,   0,    0,
           0,    0,  1e6,   0,   0,    0,
           0,    0,    0, 1e6,   0,    0,
           0,    0,    0,   0, 1e6,    0,
           0,    0,    0,   0,   0, 1e-9
    ])
    
    odom_twist_covariance: list = dataclasses.field(default_factory=lambda: [
        1e-3,    0,    0,   0,   0,    0,
           0, 1e-3,    0,   0,   0,    0,
           0,    0,  1e6,   0,   0,    0,
           0,    0,    0, 1e6,   0,   0,
           0,    0,    0,   0, 1e6,    0,
           0,    0,    0,   0,   0,  1e3
    ])
    
    odom_twist_covariance2: list = dataclasses.field(default_factory=lambda: [
        1e-9,    0,    0,   0,   0,    0,
           0, 1e-3, 1e-9,   0,   0,    0,
           0,    0,  1e6,   0,   0,    0,
           0,    0,    0, 1e6,   0,    0,
           0,    0,    0,   0, 1e6,    0,
           0,    0,    0,   0,   0, 1e-9
    ])


@dataclasses.dataclass
class CallbackConfig:
    """回调函数配置类"""
    
    # 速度命令回调
    cmd_vel_callback: Optional[Callable[[dict], None]] = None
    
    # 数据发布回调
    odom_callback: Optional[Callable[[dict], None]] = None
    imu_callback: Optional[Callable[[dict], None]] = None
    voltage_callback: Optional[Callable[[float], None]] = None
    
    # 错误处理回调
    error_callback: Optional[Callable[[str], None]] = None
    info_callback: Optional[Callable[[str], None]] = None


# 常量定义
class Constants:
    """常量定义类"""
    
    # 数据校验标志位
    SEND_DATA_CHECK = 1
    READ_DATA_CHECK = 0
    
    # 帧头帧尾
    FRAME_HEADER = 0x7B
    FRAME_TAIL = 0x7D
    
    # 数据包大小
    RECEIVE_DATA_SIZE = 24
    SEND_DATA_SIZE = 11
    
    # 数学常量
    PI = 3.1415926
    
    # IMU转换比率
    GYROSCOPE_RATIO = 0.00026644  # 陀螺仪原始数据转换为弧度单位
    ACCEL_RATIO = 1671.84  # 加速度计原始数据转换为m/s^2单位
    
    # 四元数解算参数
    TWO_KP = 1.0  # 比例增益
    TWO_KI = 0.0  # 积分增益
