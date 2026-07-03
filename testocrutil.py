import cv2
from ocrutil import plate_ocr

# 读取测试车牌图像（确保test_plate.jpg与脚本同目录，或填写完整路径）
img = cv2.imread("test_plate.jpg")
if img is None:
    print("图像读取失败，请检查图片路径或名称")
else:
    # 调用OCR识别函数
    plate_number = plate_ocr(img)
    print(f"OCR识别结果：{plate_number}")
    # 验证识别准确性
    expected_plate = "粤K98A25"
    if plate_number == expected_plate:
        print("OCR识别准确")
    else:
        print(f"OCR识别错误，预期：{expected_plate}，实际：{plate_number}，需优化训练数据或算法")