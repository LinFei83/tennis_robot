#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网球机器人Web控制服务器
提供轻量级的网页控制界面，支持键盘控制、视频流和系统监控
"""

import os
import time
import json
import threading
import psutil
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit

# 导入机器人控制模块
from base_robot.wheeltec_robot import WheelTecRobot
from base_robot.wheeltec_robot_config import WheelTecRobotConfig, CallbackConfig
from vision.tennis_detector import TennisDetector
from vision.camera_manager import CameraConfig, CameraManager, PerformanceMonitor


class WebRobotController:
    """Web机器人控制器"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'tennis_robot_2024'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 机器人相关
        self.robot = None
        self.robot_config = None
        self.robot_callbacks = None
        self.robot_running = False
        
        # 视觉相关
        self.detector = None
        self.camera_manager = None
        self.camera_config = None
        self.perf_monitor = None
        self.vision_running = False
        self.current_frame = None
        self.detection_boxes = []
        self.detection_scores = []
        
        # 系统监控
        self.system_stats = {}
        
        # 当前速度状态
        self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        
        self._setup_routes()
        self._setup_socketio()
        self._init_components()
        
    def _init_components(self):
        """初始化组件"""
        try:
            # 初始化机器人
            self._init_robot()
            
            # 初始化视觉系统
            self._init_vision()
            
            # 启动系统监控
            self._start_system_monitor()
            
        except Exception as e:
            print(f"组件初始化失败: {e}")
    
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
    
    def _init_vision(self):
        """初始化视觉系统"""
        try:
            # 模型路径
            model_path = "vision/model/model_float32_myv8.tflite"
            if not os.path.exists(model_path):
                print(f"警告: 模型文件不存在: {model_path}")
                return
            
            # 初始化检测器
            self.detector = TennisDetector(
                model_path,
                confidence_threshold=0.6,
                iou_threshold=0.5
            )
            
            # 初始化摄像头管理器
            self.camera_config = CameraConfig()
            self.camera_manager = CameraManager(
                self.camera_config,
                self.detector.input_width,
                self.detector.input_height
            )
            
            self.perf_monitor = PerformanceMonitor()
            print("视觉系统初始化成功")
            
            # 自动启动视觉系统
            if self.camera_manager.initialize_camera():
                self.vision_running = True
                self._start_vision_thread()
                print("视觉系统自动启动成功")
            else:
                print("警告: 摄像头初始化失败，视觉系统未启动")
        except Exception as e:
            print(f"视觉系统初始化失败: {e}")
    
    def _start_system_monitor(self):
        """启动系统监控线程"""
        def monitor_loop():
            while True:
                try:
                    # 获取系统信息
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    
                    self.system_stats = {
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_used': memory.used / (1024**3),  # GB
                        'memory_total': memory.total / (1024**3),  # GB
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    }
                    
                    # 通过WebSocket发送系统状态
                    self.socketio.emit('system_stats', self.system_stats)
                    
                except Exception as e:
                    print(f"系统监控错误: {e}")
                
                time.sleep(2)  # 每2秒更新一次
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/video_feed')
        def video_feed():
            """视频流路由"""
            return Response(self._generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/robot/start', methods=['POST'])
        def start_robot():
            """启动机器人"""
            try:
                if self.robot_running:
                    return jsonify({'status': 'error', 'message': '机器人已在运行中'})
                
                if not self.robot:
                    return jsonify({'status': 'error', 'message': '机器人未初始化'})
                
                # 启动机器人（内部会自动处理串口重连）
                self.robot.start()
                self.robot_running = True
                return jsonify({'status': 'success', 'message': '机器人已启动'})
                
            except Exception as e:
                self.robot_running = False  # 确保状态一致
                return jsonify({'status': 'error', 'message': f'机器人启动失败: {str(e)}'})
        
        @self.app.route('/api/robot/stop', methods=['POST'])
        def stop_robot():
            """停止机器人"""
            try:
                if not self.robot_running:
                    return jsonify({'status': 'error', 'message': '机器人未运行'})
                
                if not self.robot:
                    self.robot_running = False
                    return jsonify({'status': 'error', 'message': '机器人未初始化'})
                
                # 先停止运动
                try:
                    self.robot.set_velocity(0.0, 0.0, 0.0)
                except Exception as vel_e:
                    print(f"停止运动失败: {vel_e}")
                
                # 停止机器人控制
                self.robot.stop()
                self.robot_running = False
                self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
                
                return jsonify({'status': 'success', 'message': '机器人已停止'})
                
            except Exception as e:
                self.robot_running = False  # 确保状态一致
                self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
                return jsonify({'status': 'error', 'message': f'机器人停止失败: {str(e)}'})
        
        @self.app.route('/api/robot/velocity', methods=['POST'])
        def set_velocity():
            """设置机器人速度"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': '无效的JSON数据'})
                
                linear_x = data.get('linear_x', 0.0)
                linear_y = data.get('linear_y', 0.0)
                angular_z = data.get('angular_z', 0.0)
                
                if self.robot_running and self.robot:
                    self.robot.set_velocity(linear_x, linear_y, angular_z)
                    self.current_velocity = {'x': linear_x, 'y': linear_y, 'z': angular_z}
                    return jsonify({'status': 'success', 'velocity': self.current_velocity})
                else:
                    return jsonify({'status': 'error', 'message': '机器人未运行'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)})
        
        @self.app.route('/api/vision/start', methods=['POST'])
        def start_vision():
            """启动视觉系统"""
            try:
                if not self.vision_running and self.camera_manager:
                    if self.camera_manager.initialize_camera():
                        self.vision_running = True
                        self._start_vision_thread()
                        return jsonify({'status': 'success', 'message': '视觉系统已启动'})
                    else:
                        return jsonify({'status': 'error', 'message': '摄像头初始化失败'})
                else:
                    return jsonify({'status': 'error', 'message': '视觉系统已在运行或未初始化'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)})
        
        @self.app.route('/api/vision/stop', methods=['POST'])
        def stop_vision():
            """停止视觉系统"""
            try:
                if self.vision_running:
                    self.vision_running = False
                    if self.camera_manager:
                        self.camera_manager.release()
                    return jsonify({'status': 'success', 'message': '视觉系统已停止'})
                else:
                    return jsonify({'status': 'error', 'message': '视觉系统未运行'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)})
        
        @self.app.route('/api/system/stats')
        def get_system_stats():
            """获取系统状态"""
            return jsonify(self.system_stats)
    
    def _setup_socketio(self):
        """设置WebSocket事件"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print('客户端已连接')
            emit('status', {'robot': self.robot_running, 'vision': self.vision_running})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('客户端已断开连接')
        
        @self.socketio.on('robot_control')
        def handle_robot_control(data):
            """处理机器人控制命令"""
            try:
                if self.robot_running and self.robot:
                    command = data.get('command')
                    
                    # 预定义的速度值
                    speed_linear = 0.3  # m/s
                    speed_angular = 0.5  # rad/s
                    
                    if command == 'forward':
                        self.robot.set_velocity(speed_linear, 0.0, 0.0)
                        self.current_velocity = {'x': speed_linear, 'y': 0.0, 'z': 0.0}
                    elif command == 'backward':
                        self.robot.set_velocity(-speed_linear, 0.0, 0.0)
                        self.current_velocity = {'x': -speed_linear, 'y': 0.0, 'z': 0.0}
                    elif command == 'left':
                        self.robot.set_velocity(0.0, 0.0, speed_angular)
                        self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': speed_angular}
                    elif command == 'right':
                        self.robot.set_velocity(0.0, 0.0, -speed_angular)
                        self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': -speed_angular}
                    elif command == 'stop':
                        self.robot.set_velocity(0.0, 0.0, 0.0)
                        self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
                    
                    emit('velocity_update', self.current_velocity)
            except Exception as e:
                emit('error', {'message': str(e)})
    
    def _start_vision_thread(self):
        """启动视觉处理线程"""
        def vision_loop():
            while self.vision_running:
                try:
                    if not self.camera_manager:
                        break
                    
                    # 获取帧
                    ret, frame = self.camera_manager.get_latest_frame()
                    if not ret or frame is None:
                        continue
                    
                    # 执行检测
                    detection_start = time.time()
                    boxes, scores = self.detector.detect(frame)
                    detection_time = time.time() - detection_start
                    
                    # 更新自适应跳帧
                    self.camera_manager.update_adaptive_skip(detection_time)
                    
                    # 绘制检测结果
                    annotated_frame = self.detector.draw_detections(frame, boxes, scores)
                    
                    # 添加性能信息
                    fps = self.perf_monitor.get_fps()
                    skip_frames = self.camera_manager.get_skip_frames()
                    info_text = f"FPS: {fps:.1f} | {detection_time*1000:.1f}ms | {len(boxes)} | Skip:{skip_frames}"
                    cv2.putText(annotated_frame, info_text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    # 保存当前帧和检测结果
                    self.current_frame = annotated_frame
                    self.detection_boxes = boxes
                    self.detection_scores = scores
                    
                    # 更新性能统计
                    self.perf_monitor.update_frame_count()
                    
                    # 发送检测结果
                    self.socketio.emit('detection_update', {
                        'boxes': len(boxes),
                        'fps': fps,
                        'detection_time': detection_time * 1000
                    })
                    
                except Exception as e:
                    print(f"视觉处理错误: {e}")
                    break
                
                time.sleep(0.01)  # 短暂休眠
        
        vision_thread = threading.Thread(target=vision_loop, daemon=True)
        vision_thread.start()
    
    def _generate_frames(self):
        """生成视频帧"""
        while True:
            try:
                if self.current_frame is not None:
                    # 编码帧
                    ret, buffer = cv2.imencode('.jpg', self.current_frame, 
                                             [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    # 发送空白帧
                    blank_frame = cv2.imread('static/blank.jpg') if os.path.exists('static/blank.jpg') else \
                                 np.zeros((480, 640, 3), dtype=np.uint8)
                    ret, buffer = cv2.imencode('.jpg', blank_frame)
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                print(f"帧生成错误: {e}")
                time.sleep(1)
    
    # 机器人回调函数
    def _odom_callback(self, data):
        """里程计回调"""
        self.socketio.emit('odom_update', data)
    
    def _imu_callback(self, data):
        """IMU回调"""
        self.socketio.emit('imu_update', data)
    
    def _voltage_callback(self, voltage):
        """电压回调"""
        self.socketio.emit('voltage_update', {'voltage': voltage})
    
    def _error_callback(self, error_msg):
        """错误回调"""
        print(f"机器人错误: {error_msg}")
        self.socketio.emit('robot_error', {'message': error_msg})
    
    def _info_callback(self, info_msg):
        """信息回调"""
        print(f"机器人信息: {info_msg}")
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """运行服务器"""
        try:
            print(f"启动Web服务器: http://{host}:{port}")
            self.socketio.run(self.app, host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            print("\n正在关闭服务器...")
            self._cleanup()
        except Exception as e:
            print(f"服务器运行错误: {e}")
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.robot_running and self.robot:
                self.robot.set_velocity(0.0, 0.0, 0.0)
                self.robot.stop()
            
            if self.vision_running and self.camera_manager:
                self.vision_running = False
                self.camera_manager.release()
            
            print("资源清理完成")
        except Exception as e:
            print(f"资源清理错误: {e}")


def main():
    """主函数"""
    print("网球机器人Web控制服务器")
    print("=" * 50)
    
    try:
        # 创建控制器
        controller = WebRobotController()
        
        # 运行服务器
        controller.run(host='0.0.0.0', port=5000, debug=False)
        
    except Exception as e:
        print(f"程序运行错误: {e}")
    finally:
        print("程序结束")


if __name__ == "__main__":
    main()
