/*
 * CTP完整功能实现 - C++版本
 * 作者: CTP Development Team
 * 日期: 2024
 * 功能: 实现文档中所有交易和行情接口
 */

#include <iostream>
#include <string>
#include <map>
#include <vector>
#include <cstring>
#include <ctime>
#include <thread>
#include <mutex>
#include "ThostFtdcTraderApi.h"
#include "ThostFtdcMdApi.h"

using namespace std;

// ==================== 配置管理类 ====================
class CtpConfig {
public:
    // 经纪商信息
    string BrokerID;
    string InvestorID;
    string Password;
    string AppID;
    string AuthCode;

    // 前置地址
    string TradeFrontAddress;
    string MdFrontAddress;

    // 流文件路径
    string TradeFlowPath;
    string MdFlowPath;

    CtpConfig() {
        BrokerID = "9999";
        InvestorID = "000001";
        Password = "123456";
        AppID = "simnow_client_test";
        AuthCode = "0000000000000000";
        TradeFrontAddress = "tcp://180.168.146.187:10101";
        MdFrontAddress = "tcp://180.168.146.187:10111";
        TradeFlowPath = "./flow_trade/";
        MdFlowPath = "./flow_md/";
    }
};

// ==================== 工具函数 ====================
class CtpUtils {
public:
    // 获取当前时间字符串
    static string GetCurrentTime() {
        time_t now = time(0);
        char buf[80];
        strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", localtime(&now));
        return string(buf);
    }

    // 打印错误信息
    static void PrintError(const char* funcName, CThostFtdcRspInfoField* pRspInfo) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            cout << "[ERROR] " << funcName << " failed: "
                 << "ErrorID=" << pRspInfo->ErrorID
                 << ", ErrorMsg=" << pRspInfo->ErrorMsg << endl;
        }
    }

    // 方向转字符串
    static string DirectionToString(TThostFtdcDirectionType direction) {
        switch(direction) {
            case THOST_FTDC_D_Buy: return "Buy";
            case THOST_FTDC_D_Sell: return "Sell";
            default: return "Unknown";
        }
    }

    // 报单状态转字符串
    static string OrderStatusToString(TThostFtdcOrderStatusType status) {
        switch(status) {
            case THOST_FTDC_OST_AllTraded: return "AllTraded";
            case THOST_FTDC_OST_PartTradedQueueing: return "PartTraded";
            case THOST_FTDC_OST_PartTradedNotQueueing: return "PartTradedNotQueuing";
            case THOST_FTDC_OST_NoTradeQueueing: return "NoTradeQueuing";
            case THOST_FTDC_OST_NoTradeNotQueueing: return "NoTradeNotQueuing";
            case THOST_FTDC_OST_Canceled: return "Canceled";
            case THOST_FTDC_OST_Unknown: return "Unknown";
            case THOST_FTDC_OST_NotTouched: return "NotTouched";
            case THOST_FTDC_OST_Touched: return "Touched";
            default: return "Unknown";
        }
    }
};

// ==================== 行情接口完整实现 ====================
class CtpMdSpi : public CThostFtdcMdSpi {
private:
    CThostFtdcMdApi* m_pApi;
    CtpConfig m_config;
    int m_requestId;
    bool m_isLogin;
    mutex m_mutex;

public:
    CtpMdSpi(CThostFtdcMdApi* api, CtpConfig config)
        : m_pApi(api), m_config(config), m_requestId(0), m_isLogin(false) {}

    // ========== 连接回调 ==========
    virtual void OnFrontConnected() {
        cout << "[INFO] " << CtpUtils::GetCurrentTime()
             << " MD OnFrontConnected" << endl;

        // 发送登录请求
        CThostFtdcReqUserLoginField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.UserID, m_config.InvestorID.c_str());
        strcpy(req.Password, m_config.Password.c_str());

