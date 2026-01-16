@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================
echo   CTP程序化交易系统 - 便携版打包工具
echo ============================================
echo.

set "BUILD_DIR=dist\CTP_Trading_System"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip"

:: 清理旧构建
if exist dist rmdir /s /q dist
mkdir "%BUILD_DIR%"

echo [1/6] 下载 Python Embedded...
curl -L -o python-embed.zip "%PYTHON_EMBED_URL%"
if errorlevel 1 (
    echo 错误: 下载 Python 失败，请检查网络
    pause
    exit /b 1
)

echo [2/6] 解压 Python...
powershell -Command "Expand-Archive -Path 'python-embed.zip' -DestinationPath '%BUILD_DIR%\python' -Force"
del python-embed.zip

:: 启用 pip（修改 python311._pth）
echo [3/6] 配置 Python 环境...
set "PTH_FILE=%BUILD_DIR%\python\python311._pth"
echo python311.zip > "%PTH_FILE%"
echo . >> "%PTH_FILE%"
echo Lib\site-packages >> "%PTH_FILE%"
echo import site >> "%PTH_FILE%"

:: 下载 get-pip.py
curl -L -o "%BUILD_DIR%\python\get-pip.py" https://bootstrap.pypa.io/get-pip.py
"%BUILD_DIR%\python\python.exe" "%BUILD_DIR%\python\get-pip.py" --no-warn-script-location
del "%BUILD_DIR%\python\get-pip.py"

echo [4/6] 安装依赖...
:: 创建精简版 requirements（排除测试依赖）
echo openctp-ctp>=6.7.7 > requirements_portable.txt
echo pyyaml>=6.0 >> requirements_portable.txt
echo loguru>=0.7.0 >> requirements_portable.txt
echo fastapi>=0.104.0 >> requirements_portable.txt
echo uvicorn[standard]>=0.24.0 >> requirements_portable.txt
echo jinja2>=3.1.2 >> requirements_portable.txt
echo python-multipart>=0.0.6 >> requirements_portable.txt
echo websockets>=12.0 >> requirements_portable.txt

"%BUILD_DIR%\python\python.exe" -m pip install -r requirements_portable.txt --no-warn-script-location -q
del requirements_portable.txt

echo [5/6] 复制项目文件...
xcopy /E /I /Q ctp_trading_system "%BUILD_DIR%\ctp_trading_system"
:: 清理不必要的文件
if exist "%BUILD_DIR%\ctp_trading_system\__pycache__" rmdir /s /q "%BUILD_DIR%\ctp_trading_system\__pycache__"
if exist "%BUILD_DIR%\ctp_trading_system\logs" rmdir /s /q "%BUILD_DIR%\ctp_trading_system\logs"
if exist "%BUILD_DIR%\ctp_trading_system\test_reports" rmdir /s /q "%BUILD_DIR%\ctp_trading_system\test_reports"
for /d /r "%BUILD_DIR%\ctp_trading_system" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /d /r "%BUILD_DIR%\ctp_trading_system" %%d in (flow*) do @if exist "%%d" rmdir /s /q "%%d"

:: 复制文档
copy CLAUDE.md "%BUILD_DIR%\" >nul 2>&1

echo [6/6] 创建启动脚本...
:: 创建启动脚本
(
echo @echo off
echo chcp 65001 ^>nul
echo cd /d "%%~dp0"
echo echo ============================================
echo echo   CTP程序化交易系统 v1.0
echo echo   符合 T/ZQX 0004-2025 测试指引
echo echo ============================================
echo echo.
echo echo 正在启动 Web 服务...
echo echo 请在浏览器中打开: http://127.0.0.1:8000
echo echo 按 Ctrl+C 停止服务
echo echo.
echo python\python.exe -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000
echo pause
) > "%BUILD_DIR%\启动交易系统.bat"

:: 创建说明文件
(
echo CTP程序化交易系统 - 便携版
echo ============================
echo.
echo 使用方法：
echo 1. 双击运行 "启动交易系统.bat"
echo 2. 在浏览器中打开 http://127.0.0.1:8000
echo 3. 按照界面指引连接CTP服务器
echo.
echo 系统要求：
echo - Windows 10/11 64位
echo - 无需安装Python
echo.
echo 详细文档请查看 ctp_trading_system\docs\ 目录
) > "%BUILD_DIR%\使用说明.txt"

echo.
echo ============================================
echo   打包完成！
echo   输出目录: dist\CTP_Trading_System
echo ============================================
echo.

:: 计算大小
for /f "tokens=3" %%a in ('dir /s "%BUILD_DIR%" ^| findstr "个文件"') do set SIZE=%%a
echo 文件夹大小: 约 %SIZE% 字节

echo.
echo 是否压缩为 zip 文件？
choice /c YN /m "选择"
if errorlevel 2 goto :end
if errorlevel 1 (
    echo 正在压缩...
    powershell -Command "Compress-Archive -Path '%BUILD_DIR%' -DestinationPath 'dist\CTP_Trading_System.zip' -Force"
    echo 已生成: dist\CTP_Trading_System.zip
)

:end
echo.
pause
