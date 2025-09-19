# WheelTec机器人Python组件

将ROS C++节点转换为普通Python程序，提供优雅简洁的机器人控制接口。

## 功能特性

- 🚀 **无ROS依赖**: 完全独立的Python程序，不需要ROS环境
- 🔧 **串口通信**: 直接与机器人底盘控制板通信
- 📊 **数据获取**: 实时获取里程计、IMU、电压等传感器数据
- 🎯 **回调机制**: 灵活的回调函数系统替代ROS发布订阅
- 📍 **里程计功能**: 返回相对于起点的位置和姿态
- 🔄 **四元数解算**: 内置IMU姿态解算算法
- 🛡️ **错误处理**: 完善的异常处理和日志系统
- 🧵 **多线程**: 非阻塞的数据采集和控制

## 文件结构

```
├── wheeltec_robot_config.py    # 配置文件（基于launch文件转换）
├── wheeltec_robot.py          # 主要机器人控制类
├── example_usage.py           # 使用示例
└── README.md                  # 说明文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install pyserial
```

### 2. 基本使用

```python
from wheeltec_robot import WheelTecRobot
from wheeltec_robot_config import WheelTecRobotConfig, CallbackConfig

# 创建配置
config = WheelTecRobotConfig(
    usart_port_name="/dev/wheeltec_controller",  # 串口设备
    serial_baud_rate=115200,                     # 波特率
    odom_x_scale=1.0,                           # 里程计X轴修正
    odom_y_scale=1.0                            # 里程计Y轴修正
)

# 创建回调函数
def odom_callback(odom_data):
    pos = odom_data['position']
    print(f"位置: x={pos['x']:.3f}, y={pos['y']:.3f}")

callbacks = CallbackConfig(
    odom_callback=odom_callback,
    error_callback=lambda msg: print(f"错误: {msg}"),
    info_callback=lambda msg: print(f"信息: {msg}")
)

# 使用机器人
with WheelTecRobot(config, callbacks) as robot:
    robot.start()                              # 启动数据采集
    
    robot.set_velocity(0.2, 0.0, 0.0)         # 前进 0.2 m/s
    time.sleep(3.0)
    
    robot.set_velocity(0.0, 0.0, 0.5)         # 转弯 0.5 rad/s
    time.sleep(2.0)
    
    robot.set_velocity(0.0, 0.0, 0.0)         # 停止
    
    # 获取当前状态
    odom = robot.get_odometry()                # 获取里程计
    imu = robot.get_imu_data()                 # 获取IMU数据
    voltage = robot.get_voltage()              # 获取电压
```

## 配置说明

### WheelTecRobotConfig

基于`launch/include/base_serial.launch`转换的配置类：

```python
@dataclass
class WheelTecRobotConfig:
    # 串口通信配置
    usart_port_name: str = "/dev/wheeltec_controller"
    serial_baud_rate: int = 115200
    
    # TF坐标系配置
    odom_frame_id: str = "odom_combined"
    robot_frame_id: str = "base_footprint"
    gyro_frame_id: str = "gyro_link"
    
    # 里程计修正参数
    odom_x_scale: float = 1.0
    odom_y_scale: float = 1.0
    odom_z_scale_positive: float = 1.0
    odom_z_scale_negative: float = 1.0
    
    # 其他配置...
```

### CallbackConfig

回调函数配置，替代ROS的发布订阅机制：

```python
@dataclass
class CallbackConfig:
    # 数据回调
    odom_callback: Optional[Callable[[dict], None]] = None
    imu_callback: Optional[Callable[[dict], None]] = None
    voltage_callback: Optional[Callable[[float], None]] = None
    
    # 日志回调
    error_callback: Optional[Callable[[str], None]] = None
    info_callback: Optional[Callable[[str], None]] = None
```

## 主要接口

### WheelTecRobot类

```python
class WheelTecRobot:
    def __init__(self, config: WheelTecRobotConfig, callbacks: CallbackConfig)
    
    # 控制方法
    def start(self) -> None                    # 启动机器人控制
    def stop(self) -> None                     # 停止机器人控制
    def set_velocity(self, x: float, y: float, z: float) -> None  # 设置速度
    
    # 数据获取方法
    def get_odometry(self) -> OdomData         # 获取里程计数据
    def get_imu_data(self) -> IMUSensorData    # 获取IMU数据
    def get_voltage(self) -> float             # 获取电压数据
    
    # 工具方法
    def reset_odometry(self) -> None           # 重置里程计
```

### 数据结构

```python
@dataclass
class OdomData:
    """里程计数据 - 相对于起点的位置和姿态"""
    position: VelPosData           # 位置 (x, y, z)
    orientation: QuaternionData    # 姿态四元数
    linear_velocity: VelPosData    # 线速度
    angular_velocity: VelPosData   # 角速度
    timestamp: float               # 时间戳

@dataclass
class IMUSensorData:
    """IMU传感器数据"""
    orientation: QuaternionData    # 姿态四元数
    angular_velocity: VelPosData   # 角速度
    linear_acceleration: VelPosData # 线加速度
```

