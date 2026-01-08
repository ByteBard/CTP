/*
 * CTP最小交易Demo - C#版本
 * 功能：连接、登录、查询合约
 * 需要：CTP .NET封装库（如CTP.NET或自行封装P/Invoke）
 */

using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace CtpMinimalDemo
{
    // 配置信息
    class Config
    {
        public const string BROKER_ID = "9999";           // 模拟经纪商代码
        public const string INVESTOR_ID = "000001";       // 投资者账号
        public const string PASSWORD = "123456";          // 密码
        public const string TRADE_FRONT = "tcp://180.168.146.187:10101";
    }

    // 简化的CTP API封装（实际使用时需要完整封装或使用第三方库）
    // 这里仅作示例，展示调用逻辑
    class CtpTraderApi
    {
        // DLL导入示例（需要根据实际CTP .NET封装调整）
        // 注：CTP官方提供C++ API，C#需要通过P/Invoke或封装库调用

        private IntPtr apiInstance;
        private CtpTraderSpi spi;

        public CtpTraderApi(string flowPath)
        {
            Console.WriteLine("[INFO] 初始化交易API");
            // 实际代码中调用C++接口创建实例
            // apiInstance = CreateFtdcTraderApi(flowPath);
        }

        public void RegisterSpi(CtpTraderSpi spiInstance)
        {
            this.spi = spiInstance;
            Console.WriteLine("[INFO] 注册SPI回调");
        }

        public void RegisterFront(string frontAddress)
        {
            Console.WriteLine($"[INFO] 注册前置地址: {frontAddress}");
            // RegisterFront_Native(apiInstance, frontAddress);
        }

        public void SubscribePrivateTopic(int resumeType)
        {
            Console.WriteLine("[INFO] 订阅私有流");
        }

        public void SubscribePublicTopic(int resumeType)
        {
            Console.WriteLine("[INFO] 订阅公有流");
        }

        public void Init()
        {
            Console.WriteLine("[INFO] 启动API");
            // Init_Native(apiInstance);

            // 模拟连接成功
            Thread.Sleep(1000);
            spi?.OnFrontConnected();
        }

        public int ReqUserLogin(LoginField req, int requestId)
        {
            Console.WriteLine($"[INFO] 请求登录: {req.UserID}");

            // 模拟登录成功
            Thread.Sleep(500);
            var rsp = new RspUserLoginField
            {
                TradingDay = DateTime.Now.ToString("yyyyMMdd"),
                FrontID = 1,
                SessionID = 12345
            };
            spi?.OnRspUserLogin(rsp, null, requestId, true);

            return 0;
        }

        public int ReqQryInstrument(QryInstrumentField req, int requestId)
        {
            Console.WriteLine("[INFO] 请求查询合约");

            // 模拟返回几个合约
            Thread.Sleep(500);
            var instruments = new[]
            {
                new InstrumentField { InstrumentID = "rb2505", InstrumentName = "螺纹钢2505", ExchangeID = "SHFE" },
                new InstrumentField { InstrumentID = "ag2506", InstrumentName = "白银2506", ExchangeID = "SHFE" }
            };

            for (int i = 0; i < instruments.Length; i++)
            {
                bool isLast = (i == instruments.Length - 1);
                spi?.OnRspQryInstrument(instruments[i], null, requestId, isLast);
                Thread.Sleep(100);
            }

            return 0;
        }

        public void Release()
        {
            Console.WriteLine("[INFO] 释放API资源");
        }
    }

    // SPI回调类
    class CtpTraderSpi
    {
        private CtpTraderApi api;
        private int requestId = 0;

        public CtpTraderSpi(CtpTraderApi apiInstance)
        {
            this.api = apiInstance;
        }

        public void OnFrontConnected()
        {
            Console.WriteLine("[INFO] 已连接到交易前置");

            // 发送登录请求
            var loginReq = new LoginField
            {
                BrokerID = Config.BROKER_ID,
                UserID = Config.INVESTOR_ID,
                Password = Config.PASSWORD
            };

            api.ReqUserLogin(loginReq, ++requestId);
        }

        public void OnFrontDisconnected(int reason)
        {
            Console.WriteLine($"[ERROR] 连接断开, 原因={reason}");
        }

        public void OnRspUserLogin(RspUserLoginField pRspUserLogin,
                                  RspInfoField pRspInfo,
                                  int nRequestID, bool bIsLast)
        {
            if (pRspInfo != null && pRspInfo.ErrorID != 0)
            {
                Console.WriteLine($"[ERROR] 登录失败: {pRspInfo.ErrorMsg}");
                return;
            }

            Console.WriteLine("[INFO] 登录成功!");
            Console.WriteLine($"  交易日: {pRspUserLogin.TradingDay}");
            Console.WriteLine($"  前置编号: {pRspUserLogin.FrontID}");
            Console.WriteLine($"  会话编号: {pRspUserLogin.SessionID}");

            // 查询合约
            var qryReq = new QryInstrumentField();
            api.ReqQryInstrument(qryReq, ++requestId);
        }

        public void OnRspQryInstrument(InstrumentField pInstrument,
                                      RspInfoField pRspInfo,
                                      int nRequestID, bool bIsLast)
        {
            if (pRspInfo != null && pRspInfo.ErrorID != 0)
            {
                Console.WriteLine($"[ERROR] 查询合约失败: {pRspInfo.ErrorMsg}");
                return;
            }

            if (pInstrument != null)
            {
                Console.WriteLine($"  合约: {pInstrument.InstrumentID}, " +
                                $"名称: {pInstrument.InstrumentName}, " +
                                $"交易所: {pInstrument.ExchangeID}");
            }

            if (bIsLast)
            {
                Console.WriteLine("[INFO] 合约查询完成");
            }
        }
    }

    // 数据结构定义
    class LoginField
    {
        public string BrokerID { get; set; }
        public string UserID { get; set; }
        public string Password { get; set; }
    }

    class RspUserLoginField
    {
        public string TradingDay { get; set; }
        public int FrontID { get; set; }
        public int SessionID { get; set; }
    }

    class RspInfoField
    {
        public int ErrorID { get; set; }
        public string ErrorMsg { get; set; }
    }

    class QryInstrumentField
    {
        public string InstrumentID { get; set; }
    }

    class InstrumentField
    {
        public string InstrumentID { get; set; }
        public string InstrumentName { get; set; }
        public string ExchangeID { get; set; }
    }

    // 主程序
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("========================================");
            Console.WriteLine("  CTP最小交易Demo - C#版本");
            Console.WriteLine("========================================");

            // 1. 创建API实例
            var api = new CtpTraderApi("./flow/");

            // 2. 创建并注册SPI
            var spi = new CtpTraderSpi(api);
            api.RegisterSpi(spi);

            // 3. 注册前置地址
            api.RegisterFront(Config.TRADE_FRONT);

            // 4. 订阅流
            api.SubscribePrivateTopic(2);  // THOST_TERT_QUICK
            api.SubscribePublicTopic(2);

            // 5. 初始化
            api.Init();

            // 6. 等待用户按键退出
            Console.WriteLine("\n按任意键退出...");
            Console.ReadKey();

            // 7. 释放资源
            api.Release();
        }
    }
}

/*
使用说明：
1. 本示例为演示逻辑，实际使用需要：
   - 使用CTP.NET封装库（如开源的CTPAPI.NET）
   - 或使用P/Invoke直接调用thosttraderapi.dll

2. 编译运行：
   csc /out:CtpDemo.exe csharp_minimal_demo.cs
   CtpDemo.exe

3. 推荐的C# CTP库：
   - https://github.com/kelin-xycs/CTPZQ (CTP.NET)
   - 使用NuGet安装相关封装包

4. 实际部署时需要：
   - thosttraderapi.dll
   - 正确的P/Invoke声明或封装库
*/
