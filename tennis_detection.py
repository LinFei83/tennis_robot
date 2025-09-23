#!/usr/bin/env python3
"""
实时网球检测 - 使用TensorFlow Lite int8量化模型
适用于树莓派USB摄像头实时推理
"""

import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import time

class TennisDetector:
    def __init__(self, model_path, confidence_threshold=0.5, iou_threshold=0.5):
        """
        初始化网球检测器
        
        Args:
            model_path: TensorFlow Lite模型路径
            confidence_threshold: 置信度阈值
            iou_threshold: NMS的IOU阈值
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        
        # 加载TensorFlow Lite模型
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        
        # 获取输入输出详情
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # 获取输入尺寸和数据类型
        self.input_height = self.input_details[0]['shape'][1]
        self.input_width = self.input_details[0]['shape'][2]
        self.input_dtype = self.input_details[0]['dtype']
        
        # 获取输入量化参数（如果是量化模型）
        self.input_scale = self.input_details[0].get('quantization_parameters', {}).get('scales', [1.0])[0]
        self.input_zero_point = self.input_details[0].get('quantization_parameters', {}).get('zero_points', [0])[0]
        
        # 获取输出量化参数
        self.output_scale = self.output_details[0].get('quantization_parameters', {}).get('scales', [1.0])[0]
        self.output_zero_point = self.output_details[0].get('quantization_parameters', {}).get('zero_points', [0])[0]
        self.output_dtype = self.output_details[0]['dtype']
        
        print(f"模型输入尺寸: {self.input_width}x{self.input_height}")
        print(f"输入数据类型: {self.input_dtype}")
        print(f"输入量化参数 - Scale: {self.input_scale}, Zero Point: {self.input_zero_point}")
        print(f"输出数据类型: {self.output_dtype}")
        print(f"输出量化参数 - Scale: {self.output_scale}, Zero Point: {self.output_zero_point}")
        print(f"置信度阈值: {self.confidence_threshold}")
        
    def preprocess_image(self, image):
        """
        图像预处理
        
        Args:
            image: 原始图像
            
        Returns:
            processed_image: 预处理后的图像
        """
        # 检查图像尺寸是否与模型输入尺寸匹配
        current_height, current_width = image.shape[:2]
        if current_width == self.input_width and current_height == self.input_height:
            # 尺寸匹配，无需resize
            resized_image = image
        else:
            # 尺寸不匹配，需要resize
            resized_image = cv2.resize(image, (self.input_width, self.input_height))
        
        if self.input_dtype == np.int8:
            # int8量化模型预处理
            # 先归一化到[0,1]，然后量化到int8
            input_image = np.array(resized_image, dtype=np.float32)
            input_image = input_image / 255.0
            
            # 应用量化参数
            input_image = input_image / self.input_scale + self.input_zero_point
            input_image = np.clip(input_image, -128, 127).astype(np.int8)
        else:
            # float32模型预处理
            input_image = np.array(resized_image, dtype=np.float32)
            input_image = input_image / 255.0
        
        # 添加batch维度
        input_image = np.expand_dims(input_image, axis=0)
        
        return input_image
    
    def postprocess_output(self, output, original_width, original_height):
        """
        后处理模型输出
        
        Args:
            output: 模型原始输出
            original_width: 原始图像宽度
            original_height: 原始图像高度
            
        Returns:
            boxes: 检测框列表 [(x1, y1, x2, y2), ...]
            scores: 置信度列表
        """
        output = output[0].T  # 转置输出
        
        # 解析输出：前4列是bbox，第5列开始是类别置信度
        boxes_xywh = output[..., :4]
        scores = np.max(output[..., 4:], axis=1)
        classes = np.argmax(output[..., 4:], axis=1)
        
        # NMS去重
        indices = cv2.dnn.NMSBoxes(boxes_xywh.tolist(), scores.tolist(), 
                                 self.confidence_threshold, self.iou_threshold)
        
        filtered_boxes = []
        filtered_scores = []
        
        if len(indices) > 0:
            for i in indices.flatten():
                if scores[i] >= self.confidence_threshold:
                    x_center, y_center, width, height = boxes_xywh[i]
                    
                    # 转换为绝对坐标
                    x1 = int((x_center - width / 2) * original_width)
                    y1 = int((y_center - height / 2) * original_height)
                    x2 = int((x_center + width / 2) * original_width)
                    y2 = int((y_center + height / 2) * original_height)
                    
                    # 确保坐标在图像范围内
                    x1 = max(0, min(x1, original_width))
                    y1 = max(0, min(y1, original_height))
                    x2 = max(0, min(x2, original_width))
                    y2 = max(0, min(y2, original_height))
                    
                    filtered_boxes.append((x1, y1, x2, y2))
                    filtered_scores.append(scores[i])
        
        return filtered_boxes, filtered_scores
    
    def detect(self, image):
        """
        执行检测
        
        Args:
            image: 输入图像
            
        Returns:
            boxes: 检测框列表
            scores: 置信度列表
        """
        original_height, original_width = image.shape[:2]
        
        # 预处理
        input_image = self.preprocess_image(image)
        
        # 推理
        self.interpreter.set_tensor(self.input_details[0]['index'], input_image)
        self.interpreter.invoke()
        
        # 获取输出
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        # 如果输出是量化的，进行反量化
        if self.output_dtype == np.int8:
            output = output.astype(np.float32)
            output = (output - self.output_zero_point) * self.output_scale
        
        # 后处理
        boxes, scores = self.postprocess_output(output, original_width, original_height)
        
        return boxes, scores
    
    def draw_detections(self, image, boxes, scores):
        """
        在图像上绘制检测结果
        
        Args:
            image: 原始图像
            boxes: 检测框列表
            scores: 置信度列表
            
        Returns:
            annotated_image: 标注后的图像
        """
        annotated_image = image.copy()
        
        for (x1, y1, x2, y2), score in zip(boxes, scores):
            # 绘制检测框
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 绘制置信度标签
            label = f'Tennis: {score:.2f}'
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # 绘制标签背景
            cv2.rectangle(annotated_image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            
            # 绘制标签文本
            cv2.putText(annotated_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        return annotated_image


def main():
    """主函数"""
    # 配置参数
    MODEL_PATH = "/home/ubuntu/project/tennis_robot/vision/model/model_int8_v5.tflite"
    CAMERA_INDEX = 0  # USB摄像头索引
    CONFIDENCE_THRESHOLD = 0.6
    IOU_THRESHOLD = 0.5
    
    # 初始化检测器
    print("正在加载模型...")
    detector = TennisDetector(MODEL_PATH, CONFIDENCE_THRESHOLD, IOU_THRESHOLD)
    print("模型加载完成")
    
    # 初始化摄像头
    print("正在初始化摄像头...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print(f"错误: 无法打开摄像头 {CAMERA_INDEX}")
        return
    
    # 设置摄像头参数为模型输入尺寸
    print(f"设置摄像头分辨率为模型输入尺寸: {detector.input_width}x{detector.input_height}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, detector.input_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, detector.input_height)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # 验证实际设置的分辨率
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"摄像头实际分辨率: {actual_width}x{actual_height}")
    
    if actual_width != detector.input_width or actual_height != detector.input_height:
        print(f"警告: 摄像头不支持目标分辨率，将使用resize调整图像尺寸")
    
    print("摄像头初始化完成")
    print("按 'q' 键退出程序")
    
    # 性能统计
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # 读取帧
            ret, frame = cap.read()
            if not ret:
                print("错误: 无法读取摄像头帧")
                break
            
            # 执行检测
            detection_start = time.time()
            boxes, scores = detector.detect(frame)
            detection_time = time.time() - detection_start
            
            # 绘制检测结果
            annotated_frame = detector.draw_detections(frame, boxes, scores)
            
            # 显示性能信息
            fps = frame_count / (time.time() - start_time + 1e-6)
            info_text = f"FPS: {fps:.1f} | {detection_time*1000:.1f}ms | {len(boxes)}"
            cv2.putText(annotated_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 显示结果
            cv2.imshow('Tennis Detection', annotated_frame)
            
            # 检查退出键
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            frame_count += 1
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    
    finally:
        # 清理资源
        cap.release()
        cv2.destroyAllWindows()
        
        # 输出统计信息
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        print(f"\n统计信息:")
        print(f"总帧数: {frame_count}")
        print(f"运行时间: {total_time:.1f}秒")
        print(f"平均FPS: {avg_fps:.1f}")


if __name__ == "__main__":
    main()