## 使用示例

### 1. 基本运动控制

```python
# 前进
robot.set_velocity(0.2, 0.0, 0.0)    # x=0.2m/s, y=0, z=0

# 左转
robot.set_velocity(0.0, 0.0, 0.5)    # x=0, y=0, z=0.5rad/s

# 全向移动（仅支持全向轮机器人）
robot.set_velocity(0.1, 0.1, 0.2)    # x=0.1m/s, y=0.1m/s, z=0.2rad/s

# 停止
robot.set_velocity(0.0, 0.0, 0.0)
```

### 2. 数据监控

```python
def monitor_robot_status(odom_data):
    pos = odom_data['position']
    vel = odom_data['linear_velocity']
    print(f"位置: ({pos['x']:.2f}, {pos['y']:.2f})")
    print(f"速度: {vel['x']:.2f} m/s")

def monitor_imu(imu_data):
    acc = imu_data['linear_acceleration']
    print(f"加速度: ({acc['x']:.2f}, {acc['y']:.2f}, {acc['z']:.2f})")

callbacks = CallbackConfig(
    odom_callback=monitor_robot_status,
    imu_callback=monitor_imu,
    voltage_callback=lambda v: print(f"电压: {v:.1f}V")
)
```

### 3. 自定义控制算法

```python
class SimplePathFollower:
    def __init__(self, robot: WheelTecRobot):
        self.robot = robot
        self.waypoints = [(1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
        self.current_target = 0
        self.tolerance = 0.1
    
    def update(self):
        if self.current_target >= len(self.waypoints):
            self.robot.set_velocity(0.0, 0.0, 0.0)
            return False
        
        odom = self.robot.get_odometry()
        target_x, target_y = self.waypoints[self.current_target]
        
        dx = target_x - odom.position.X
        dy = target_y - odom.position.Y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < self.tolerance:
            self.current_target += 1
            return True
        
        # 简单比例控制
        target_angle = math.atan2(dy, dx)
        angle_error = target_angle - odom.position.Z
        
        linear_vel = min(0.5 * distance, 0.3)
        angular_vel = 1.0 * angle_error
        
        self.robot.set_velocity(linear_vel, 0.0, angular_vel)
        return True

# 使用路径跟踪器
with WheelTecRobot(config, callbacks) as robot:
    robot.start()
    robot.reset_odometry()
    
    follower = SimplePathFollower(robot)
    while follower.update():
        time.sleep(0.1)
```

## 技术细节

### 串口通信协议

- **帧头**: 0x7B
- **帧尾**: 0x7D  
- **数据长度**: 24字节（接收），11字节（发送）
- **校验**: BCC异或校验
- **波特率**: 115200

### 数据转换

- **速度单位**: mm/s → m/s （除以1000）
- **IMU加速度**: 原始数据 → m/s² （除以1671.84）
- **IMU角速度**: 原始数据 → rad/s （乘以0.00026644）
- **电压**: mv → V （除以1000）

### 坐标系统

- **X轴**: 机器人前进方向
- **Y轴**: 机器人左侧方向（仅全向轮有效）
- **Z轴**: 机器人垂直向上，绕Z轴旋转为偏航角

### 里程计积分

位置通过速度积分计算，考虑机器人当前姿态：

```python
self.robot_pos.X += (vel_x * cos(θ) - vel_y * sin(θ)) * dt
self.robot_pos.Y += (vel_x * sin(θ) + vel_y * cos(θ)) * dt  
self.robot_pos.Z += vel_z * dt
```

## 注意事项

1. **串口权限**: 确保有串口设备的读写权限
2. **设备连接**: 确认机器人底盘控制板正确连接
3. **波特率匹配**: 确保配置的波特率与底盘一致
4. **线程安全**: 数据采集在独立线程中进行
5. **资源释放**: 使用上下文管理器确保资源正确释放

## 故障排除

### 串口无法打开
```bash
# 检查设备是否存在
ls /dev/ttyUSB* /dev/wheeltec_controller

# 添加用户到dialout组
sudo usermod -a -G dialout $USER

# 设置设备权限
sudo chmod 666 /dev/ttyUSB0
```

### 数据接收异常
- 检查串口连接
- 确认波特率设置
- 查看错误回调输出

### 里程计漂移
- 调整里程计修正参数
- 定期重置里程计
- 检查机器人机械状态

## 扩展开发

这个组件设计为可扩展的，你可以：

1. **添加新的传感器**: 扩展数据解析函数
2. **实现新的控制算法**: 继承或组合使用机器人类
3. **集成其他系统**: 通过回调函数与其他模块交互
4. **数据记录**: 实现数据日志和回放功能

## 许可证

本项目基于原ROS源码转换，请遵循相应的开源许可证。
