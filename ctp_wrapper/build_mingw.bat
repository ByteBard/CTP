@echo off
REM CTP Wrapper 编译脚本 (MinGW-w64)
REM 使用方法: 确保 MinGW-w64 的 bin 目录在 PATH 中

echo ============================================
echo CTP Wrapper Build Script (MinGW-w64)
echo ============================================

set SRC_DIR=%~dp0src
set CTP_DIR=%~dp0..\Sim\v6.6.8_T1_20220520_winApi\tradeapi\20220520_tradeapi64_se_windows
set OUT_DIR=%~dp0python

echo Source Dir: %SRC_DIR%
echo CTP API Dir: %CTP_DIR%
echo Output Dir: %OUT_DIR%

REM 检查g++
where g++ >nul 2>&1
if errorlevel 1 (
    echo ERROR: g++ not found! Please install MinGW-w64 and add to PATH.
    exit /b 1
)

REM 检查CTP API目录
if not exist "%CTP_DIR%\ThostFtdcTraderApi.h" (
    echo ERROR: CTP API headers not found!
    exit /b 1
)

REM 创建输出目录
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo.
echo Compiling ctp_wrapper.dll ...

REM 编译
g++ -shared -o "%OUT_DIR%\ctp_wrapper.dll" ^
    -DCTP_WRAPPER_EXPORTS ^
    -I"%SRC_DIR%" ^
    -I"%CTP_DIR%" ^
    "%SRC_DIR%\ctp_wrapper.cpp" ^
    -L"%CTP_DIR%" ^
    -lthosttraderapi_se ^
    -static-libgcc -static-libstdc++

if errorlevel 1 (
    echo.
    echo ERROR: Compilation failed!
    exit /b 1
)

REM 复制CTP DLL
echo Copying CTP DLL...
copy /Y "%CTP_DIR%\thosttraderapi_se.dll" "%OUT_DIR%\"

echo.
echo ============================================
echo Build successful!
echo Output: %OUT_DIR%\ctp_wrapper.dll
echo ============================================
