# CTP程序化交易系统

符合 **T/ZQX 0004-2025《期货程序化交易系统功能测试指引》** 标准的CTP程序化交易系统。

## 项目信息

- **开发语言**: Python 3.8+
- **CTP版本**: v6.6.8 (官方 API)
- **状态**: 已完成全部功能测试 (36/36 通过)

## 快速启动

### 1. 编译 CTP Wrapper（首次需要）

需要 Visual Studio 2022：

```cmd
cd ctp_wrapper
build.bat
```

### 2. 打包

```cmd
build_official_api.bat
```

### 3. 运行

```cmd
cd dist\CTP_Official_v6.6.8
python -m uvicorn ctp_trading_system.web.app:app --host 127.0.0.1 --port 8000
```

访问 http://127.0.0.1:8000

## 运行测试

```cmd
# 启动服务后，在另一个终端运行
python -m pytest ctp_trading_system/tests/test_api_assessment.py -v
```

## 项目结构

```
CTP/
├── build_official_api.bat      # 打包脚本
├── ctp_wrapper/                # CTP C++ 封装
│   ├── build.bat               # 编译脚本
│   └── python/                 # 编译输出
├── Sim/                        # 官方 v6.6.8 API
├── ctp_trading_system/         # 主项目
│   ├── ctp_api/                # Python 封装
│   ├── core/                   # 核心模块
│   ├── web/                    # Web UI
│   └── tests/                  # 测试用例
└── CLAUDE.md                   # 详细文档
```

## API 架构

```
Python → ctp_wrapper.dll → thosttraderapi_se.dll (官方 v6.6.8)
```

## 依赖安装

```bash
pip install pyyaml loguru fastapi uvicorn jinja2 python-multipart websockets httpx pytest
```

## 详细文档

查看 [CLAUDE.md](CLAUDE.md) 获取完整文档。

## 许可证

本项目仅供学习参考，使用时请遵守 CTP API 使用协议及相关监管要求。
