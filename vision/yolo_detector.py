"""
YOLOv11 ONNX 网球检测器
用于在树莓派上实时检测网球位置
"""

import cv2
import numpy as np
import onnxruntime as ort
from typing import List, Tuple, Optional
import time


class YOLODetector:
    """YOLOv11 ONNX模型网球检测器"""
    
    def __init__(self, model_path: str, conf_threshold: float = 0.5, nms_threshold: float = 0.4):
        """
        初始化检测器
        
        Args:
            model_path: ONNX模型文件路径
            conf_threshold: 置信度阈值
            nms_threshold: NMS阈值
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        
        # 初始化ONNX Runtime会话
        self.session = self._load_model()
        
        # 获取模型输入输出信息
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
        # 模型输入尺寸 (YOLOv11通常是640x640)
        self.input_width = 320
        self.input_height = 320
        
    def _load_model(self) -> ort.InferenceSession:
        """加载ONNX模型"""
        try:
            # 为树莓派优化的提供者设置
            providers = [
                'CPUExecutionProvider'  # 树莓派主要使用CPU
            ]
            
            session = ort.InferenceSession(
                self.model_path,
                providers=providers
            )
            print(f"成功加载模型: {self.model_path}")
            return session
            
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
        
        # 归一化到0-1
        normalized_image = rgb_image.astype(np.float32) / 255.0
        
        # 转换为NCHW格式 (批次, 通道, 高度, 宽度)
        input_tensor = np.transpose(normalized_image, (2, 0, 1))
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
        
        # YOLOv11输出格式: [batch, 84, 8400] 其中84 = 4(bbox) + 80(classes)
        # 对于单类别(网球)，输出应该是 [batch, 5, num_anchors] 其中5 = 4(bbox) + 1(conf)
        output = outputs[0]  # 移除批次维度
        
        if output.shape[0] == 5:  # [5, num_anchors] 格式
            # 转置为 [num_anchors, 5]
            output = output.transpose()
        
        for detection in output:
            # 提取边界框坐标和置信度
            if len(detection) >= 5:
                x_center, y_center, width, height, confidence = detection[:5]
                
                # 过滤低置信度检测
                if confidence >= self.conf_threshold:
                    # 转换为原始图像坐标
                    x_center *= scale_x
                    y_center *= scale_y
                    width *= scale_x
                    height *= scale_y
                    
                    # 计算边界框坐标
                    x1 = int(x_center - width / 2)
                    y1 = int(y_center - height / 2)
                    x2 = int(x_center + width / 2)
                    y2 = int(y_center + height / 2)
                    
                    detections.append({
                        'bbox': (x1, y1, x2, y2),
                        'confidence': float(confidence),
                        'class_id': 0,  # 网球类别ID
                        'center': (int(x_center), int(y_center))
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
        
        # 推理
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})
        
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
