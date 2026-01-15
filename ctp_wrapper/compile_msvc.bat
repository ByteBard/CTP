@echo off
echo ============================================
echo Compiling ctp_wrapper.dll with MSVC
echo ============================================

call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 (
    echo ERROR: Failed to set up MSVC environment
    exit /b 1
)

cd /d D:\CTP\ctp_wrapper
echo Current directory: %CD%

echo.
echo Compiling...
cl /EHsc /LD /DCTP_WRAPPER_EXPORTS ^
   /I"src" ^
   /I"include" ^
   /I"..\Sim\v6.6.8_T1_20220520_winApi\tradeapi\20220520_tradeapi64_se_windows" ^
   src\ctp_wrapper.cpp ^
   /link ^
   /LIBPATH:"..\Sim\v6.6.8_T1_20220520_winApi\tradeapi\20220520_tradeapi64_se_windows" ^
   thosttraderapi_se.lib ^
   /OUT:python\ctp_wrapper.dll

if errorlevel 1 (
    echo.
    echo ERROR: Compilation failed!
    exit /b 1
)

echo.
echo ============================================
echo Compilation successful!
echo Output: python\ctp_wrapper.dll
echo ============================================

copy /Y "..\Sim\v6.6.8_T1_20220520_winApi\tradeapi\20220520_tradeapi64_se_windows\thosttraderapi_se.dll" python\
echo Copied thosttraderapi_se.dll to python\

dir python\*.dll