        int ret = m_pApi->ReqUserLogin(&req, ++m_requestId);
        cout << "[INFO] Send MD login request, ret=" << ret << endl;
    }

    virtual void OnFrontDisconnected(int nReason) {
        cout << "[WARN] MD OnFrontDisconnected, reason=" << nReason << endl;
        m_isLogin = false;
    }

    virtual void OnHeartBeatWarning(int nTimeLapse) {
        cout << "[WARN] MD HeartBeat warning! TimeLapse: " << nTimeLapse << "s" << endl;
    }

    // ========== 登录回调 ==========
    virtual void OnRspUserLogin(CThostFtdcRspUserLoginField* pRspUserLogin,
                               CThostFtdcRspInfoField* pRspInfo,
                               int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("MD Login", pRspInfo);
            return;
        }

        cout << "[INFO] MD Login Success!" << endl;
        cout << "  TradingDay: " << pRspUserLogin->TradingDay << endl;
        cout << "  LoginTime: " << pRspUserLogin->LoginTime << endl;

        m_isLogin = true;
    }

    virtual void OnRspUserLogout(CThostFtdcUserLogoutField* pUserLogout,
                                CThostFtdcRspInfoField* pRspInfo,
                                int nRequestID, bool bIsLast) {
        cout << "[INFO] MD Logout" << endl;
        m_isLogin = false;
    }

    // ========== 订阅回调 ==========
    virtual void OnRspSubMarketData(CThostFtdcSpecificInstrumentField* pSpecificInstrument,
                                   CThostFtdcRspInfoField* pRspInfo,
                                   int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Subscribe MD", pRspInfo);
            return;
        }

        if (pSpecificInstrument) {
            cout << "[INFO] Subscribe Success: "
                 << pSpecificInstrument->InstrumentID
                 << "@" << pSpecificInstrument->ExchangeID << endl;
        }
    }

    virtual void OnRspUnSubMarketData(CThostFtdcSpecificInstrumentField* pSpecificInstrument,
                                     CThostFtdcRspInfoField* pRspInfo,
                                     int nRequestID, bool bIsLast) {
        cout << "[INFO] Unsubscribe: "
             << (pSpecificInstrument ? pSpecificInstrument->InstrumentID : "NULL") << endl;
    }

    // ========== 行情数据回调 ==========
    virtual void OnRtnDepthMarketData(CThostFtdcDepthMarketDataField* pDepthMarketData) {
        if (!pDepthMarketData) return;

        lock_guard<mutex> lock(m_mutex);

        cout << "[MD] " << pDepthMarketData->InstrumentID << "@" << pDepthMarketData->ExchangeID
             << " UpdateTime:" << pDepthMarketData->UpdateTime
             << "." << pDepthMarketData->UpdateMillisec
             << " Last:" << pDepthMarketData->LastPrice
             << " Bid:" << pDepthMarketData->BidPrice1 << "x" << pDepthMarketData->BidVolume1
             << " Ask:" << pDepthMarketData->AskPrice1 << "x" << pDepthMarketData->AskVolume1
             << " Volume:" << pDepthMarketData->Volume
             << " OpenInterest:" << pDepthMarketData->OpenInterest
             << endl;
    }

    // ========== 错误回调 ==========
    virtual void OnRspError(CThostFtdcRspInfoField* pRspInfo,
                           int nRequestID, bool bIsLast) {
        CtpUtils::PrintError("MD Error", pRspInfo);
    }

    // ========== 询价相关回调 ==========
    virtual void OnRspSubForQuoteRsp(CThostFtdcSpecificInstrumentField* pSpecificInstrument,
                                     CThostFtdcRspInfoField* pRspInfo,
                                     int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Subscribe ForQuote", pRspInfo);
            return;
        }

        if (pSpecificInstrument) {
            cout << "[INFO] Subscribe ForQuote Success: "
                 << pSpecificInstrument->InstrumentID << endl;
        }
    }

    virtual void OnRspUnSubForQuoteRsp(CThostFtdcSpecificInstrumentField* pSpecificInstrument,
                                       CThostFtdcRspInfoField* pRspInfo,
                                       int nRequestID, bool bIsLast) {
        cout << "[INFO] Unsubscribe ForQuote: "
             << (pSpecificInstrument ? pSpecificInstrument->InstrumentID : "NULL") << endl;
    }

    virtual void OnRtnForQuoteRsp(CThostFtdcForQuoteRspField* pForQuoteRsp) {
        if (!pForQuoteRsp) return;

        cout << "[INFO] ForQuote: " << pForQuoteRsp->InstrumentID
             << " @" << pForQuoteRsp->ExchangeID
             << " TradingDay:" << pForQuoteRsp->TradingDay
             << " ForQuoteTime:" << pForQuoteRsp->ForQuoteTime << endl;
    }

    virtual void OnRspQryMulticastInstrument(CThostFtdcMulticastInstrumentField* pMulticastInstrument,
                                             CThostFtdcRspInfoField* pRspInfo,
                                             int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Multicast Instrument", pRspInfo);
            return;
        }

        if (pMulticastInstrument) {
            cout << "[INFO] Multicast Instrument: " << pMulticastInstrument->InstrumentID << endl;
        }

        if (bIsLast) {
            cout << "[INFO] Multicast Instrument query completed" << endl;
        }
    }

    // ========== 公共方法 ==========
    bool IsLogin() const { return m_isLogin; }

    // 订阅行情
    int SubscribeMarketData(const vector<string>& instruments) {
        if (!m_isLogin) {
            cout << "[WARN] Not logged in, cannot subscribe" << endl;
            return -1;
        }

        int count = instruments.size();
        CThostFtdcSpecificInstrumentField* instArray =
            new CThostFtdcSpecificInstrumentField[count];

        for (int i = 0; i < count; i++) {
            memset(&instArray[i], 0, sizeof(CThostFtdcSpecificInstrumentField));
            strcpy(instArray[i].InstrumentID, instruments[i].c_str());
            // 默认CME交易所，可根据需要修改
            strcpy(instArray[i].ExchangeID, "CME");
        }

        int ret = m_pApi->SubscribeMarketData(instArray, count);
        delete[] instArray;

        return ret;
    }
};

// ==================== 交易接口完整实现 ====================
class CtpTraderSpi : public CThostFtdcTraderSpi {
private:
    CThostFtdcTraderApi* m_pApi;
    CtpConfig m_config;
    int m_requestId;
    bool m_isLogin;
    mutex m_mutex;

