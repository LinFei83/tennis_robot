"""
YOLOv8 TensorFlow Lite 网球检测器
用于在树莓派上实时检测网球位置
使用量化为INT8的TensorFlow Lite模型进行推理
"""

import cv2
import numpy as np
import tensorflow as tf
from typing import List, Tuple, Optional
import time


class YOLODetector:
    """YOLOv8 TensorFlow Lite模型网球检测器"""
    
    def __init__(self, model_path: str, conf_threshold: float = 0.5, nms_threshold: float = 0.4):
        """
        初始化检测器
        
        Args:
            model_path: TensorFlow Lite模型文件路径
            conf_threshold: 置信度阈值
            nms_threshold: NMS阈值
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        
        # 初始化TensorFlow Lite解释器
        self.interpreter = self._load_model()
        
        # 获取模型输入输出信息
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # 从模型中获取输入尺寸
        input_shape = self.input_details[0]['shape']
        self.input_height = input_shape[1]
        self.input_width = input_shape[2]
        
        print(f"模型输入尺寸: {self.input_width}x{self.input_height}")
        print(f"输入数据类型: {self.input_details[0]['dtype']}")
        
    def _load_model(self) -> tf.lite.Interpreter:
        """加载TensorFlow Lite模型"""
        try:
            # 创建TensorFlow Lite解释器
            interpreter = tf.lite.Interpreter(model_path=self.model_path)
            interpreter.allocate_tensors()
            
            print(f"成功加载TensorFlow Lite模型: {self.model_path}")
            return interpreter
            
        except Exception as e:
            raise RuntimeError(f"无法加载模型 {self.model_path}: {e}")
    
    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        预处理输入图像
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            preprocessed_image: 预处理后的图像
            scale_x: X轴缩放比例
            scale_y: Y轴缩放比例
        """
        # 获取原始图像尺寸
        original_height, original_width = image.shape[:2]
        
        # 计算缩放比例
        scale_x = original_width / self.input_width
        scale_y = original_height / self.input_height
        
        # 调整图像大小
        resized_image = cv2.resize(image, (self.input_width, self.input_height))
        
        # 转换为RGB
        rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        
        # 检查输入数据类型
        input_dtype = self.input_details[0]['dtype']
        
        if input_dtype == np.int8:
            # 对于INT8量化模型，将图像从[0,255]范围转换为[-128,127]范围
            input_tensor = rgb_image.astype(np.int8) - 128
        else:
            # 对于float32模型，归一化到[0,1]范围
            input_tensor = rgb_image.astype(np.float32) / 255.0
        
        # 添加批次维度 (NHWC格式: 批次, 高度, 宽度, 通道)
        input_tensor = np.expand_dims(input_tensor, axis=0)
        
        return input_tensor, scale_x, scale_y
    
    def postprocess(self, outputs: np.ndarray, scale_x: float, scale_y: float) -> List[dict]:
        """
        后处理模型输出
        
        Args:
            outputs: 模型输出
            scale_x: X轴缩放比例
            scale_y: Y轴缩放比例
            
        Returns:
            检测结果列表，每个元素包含 'bbox', 'confidence', 'class_id'
        """
        detections = []
        
        # YOLOv8输出格式通常是 [batch, num_detections, 85] 
        # 其中85 = 4(bbox) + 1(objectness) + 80(classes)
        # 对于单类别(网球)，可能是 [batch, num_detections, 6] 其中6 = 4(bbox) + 1(objectness) + 1(class)
        output = outputs[0]  # 移除批次维度
        
        # 如果输出是 [num_classes, num_detections] 格式，需要转置
        if len(output.shape) == 2 and output.shape[0] < output.shape[1]:
            output = output.transpose()
        
        for detection in output:
            # 提取边界框坐标和置信度
            if len(detection) >= 5:
                x_center, y_center, width, height, confidence = detection[:5]
                
                # 过滤低置信度检测
                if confidence >= self.conf_threshold:
                    # 修复后：先转换为像素坐标，再缩放到原始图像（正确）
                    x_center_pixels = x_center * self.input_width
                    y_center_pixels = y_center * self.input_height
                    width_pixels = width * self.input_width
                    height_pixels = height * self.input_height
                    
                    # 缩放到原始图像尺寸
                    x_center_orig = x_center_pixels * scale_x
                    y_center_orig = y_center_pixels * scale_y
                    width_orig = width_pixels * scale_x
                    height_orig = height_pixels * scale_y
                    
                    # 计算边界框坐标
                    x1 = int(x_center_orig - width_orig / 2)
                    y1 = int(y_center_orig - height_orig / 2)
                    x2 = int(x_center_orig + width_orig / 2)
                    y2 = int(y_center_orig + height_orig / 2)
                    
                    detections.append({
                        'bbox': (x1, y1, x2, y2),
                        'confidence': float(confidence),
                        'class_id': 0,  # 网球类别ID
                        'center': (int(x_center_orig), int(y_center_orig))
                    })
        
        # 应用非极大值抑制
        if detections:
            detections = self._apply_nms(detections)
        
        return detections
    
    def _apply_nms(self, detections: List[dict]) -> List[dict]:
        """应用非极大值抑制"""
        if not detections:
            return []
        
        # 提取边界框和置信度
        boxes = []
        confidences = []
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            boxes.append([x1, y1, x2 - x1, y2 - y1])  # [x, y, w, h]
            confidences.append(det['confidence'])
        
        # 应用NMS
        indices = cv2.dnn.NMSBoxes(
            boxes, confidences, self.conf_threshold, self.nms_threshold
        )
        
        # 返回保留的检测结果
        if len(indices) > 0:
            return [detections[i] for i in indices.flatten()]
        else:
            return []
    
    def detect(self, image: np.ndarray) -> List[dict]:
        """
        检测图像中的网球
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            检测结果列表
        """
        # 预处理
        input_tensor, scale_x, scale_y = self.preprocess(image)
        
        # 设置输入张量
        self.interpreter.set_tensor(self.input_details[0]['index'], input_tensor)
        
        # 运行推理
        self.interpreter.invoke()
        
        # 获取输出张量
        outputs = []
        for output_detail in self.output_details:
            output = self.interpreter.get_tensor(output_detail['index'])
            outputs.append(output)
        
        # 后处理
        detections = self.postprocess(outputs[0], scale_x, scale_y)
        
        return detections
    
    def draw_detections(self, image: np.ndarray, detections: List[dict]) -> np.ndarray:
        """
        在图像上绘制检测结果
        
        Args:
            image: 输入图像
            detections: 检测结果
            
        Returns:
            绘制了检测结果的图像
        """
        result_image = image.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            center = detection['center']
            
            x1, y1, x2, y2 = bbox
            
            # 绘制边界框
            cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 绘制中心点
            cv2.circle(result_image, center, 5, (0, 0, 255), -1)
            
            # 绘制置信度标签
            label = f"Tennis: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result_image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(result_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return result_image
