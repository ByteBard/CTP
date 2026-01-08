/*
 * CTP最小交易Demo - C++版本
 * 功能：连接、登录、查询合约
 */

#include <iostream>
#include <cstring>
#include "ThostFtdcTraderApi.h"

using namespace std;

// 配置信息
#define BROKER_ID "9999"           // 模拟经纪商代码，请替换为实际值
#define INVESTOR_ID "000001"       // 投资者账号，请替换为实际值
#define PASSWORD "123456"          // 密码，请替换为实际值
#define TRADE_FRONT "tcp://180.168.146.187:10101"  // CTP交易前置地址

class MinimalTraderSpi : public CThostFtdcTraderSpi
{
public:
    MinimalTraderSpi(CThostFtdcTraderApi* api) : m_pApi(api) {}

    // 连接成功回调
    virtual void OnFrontConnected()
    {
        cout << "[INFO] 已连接到交易前置" << endl;

        // 发送登录请求
        CThostFtdcReqUserLoginField loginReq;
        memset(&loginReq, 0, sizeof(loginReq));
        strcpy(loginReq.BrokerID, BROKER_ID);
        strcpy(loginReq.UserID, INVESTOR_ID);
        strcpy(loginReq.Password, PASSWORD);

        int ret = m_pApi->ReqUserLogin(&loginReq, ++m_requestId);
        cout << "[INFO] 发送登录请求, 返回值=" << ret << endl;
    }

    // 连接断开回调
    virtual void OnFrontDisconnected(int nReason)
    {
        cout << "[ERROR] 连接断开, 原因=" << nReason << endl;
    }

    // 登录响应
    virtual void OnRspUserLogin(CThostFtdcRspUserLoginField* pRspUserLogin,
                               CThostFtdcRspInfoField* pRspInfo,
                               int nRequestID, bool bIsLast)
    {
        if (pRspInfo && pRspInfo->ErrorID != 0)
        {
            cout << "[ERROR] 登录失败: " << pRspInfo->ErrorMsg << endl;
            return;
        }

        cout << "[INFO] 登录成功!" << endl;
        cout << "  交易日: " << pRspUserLogin->TradingDay << endl;
        cout << "  前置编号: " << pRspUserLogin->FrontID << endl;
        cout << "  会话编号: " << pRspUserLogin->SessionID << endl;

        // 查询合约
        CThostFtdcQryInstrumentField qryReq;
        memset(&qryReq, 0, sizeof(qryReq));
        // 不指定合约代码，查询所有合约

        int ret = m_pApi->ReqQryInstrument(&qryReq, ++m_requestId);
        cout << "[INFO] 发送查询合约请求, 返回值=" << ret << endl;
    }

    // 查询合约响应
    virtual void OnRspQryInstrument(CThostFtdcInstrumentField* pInstrument,
                                   CThostFtdcRspInfoField* pRspInfo,
                                   int nRequestID, bool bIsLast)
    {
        if (pRspInfo && pRspInfo->ErrorID != 0)
        {
            cout << "[ERROR] 查询合约失败: " << pRspInfo->ErrorMsg << endl;
            return;
        }

        if (pInstrument)
        {
            cout << "  合约: " << pInstrument->InstrumentID
                 << ", 名称: " << pInstrument->InstrumentName
                 << ", 交易所: " << pInstrument->ExchangeID << endl;
        }

        if (bIsLast)
        {
            cout << "[INFO] 合约查询完成" << endl;
        }
    }

    // 错误回调
    virtual void OnRspError(CThostFtdcRspInfoField* pRspInfo,
                           int nRequestID, bool bIsLast)
    {
        if (pRspInfo)
        {
            cout << "[ERROR] " << pRspInfo->ErrorMsg << endl;
        }
    }

private:
    CThostFtdcTraderApi* m_pApi;
    int m_requestId = 0;
};

int main()
{
    cout << "========================================" << endl;
    cout << "  CTP最小交易Demo - C++版本" << endl;
    cout << "========================================" << endl;

    // 1. 创建交易API实例
    CThostFtdcTraderApi* pApi = CThostFtdcTraderApi::CreateFtdcTraderApi("./flow/");

    // 2. 创建并注册SPI回调实例
    MinimalTraderSpi* pSpi = new MinimalTraderSpi(pApi);
    pApi->RegisterSpi(pSpi);

    // 3. 注册交易前置地址
    char frontAddr[] = TRADE_FRONT;
    pApi->RegisterFront(frontAddr);

    // 4. 订阅私有流和公有流（从当前开始）
    pApi->SubscribePrivateTopic(THOST_TERT_QUICK);
    pApi->SubscribePublicTopic(THOST_TERT_QUICK);

    // 5. 初始化API，开始连接
    pApi->Init();

    cout << "[INFO] 正在连接交易前置..." << endl;

    // 6. 等待，让工作线程运行
    pApi->Join();

    // 清理资源
    delete pSpi;
    pApi->Release();

    return 0;
}

/*
编译说明（Windows + Visual Studio）：
1. 将thosttraderapi.dll, thosttraderapi.lib复制到项目目录
2. 将头文件ThostFtdcTraderApi.h, ThostFtdcUserApiStruct.h等复制到项目目录
3. 在项目属性中添加库依赖：thosttraderapi.lib
4. 编译运行

编译说明（Linux）：
g++ -o ctp_demo cpp_minimal_demo.cpp -L. -lthosttraderapi -lpthread -std=c++11
export LD_LIBRARY_PATH=.:$LD_LIBRARY_PATH
./ctp_demo
*/
