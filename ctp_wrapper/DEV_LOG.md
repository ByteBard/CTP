# CTP Wrapper 开发日志

## 项目概述
将 CTP v6.6.8 C++ API 封装为 C 接口，再通过 Python ctypes 调用。

## 2026-01-14 开发记录

### 14:37 - 项目初始化
- 创建项目目录结构
  ```
  ctp_wrapper/
  ├── src/           # C++ 源代码
  ├── include/       # 头文件
  ├── build/         # 编译输出
  └── python/        # Python 封装
  ```

### 14:38 - C++ 包装层
- 创建 `src/ctp_wrapper.h` - C 接口头文件
  - 定义回调函数类型
  - 定义 TraderCallbacks 结构体
  - 声明 API 函数

- 创建 `src/ctp_wrapper.cpp` - 实现文件
  - TraderSpiWrapper 类：继承 CThostFtdcTraderSpi
  - ApiWrapper 结构：持有 API 和 Spi 实例
  - C 接口实现：CreateTraderApi, RegisterCallbacks, ReqAuthenticate 等

### 14:39 - 构建配置
- 创建 `CMakeLists.txt` - CMake 构建配置
- 创建 `build.bat` - MSVC 编译脚本
- 创建 `build_mingw.bat` - MinGW 编译脚本

### 14:40 - Python 封装
- 创建 `python/ctp_api.py`
  - Logger 类：日志记录
  - 回调函数类型定义 (CFUNCTYPE)
  - TraderCallbacks 结构体
  - CTPTraderApi 类：主要封装类
    - create_api() - 创建 API 实例
    - register_front() - 注册前置地址
    - req_authenticate() - 认证请求
    - req_user_login() - 登录请求
    - 等等...

## 待完成
- [ ] 编写登录测试脚本
- [ ] 编译生成 DLL
- [ ] 完整测试

## 技术要点

### 为什么需要 C++ 包装层？
CTP API 是 C++ 接口，使用虚函数实现回调。Python ctypes 无法直接：
1. 创建 C++ 对象
2. 继承 C++ 类
3. 处理虚函数表

解决方案：C++ 包装层导出 C 函数，内部处理 C++ 细节。

### 回调机制
```
Python 回调函数 → ctypes CFUNCTYPE → C 函数指针 → C++ TraderSpiWrapper → CTP API
```

### 编码问题
CTP 使用 GBK 编码，Python 字符串需要：
- 发送时：`str.encode('gbk')`
- 接收时：`bytes.decode('gbk')`