    // 会话信息
    int m_frontId;
    int m_sessionId;
    int m_maxOrderRef;

public:
    CtpTraderSpi(CThostFtdcTraderApi* api, CtpConfig config)
        : m_pApi(api), m_config(config), m_requestId(0), m_isLogin(false),
          m_frontId(0), m_sessionId(0), m_maxOrderRef(0) {}

    // ========== 连接回调 ==========
    virtual void OnFrontConnected() {
        cout << "[INFO] " << CtpUtils::GetCurrentTime()
             << " Trader OnFrontConnected" << endl;

        // 身份认证（可选）
        ReqAuthenticate();
    }

    virtual void OnFrontDisconnected(int nReason) {
        cout << "[WARN] Trader OnFrontDisconnected, reason=0x"
             << hex << nReason << dec << endl;
        m_isLogin = false;
    }

    virtual void OnHeartBeatWarning(int nTimeLapse) {
        cout << "[WARN] Trader HeartBeat warning! TimeLapse: " << nTimeLapse << "s" << endl;
    }

    // ========== 身份认证 ==========
    void ReqAuthenticate() {
        CThostFtdcReqAuthenticateField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.UserID, m_config.InvestorID.c_str());
        strcpy(req.AppID, m_config.AppID.c_str());
        strcpy(req.AuthCode, m_config.AuthCode.c_str());

