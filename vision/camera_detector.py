"""
实时摄像头网球检测程序
使用USB摄像头实时检测网球位置
"""

import cv2
import time
import argparse
from pathlib import Path
from yolo_detector import YOLODetector


class CameraDetector:
    """摄像头实时检测器"""
    
    def __init__(self, model_path: str, camera_id: int = 0, conf_threshold: float = 0.5):
        """
        初始化摄像头检测器
        
        Args:
            model_path: ONNX模型路径
            camera_id: 摄像头ID (通常为0)
            conf_threshold: 置信度阈值
        """
        self.camera_id = camera_id
        self.model_path = model_path
        
        # 初始化YOLOv11检测器
        print("正在加载YOLOv11模型...")
        self.detector = YOLODetector(model_path, conf_threshold=conf_threshold)
        print("模型加载完成!")
        
        # 初始化摄像头
        self.cap = None
        self.fps_counter = FPSCounter()
        
    def initialize_camera(self) -> bool:
        """
        初始化USB摄像头
        
        Returns:
            是否成功初始化摄像头
        """
        print(f"正在初始化摄像头 (ID: {self.camera_id})...")
        
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            print(f"错误: 无法打开摄像头 {self.camera_id}")
            return False
        
        # 设置摄像头参数
        # 设置分辨率为640x640以匹配模型输入
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 320)
        
        # 设置帧率
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # 获取实际设置的参数
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"摄像头初始化成功!")
        print(f"分辨率: {width}x{height}")
        print(f"帧率: {fps}")
        
        return True
    
    def run_detection(self, show_fps: bool = True, save_video: bool = False, output_path: str = None):
        """
        运行实时检测
        
        Args:
            show_fps: 是否显示FPS
            save_video: 是否保存视频
            output_path: 输出视频路径
        """
        if not self.initialize_camera():
            return
        
        # 视频写入器 (如果需要保存视频)
        video_writer = None
        if save_video and output_path:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            video_writer = cv2.VideoWriter(output_path, fourcc, 20.0, (width, height))
        
        print("Starting real-time detection... Press 'q' to exit")
        print("Key controls:")
        print("  'q' - Exit program")
        print("  's' - Save current frame")
        print("  'f' - Toggle FPS display")
        
        frame_count = 0
        
        try:
            while True:
                # 读取帧
                ret, frame = self.cap.read()
                if not ret:
                    print("警告: 无法读取摄像头帧")
                    break
                
                start_time = time.time()
                
                # 进行检测
                detections = self.detector.detect(frame)
                
                # 绘制检测结果
                result_frame = self.detector.draw_detections(frame, detections)
                
                # 计算推理时间
                inference_time = time.time() - start_time
                
                # 更新FPS计数器
                self.fps_counter.update()
                
                # 添加信息文本
                result_frame = self._add_info_text(result_frame, detections, inference_time, show_fps)
                
                # 显示结果
                cv2.imshow('Tennis Detection', result_frame)  # 使用英文窗口标题避免中文问题
                
                # 保存视频帧
                if video_writer:
                    video_writer.write(result_frame)
                
                frame_count += 1
                
                # 处理按键 - 增加延迟确保窗口正常刷新
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    print("退出检测...")
                    break
                elif key == ord('s'):
                    # Save current frame
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"tennis_detection_{timestamp}.jpg"
                    cv2.imwrite(filename, result_frame)
                    print(f"Frame saved: {filename}")
                elif key == ord('f'):
                    # Toggle FPS display
                    show_fps = not show_fps
                    print(f"FPS display: {'ON' if show_fps else 'OFF'}")
                
        except KeyboardInterrupt:
            print("\n检测被用户中断")
        
        finally:
            # 清理资源
            if self.cap:
                self.cap.release()
            if video_writer:
                video_writer.release()
            cv2.destroyAllWindows()
            
            print(f"Processed {frame_count} frames")
            print("Program ended")
    
    def _add_info_text(self, frame, detections, inference_time, show_fps):
        """在帧上添加英文信息文本"""
        height, width = frame.shape[:2]
        
        # 信息文本
        info_texts = []
        
        if show_fps:
            fps = self.fps_counter.get_fps()
            info_texts.append(f"FPS: {fps:.1f}")
        
        info_texts.append(f"Inference: {inference_time*1000:.1f}ms")
        info_texts.append(f"Tennis Count: {len(detections)}")
        
        # 绘制信息背景
        info_height = len(info_texts) * 25 + 10
        cv2.rectangle(frame, (10, 10), (280, info_height), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (280, info_height), (255, 255, 255), 2)
        
        # 绘制信息文本
        for i, text in enumerate(info_texts):
            y = 30 + i * 25
            cv2.putText(frame, text, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.6, (255, 255, 255), 2)
        
        # 如果检测到网球，显示详细信息
        if detections:
            for i, detection in enumerate(detections):
                center = detection['center']
                confidence = detection['confidence']
                
                # 在右上角显示网球信息
                info_x = width - 180
                info_y = 30 + i * 70
                
                cv2.rectangle(frame, (info_x - 10, info_y - 20), 
                             (width - 10, info_y + 45), (0, 0, 0), -1)
                cv2.rectangle(frame, (info_x - 10, info_y - 20), 
                             (width - 10, info_y + 45), (0, 255, 0), 2)
                
                cv2.putText(frame, f"Tennis #{i+1}", (info_x, info_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, f"Pos: ({center[0]}, {center[1]})", 
                           (info_x, info_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.4, (255, 255, 255), 1)
                cv2.putText(frame, f"Conf: {confidence:.3f}", 
                           (info_x, info_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.4, (255, 255, 255), 1)
        
        return frame


class FPSCounter:
    """FPS计数器"""
    
    def __init__(self, buffer_size: int = 30):
        """
        初始化FPS计数器
        
        Args:
            buffer_size: 用于计算平均FPS的帧数缓冲区大小
        """
        self.buffer_size = buffer_size
        self.frame_times = []
        self.last_time = time.time()
    
    def update(self):
        """更新FPS计数器"""
        current_time = time.time()
        self.frame_times.append(current_time - self.last_time)
        
        # 保持缓冲区大小
        if len(self.frame_times) > self.buffer_size:
            self.frame_times.pop(0)
        
        self.last_time = current_time
    
    def get_fps(self) -> float:
        """获取当前FPS"""
        if len(self.frame_times) < 2:
            return 0.0
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='YOLOv11网球实时检测')
    parser.add_argument('--model', type=str, default='vision/model/best.onnx',
                       help='ONNX模型路径')
    parser.add_argument('--camera', type=int, default=0,
                       help='摄像头ID')
    parser.add_argument('--conf', type=float, default=0.5,
                       help='置信度阈值')
    parser.add_argument('--save-video', action='store_true',
                       help='保存检测视频')
    parser.add_argument('--output', type=str, default='tennis_detection.avi',
                       help='输出视频路径')
    parser.add_argument('--no-fps', action='store_true',
                       help='不显示FPS')
    
    args = parser.parse_args()
    
    # 检查模型文件是否存在
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"错误: 模型文件不存在: {args.model}")
        return
    
    # 创建检测器
    try:
        detector = CameraDetector(
            model_path=str(model_path),
            camera_id=args.camera,
            conf_threshold=args.conf
        )
        
        # 运行检测
        detector.run_detection(
            show_fps=not args.no_fps,
            save_video=args.save_video,
            output_path=args.output if args.save_video else None
        )
        
    except Exception as e:
        print(f"错误: {e}")
        return


if __name__ == "__main__":
    main()
