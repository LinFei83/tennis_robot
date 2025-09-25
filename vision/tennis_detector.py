#!/usr/bin/env python3
"""
网球检测器模块 - TensorFlow Lite 量化模型推理
"""

import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import os
from datetime import datetime


class TennisDetector:
    """网球检测器类，负责模型加载、推理和结果处理"""
    
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
        
        self._load_model()
        self._print_model_info()
        
    def _load_model(self):
        """加载TensorFlow Lite模型并获取输入输出信息"""
        try:
            self.interpreter = tflite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # 获取输入输出详情
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            
            # 获取输入参数
            self.input_height = self.input_details[0]['shape'][1]
            self.input_width = self.input_details[0]['shape'][2]
            self.input_dtype = self.input_details[0]['dtype']
            
            # 获取量化参数 - 处理float32模型没有量化参数的情况
            input_quant_params = self.input_details[0].get('quantization_parameters', {})
            output_quant_params = self.output_details[0].get('quantization_parameters', {})
            
            # 安全获取量化参数
            input_scales = input_quant_params.get('scales', [1.0])
            input_zero_points = input_quant_params.get('zero_points', [0])
            output_scales = output_quant_params.get('scales', [1.0])
            output_zero_points = output_quant_params.get('zero_points', [0])
            
            self.input_scale = input_scales[0] if len(input_scales) > 0 else 1.0
            self.input_zero_point = input_zero_points[0] if len(input_zero_points) > 0 else 0
            self.output_scale = output_scales[0] if len(output_scales) > 0 else 1.0
            self.output_zero_point = output_zero_points[0] if len(output_zero_points) > 0 else 0
            self.output_dtype = self.output_details[0]['dtype']
            
            
        except Exception as e:
            print(f"模型加载失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    def _print_model_info(self):
        """打印模型信息"""
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
        # 调整图像尺寸
        current_height, current_width = image.shape[:2]
        if current_width != self.input_width or current_height != self.input_height:
            resized_image = cv2.resize(image, (self.input_width, self.input_height))
        else:
            resized_image = image
        
        # 数据类型转换和量化
        if self.input_dtype == np.int8:
            # int8量化模型预处理
            input_image = np.array(resized_image, dtype=np.float32) / 255.0
            input_image = input_image / self.input_scale + self.input_zero_point
            input_image = np.clip(input_image, -128, 127).astype(np.int8)
        else:
            # float32模型预处理
            input_image = np.array(resized_image, dtype=np.float32) / 255.0
        
        return np.expand_dims(input_image, axis=0)
    
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
        try:
            if output.shape[0] == 0:
                print("警告: 模型输出为空")
                return [], []
                
            output = output[0].T
            
            # 解析输出
            boxes_xywh = output[..., :4]
            scores = np.max(output[..., 4:], axis=1)
            
            
        except Exception as e:
            print(f"后处理解析输出时出错: {e}")
            return [], []
        
        # NMS去重
        indices = cv2.dnn.NMSBoxes(
            boxes_xywh.tolist(), 
            scores.tolist(), 
            self.confidence_threshold, 
            self.iou_threshold
        )
        
        filtered_boxes = []
        filtered_scores = []
        
        # 检查indices是否为空或格式问题
        if len(indices) > 0 and indices is not None:
            # 处理不同版本OpenCV返回格式的差异
            if isinstance(indices, tuple):
                indices_list = indices
            else:
                indices_list = indices.flatten() if hasattr(indices, 'flatten') else indices
                
            for i in indices_list:
                if scores[i] >= self.confidence_threshold:
                    x_center, y_center, width, height = boxes_xywh[i]
                    
                    # 转换为绝对坐标并限制在图像范围内
                    x1 = max(0, min(int((x_center - width / 2) * original_width), original_width))
                    y1 = max(0, min(int((y_center - height / 2) * original_height), original_height))
                    x2 = max(0, min(int((x_center + width / 2) * original_width), original_width))
                    y2 = max(0, min(int((y_center + height / 2) * original_height), original_height))
                    
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
        try:
            original_height, original_width = image.shape[:2]
            # 预处理
            input_image = self.preprocess_image(image)
            
            # 推理
            self.interpreter.set_tensor(self.input_details[0]['index'], input_image)
            self.interpreter.invoke()
            
            # 获取输出并反量化
            output = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            if self.output_dtype == np.int8:
                output = output.astype(np.float32)
                output = (output - self.output_zero_point) * self.output_scale
            
            # 后处理
            return self.postprocess_output(output, original_width, original_height)
            
        except Exception as e:
            print(f"检测过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
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
            
            # 绘制标签背景和文本
            cv2.rectangle(annotated_image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(annotated_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        return annotated_image
    
    def save_screenshot(self, image, screenshot_type="full", base_dir="screenshot"):
        """
        保存截图
        
        Args:
            image: 要保存的图像
            screenshot_type: 截图类型 ("full" 或 "raw")
            base_dir: 基础保存目录
        """
        dir_name = "full_screenshots" if screenshot_type == "full" else "raw_images"
        save_dir = os.path.join(base_dir, dir_name)
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{screenshot_type}_screenshot_{timestamp}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        cv2.imwrite(filepath, image)
        print(f"{'完整' if screenshot_type == 'full' else '原始'}截图已保存: {filepath}")