        int ret = m_pApi->ReqAuthenticate(&req, ++m_requestId);
        cout << "[INFO] Send Authenticate request, ret=" << ret << endl;
    }

    virtual void OnRspAuthenticate(CThostFtdcRspAuthenticateField* pRspAuthenticateField,
                                  CThostFtdcRspInfoField* pRspInfo,
                                  int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Authenticate", pRspInfo);
            // 认证失败也继续登录（某些环境不需要认证）
        }

        cout << "[INFO] Authenticate Success, start login..." << endl;

        // 发送登录请求
        CThostFtdcReqUserLoginField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.UserID, m_config.InvestorID.c_str());
        strcpy(req.Password, m_config.Password.c_str());

        int ret = m_pApi->ReqUserLogin(&req, ++m_requestId);
        cout << "[INFO] Send Trader login request, ret=" << ret << endl;
    }

    // ========== 登录回调 ==========
    virtual void OnRspUserLogin(CThostFtdcRspUserLoginField* pRspUserLogin,
                               CThostFtdcRspInfoField* pRspInfo,
                               int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Trader Login", pRspInfo);
            return;
        }

        cout << "[INFO] Trader Login Success!" << endl;
        cout << "  TradingDay: " << pRspUserLogin->TradingDay << endl;
        cout << "  FrontID: " << pRspUserLogin->FrontID << endl;
        cout << "  SessionID: " << pRspUserLogin->SessionID << endl;
        cout << "  MaxOrderRef: " << pRspUserLogin->MaxOrderRef << endl;
        cout << "  LoginTime: " << pRspUserLogin->LoginTime << endl;

        m_frontId = pRspUserLogin->FrontID;
        m_sessionId = pRspUserLogin->SessionID;
        m_maxOrderRef = atoi(pRspUserLogin->MaxOrderRef);
        m_isLogin = true;
    }

    virtual void OnRspUserLogout(CThostFtdcUserLogoutField* pUserLogout,
                                CThostFtdcRspInfoField* pRspInfo,
                                int nRequestID, bool bIsLast) {
        cout << "[INFO] Trader Logout" << endl;
        m_isLogin = false;
    }

    // ========== 修改密码 ==========
    int ReqUserPasswordUpdate(const string& oldPassword, const string& newPassword) {
        CThostFtdcUserPasswordUpdateField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.UserID, m_config.InvestorID.c_str());
        strcpy(req.OldPassword, oldPassword.c_str());
        strcpy(req.NewPassword, newPassword.c_str());

        return m_pApi->ReqUserPasswordUpdate(&req, ++m_requestId);
    }

    virtual void OnRspUserPasswordUpdate(CThostFtdcUserPasswordUpdateField* pUserPasswordUpdate,
                                        CThostFtdcRspInfoField* pRspInfo,
                                        int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Password Update", pRspInfo);
            return;
        }
        cout << "[INFO] Password updated successfully" << endl;
    }

    int ReqTradingAccountPasswordUpdate(const string& accountID,
                                       const string& oldPassword,
                                       const string& newPassword,
                                       const string& currencyID = "USD") {
        CThostFtdcTradingAccountPasswordUpdateField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.AccountID, accountID.c_str());
        strcpy(req.OldPassword, oldPassword.c_str());
        strcpy(req.NewPassword, newPassword.c_str());
        strcpy(req.CurrencyID, currencyID.c_str());

        return m_pApi->ReqTradingAccountPasswordUpdate(&req, ++m_requestId);
    }

    virtual void OnRspTradingAccountPasswordUpdate(
        CThostFtdcTradingAccountPasswordUpdateField* pTradingAccountPasswordUpdate,
        CThostFtdcRspInfoField* pRspInfo,
        int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Trading Account Password Update", pRspInfo);
            return;
        }
        cout << "[INFO] Trading account password updated successfully" << endl;
    }

    // ========== 结算单确认 ==========
    int ReqSettlementInfoConfirm() {
        CThostFtdcSettlementInfoConfirmField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());

        return m_pApi->ReqSettlementInfoConfirm(&req, ++m_requestId);
    }

    virtual void OnRspSettlementInfoConfirm(
        CThostFtdcSettlementInfoConfirmField* pSettlementInfoConfirm,
        CThostFtdcRspInfoField* pRspInfo,
        int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Settlement Confirm", pRspInfo);
            return;
        }
        cout << "[INFO] Settlement confirmed: "
             << pSettlementInfoConfirm->ConfirmDate << " "
             << pSettlementInfoConfirm->ConfirmTime << endl;
    }

    // ========== 查询接口 ==========

    // 查询合约
    int ReqQryInstrument(const string& instrumentID = "",
                        const string& exchangeID = "") {
        CThostFtdcQryInstrumentField req;
        memset(&req, 0, sizeof(req));
        if (!instrumentID.empty())
            strcpy(req.InstrumentID, instrumentID.c_str());
        if (!exchangeID.empty())
            strcpy(req.ExchangeID, exchangeID.c_str());

        return m_pApi->ReqQryInstrument(&req, ++m_requestId);
    }

    virtual void OnRspQryInstrument(CThostFtdcInstrumentField* pInstrument,
                                   CThostFtdcRspInfoField* pRspInfo,
                                   int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Instrument", pRspInfo);
            return;
        }

        if (pInstrument) {
            cout << "[Instrument] "
                 << pInstrument->InstrumentID << "@" << pInstrument->ExchangeID
                 << " Name:" << pInstrument->InstrumentName
                 << " Multiplier:" << pInstrument->VolumeMultiple
                 << " PriceTick:" << pInstrument->PriceTick
                 << endl;
        }

        if (bIsLast) {
            cout << "[INFO] Query instrument completed" << endl;
        }
    }

    // 查询资金账户
    int ReqQryTradingAccount(const string& currencyID = "") {
        CThostFtdcQryTradingAccountField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        if (!currencyID.empty())
            strcpy(req.CurrencyID, currencyID.c_str());

        return m_pApi->ReqQryTradingAccount(&req, ++m_requestId);
    }

    virtual void OnRspQryTradingAccount(CThostFtdcTradingAccountField* pTradingAccount,
                                       CThostFtdcRspInfoField* pRspInfo,
                                       int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Trading Account", pRspInfo);
            return;
        }

        if (pTradingAccount) {
            cout << "[Account] Currency:" << pTradingAccount->CurrencyID
                 << " Balance:" << pTradingAccount->Balance
                 << " Available:" << pTradingAccount->Available
                 << " Margin:" << pTradingAccount->CurrMargin
                 << " Commission:" << pTradingAccount->Commission
                 << " P&L:" << pTradingAccount->PositionProfit
                 << endl;
        }

        if (bIsLast) {
            cout << "[INFO] Query trading account completed" << endl;
        }
    }

    // 查询持仓
    int ReqQryInvestorPosition(const string& instrumentID = "",
                              const string& exchangeID = "") {
        CThostFtdcQryInvestorPositionField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        if (!instrumentID.empty())
            strcpy(req.InstrumentID, instrumentID.c_str());
        if (!exchangeID.empty())
            strcpy(req.ExchangeID, exchangeID.c_str());

        return m_pApi->ReqQryInvestorPosition(&req, ++m_requestId);
    }

    virtual void OnRspQryInvestorPosition(CThostFtdcInvestorPositionField* pInvestorPosition,
                                         CThostFtdcRspInfoField* pRspInfo,
                                         int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Position", pRspInfo);
            return;
        }

        if (pInvestorPosition) {
            cout << "[Position] "
                 << pInvestorPosition->InstrumentID
                 << " Direction:" << CtpUtils::DirectionToString(pInvestorPosition->PosiDirection)
                 << " Position:" << pInvestorPosition->Position
                 << " YdPosition:" << pInvestorPosition->YdPosition
                 << " TodayPosition:" << pInvestorPosition->TodayPosition
                 << " OpenCost:" << pInvestorPosition->OpenCost
                 << " P&L:" << pInvestorPosition->PositionProfit
                 << endl;
        }

        if (bIsLast) {
            cout << "[INFO] Query position completed" << endl;
        }
    }

    // 查询保证金率
    int ReqQryInstrumentMarginRate(const string& instrumentID,
                                   TThostFtdcHedgeFlagType hedgeFlag = THOST_FTDC_HF_Speculation) {
        CThostFtdcQryInstrumentMarginRateField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        strcpy(req.InstrumentID, instrumentID.c_str());
        req.HedgeFlag = hedgeFlag;

        return m_pApi->ReqQryInstrumentMarginRate(&req, ++m_requestId);
    }

    virtual void OnRspQryInstrumentMarginRate(
        CThostFtdcInstrumentMarginRateField* pInstrumentMarginRate,
        CThostFtdcRspInfoField* pRspInfo,
        int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Margin Rate", pRspInfo);
            return;
        }

        if (pInstrumentMarginRate) {
            cout << "[MarginRate] " << pInstrumentMarginRate->InstrumentID
                 << " LongByMoney:" << pInstrumentMarginRate->LongMarginRatioByMoney
                 << " LongByVolume:" << pInstrumentMarginRate->LongMarginRatioByVolume
                 << " ShortByMoney:" << pInstrumentMarginRate->ShortMarginRatioByMoney
                 << " ShortByVolume:" << pInstrumentMarginRate->ShortMarginRatioByVolume
                 << endl;
        }
    }

    // 查询手续费率
    int ReqQryInstrumentCommissionRate(const string& instrumentID) {
        CThostFtdcQryInstrumentCommissionRateField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        strcpy(req.InstrumentID, instrumentID.c_str());

        return m_pApi->ReqQryInstrumentCommissionRate(&req, ++m_requestId);
    }

    virtual void OnRspQryInstrumentCommissionRate(
        CThostFtdcInstrumentCommissionRateField* pInstrumentCommissionRate,
        CThostFtdcRspInfoField* pRspInfo,
        int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Commission Rate", pRspInfo);
            return;
        }

        if (pInstrumentCommissionRate) {
            cout << "[CommissionRate] " << pInstrumentCommissionRate->InstrumentID
                 << " OpenByMoney:" << pInstrumentCommissionRate->OpenRatioByMoney
                 << " OpenByVolume:" << pInstrumentCommissionRate->OpenRatioByVolume
                 << " CloseByMoney:" << pInstrumentCommissionRate->CloseRatioByMoney
                 << " CloseByVolume:" << pInstrumentCommissionRate->CloseRatioByVolume
                 << endl;
        }
    }

    // 查询成交
    int ReqQryTrade(const string& instrumentID = "",
                   const string& exchangeID = "") {
        CThostFtdcQryTradeField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        if (!instrumentID.empty())
            strcpy(req.InstrumentID, instrumentID.c_str());
        if (!exchangeID.empty())
            strcpy(req.ExchangeID, exchangeID.c_str());

        return m_pApi->ReqQryTrade(&req, ++m_requestId);
    }

    virtual void OnRspQryTrade(CThostFtdcTradeField* pTrade,
                              CThostFtdcRspInfoField* pRspInfo,
                              int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Trade", pRspInfo);
            return;
        }

        if (pTrade) {
            cout << "[Trade] " << pTrade->InstrumentID
                 << " TradeID:" << pTrade->TradeID
                 << " Direction:" << CtpUtils::DirectionToString(pTrade->Direction)
                 << " Price:" << pTrade->Price
                 << " Volume:" << pTrade->Volume
                 << " TradeDate:" << pTrade->TradeDate
                 << " TradeTime:" << pTrade->TradeTime
                 << endl;
        }

        if (bIsLast) {
            cout << "[INFO] Query trade completed" << endl;
        }
    }

    // 查询报单
    int ReqQryOrder(const string& instrumentID = "",
                   const string& exchangeID = "") {
        CThostFtdcQryOrderField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        if (!instrumentID.empty())
            strcpy(req.InstrumentID, instrumentID.c_str());
        if (!exchangeID.empty())
            strcpy(req.ExchangeID, exchangeID.c_str());

        return m_pApi->ReqQryOrder(&req, ++m_requestId);
    }

    virtual void OnRspQryOrder(CThostFtdcOrderField* pOrder,
                              CThostFtdcRspInfoField* pRspInfo,
                              int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Order", pRspInfo);
            return;
        }

        if (pOrder) {
            cout << "[Order] " << pOrder->InstrumentID
                 << " OrderRef:" << pOrder->OrderRef
                 << " Direction:" << CtpUtils::DirectionToString(pOrder->Direction)
                 << " Price:" << pOrder->LimitPrice
                 << " Volume:" << pOrder->VolumeTotalOriginal
                 << " Status:" << CtpUtils::OrderStatusToString(pOrder->OrderStatus)
                 << " StatusMsg:" << pOrder->StatusMsg
                 << endl;
        }

        if (bIsLast) {
            cout << "[INFO] Query order completed" << endl;
        }
    }

    // ========== 国际版特色查询 ==========

    // 查询基币
    int ReqQryBaseCurrencyAccount() {
        CThostFtdcQryBaseCurrencyAccountField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.AccountID, m_config.InvestorID.c_str());

        return m_pApi->ReqQryBaseCurrencyAccount(&req, ++m_requestId);
    }

    virtual void OnRspQryBaseCurrencyAccount(
        CThostFtdcBaseCurrencyAccountField* pBaseCurrencyAccount,
        CThostFtdcRspInfoField* pRspInfo,
        int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Base Currency", pRspInfo);
            return;
        }

        if (pBaseCurrencyAccount) {
            cout << "[BaseCurrency] AccountID:" << pBaseCurrencyAccount->AccountID
                 << " CurrencyID:" << pBaseCurrencyAccount->CurrencyID
                 << endl;
        }
    }

    // 查询汇率
    int ReqQryExchangeRate(const string& fromCurrency = "",
                          const string& toCurrency = "") {
        CThostFtdcQryExchangeRateField req;
        memset(&req, 0, sizeof(req));
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        if (!fromCurrency.empty())
            strcpy(req.FromCurrencyID, fromCurrency.c_str());
        if (!toCurrency.empty())
            strcpy(req.ToCurrencyID, toCurrency.c_str());

        return m_pApi->ReqQryExchangeRate(&req, ++m_requestId);
    }

    virtual void OnRspQryExchangeRate(CThostFtdcExchangeRateField* pExchangeRate,
                                     CThostFtdcRspInfoField* pRspInfo,
                                     int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Query Exchange Rate", pRspInfo);
            return;
        }

        if (pExchangeRate) {
            cout << "[ExchangeRate] " << pExchangeRate->FromCurrencyID
                 << " -> " << pExchangeRate->ToCurrencyID
                 << " Rate:" << pExchangeRate->ExchangeRate
                 << endl;
        }

        if (bIsLast) {
            cout << "[INFO] Query exchange rate completed" << endl;
        }
    }

    // ========== 报单操作 ==========

    // 报单（通用）
    int ReqOrderInsert(const string& instrumentID,
                      const string& exchangeID,
                      TThostFtdcDirectionType direction,
                      TThostFtdcCombOffsetFlagType offsetFlag,
                      double price,
                      int volume,
                      TThostFtdcOrderPriceTypeType priceType = THOST_FTDC_OPT_LimitPrice,
                      TThostFtdcContingentConditionType contingentCondition = THOST_FTDC_CC_Immediately,
                      TThostFtdcTimeConditionType timeCondition = THOST_FTDC_TC_GFD,
                      TThostFtdcVolumeConditionType volumeCondition = THOST_FTDC_VC_AV,
                      TThostFtdcHedgeFlagType hedgeFlag = THOST_FTDC_HF_Speculation) {

        CThostFtdcInputOrderField req;
        memset(&req, 0, sizeof(req));

        // 基本信息
        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        strcpy(req.InstrumentID, instrumentID.c_str());
        strcpy(req.ExchangeID, exchangeID.c_str());

        // 报单引用（OrderRef自动递增）
        char orderRef[13];
        sprintf(orderRef, "%012d", ++m_maxOrderRef);
        strcpy(req.OrderRef, orderRef);

        // 方向和开平
        req.Direction = direction;
        req.CombOffsetFlag[0] = offsetFlag;
        req.CombHedgeFlag[0] = hedgeFlag;

        // 价格和数量
        req.LimitPrice = price;
        req.VolumeTotalOriginal = volume;
        req.MinVolume = 1;

        // 报单类型
        req.OrderPriceType = priceType;
        req.TimeCondition = timeCondition;
        req.VolumeCondition = volumeCondition;
        req.ContingentCondition = contingentCondition;

        // 其他
        req.ForceCloseReason = THOST_FTDC_FCC_NotForceClose;
        req.IsAutoSuspend = 0;
        req.UserForceClose = 0;

        return m_pApi->ReqOrderInsert(&req, ++m_requestId);
    }

    // 限价单
    int ReqLimitOrder(const string& instrumentID,
                     const string& exchangeID,
                     TThostFtdcDirectionType direction,
                     TThostFtdcCombOffsetFlagType offsetFlag,
                     double price,
                     int volume) {
        return ReqOrderInsert(instrumentID, exchangeID, direction, offsetFlag,
                            price, volume, THOST_FTDC_OPT_LimitPrice);
    }

    // 市价单
    int ReqMarketOrder(const string& instrumentID,
                      const string& exchangeID,
                      TThostFtdcDirectionType direction,
                      TThostFtdcCombOffsetFlagType offsetFlag,
                      int volume) {
        return ReqOrderInsert(instrumentID, exchangeID, direction, offsetFlag,
                            0, volume, THOST_FTDC_OPT_AnyPrice);
    }

    // FOK单
    int ReqFOKOrder(const string& instrumentID,
                   const string& exchangeID,
                   TThostFtdcDirectionType direction,
                   TThostFtdcCombOffsetFlagType offsetFlag,
                   double price,
                   int volume) {
        return ReqOrderInsert(instrumentID, exchangeID, direction, offsetFlag,
                            price, volume, THOST_FTDC_OPT_LimitPrice,
                            THOST_FTDC_CC_Immediately,
                            THOST_FTDC_TC_IOC,
                            THOST_FTDC_VC_CV);
    }

    // FAK单
    int ReqFAKOrder(const string& instrumentID,
                   const string& exchangeID,
                   TThostFtdcDirectionType direction,
                   TThostFtdcCombOffsetFlagType offsetFlag,
                   double price,
                   int volume) {
        return ReqOrderInsert(instrumentID, exchangeID, direction, offsetFlag,
                            price, volume, THOST_FTDC_OPT_LimitPrice,
                            THOST_FTDC_CC_Immediately,
                            THOST_FTDC_TC_IOC,
                            THOST_FTDC_VC_AV);
    }

    // 止损单
    int ReqStopOrder(const string& instrumentID,
                    const string& exchangeID,
                    TThostFtdcDirectionType direction,
                    TThostFtdcCombOffsetFlagType offsetFlag,
                    double price,
                    double stopPrice,
                    int volume) {

        CThostFtdcInputOrderField req;
        memset(&req, 0, sizeof(req));

        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        strcpy(req.InstrumentID, instrumentID.c_str());
        strcpy(req.ExchangeID, exchangeID.c_str());

        char orderRef[13];
        sprintf(orderRef, "%012d", ++m_maxOrderRef);
        strcpy(req.OrderRef, orderRef);

        req.Direction = direction;
        req.CombOffsetFlag[0] = offsetFlag;
        req.CombHedgeFlag[0] = THOST_FTDC_HF_Speculation;

        req.LimitPrice = price;
        req.StopPrice = stopPrice;
        req.VolumeTotalOriginal = volume;
        req.MinVolume = 1;

        req.OrderPriceType = THOST_FTDC_OPT_LimitPrice;
        req.TimeCondition = THOST_FTDC_TC_GFD;
        req.VolumeCondition = THOST_FTDC_VC_AV;
        req.ContingentCondition = THOST_FTDC_CC_Touch;  // 止损条件

        req.ForceCloseReason = THOST_FTDC_FCC_NotForceClose;
        req.IsAutoSuspend = 0;
        req.UserForceClose = 0;

        return m_pApi->ReqOrderInsert(&req, ++m_requestId);
    }

    // 报单回调
    virtual void OnRspOrderInsert(CThostFtdcInputOrderField* pInputOrder,
                                 CThostFtdcRspInfoField* pRspInfo,
                                 int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Order Insert", pRspInfo);
            cout << "  Instrument:" << (pInputOrder ? pInputOrder->InstrumentID : "NULL")
                 << " OrderRef:" << (pInputOrder ? pInputOrder->OrderRef : "NULL")
                 << endl;
        } else {
            cout << "[INFO] Order inserted successfully" << endl;
        }
    }

    virtual void OnErrRtnOrderInsert(CThostFtdcInputOrderField* pInputOrder,
                                    CThostFtdcRspInfoField* pRspInfo) {
        CtpUtils::PrintError("Order Insert Error", pRspInfo);
        if (pInputOrder) {
            cout << "  Instrument:" << pInputOrder->InstrumentID
                 << " OrderRef:" << pInputOrder->OrderRef
                 << endl;
        }
    }

    virtual void OnRtnOrder(CThostFtdcOrderField* pOrder) {
        if (!pOrder) return;

        lock_guard<mutex> lock(m_mutex);

        cout << "[OrderRtn] " << pOrder->InstrumentID
             << " OrderRef:" << pOrder->OrderRef
             << " Direction:" << CtpUtils::DirectionToString(pOrder->Direction)
             << " Price:" << pOrder->LimitPrice
             << " Volume:" << pOrder->VolumeTotalOriginal
             << " Traded:" << pOrder->VolumeTraded
             << " Status:" << CtpUtils::OrderStatusToString(pOrder->OrderStatus)
             << " OrderSysID:" << pOrder->OrderSysID
             << endl;

        if (pOrder->OrderStatus == THOST_FTDC_OST_Unknown ||
            pOrder->OrderStatus == THOST_FTDC_OST_NoTradeQueueing ||
            pOrder->OrderStatus == THOST_FTDC_OST_PartTradedQueueing) {
            cout << "  StatusMsg:" << pOrder->StatusMsg << endl;
        }
    }

    virtual void OnRtnTrade(CThostFtdcTradeField* pTrade) {
        if (!pTrade) return;

        lock_guard<mutex> lock(m_mutex);

        cout << "[TradeRtn] " << pTrade->InstrumentID
             << " TradeID:" << pTrade->TradeID
             << " Direction:" << CtpUtils::DirectionToString(pTrade->Direction)
             << " Price:" << pTrade->Price
             << " Volume:" << pTrade->Volume
             << " TradeTime:" << pTrade->TradeTime
             << " OrderRef:" << pTrade->OrderRef
             << endl;
    }

    // ========== 撤单操作 ==========
    int ReqOrderAction(const string& instrumentID,
                      const string& exchangeID,
                      const string& orderRef,
                      int frontId,
                      int sessionId,
                      TThostFtdcActionFlagType actionFlag = THOST_FTDC_AF_Delete) {

        CThostFtdcInputOrderActionField req;
        memset(&req, 0, sizeof(req));

        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        strcpy(req.InstrumentID, instrumentID.c_str());
        strcpy(req.ExchangeID, exchangeID.c_str());
        strcpy(req.OrderRef, orderRef.c_str());

        req.FrontID = frontId;
        req.SessionID = sessionId;
        req.ActionFlag = actionFlag;

        return m_pApi->ReqOrderAction(&req, ++m_requestId);
    }

    // 通过OrderSysID撤单
    int ReqOrderActionByOrderSysID(const string& orderSysID,
                                  const string& exchangeID,
                                  TThostFtdcActionFlagType actionFlag = THOST_FTDC_AF_Delete) {

        CThostFtdcInputOrderActionField req;
        memset(&req, 0, sizeof(req));

        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        strcpy(req.OrderSysID, orderSysID.c_str());
        strcpy(req.ExchangeID, exchangeID.c_str());

        req.ActionFlag = actionFlag;

        return m_pApi->ReqOrderAction(&req, ++m_requestId);
    }

    // 改单
    int ReqOrderModify(const string& instrumentID,
                      const string& exchangeID,
                      const string& orderRef,
                      int frontId,
                      int sessionId,
                      double newPrice,
                      int newVolume) {

        CThostFtdcInputOrderActionField req;
        memset(&req, 0, sizeof(req));

        strcpy(req.BrokerID, m_config.BrokerID.c_str());
        strcpy(req.InvestorID, m_config.InvestorID.c_str());
        strcpy(req.InstrumentID, instrumentID.c_str());
        strcpy(req.ExchangeID, exchangeID.c_str());
        strcpy(req.OrderRef, orderRef.c_str());

        req.FrontID = frontId;
        req.SessionID = sessionId;
        req.ActionFlag = THOST_FTDC_AF_Modify;
        req.LimitPrice = newPrice;
        req.VolumeChange = newVolume;

        return m_pApi->ReqOrderAction(&req, ++m_requestId);
    }

    virtual void OnRspOrderAction(CThostFtdcInputOrderActionField* pInputOrderAction,
                                 CThostFtdcRspInfoField* pRspInfo,
                                 int nRequestID, bool bIsLast) {
        if (pRspInfo && pRspInfo->ErrorID != 0) {
            CtpUtils::PrintError("Order Action", pRspInfo);
            if (pInputOrderAction) {
                cout << "  OrderRef:" << pInputOrderAction->OrderRef
                     << " OrderSysID:" << pInputOrderAction->OrderSysID
                     << endl;
            }
        } else {
            cout << "[INFO] Order action success" << endl;
        }
    }

    virtual void OnErrRtnOrderAction(CThostFtdcOrderActionField* pOrderAction,
                                    CThostFtdcRspInfoField* pRspInfo) {
        CtpUtils::PrintError("Order Action Error", pRspInfo);
        if (pOrderAction) {
            cout << "  OrderRef:" << pOrderAction->OrderRef
                 << " OrderSysID:" << pOrderAction->OrderSysID
                 << endl;
        }
    }

    // ========== 错误回调 ==========
    virtual void OnRspError(CThostFtdcRspInfoField* pRspInfo,
                           int nRequestID, bool bIsLast) {
        CtpUtils::PrintError("Trader Error", pRspInfo);
    }

    // ========== 公共方法 ==========
    bool IsLogin() const { return m_isLogin; }
    int GetFrontId() const { return m_frontId; }
    int GetSessionId() const { return m_sessionId; }
    int GetMaxOrderRef() const { return m_maxOrderRef; }
};

