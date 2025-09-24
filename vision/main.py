#!/usr/bin/env python3
"""
网球检测主程序 - 模块化重构版本
"""

import cv2
import time
from tennis_detector import TennisDetector
from camera_manager import CameraConfig, CameraManager, PerformanceMonitor


def print_usage_instructions():
    """打印使用说明"""
    print("按键说明:")
    print("  's' - 保存完整截图（包含检测框和文字）")
    print("  'r' - 保存原始图像（仅摄像头画面）")
    print("  'q' - 退出程序")


def create_info_overlay(frame, fps, detection_time, num_detections, skip_frames):
    """
    在帧上添加信息覆盖层
    
    Args:
        frame: 输入帧
        fps: 当前FPS
        detection_time: 检测耗时（秒）
        num_detections: 检测到的目标数量
        skip_frames: 跳帧数
        
    Returns:
        带信息覆盖的帧
    """
    info_text = f"FPS: {fps:.1f} | {detection_time*1000:.1f}ms | {num_detections} | Skip:{skip_frames}"
    cv2.putText(frame, info_text, (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame


def main():
    """主函数"""
    # 配置参数
    MODEL_PATH = "vision/model/model_int8_v8.tflite"
    
    try:
        # 初始化配置
        print("正在加载配置...")
        config = CameraConfig()
        detection_config = config.get_detection_config()
        
        # 初始化检测器
        print("正在加载模型...")
        detector = TennisDetector(
            MODEL_PATH, 
            confidence_threshold=detection_config.get("confidence_threshold", 0.6),
            iou_threshold=detection_config.get("iou_threshold", 0.5)
        )
        print("模型加载完成")
        
        # 初始化摄像头管理器
        with CameraManager(config, detector.input_width, detector.input_height) as camera_manager:
            if not camera_manager.initialize_camera():
                return
            
            # 初始化性能监控器
            perf_monitor = PerformanceMonitor()
            
            print_usage_instructions()
            
            # 主循环
            while True:
                # 获取最新帧
                ret, frame = camera_manager.get_latest_frame()
                if not ret:
                    print("错误: 无法读取摄像头帧")
                    break
                
                # 执行检测
                detection_start = time.time()
                boxes, scores = detector.detect(frame)
                detection_time = time.time() - detection_start
                
                # 更新自适应跳帧参数
                camera_manager.update_adaptive_skip(detection_time)
                
                # 绘制检测结果
                annotated_frame = detector.draw_detections(frame, boxes, scores)
                
                # 添加性能信息覆盖层
                fps = perf_monitor.get_fps()
                skip_frames = camera_manager.get_skip_frames()
                annotated_frame = create_info_overlay(
                    annotated_frame, fps, detection_time, len(boxes), skip_frames
                )
                
                # 显示结果
                cv2.imshow('Tennis Detection', annotated_frame)
                
                # 处理按键事件
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    detector.save_screenshot(annotated_frame, "full")
                elif key == ord('r'):
                    detector.save_screenshot(frame, "raw")
                
                # 更新性能统计
                perf_monitor.update_frame_count()
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        # 清理资源
        cv2.destroyAllWindows()
        
        # 输出统计信息
        if 'perf_monitor' in locals():
            stats = perf_monitor.get_stats()
            print(f"\n统计信息:")
            print(f"总帧数: {stats['total_frames']}")
            print(f"运行时间: {stats['total_time']:.1f}秒")
            print(f"平均FPS: {stats['average_fps']:.1f}")


if __name__ == "__main__":
    main()
