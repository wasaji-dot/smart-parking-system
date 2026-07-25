# -*- coding: utf-8 -*-  ## 指定文件编码为UTF-8，确保中文字符正常显示
import os  ## 导入操作系统接口模块，用于文件路径操作
import sys  ## 导入系统相关参数和函数模块
from PyInstaller.building.api import EXE, PYZ  ## 从PyInstaller导入EXE和PYZ构建类
from PyInstaller.building.build_main import Analysis  ## 从PyInstaller导入分析主类
from PyInstaller.utils.hooks import collect_data_files, collect_submodules  ## 从PyInstaller导入钩子函数

# 获取项目根目录  ## 注释说明
project_root = r"E:\FZWJ\miniconda\停车场管理2.0"  ## 设置项目根目录路径，使用原始字符串避免转义问题

# 分析主程序及依赖  ## 注释说明
a = Analysis(  ## 创建Analysis对象，分析程序依赖
    ['main.py'],  ## 指定主程序入口文件
    pathex=[project_root],  ## 添加项目根目录到Python路径
    binaries=[],  ## 指定二进制文件列表（空列表）
    datas=[  ## 指定需要打包的数据文件列表
        # 打包自定义模块  ## 注释说明
        (os.path.join(project_root, 'btn.py'), '.'),  ## 打包按钮模块到根目录
        (os.path.join(project_root, 'db_utils.py'), '.'),  ## 打包数据库工具模块到根目录
        (os.path.join(project_root, 'ocrutil.py'), '.'),  ## 打包OCR工具模块到根目录
        (os.path.join(project_root, 'timeutil.py'), '.'),  ## 打包时间工具模块到根目录
        # 打包数据文件夹  ## 注释说明
        (os.path.join(project_root, 'datafile'), 'datafile'),  ## 打包数据文件夹到输出目录的datafile文件夹
        (os.path.join(project_root, 'file'), 'file'),  ## 打包文件文件夹到输出目录的file文件夹
        # 打包数据库文件  ## 注释说明
        (os.path.join(project_root, 'parking.db'), '.')  ## 打包数据库文件到根目录
    ],
    hiddenimports=[  ## 指定隐藏导入的模块列表（PyInstaller无法自动检测到的依赖）
        'pandas', 'pygame', 'cv2', 'matplotlib',  ## 显式导入主要依赖库
        'pandas._libs.tslibs.np_datetime',  ## 导入pandas时间处理相关子模块
        'pandas._libs.tslibs.timedeltas',  ## 导入pandas时间差相关子模块
        'pandas._libs.tslibs.offsets',  ## 导入pandas时间偏移相关子模块
        'pandas._libs.tslibs.parsing',  ## 导入pandas时间解析相关子模块
        'pandas._libs.tslibs.conversion'  ## 导入pandas时间转换相关子模块
    ],
    hookspath=[],  ## 指定自定义钩子文件路径列表（空列表）
    hooksconfig={},  ## 指定钩子配置字典（空字典）
    runtime_hooks=[],  ## 指定运行时钩子列表（空列表）
    excludes=[],  ## 指定要排除的模块列表（空列表）
    win_no_prefer_redirects=False,  ## Windows相关设置：不优先使用重定向
    win_private_assemblies=False,  ## Windows相关设置：不使用私有程序集
    cipher=None,  ## 指定加密密钥（无加密）
    noarchive=False  ## 不创建归档文件（正常打包模式）
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)  ## 创建PYZ归档文件，包含纯Python模块

# 配置可执行文件信息（已添加图标路径）  ## 注释说明
exe = EXE(  ## 创建EXE可执行文件配置
    pyz,  ## 传入PYZ归档文件
    a.scripts,  ## 传入分析得到的脚本
    a.binaries,  ## 传入分析得到的二进制文件
    a.zipfiles,  ## 传入分析得到的zip文件
    a.datas,  ## 传入分析得到的数据文件
    [],  ## 空列表（保留参数）
    name='智能停车场系统',  ## 设置生成的exe文件名
    debug=False,  ## 关闭调试模式
    bootloader_ignore_signals=False,  ## 启动加载器不忽略信号
    strip=False,  ## 不剥离符号（减小文件大小但可能影响调试）
    upx=True,  ## 启用UPX压缩以减小exe文件大小
    upx_exclude=[],  ## UPX排除文件列表（空列表）
    runtime_tmpdir=None,  ## 运行时临时目录（无特殊设置）
    console=True,  ## 显示控制台窗口（调试时方便查看输出）
    disable_windowed_traceback=False,  ## 不禁用窗口化 traceback
    argv_emulation=False,  ## 不启用参数模拟
    target_arch=None,  ## 目标架构（自动检测）
    codesign_identity=None,  ## 代码签名标识（无）
    entitlements_file=None,  ## 权限文件（无）
    icon=r"E:\FZWJ\miniconda\停车场管理2.0\tubiao.ico"  ## 设置exe文件图标路径
)