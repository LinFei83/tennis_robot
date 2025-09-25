#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网球机器人Web控制服务器
提供轻量级的网页控制界面，支持键盘控制、视频流和系统监控
"""

import time
import threading
import psutil
import io
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, request, send_file
from flask_socketio import SocketIO, emit

# 导入模块化组件
from web_modules import RobotController, VisionProcessor, BallTracker


class WebRobotController:
    """Web机器人控制器"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'tennis_robot_2024'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 系统监控
        self.system_stats = {}
        
        # 初始化模块化组件
        self.robot_controller = RobotController(self.socketio)
        self.vision_processor = VisionProcessor(self.socketio)
        self.ball_tracker = BallTracker(self.robot_controller, self.socketio)
        
        # 设置组件间的引用
        self.vision_processor.ball_tracker = self.ball_tracker
        
        self._setup_routes()
        self._setup_socketio()
        self._start_system_monitor()
    
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
            return Response(self.vision_processor.generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/robot/start', methods=['POST'])
        def start_robot():
            """启动机器人"""
            result = self.robot_controller.start_robot()
            return jsonify(result)
        
        @self.app.route('/api/robot/stop', methods=['POST'])
        def stop_robot():
            """停止机器人"""
            result = self.robot_controller.stop_robot()
            return jsonify(result)
        
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
                
                result = self.robot_controller.set_velocity(linear_x, linear_y, angular_z)
                return jsonify(result)
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)})
        
        @self.app.route('/api/vision/start', methods=['POST'])
        def start_vision():
            """启动视觉系统"""
            result = self.vision_processor.start_vision()
            return jsonify(result)
        
        @self.app.route('/api/vision/stop', methods=['POST'])
        def stop_vision():
            """停止视觉系统"""
            result = self.vision_processor.stop_vision()
            return jsonify(result)
        
        @self.app.route('/api/system/stats')
        def get_system_stats():
            """获取系统状态"""
            return jsonify(self.system_stats)
        
        @self.app.route('/api/pickup/toggle', methods=['POST'])
        def toggle_pickup_mode():
            """切换拾取模式"""
            result = self.ball_tracker.toggle_pickup_mode()
            return jsonify(result)
        
        @self.app.route('/api/pickup/status')
        def get_pickup_status():
            """获取拾取模式状态"""
            result = self.ball_tracker.get_pickup_status()
            return jsonify(result)
        
        @self.app.route('/api/pickup/parameters', methods=['GET', 'POST'])
        def handle_pickup_parameters():
            """处理拾取模式参数"""
            if request.method == 'GET':
                params = self.ball_tracker.get_current_parameters()
                return jsonify({'status': 'success', 'parameters': params})
            else:
                try:
                    data = request.get_json()
                    if not data:
                        return jsonify({'status': 'error', 'message': '无效的JSON数据'})
                    
                    result = self.ball_tracker.update_parameters(data)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'status': 'error', 'message': str(e)})
        
        @self.app.route('/api/pickup/reset_stats', methods=['POST'])
        def reset_pickup_stats():
            """重置拾取统计信息"""
            result = self.ball_tracker.reset_statistics()
            return jsonify(result)
        
        @self.app.route('/api/vision/capture_original', methods=['POST'])
        def capture_original():
            """截取原始图像"""
            result = self.vision_processor.capture_original_image()
            if result['status'] == 'success':
                # 创建内存中的文件对象
                img_io = io.BytesIO(result['data'])
                img_io.seek(0)
                return send_file(
                    img_io,
                    mimetype='image/jpeg',
                    as_attachment=True,
                    download_name=result['filename']
                )
            else:
                return jsonify(result), 400
        
        @self.app.route('/api/vision/capture_detection', methods=['POST'])
        def capture_detection():
            """截取检测画面"""
            result = self.vision_processor.capture_detection_image()
            if result['status'] == 'success':
                # 创建内存中的文件对象
                img_io = io.BytesIO(result['data'])
                img_io.seek(0)
                return send_file(
                    img_io,
                    mimetype='image/jpeg',
                    as_attachment=True,
                    download_name=result['filename']
                )
            else:
                return jsonify(result), 400
    
    def _setup_socketio(self):
        """设置WebSocket事件"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print('客户端已连接')
            robot_status = self.robot_controller.get_status()
            vision_status = self.vision_processor.get_status()
            emit('status', {'robot': robot_status['running'], 'vision': vision_status['running']})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('客户端已断开连接')
        
        @self.socketio.on('robot_control')
        def handle_robot_control(data):
            """处理机器人控制命令"""
            try:
                command = data.get('command')
                result = self.robot_controller.handle_control_command(command)
                
                if result['status'] == 'success':
                    # 发送速度更新，包含速度倍数信息
                    velocity_data = result['velocity'].copy()
                    if 'speed_multiplier' in result:
                        velocity_data['speed_multiplier'] = result['speed_multiplier']
                    emit('velocity_update', velocity_data)
                    
                    # 如果有消息（如速度调节反馈），也发送消息
                    if 'message' in result:
                        emit('info', {'message': result['message']})
                else:
                    emit('error', {'message': result['message']})
            except Exception as e:
                emit('error', {'message': str(e)})
    
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
            self.robot_controller.cleanup()
            self.vision_processor.cleanup()
            # BallTracker不需要特殊清理，它会随着其他组件停止而停止
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
