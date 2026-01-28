/**
 * CTP MdApi C Wrapper Implementation
 * 将CTP行情API封装为C接口，供Python ctypes调用
 */

#include "ctp_md_wrapper.h"
#include "ThostFtdcMdApi.h"
#include <cstring>
#include <string>

// ============================================================
// 内部包装类：实现CThostFtdcMdSpi接口
// ============================================================
class MdSpiWrapper : public CThostFtdcMdSpi
{
public:
    MdCallbacks callbacks;

    MdSpiWrapper() {
        memset(&callbacks, 0, sizeof(callbacks));
    }

    virtual void OnFrontConnected() override {
        if (callbacks.on_front_connected) {
            callbacks.on_front_connected();
        }
    }

    virtual void OnFrontDisconnected(int nReason) override {
        if (callbacks.on_front_disconnected) {
            callbacks.on_front_disconnected(nReason);
        }
    }

    virtual void OnHeartBeatWarning(int nTimeLapse) override {
        if (callbacks.on_heartbeat_warning) {
            callbacks.on_heartbeat_warning(nTimeLapse);
        }
    }

    virtual void OnRspUserLogin(
        CThostFtdcRspUserLoginField *pRspUserLogin,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_user_login) {
            const char* trading_day = pRspUserLogin ? pRspUserLogin->TradingDay : "";
            const char* login_time = pRspUserLogin ? pRspUserLogin->LoginTime : "";
            const char* broker_id = pRspUserLogin ? pRspUserLogin->BrokerID : "";
            const char* user_id = pRspUserLogin ? pRspUserLogin->UserID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_user_login(
                trading_day, login_time, broker_id, user_id,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspUserLogout(
        CThostFtdcUserLogoutField *pUserLogout,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_user_logout) {
            const char* broker_id = pUserLogout ? pUserLogout->BrokerID : "";
            const char* user_id = pUserLogout ? pUserLogout->UserID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_user_logout(
                broker_id, user_id,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspError(
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_error) {
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";
            callbacks.on_rsp_error(
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspSubMarketData(
        CThostFtdcSpecificInstrumentField *pSpecificInstrument,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_sub_market_data) {
            const char* instrument_id = pSpecificInstrument ? pSpecificInstrument->InstrumentID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";
            callbacks.on_rsp_sub_market_data(
                instrument_id,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspUnSubMarketData(
        CThostFtdcSpecificInstrumentField *pSpecificInstrument,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_unsub_market_data) {
            const char* instrument_id = pSpecificInstrument ? pSpecificInstrument->InstrumentID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";
            callbacks.on_rsp_unsub_market_data(
                instrument_id,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRtnDepthMarketData(
        CThostFtdcDepthMarketDataField *pData) override
    {
        if (callbacks.on_rtn_depth_market_data && pData) {
            callbacks.on_rtn_depth_market_data(
                pData->InstrumentID, pData->ExchangeID,
                pData->LastPrice, pData->PreSettlementPrice,
                pData->PreClosePrice, pData->PreOpenInterest,
                pData->OpenPrice, pData->HighestPrice, pData->LowestPrice,
                pData->Volume, pData->Turnover, pData->OpenInterest,
                pData->ClosePrice, pData->SettlementPrice,
                pData->UpperLimitPrice, pData->LowerLimitPrice,
                pData->BidPrice1, pData->BidVolume1,
                pData->AskPrice1, pData->AskVolume1,
                pData->BidPrice2, pData->BidVolume2,
                pData->AskPrice2, pData->AskVolume2,
                pData->BidPrice3, pData->BidVolume3,
                pData->AskPrice3, pData->AskVolume3,
                pData->BidPrice4, pData->BidVolume4,
                pData->AskPrice4, pData->AskVolume4,
                pData->BidPrice5, pData->BidVolume5,
                pData->AskPrice5, pData->AskVolume5,
                pData->AveragePrice,
                pData->UpdateTime, pData->UpdateMillisec,
                pData->TradingDay, pData->ActionDay);
        }
    }
};

// ============================================================
// 内部包装结构
// ============================================================
struct MdApiWrapper {
    CThostFtdcMdApi* api;
    MdSpiWrapper* spi;
};

// ============================================================
// C 接口实现
// ============================================================

MD_WRAPPER_API void* CreateMdApi(const char* flow_path) {
    MdApiWrapper* wrapper = new MdApiWrapper();
    wrapper->api = CThostFtdcMdApi::CreateFtdcMdApi(flow_path);
    wrapper->spi = new MdSpiWrapper();
    wrapper->api->RegisterSpi(wrapper->spi);
    return wrapper;
}

MD_WRAPPER_API void ReleaseMdApi(void* api) {
    if (api) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->Release();
        }
        if (wrapper->spi) {
            delete wrapper->spi;
        }
        delete wrapper;
    }
}

MD_WRAPPER_API const char* MdGetApiVersion() {
    return CThostFtdcMdApi::GetApiVersion();
}

MD_WRAPPER_API void MdRegisterCallbacks(void* api, MdCallbacks* callbacks) {
    if (api && callbacks) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->spi) {
            wrapper->spi->callbacks = *callbacks;
        }
    }
}

MD_WRAPPER_API void MdRegisterFront(void* api, const char* front_address) {
    if (api && front_address) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->RegisterFront(const_cast<char*>(front_address));
        }
    }
}

MD_WRAPPER_API void MdInit(void* api) {
    if (api) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->Init();
        }
    }
}

MD_WRAPPER_API int MdJoin(void* api) {
    if (api) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            return wrapper->api->Join();
        }
    }
    return -1;
}

MD_WRAPPER_API const char* MdGetTradingDay(void* api) {
    if (api) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            return wrapper->api->GetTradingDay();
        }
    }
    return "";
}

MD_WRAPPER_API int MdReqUserLogin(void* api,
    const char* broker_id, const char* user_id,
    const char* password, int request_id)
{
    if (api) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcReqUserLoginField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.UserID, user_id, sizeof(req.UserID) - 1);
            strncpy(req.Password, password, sizeof(req.Password) - 1);
            return wrapper->api->ReqUserLogin(&req, request_id);
        }
    }
    return -1;
}

MD_WRAPPER_API int MdReqUserLogout(void* api,
    const char* broker_id, const char* user_id, int request_id)
{
    if (api) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcUserLogoutField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.UserID, user_id, sizeof(req.UserID) - 1);
            return wrapper->api->ReqUserLogout(&req, request_id);
        }
    }
    return -1;
}

MD_WRAPPER_API int MdSubscribeMarketData(void* api,
    const char** instrument_ids, int count)
{
    if (api && instrument_ids && count > 0) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            return wrapper->api->SubscribeMarketData(
                const_cast<char**>(instrument_ids), count);
        }
    }
    return -1;
}

MD_WRAPPER_API int MdUnSubscribeMarketData(void* api,
    const char** instrument_ids, int count)
{
    if (api && instrument_ids && count > 0) {
        MdApiWrapper* wrapper = static_cast<MdApiWrapper*>(api);
        if (wrapper->api) {
            return wrapper->api->UnSubscribeMarketData(
                const_cast<char**>(instrument_ids), count);
        }
    }
    return -1;
}
