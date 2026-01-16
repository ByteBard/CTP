@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   CTP程序化交易系统 - 便携版启动器
echo ============================================
echo.

set "DIST_DIR=%~dp0dist"
set "APP_DIR=%DIST_DIR%\CTP_Trading_System"
set "ZIP_FILE=%DIST_DIR%\CTP_Trading_System.zip"

:: 检查zip文件是否存在
if not exist "%ZIP_FILE%" (
    echo 错误: 找不到 %ZIP_FILE%
    echo 请先运行 git pull 获取最新代码
    pause
    exit /b 1
)

:: 检查是否需要解压
if not exist "%APP_DIR%\python\python.exe" (
    echo [1/2] 首次运行，正在解压便携版...
    powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%DIST_DIR%' -Force"
    if errorlevel 1 (
        echo 解压失败！
        pause
        exit /b 1
    )
    echo 解压完成！
    echo.
) else (
    echo [1/2] 检测到已解压的便携版
)

:: 启动应用
echo [2/2] 启动交易系统...
echo.
echo ============================================
echo   Web服务地址: http://127.0.0.1:8000
echo   按 Ctrl+C 停止服务
echo ============================================
echo.

cd /d "%APP_DIR%"
python\python.exe -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000

pause
