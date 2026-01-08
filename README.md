# CTP交易接口最小Demo

本目录包含三套CTP交易接口的最小可运行示例，分别使用C++、C#和Python实现。

## 📁 文件说明

- `cpp_minimal_demo.cpp` - C++版本最小Demo
- `csharp_minimal_demo.cs` - C#版本最小Demo
- `python_minimal_demo.py` - Python版本最小Demo
- `README.md` - 本说明文档

## 🎯 功能说明

所有三个版本实现了相同的基础功能：

1. ✅ 连接到CTP交易前置
2. ✅ 用户登录认证
3. ✅ 查询合约信息
4. ✅ 错误处理和日志输出

## 🚀 快速开始

### C++ 版本

#### 前置要求
- Visual Studio 2015+ (Windows) 或 GCC 4.8+ (Linux)
- CTP API库文件（从期货公司或上期所官网获取）

#### 编译运行
```bash
# Windows (Visual Studio)
1. 将thosttraderapi.dll, thosttraderapi.lib复制到项目目录
2. 将头文件复制到项目目录
3. 在VS中创建项目，添加cpp_minimal_demo.cpp
4. 配置链接库：thosttraderapi.lib
5. 编译运行

# Linux
g++ -o ctp_demo cpp_minimal_demo.cpp -L. -lthosttraderapi -lpthread -std=c++11
export LD_LIBRARY_PATH=.:$LD_LIBRARY_PATH
./ctp_demo
```

### C# 版本

#### 前置要求
- .NET Framework 4.6+ 或 .NET Core 3.1+
- CTP .NET封装库（推荐使用开源封装）

#### 编译运行
```bash
# 方式1：使用csc编译
csc /out:CtpDemo.exe csharp_minimal_demo.cs

# 方式2：使用dotnet
dotnet new console -n CtpDemo
# 复制代码到Program.cs
dotnet run

# 注意：实际使用需要集成CTP .NET封装库
```

#### 推荐的C# CTP库
- [CTPAPI.NET](https://github.com/kelin-xycs/CTPZQ)
- 通过NuGet安装相关封装包

### Python 版本 ⭐ 推荐

#### 前置要求
- Python 3.6+
- pip包管理器

#### 安装依赖
```bash
# 推荐方式1：OpenCTP（开源，更新快）
pip install openctp-ctp

# 方式2：官方封装
pip install ctp

# 方式3：VNPY封装
pip install vnpy_ctp
```

#### 运行
```bash
python python_minimal_demo.py
```

## ⚙️ 配置说明

在运行前，需要修改以下配置（所有三个文件）：

```cpp
// C++
#define BROKER_ID "9999"           // 期货公司代码
#define INVESTOR_ID "000001"       // 投资者账号
#define PASSWORD "123456"          // 密码
#define TRADE_FRONT "tcp://180.168.146.187:10101"  // 交易前置地址
```

```csharp
// C#
class Config
{
    public const string BROKER_ID = "9999";
    public const string INVESTOR_ID = "000001";
    public const string PASSWORD = "123456";
    public const string TRADE_FRONT = "tcp://180.168.146.187:10101";
}
```

```python
# Python
BROKER_ID = "9999"
INVESTOR_ID = "000001"
PASSWORD = "123456"
TRADE_FRONT = "tcp://180.168.146.187:10101"
```

### 如何获取配置信息

1. **期货公司代码 (BrokerID)**: 向您的期货公司咨询
2. **投资者账号 (InvestorID)**: 开户后由期货公司提供
3. **密码 (Password)**: 您的交易密码
4. **交易前置地址 (TradeFront)**: 向期货公司咨询，或使用Simnow模拟环境
   - Simnow7x24: `tcp://180.168.146.187:10101`
   - Simnow电信: `tcp://180.168.146.187:10130`

## 📚 CTP API核心概念

### 1. API/SPI模式
- **API**: 提供主动调用的接口（如登录、查询、报单）
- **SPI**: 提供回调函数（如连接成功、登录响应）

### 2. 工作流程
```
创建API实例 → 注册SPI → 注册前置 → 订阅流 → Init初始化
       ↓
   OnFrontConnected (连接成功回调)
       ↓
   ReqUserLogin (请求登录)
       ↓
   OnRspUserLogin (登录响应)
       ↓
   业务操作 (查询、报单等)
```

### 3. 请求响应模式
- 每个请求函数返回值：0成功，-1网络失败，-2超限，-3超限
- 响应通过回调函数返回
- 使用RequestID关联请求和响应

### 4. 流控限制
- 查询类请求：每秒最多1次
- 每次查询必须等待上次查询结束（bIsLast=true）

## 🔧 常见问题

### Q1: 连接失败怎么办？
- 检查网络连接
- 确认前置地址正确
- 检查防火墙设置

### Q2: 登录失败提示"不合法的登录"？
- 确认BrokerID、InvestorID、Password正确
- 确认账号状态正常（未冻结）
- 注意：Simnow需要先注册

### Q3: 查询时提示超流控？
- 每秒最多查询1次
- 必须等待上次查询完成（bIsLast=true）
- 在查询间添加sleep延时

### Q4: Python版本找不到dll/so文件？
```bash
# Windows: 将dll文件复制到Python脚本同目录或System32
# Linux: 设置LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/path/to/ctp:$LD_LIBRARY_PATH
```

## 📖 学习资源

### 官方资源
- CTP官网: http://www.sfit.com.cn/
- SimNow模拟环境: http://www.simnow.com.cn/
- 官方文档: 本目录包含的`CTP_help_document.pdf`

### 开源项目
- OpenCTP: https://github.com/openctp/openctp
- VNPY: https://github.com/vnpy/vnpy
- WonderTrader: https://github.com/wondertrader/wondertrader

### 社区论坛
- 知乎：搜索"CTP开发"
- CSDN：CTP相关博客
- GitHub：搜索"CTP"相关项目

## 📝 进阶开发

基于这些最小Demo，您可以扩展以下功能：

1. **行情接口** - 订阅实时行情（MdApi）
2. **报单交易** - 下单、撤单、改单
3. **查询功能** - 资金、持仓、成交查询
4. **风险管理** - 止损止盈、仓位控制
5. **策略回测** - 历史数据回测
6. **实盘交易** - 自动化交易策略

## ⚠️ 风险提示

- 本Demo仅用于学习和测试
- 实盘交易前请充分测试
- 期货交易有风险，投资需谨慎
- 建议先在SimNow模拟环境测试

## 📄 许可证

本示例代码仅供学习参考，使用时请遵守：
- CTP API使用协议
- 期货公司相关规定
- 证监会监管要求

---

**最后更新**: 2024年
**作者**: CTP开发示例
**联系**: 如有问题请查阅官方文档或社区论坛
