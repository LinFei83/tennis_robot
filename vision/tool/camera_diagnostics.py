#!/usr/bin/env python3
"""
摄像头诊断工具
用于检测摄像头支持的属性和参数范围
"""

import cv2
import sys

def get_camera_properties():
    """获取摄像头支持的所有属性"""
    
    # OpenCV摄像头属性映射
    camera_properties = {
        cv2.CAP_PROP_BRIGHTNESS: "brightness",
        cv2.CAP_PROP_CONTRAST: "contrast", 
        cv2.CAP_PROP_SATURATION: "saturation",
        cv2.CAP_PROP_HUE: "hue",
        cv2.CAP_PROP_GAIN: "gain",
        cv2.CAP_PROP_EXPOSURE: "exposure",
        cv2.CAP_PROP_AUTO_EXPOSURE: "auto_exposure",
        cv2.CAP_PROP_GAMMA: "gamma",
        cv2.CAP_PROP_TEMPERATURE: "temperature",
        cv2.CAP_PROP_WHITE_BALANCE_BLUE_U: "white_balance_blue",
        cv2.CAP_PROP_WHITE_BALANCE_RED_V: "white_balance_red",
        cv2.CAP_PROP_ZOOM: "zoom",
        cv2.CAP_PROP_FOCUS: "focus",
        cv2.CAP_PROP_AUTOFOCUS: "autofocus",
        cv2.CAP_PROP_BACKLIGHT: "backlight",
        cv2.CAP_PROP_PAN: "pan",
        cv2.CAP_PROP_TILT: "tilt",
        cv2.CAP_PROP_SHARPNESS: "sharpness",
        cv2.CAP_PROP_AUTO_WB: "auto_white_balance",
        cv2.CAP_PROP_WB_TEMPERATURE: "wb_temperature",
    }
    
    return camera_properties

def diagnose_camera(camera_index=0):
    """诊断指定摄像头的属性"""
    print(f"正在诊断摄像头 {camera_index}...")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"错误: 无法打开摄像头 {camera_index}")
        return
    
    print(f"摄像头 {camera_index} 已成功打开\n")
    
    # 获取基本信息
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print("=== 基本信息 ===")
    print(f"分辨率: {int(width)} x {int(height)}")
    print(f"帧率: {fps}")
    print()
    
    # 检查所有属性
    camera_properties = get_camera_properties()
    
    print("=== 支持的属性 ===")
    supported_properties = {}
    
    for prop_id, prop_name in camera_properties.items():
        try:
            current_value = cap.get(prop_id)
            # 检查属性是否真正支持（某些属性可能返回默认值但实际不支持）
            if current_value != -1:
                supported_properties[prop_name] = {
                    'id': prop_id,
                    'current_value': current_value
                }
                print(f"{prop_name:20}: {current_value}")
        except Exception as e:
            pass
    
    print()
    
    # 特别检查曝光相关属性
    print("=== 曝光相关详细信息 ===")
    exposure_props = [
        (cv2.CAP_PROP_EXPOSURE, "exposure"),
        (cv2.CAP_PROP_AUTO_EXPOSURE, "auto_exposure"),
        (cv2.CAP_PROP_GAIN, "gain"),
        (cv2.CAP_PROP_BRIGHTNESS, "brightness"),
    ]
    
    for prop_id, prop_name in exposure_props:
        current_value = cap.get(prop_id)
        print(f"{prop_name:15}: {current_value}")
        
        # 尝试设置不同值来测试范围
        if prop_name == "exposure":
            print(f"  测试曝光范围:")
            test_values = [-15, -10, -6, -3, -1, 0]
            for test_val in test_values:
                cap.set(prop_id, test_val)
                actual_val = cap.get(prop_id)
                print(f"    设置 {test_val:3} -> 实际 {actual_val}")
        
        elif prop_name == "auto_exposure":
            print(f"  测试自动曝光模式:")
            test_modes = [0.25, 0.75]  # 手动模式, 自动模式
            for test_mode in test_modes:
                cap.set(prop_id, test_mode)
                actual_mode = cap.get(prop_id)
                mode_desc = "手动" if test_mode == 0.25 else "自动"
                print(f"    设置 {mode_desc} ({test_mode}) -> 实际 {actual_mode}")
    
    print()
    
    # 测试实时曝光调整效果
    print("=== 实时曝光测试 ===")
    print("按 'q' 退出测试")
    print("按 '1' 降低曝光")
    print("按 '2' 增加曝光")
    print("按 '3' 切换自动/手动曝光")
    
    current_exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
    auto_exposure_mode = 0.25  # 开始使用手动模式
    
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exposure_mode)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头画面")
            break
        
        # 显示当前设置
        exposure_val = cap.get(cv2.CAP_PROP_EXPOSURE)
        auto_exp_val = cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)
        
        info_text = f"Exposure: {exposure_val:.2f}, Auto: {auto_exp_val:.2f}"
        cv2.putText(frame, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Camera Exposure Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('1'):  # 降低曝光
            current_exposure -= 1
            cap.set(cv2.CAP_PROP_EXPOSURE, current_exposure)
            print(f"设置曝光为: {current_exposure}")
        elif key == ord('2'):  # 增加曝光
            current_exposure += 1
            cap.set(cv2.CAP_PROP_EXPOSURE, current_exposure)
            print(f"设置曝光为: {current_exposure}")
        elif key == ord('3'):  # 切换自动/手动模式
            auto_exposure_mode = 0.75 if auto_exposure_mode == 0.25 else 0.25
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exposure_mode)
            mode_desc = "自动" if auto_exposure_mode == 0.75 else "手动"
            print(f"切换到{mode_desc}曝光模式")
    
    # 清理
    cap.release()
    cv2.destroyAllWindows()
    
    return supported_properties

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='摄像头诊断工具')
    parser.add_argument('--camera', '-c', type=int, default=0, help='摄像头索引 (默认: 0)')
    
    args = parser.parse_args()
    
    try:
        supported_props = diagnose_camera(args.camera)
        
        print("\n=== 诊断完成 ===")
        print("支持的属性数量:", len(supported_props) if supported_props else 0)
        
    except KeyboardInterrupt:
        print("\n诊断被用户中断")
    except Exception as e:
        print(f"诊断过程中出现错误: {e}")

if __name__ == "__main__":
    main()
