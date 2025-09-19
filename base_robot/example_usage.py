#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WheelTec机器人使用示例
展示如何使用转换后的Python组件
"""

import time
import math
from wheeltec_robot import WheelTecRobot
from wheeltec_robot_config import WheelTecRobotConfig, CallbackConfig


def odom_callback(odom_data: dict):
    """里程计数据回调函数"""
    pos = odom_data['position']
    orient = odom_data['orientation']
    lin_vel = odom_data['linear_velocity']
    ang_vel = odom_data['angular_velocity']
    
    print(f"位置: x={pos['x']:.3f}, y={pos['y']:.3f}")
    print(f"姿态: w={orient['w']:.3f}, z={orient['z']:.3f}")
    print(f"线速度: x={lin_vel['x']:.3f}, y={lin_vel['y']:.3f}")
    print(f"角速度: z={ang_vel['z']:.3f}")
    print("-" * 50)


def imu_callback(imu_data: dict):
    """IMU数据回调函数"""
    orient = imu_data['orientation']
    ang_vel = imu_data['angular_velocity']
    lin_acc = imu_data['linear_acceleration']
    
    print(f"IMU姿态: w={orient['w']:.3f}, x={orient['x']:.3f}, y={orient['y']:.3f}, z={orient['z']:.3f}")
    print(f"角速度: x={ang_vel['x']:.3f}, y={ang_vel['y']:.3f}, z={ang_vel['z']:.3f}")
    print(f"线加速度: x={lin_acc['x']:.3f}, y={lin_acc['y']:.3f}, z={lin_acc['z']:.3f}")


def voltage_callback(voltage: float):
    """电压数据回调函数"""
    print(f"电池电压: {voltage:.2f}V")


def error_callback(error_msg: str):
    """错误回调函数"""
    print(f"错误: {error_msg}")


def info_callback(info_msg: str):
    """信息回调函数"""
    print(f"信息: {info_msg}")


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建配置
    config = WheelTecRobotConfig(
        usart_port_name="COM12",
        serial_baud_rate=115200,
        odom_x_scale=1.0,
        odom_y_scale=1.0
    )
    
    # 创建回调配置
    callbacks = CallbackConfig(
        odom_callback=odom_callback,
        imu_callback=imu_callback,
        voltage_callback=voltage_callback,
        error_callback=error_callback,
        info_callback=info_callback
    )
    
    # 使用上下文管理器确保资源正确释放
    with WheelTecRobot(config, callbacks) as robot:
        # 启动机器人
        robot.start()
        
        # 等待系统初始化
        time.sleep(1.0)
        
        # 控制机器人前进
        print("机器人前进...")
        robot.set_velocity(0.0, 0.2, 0.0)  # 0.2 m/s前进
        time.sleep(5.0)
        
        # 控制机器人转弯
        print("机器人转弯...")
        robot.set_velocity(0.1, 0.0, 0.5)  # 慢速前进同时转弯
        time.sleep(2.0)
        
        # 停止机器人
        print("机器人停止...")
        robot.set_velocity(0.0, 0.0, 0.0)
        time.sleep(1.0)
        
        # 获取当前里程计数据
        odom_data = robot.get_odometry()
        print(f"最终位置: x={odom_data.position.X:.3f}, y={odom_data.position.Y:.3f}")
        print(f"最终姿态角: {odom_data.position.Z:.3f} rad")


def example_circle_motion():
    """圆形运动示例"""
    print("=== 圆形运动示例 ===")
    
    config = WheelTecRobotConfig()
    callbacks = CallbackConfig(
        odom_callback=lambda data: print(f"位置: ({data['position']['x']:.2f}, {data['position']['y']:.2f})"),
        error_callback=error_callback,
        info_callback=info_callback
    )
    
    with WheelTecRobot(config, callbacks) as robot:
        robot.start()
        time.sleep(1.0)
        
        # 重置里程计
        robot.reset_odometry()
        
        # 执行圆形运动
        print("开始圆形运动...")
        linear_speed = 0.2  # m/s
        angular_speed = 0.3  # rad/s
        duration = 10.0  # 秒
        
        start_time = time.time()
        while time.time() - start_time < duration:
            robot.set_velocity(linear_speed, 0.0, angular_speed)
            time.sleep(0.1)
        
        # 停止
        robot.set_velocity(0.0, 0.0, 0.0)
        
        # 获取最终位置
        final_odom = robot.get_odometry()
        print(f"圆形运动完成，最终位置: ({final_odom.position.X:.2f}, {final_odom.position.Y:.2f})")


def example_data_collection():
    """数据采集示例"""
    print("=== 数据采集示例 ===")
    
    # 数据存储列表
    odom_history = []
    imu_history = []
    voltage_history = []
    
    def collect_odom(data):
        odom_history.append(data.copy())
    
    def collect_imu(data):
        imu_history.append(data.copy())
    
    def collect_voltage(voltage):
        voltage_history.append(voltage)
    
    config = WheelTecRobotConfig()
    callbacks = CallbackConfig(
        odom_callback=collect_odom,
        imu_callback=collect_imu,
        voltage_callback=collect_voltage,
        error_callback=error_callback,
        info_callback=info_callback
    )
    
    with WheelTecRobot(config, callbacks) as robot:
        robot.start()
        
        # 采集数据10秒
        print("开始数据采集...")
        robot.set_velocity(0.1, 0.0, 0.2)  # 慢速运动
        time.sleep(10.0)
        robot.set_velocity(0.0, 0.0, 0.0)
        
        print(f"采集完成:")
        print(f"里程计数据点: {len(odom_history)}")
        print(f"IMU数据点: {len(imu_history)}")
        print(f"电压数据点: {len(voltage_history)}")
        
        if voltage_history:
            avg_voltage = sum(voltage_history) / len(voltage_history)
            print(f"平均电压: {avg_voltage:.2f}V")


def example_custom_control():
    """自定义控制示例"""
    print("=== 自定义控制示例 ===")
    
    class CustomRobotController:
        def __init__(self, robot: WheelTecRobot):
            self.robot = robot
            self.target_x = 1.0  # 目标X坐标
            self.target_y = 1.0  # 目标Y坐标
            self.tolerance = 0.1  # 位置容差
            
        def move_to_target(self):
            """移动到目标位置的简单控制算法"""
            while True:
                odom = self.robot.get_odometry()
                current_x = odom.position.X
                current_y = odom.position.Y
                
                # 计算到目标的距离
                dx = self.target_x - current_x
                dy = self.target_y - current_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < self.tolerance:
                    print("到达目标位置!")
                    self.robot.set_velocity(0.0, 0.0, 0.0)
                    break
                
                # 简单的比例控制
                kp_linear = 0.5
                kp_angular = 1.0
                
                # 计算目标角度
                target_angle = math.atan2(dy, dx)
                current_angle = odom.position.Z
                angle_error = target_angle - current_angle
                
                # 角度归一化到[-pi, pi]
                while angle_error > math.pi:
                    angle_error -= 2 * math.pi
                while angle_error < -math.pi:
                    angle_error += 2 * math.pi
                
                # 控制命令
                linear_vel = min(kp_linear * distance, 0.3)  # 限制最大速度
                angular_vel = kp_angular * angle_error
                
                self.robot.set_velocity(linear_vel, 0.0, angular_vel)
                
                print(f"当前位置: ({current_x:.2f}, {current_y:.2f}), 距离目标: {distance:.2f}m")
                time.sleep(0.1)
    
    config = WheelTecRobotConfig()
    callbacks = CallbackConfig(
        error_callback=error_callback,
        info_callback=info_callback
    )
    
    with WheelTecRobot(config, callbacks) as robot:
        robot.start()
        time.sleep(1.0)
        
        robot.reset_odometry()
        
        # 使用自定义控制器
        controller = CustomRobotController(robot)
        controller.move_to_target()


if __name__ == "__main__":
    print("WheelTec机器人Python组件使用示例")
    print("请确保机器人已连接并且串口设备可用")
    
    try:
        # 运行基本使用示例
        example_basic_usage()
        
        # 取消注释以运行其他示例
        # example_circle_motion()
        # example_data_collection()
        # example_custom_control()
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
    
    print("示例程序结束")
