@echo off
REM CTP Wrapper 编译脚本 (Windows MSVC)
REM 使用方法: 在 Visual Studio Developer Command Prompt 中运行

echo ============================================
echo CTP Wrapper Build Script
echo ============================================

set SRC_DIR=%~dp0src
set CTP_DIR=%~dp0..\Sim\v6.6.8_T1_20220520_winApi\tradeapi\20220520_tradeapi64_se_windows
set OUT_DIR=%~dp0python

echo Source Dir: %SRC_DIR%
echo CTP API Dir: %CTP_DIR%
echo Output Dir: %OUT_DIR%

REM 检查CTP API目录
if not exist "%CTP_DIR%\ThostFtdcTraderApi.h" (
    echo ERROR: CTP API headers not found!
    echo Expected: %CTP_DIR%\ThostFtdcTraderApi.h
    exit /b 1
)

REM 创建输出目录
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo.
echo Compiling ctp_wrapper.dll ...

REM 编译
cl.exe /nologo /EHsc /MD /O2 ^
    /DCTP_WRAPPER_EXPORTS ^
    /D_CRT_SECURE_NO_WARNINGS ^
    /I"%SRC_DIR%" ^
    /I"%CTP_DIR%" ^
    "%SRC_DIR%\ctp_wrapper.cpp" ^
    /link /DLL ^
    /LIBPATH:"%CTP_DIR%" ^
    thosttraderapi_se.lib ^
    /OUT:"%OUT_DIR%\ctp_wrapper.dll"

if errorlevel 1 (
    echo.
    echo ERROR: Compilation failed!
    exit /b 1
)

REM 复制CTP DLL
echo Copying CTP DLL...
copy /Y "%CTP_DIR%\thosttraderapi_se.dll" "%OUT_DIR%\"

REM 清理临时文件
del /Q ctp_wrapper.obj 2>nul
del /Q ctp_wrapper.exp 2>nul
del /Q ctp_wrapper.lib 2>nul

echo.
echo ============================================
echo Build successful!
echo Output: %OUT_DIR%\ctp_wrapper.dll
echo ============================================
