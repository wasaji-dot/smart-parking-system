# ocrutil.py 完整修复版（直接复制替换）
# coding:utf-8
from aip import AipOcr
import os

# 替换成你的百度OCR密钥

APP_ID='122367578'
API_KEY='45GCIEMwtMF9sRlcDOaRGBOy'
SECRET_KEY='xbpkHlNTPg9ygoS1cXvOUj1KtXIKKIwZ'

# 初始化百度OCR客户端
client = AipOcr(APP_ID, API_KEY, SECRET_KEY)


def get_file_content(filepath):
    """读取图片文件（二进制）"""
    try:
        with open(filepath, 'rb') as file:
            return file.read()
    except Exception as e:
        print(f"读取图片失败：{e}")
        return None


def getcn(img_path="./file/test2.jpg"):
    """
    识别车牌，兼容单/多车牌返回格式
    :param img_path: 图片路径，默认使用摄像头抓拍的test2.jpg
    :return: 车牌号/None
    """
    global client
    if not client:
        print("OCR客户端初始化失败，请检查密钥！")
        return None

    try:
        # 1. 读取图片
        image = get_file_content(img_path)
        if not image:
            print(f"图片读取为空：{img_path}")
            return None

        # 2. 调用百度车牌识别接口（移除废弃的multi_detect参数）
        options = {
            "detect_direction": True  # 仅保留方向检测
        }
        results = client.licensePlate(image, options)
        print("OCR原始返回：", results)

        # 3. 处理错误
        if 'error_msg' in results:
            print(f"百度OCR接口错误：{results['error_msg']}")
            return None

        # 4. 兼容单/多车牌返回格式
        words_result = results.get('words_result', None)
        if not words_result:
            print("OCR未识别到任何车牌")
            return None

        if isinstance(words_result, list):
            # 多车牌：取第一个有效车牌
            return words_result[0]['number'] if words_result else None
        else:
            # 单车牌：直接取
            return words_result['number']

    except FileNotFoundError:
        print(f"图片文件不存在：{img_path}")
        return None
    except KeyError as e:
        print(f"OCR结果解析失败（缺少字段）：{e}")
        return None
    except Exception as e:
        print(f"OCR识别异常：{str(e)}")
        return None


# 测试代码（可选）
if __name__ == "__main__":
    test_result = getcn("./file/test2.jpg")
    print(f"测试识别结果：{test_result}")