// ==================== 主程序示例 ====================
int main() {
    cout << "========================================" << endl;
    cout << "  CTP Full Implementation - C++ Version" << endl;
    cout << "========================================" << endl;

    // 配置
    CtpConfig config;

    // 创建行情接口
    CThostFtdcMdApi* pMdApi = CThostFtdcMdApi::CreateFtdcMdApi(config.MdFlowPath.c_str());
    CtpMdSpi* pMdSpi = new CtpMdSpi(pMdApi, config);
    pMdApi->RegisterSpi(pMdSpi);
    pMdApi->RegisterFront((char*)config.MdFrontAddress.c_str());
    pMdApi->Init();

    cout << "[INFO] MD API initialized" << endl;

    // 创建交易接口
    CThostFtdcTraderApi* pTraderApi =
        CThostFtdcTraderApi::CreateFtdcTraderApi(config.TradeFlowPath.c_str());
    CtpTraderSpi* pTraderSpi = new CtpTraderSpi(pTraderApi, config);
    pTraderApi->RegisterSpi(pTraderSpi);
    pTraderApi->RegisterFront((char*)config.TradeFrontAddress.c_str());
    pTraderApi->SubscribePrivateTopic(THOST_TERT_QUICK);
    pTraderApi->SubscribePublicTopic(THOST_TERT_QUICK);
    pTraderApi->Init();

    cout << "[INFO] Trader API initialized" << endl;

    // 等待登录
    this_thread::sleep_for(chrono::seconds(3));

    // 示例操作
    if (pTraderSpi->IsLogin()) {
        cout << "\n[INFO] Starting demo operations..." << endl;

        // 1. 查询合约
        cout << "\n1. Query instruments..." << endl;
        pTraderSpi->ReqQryInstrument();
        this_thread::sleep_for(chrono::seconds(2));

        // 2. 查询资金账户
        cout << "\n2. Query trading account..." << endl;
        pTraderSpi->ReqQryTradingAccount();
        this_thread::sleep_for(chrono::seconds(2));

        // 3. 查询持仓
        cout << "\n3. Query positions..." << endl;
        pTraderSpi->ReqQryInvestorPosition();
        this_thread::sleep_for(chrono::seconds(2));

        // 4. 订阅行情
        if (pMdSpi->IsLogin()) {
            cout << "\n4. Subscribe market data..." << endl;
            vector<string> instruments = {"ES2503", "NQ2503"};
            pMdSpi->SubscribeMarketData(instruments);
        }

        cout << "\n[INFO] Demo operations completed" << endl;
    }

    // 保持运行
    cout << "\nPress Enter to exit..." << endl;
    getchar();

    // 清理
    pMdApi->Release();
    pTraderApi->Release();

    delete pMdSpi;
    delete pTraderSpi;

    return 0;
}
