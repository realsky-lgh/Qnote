@echo off
rem ===================================================
rem Qnote Windows Standalone Binary Build Script
rem Produces dist\Qnote.exe
rem ===================================================

echo [1/3] 检查构建环境与依赖...
python -m pip install --upgrade pip
pip install PyQt6 pynput pyinstaller

echo [2/3] 开始打包独立二进制 Qnote.exe...
pyinstaller --name Qnote ^
    --onefile ^
    --windowed ^
    --icon resources\qnote.png ^
    --add-data "resources\qnote.png;resources" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import PyQt6.QtNetwork ^
    --hidden-import pynput.keyboard ^
    --hidden-import pynput.keyboard._win32 ^
    --collect-all qnote ^
    main.py

echo [3/3] 打包完成！独立二进制位于 dist\Qnote.exe
pause
