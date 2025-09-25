#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉处理模块
负责摄像头管理、图像检测和视频流处理
"""

import os
import time
import threading
import cv2
import numpy as np

from vision.tennis_detector import TennisDetector
from vision.camera_manager import CameraConfig, CameraManager, PerformanceMonitor


class VisionProcessor:
    """视觉处理器"""
    
    def __init__(self, socketio=None, model_path="vision/model/model_float32_myv8.tflite"):
        """
        初始化视觉处理器
        
        Args:
            socketio: WebSocket对象，用于发送状态更新
            model_path: 模型文件路径
        """
        self.socketio = socketio
        self.model_path = model_path
        self.ball_tracker = None  # 将在主控制器中设置
        
        # 视觉相关
        self.detector = None
        self.camera_manager = None
        self.camera_config = None
        self.perf_monitor = None
        self.vision_running = False
        self.current_frame = None
        self.original_frame = None  # 保存原始帧
        self.detection_boxes = []
        self.detection_scores = []
        
        # 初始化视觉系统
        self._init_vision()
    
    def _init_vision(self):
        """初始化视觉系统"""
        try:
            # 检查模型文件
            if not os.path.exists(self.model_path):
                print(f"警告: 模型文件不存在: {self.model_path}")
                return
            
            # 初始化检测器
            self.detector = TennisDetector(
                self.model_path,
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
    
    def start_vision(self):
        """启动视觉系统"""
        try:
            if not self.vision_running and self.camera_manager:
                if self.camera_manager.initialize_camera():
                    self.vision_running = True
                    self._start_vision_thread()
                    return {'status': 'success', 'message': '视觉系统已启动'}
                else:
                    return {'status': 'error', 'message': '摄像头初始化失败'}
            else:
                return {'status': 'error', 'message': '视觉系统已在运行或未初始化'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def stop_vision(self):
        """停止视觉系统"""
        try:
            if self.vision_running:
                self.vision_running = False
                if self.camera_manager:
                    self.camera_manager.release()
                return {'status': 'success', 'message': '视觉系统已停止'}
            else:
                return {'status': 'error', 'message': '视觉系统未运行'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_status(self):
        """获取视觉系统状态"""
        return {
            'running': self.vision_running,
            'detections': len(self.detection_boxes) if self.detection_boxes else 0,
            'fps': self.perf_monitor.get_fps() if self.perf_monitor else 0
        }
    
    def get_current_frame(self):
        """获取当前帧"""
        return self.current_frame
    
    def get_original_frame(self):
        """获取原始帧（未经过检测处理的）"""
        return self.original_frame
    
    def capture_original_image(self):
        """截取原始摄像头图像"""
        try:
            if self.original_frame is not None:
                timestamp = int(time.time())
                filename = f"original_{timestamp}.jpg"
                # 编码图像为JPEG格式
                ret, buffer = cv2.imencode('.jpg', self.original_frame, 
                                         [cv2.IMWRITE_JPEG_QUALITY, 95])
                if ret:
                    return {
                        'status': 'success',
                        'filename': filename,
                        'data': buffer.tobytes(),
                        'message': '原始图像截取成功'
                    }
                else:
                    return {'status': 'error', 'message': '图像编码失败'}
            else:
                return {'status': 'error', 'message': '没有可用的原始图像'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def capture_detection_image(self):
        """截取检测后的画面"""
        try:
            if self.current_frame is not None:
                timestamp = int(time.time())
                filename = f"detection_{timestamp}.jpg"
                # 编码图像为JPEG格式
                ret, buffer = cv2.imencode('.jpg', self.current_frame, 
                                         [cv2.IMWRITE_JPEG_QUALITY, 95])
                if ret:
                    return {
                        'status': 'success',
                        'filename': filename,
                        'data': buffer.tobytes(),
                        'message': '检测画面截取成功'
                    }
                else:
                    return {'status': 'error', 'message': '图像编码失败'}
            else:
                return {'status': 'error', 'message': '没有可用的检测画面'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
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
                    
                    # 保存原始帧
                    self.original_frame = frame.copy()
                    
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


                    # 保存当前帧和检测结果
                    self.current_frame = annotated_frame
                    self.detection_boxes = boxes
                    self.detection_scores = scores
                    
                    # 如果有球跟踪器，处理检测结果
                    if self.ball_tracker:
                        try:
                            self.ball_tracker.process_detections(boxes, scores, frame.shape)
                        except Exception as tracker_error:
                            print(f"球跟踪处理错误: {tracker_error}")
                            # 继续处理，不中断视频流
                    
                    # 更新性能统计
                    self.perf_monitor.update_frame_count()
                    
                    # 发送检测结果
                    if self.socketio:
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
    
    def generate_frames(self):
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
    
    def cleanup(self):
        """清理视觉系统资源"""
        try:
            if self.vision_running and self.camera_manager:
                self.vision_running = False
                self.camera_manager.release()
            print("视觉系统资源清理完成")
        except Exception as e:
            print(f"视觉系统资源清理错误: {e}")
