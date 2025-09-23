# 网球实时检测系统

基于YOLOv11 ONNX模型的实时网球检测程序，专为树莓派4B Ubuntu 24.04优化。

## 安装依赖

在项目根目录下使用uv安装依赖：

```bash
# 同步依赖
uv sync

# 或者手动安装依赖
uv add opencv-python numpy onnxruntime Pillow
```

## 使用方法

### 基本使用

在vision目录下运行：

```bash
cd vision
uv run python camera_detector.py
```

### 高级参数

```bash
# 指定模型路径和摄像头ID
uv run python camera_detector.py --model model/best.onnx --camera 0

# 调整置信度阈值
uv run python camera_detector.py --conf 0.3

# 保存检测视频
uv run python camera_detector.py --save-video --output tennis_detection.avi

# 不显示FPS
uv run python camera_detector.py --no-fps
```

### 参数说明

- `--model`: ONNX模型文件路径 (默认: model/best.onnx)
- `--camera`: USB摄像头ID (默认: 0)
- `--conf`: 置信度阈值 (默认: 0.5)
- `--save-video`: 保存检测视频
- `--output`: 输出视频文件名 (默认: tennis_detection.avi)
- `--no-fps`: 不显示FPS信息

### 运行时按键

- `q`: 退出程序
- `s`: 保存当前检测帧为图片
- `f`: 切换FPS显示开关

## 程序特性

- **实时检测**: 使用USB摄像头进行实时网球检测
- **高效推理**: 针对树莓派CPU优化的ONNX Runtime
- **可视化结果**: 实时显示检测框、置信度和网球中心位置
- **性能监控**: 显示FPS和推理时间
- **灵活配置**: 可调整置信度阈值和NMS参数

## 文件结构

```
vision/
├── model/
│   └── best.onnx          # YOLOv11训练的ONNX模型
├── yolo_detector.py       # YOLOv11检测器核心类
├── camera_detector.py     # 摄像头实时检测主程序
└── README.md             # 使用说明
```

## 故障排除

### 摄像头问题
- 确保USB摄像头已连接并被系统识别
- 检查摄像头权限: `ls -la /dev/video*`
- 尝试不同的摄像头ID: `--camera 1` 或 `--camera 2`

### 性能优化
- 降低摄像头分辨率以提高帧率
- 调整置信度阈值以减少误检
- 确保树莓派有足够的散热

### 模型问题
- 确认模型文件路径正确
- 检查模型是否为YOLOv11格式且输入尺寸为640x640
