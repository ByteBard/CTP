@echo off
REM ============================================================
REM CTP Trading System - 官方 v6.6.8 API 打包脚本
REM ============================================================
REM 使用官方 CTP v6.6.8 API (非 openctp)
REM API 来源: Sim\v6.6.8_T1_20220520_winApi\tradeapi\20220520_tradeapi64_se_windows
REM ============================================================

echo ============================================================
echo CTP Trading System - Official v6.6.8 API Build
echo ============================================================

set ROOT_DIR=%~dp0
set DIST_DIR=%ROOT_DIR%dist\CTP_Official_v6.6.8
set CTP_WRAPPER=%ROOT_DIR%ctp_wrapper\python
set CTP_API=%ROOT_DIR%Sim\v6.6.8_T1_20220520_winApi\tradeapi\20220520_tradeapi64_se_windows

echo.
echo [1/5] Checking ctp_wrapper.dll...
if not exist "%CTP_WRAPPER%\ctp_wrapper.dll" (
    echo ERROR: ctp_wrapper.dll not found!
    echo Please run: ctp_wrapper\build.bat first
    exit /b 1
)
echo OK: ctp_wrapper.dll found

echo.
echo [2/5] Creating distribution directory...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
mkdir "%DIST_DIR%\ctp_trading_system"
mkdir "%DIST_DIR%\ctp_trading_system\ctp_api"
mkdir "%DIST_DIR%\logs"

echo.
echo [3/5] Copying source files...
REM Copy main package
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\*.py" "%DIST_DIR%\ctp_trading_system\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\config" "%DIST_DIR%\ctp_trading_system\config\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\core" "%DIST_DIR%\ctp_trading_system\core\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\monitor" "%DIST_DIR%\ctp_trading_system\monitor\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\validator" "%DIST_DIR%\ctp_trading_system\validator\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\alert" "%DIST_DIR%\ctp_trading_system\alert\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\emergency" "%DIST_DIR%\ctp_trading_system\emergency\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\trade_logging" "%DIST_DIR%\ctp_trading_system\trade_logging\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\web" "%DIST_DIR%\ctp_trading_system\web\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\strategy" "%DIST_DIR%\ctp_trading_system\strategy\" >nul
xcopy /E /I /Y "%ROOT_DIR%ctp_trading_system\tests" "%DIST_DIR%\ctp_trading_system\tests\" >nul

REM Copy ctp_api module
copy /Y "%ROOT_DIR%ctp_trading_system\ctp_api\*.py" "%DIST_DIR%\ctp_trading_system\ctp_api\" >nul

echo.
echo [4/5] Copying CTP v6.6.8 DLLs...
copy /Y "%CTP_WRAPPER%\ctp_wrapper.dll" "%DIST_DIR%\ctp_trading_system\ctp_api\" >nul
copy /Y "%CTP_WRAPPER%\thosttraderapi_se.dll" "%DIST_DIR%\ctp_trading_system\ctp_api\" >nul
REM Copy MdApi DLLs (optional)
if exist "%CTP_WRAPPER%\ctp_md_wrapper.dll" (
    copy /Y "%CTP_WRAPPER%\ctp_md_wrapper.dll" "%DIST_DIR%\ctp_trading_system\ctp_api\" >nul
    echo OK: ctp_md_wrapper.dll copied
)
if exist "%CTP_WRAPPER%\thostmduserapi_se.dll" (
    copy /Y "%CTP_WRAPPER%\thostmduserapi_se.dll" "%DIST_DIR%\ctp_trading_system\ctp_api\" >nul
    echo OK: thostmduserapi_se.dll copied
)

echo.
echo [5/5] Creating launcher script...
(
echo @echo off
echo REM CTP Trading System Launcher - Official v6.6.8 API
echo cd /d %%~dp0
echo python -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000
echo pause
) > "%DIST_DIR%\start_server.bat"

echo.
echo ============================================================
echo Build completed successfully!
echo ============================================================
echo.
echo Output directory: %DIST_DIR%
echo.
echo API Version: CTP v6.6.8 (Official)
echo API Source: Sim\v6.6.8_T1_20220520_winApi
echo.
echo Files:
echo   - ctp_wrapper.dll (custom wrapper)
echo   - thosttraderapi_se.dll (official v6.6.8)
echo.
echo To run: cd %DIST_DIR% ^&^& start_server.bat
echo ============================================================

dir "%DIST_DIR%\ctp_trading_system\ctp_api\*.dll"
