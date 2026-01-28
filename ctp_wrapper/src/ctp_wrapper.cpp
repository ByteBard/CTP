/**
 * CTP API C Wrapper Implementation
 * 将CTP C++ API封装为C接口，供Python ctypes调用
 *
 * 作者: CTP Wrapper
 * 版本: 2.0.0 (对应CTP v6.6.8) - 完整功能版
 */

#include "ctp_wrapper.h"
#include "ThostFtdcTraderApi.h"
#include <cstring>
#include <string>

// ============================================================
// 内部包装类：实现CThostFtdcTraderSpi接口
// ============================================================
class TraderSpiWrapper : public CThostFtdcTraderSpi
{
public:
    TraderCallbacks callbacks;

    TraderSpiWrapper() {
        memset(&callbacks, 0, sizeof(callbacks));
    }

    // ========== 连接相关回调 ==========
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

    // ========== 认证登录回调 ==========
    virtual void OnRspAuthenticate(
        CThostFtdcRspAuthenticateField *pRspAuthenticateField,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_authenticate) {
            const char* broker_id = pRspAuthenticateField ? pRspAuthenticateField->BrokerID : "";
            const char* user_id = pRspAuthenticateField ? pRspAuthenticateField->UserID : "";
            const char* app_id = pRspAuthenticateField ? pRspAuthenticateField->AppID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_authenticate(
                broker_id, user_id, app_id,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
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
            int front_id = pRspUserLogin ? pRspUserLogin->FrontID : 0;
            int session_id = pRspUserLogin ? pRspUserLogin->SessionID : 0;
            const char* max_order_ref = pRspUserLogin ? pRspUserLogin->MaxOrderRef : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_user_login(
                trading_day, login_time, broker_id, user_id,
                front_id, session_id, max_order_ref,
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

    virtual void OnRspUserPasswordUpdate(
        CThostFtdcUserPasswordUpdateField *pUserPasswordUpdate,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_user_password_update) {
            const char* broker_id = pUserPasswordUpdate ? pUserPasswordUpdate->BrokerID : "";
            const char* user_id = pUserPasswordUpdate ? pUserPasswordUpdate->UserID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_user_password_update(
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

    // ========== 结算回调 ==========
    virtual void OnRspSettlementInfoConfirm(
        CThostFtdcSettlementInfoConfirmField *pSettlementInfoConfirm,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_settlement_info_confirm) {
            const char* broker_id = pSettlementInfoConfirm ? pSettlementInfoConfirm->BrokerID : "";
            const char* investor_id = pSettlementInfoConfirm ? pSettlementInfoConfirm->InvestorID : "";
            const char* confirm_date = pSettlementInfoConfirm ? pSettlementInfoConfirm->ConfirmDate : "";
            const char* confirm_time = pSettlementInfoConfirm ? pSettlementInfoConfirm->ConfirmTime : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_settlement_info_confirm(
                broker_id, investor_id, confirm_date, confirm_time,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQrySettlementInfo(
        CThostFtdcSettlementInfoField *pSettlementInfo,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_settlement_info) {
            const char* broker_id = pSettlementInfo ? pSettlementInfo->BrokerID : "";
            const char* investor_id = pSettlementInfo ? pSettlementInfo->InvestorID : "";
            const char* trading_day = pSettlementInfo ? pSettlementInfo->TradingDay : "";
            const char* content = pSettlementInfo ? pSettlementInfo->Content : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_settlement_info(
                broker_id, investor_id, trading_day, content,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    // ========== 报单相关回调 ==========
    virtual void OnRspOrderInsert(
        CThostFtdcInputOrderField *pInputOrder,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_order_insert) {
            const char* broker_id = pInputOrder ? pInputOrder->BrokerID : "";
            const char* investor_id = pInputOrder ? pInputOrder->InvestorID : "";
            const char* instrument_id = pInputOrder ? pInputOrder->InstrumentID : "";
            const char* order_ref = pInputOrder ? pInputOrder->OrderRef : "";
            char direction = pInputOrder ? pInputOrder->Direction : '0';
            char offset_flag = pInputOrder ? pInputOrder->CombOffsetFlag[0] : '0';
            double price = pInputOrder ? pInputOrder->LimitPrice : 0.0;
            int volume = pInputOrder ? pInputOrder->VolumeTotalOriginal : 0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_order_insert(
                broker_id, investor_id, instrument_id, order_ref,
                direction, offset_flag, price, volume,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspOrderAction(
        CThostFtdcInputOrderActionField *pInputOrderAction,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_order_action) {
            const char* broker_id = pInputOrderAction ? pInputOrderAction->BrokerID : "";
            const char* investor_id = pInputOrderAction ? pInputOrderAction->InvestorID : "";
            const char* instrument_id = pInputOrderAction ? pInputOrderAction->InstrumentID : "";
            const char* order_ref = pInputOrderAction ? pInputOrderAction->OrderRef : "";
            int front_id = pInputOrderAction ? pInputOrderAction->FrontID : 0;
            int session_id = pInputOrderAction ? pInputOrderAction->SessionID : 0;
            const char* order_sys_id = pInputOrderAction ? pInputOrderAction->OrderSysID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_order_action(
                broker_id, investor_id, instrument_id, order_ref,
                front_id, session_id, order_sys_id,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRtnOrder(CThostFtdcOrderField *pOrder) override
    {
        if (callbacks.on_rtn_order) {
            const char* broker_id = pOrder ? pOrder->BrokerID : "";
            const char* investor_id = pOrder ? pOrder->InvestorID : "";
            const char* instrument_id = pOrder ? pOrder->InstrumentID : "";
            const char* order_ref = pOrder ? pOrder->OrderRef : "";
            const char* user_id = pOrder ? pOrder->UserID : "";
            char direction = pOrder ? pOrder->Direction : '0';
            char offset_flag = pOrder ? pOrder->CombOffsetFlag[0] : '0';
            double price = pOrder ? pOrder->LimitPrice : 0.0;
            int volume_total = pOrder ? pOrder->VolumeTotalOriginal : 0;
            int volume_traded = pOrder ? pOrder->VolumeTraded : 0;
            char order_status = pOrder ? pOrder->OrderStatus : '0';
            const char* order_sys_id = pOrder ? pOrder->OrderSysID : "";
            int front_id = pOrder ? pOrder->FrontID : 0;
            int session_id = pOrder ? pOrder->SessionID : 0;
            const char* insert_date = pOrder ? pOrder->InsertDate : "";
            const char* insert_time = pOrder ? pOrder->InsertTime : "";
            const char* status_msg = pOrder ? pOrder->StatusMsg : "";

            callbacks.on_rtn_order(
                broker_id, investor_id, instrument_id, order_ref,
                user_id, direction, offset_flag, price, volume_total, volume_traded,
                order_status, order_sys_id, front_id, session_id,
                insert_date, insert_time, status_msg);
        }
    }

    virtual void OnRtnTrade(CThostFtdcTradeField *pTrade) override
    {
        if (callbacks.on_rtn_trade) {
            const char* broker_id = pTrade ? pTrade->BrokerID : "";
            const char* investor_id = pTrade ? pTrade->InvestorID : "";
            const char* instrument_id = pTrade ? pTrade->InstrumentID : "";
            const char* order_ref = pTrade ? pTrade->OrderRef : "";
            const char* user_id = pTrade ? pTrade->UserID : "";
            const char* trade_id = pTrade ? pTrade->TradeID : "";
            char direction = pTrade ? pTrade->Direction : '0';
            char offset_flag = pTrade ? pTrade->OffsetFlag : '0';
            double price = pTrade ? pTrade->Price : 0.0;
            int volume = pTrade ? pTrade->Volume : 0;
            const char* trade_date = pTrade ? pTrade->TradeDate : "";
            const char* trade_time = pTrade ? pTrade->TradeTime : "";
            const char* order_sys_id = pTrade ? pTrade->OrderSysID : "";

            callbacks.on_rtn_trade(
                broker_id, investor_id, instrument_id, order_ref,
                user_id, trade_id, direction, offset_flag,
                price, volume, trade_date, trade_time, order_sys_id);
        }
    }

    virtual void OnErrRtnOrderInsert(
        CThostFtdcInputOrderField *pInputOrder,
        CThostFtdcRspInfoField *pRspInfo) override
    {
        if (callbacks.on_err_rtn_order_insert) {
            const char* broker_id = pInputOrder ? pInputOrder->BrokerID : "";
            const char* investor_id = pInputOrder ? pInputOrder->InvestorID : "";
            const char* instrument_id = pInputOrder ? pInputOrder->InstrumentID : "";
            const char* order_ref = pInputOrder ? pInputOrder->OrderRef : "";
            char direction = pInputOrder ? pInputOrder->Direction : '0';
            char offset_flag = pInputOrder ? pInputOrder->CombOffsetFlag[0] : '0';
            double price = pInputOrder ? pInputOrder->LimitPrice : 0.0;
            int volume = pInputOrder ? pInputOrder->VolumeTotalOriginal : 0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_err_rtn_order_insert(
                broker_id, investor_id, instrument_id, order_ref,
                direction, offset_flag, price, volume,
                error_id, error_msg);
        }
    }

    virtual void OnErrRtnOrderAction(
        CThostFtdcOrderActionField *pOrderAction,
        CThostFtdcRspInfoField *pRspInfo) override
    {
        if (callbacks.on_err_rtn_order_action) {
            const char* broker_id = pOrderAction ? pOrderAction->BrokerID : "";
            const char* investor_id = pOrderAction ? pOrderAction->InvestorID : "";
            const char* instrument_id = pOrderAction ? pOrderAction->InstrumentID : "";
            const char* order_sys_id = pOrderAction ? pOrderAction->OrderSysID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_err_rtn_order_action(
                broker_id, investor_id, instrument_id, order_sys_id,
                error_id, error_msg);
        }
    }

    // ========== 查询响应回调 ==========
    virtual void OnRspQryOrder(
        CThostFtdcOrderField *pOrder,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_order) {
            const char* broker_id = pOrder ? pOrder->BrokerID : "";
            const char* investor_id = pOrder ? pOrder->InvestorID : "";
            const char* instrument_id = pOrder ? pOrder->InstrumentID : "";
            const char* order_ref = pOrder ? pOrder->OrderRef : "";
            char direction = pOrder ? pOrder->Direction : '0';
            char offset_flag = pOrder ? pOrder->CombOffsetFlag[0] : '0';
            double price = pOrder ? pOrder->LimitPrice : 0.0;
            int volume_total = pOrder ? pOrder->VolumeTotalOriginal : 0;
            int volume_traded = pOrder ? pOrder->VolumeTraded : 0;
            char order_status = pOrder ? pOrder->OrderStatus : '0';
            const char* order_sys_id = pOrder ? pOrder->OrderSysID : "";
            const char* insert_date = pOrder ? pOrder->InsertDate : "";
            const char* insert_time = pOrder ? pOrder->InsertTime : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_order(
                broker_id, investor_id, instrument_id, order_ref,
                direction, offset_flag, price, volume_total, volume_traded,
                order_status, order_sys_id, insert_date, insert_time,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryTrade(
        CThostFtdcTradeField *pTrade,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_trade) {
            const char* broker_id = pTrade ? pTrade->BrokerID : "";
            const char* investor_id = pTrade ? pTrade->InvestorID : "";
            const char* instrument_id = pTrade ? pTrade->InstrumentID : "";
            const char* trade_id = pTrade ? pTrade->TradeID : "";
            char direction = pTrade ? pTrade->Direction : '0';
            char offset_flag = pTrade ? pTrade->OffsetFlag : '0';
            double price = pTrade ? pTrade->Price : 0.0;
            int volume = pTrade ? pTrade->Volume : 0;
            const char* trade_date = pTrade ? pTrade->TradeDate : "";
            const char* trade_time = pTrade ? pTrade->TradeTime : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_trade(
                broker_id, investor_id, instrument_id, trade_id,
                direction, offset_flag, price, volume,
                trade_date, trade_time,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryInvestorPosition(
        CThostFtdcInvestorPositionField *pInvestorPosition,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_investor_position) {
            const char* broker_id = pInvestorPosition ? pInvestorPosition->BrokerID : "";
            const char* investor_id = pInvestorPosition ? pInvestorPosition->InvestorID : "";
            const char* instrument_id = pInvestorPosition ? pInvestorPosition->InstrumentID : "";
            char position_direction = pInvestorPosition ? pInvestorPosition->PosiDirection : '0';
            int position = pInvestorPosition ? pInvestorPosition->Position : 0;
            int yd_position = pInvestorPosition ? pInvestorPosition->YdPosition : 0;
            double position_cost = pInvestorPosition ? pInvestorPosition->PositionCost : 0.0;
            double open_cost = pInvestorPosition ? pInvestorPosition->OpenCost : 0.0;
            double use_margin = pInvestorPosition ? pInvestorPosition->UseMargin : 0.0;
            double frozen_margin = pInvestorPosition ? pInvestorPosition->FrozenMargin : 0.0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_investor_position(
                broker_id, investor_id, instrument_id, position_direction,
                position, yd_position, position_cost, open_cost,
                use_margin, frozen_margin,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryTradingAccount(
        CThostFtdcTradingAccountField *pTradingAccount,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_trading_account) {
            const char* broker_id = pTradingAccount ? pTradingAccount->BrokerID : "";
            const char* account_id = pTradingAccount ? pTradingAccount->AccountID : "";
            double balance = pTradingAccount ? pTradingAccount->Balance : 0.0;
            double available = pTradingAccount ? pTradingAccount->Available : 0.0;
            double frozen_cash = pTradingAccount ? pTradingAccount->FrozenCash : 0.0;
            double curr_margin = pTradingAccount ? pTradingAccount->CurrMargin : 0.0;
            double close_profit = pTradingAccount ? pTradingAccount->CloseProfit : 0.0;
            double position_profit = pTradingAccount ? pTradingAccount->PositionProfit : 0.0;
            double commission = pTradingAccount ? pTradingAccount->Commission : 0.0;
            double withdraw_quota = pTradingAccount ? pTradingAccount->WithdrawQuota : 0.0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_trading_account(
                broker_id, account_id, balance, available, frozen_cash,
                curr_margin, close_profit, position_profit,
                commission, withdraw_quota,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryInstrument(
        CThostFtdcInstrumentField *pInstrument,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_instrument) {
            const char* instrument_id = pInstrument ? pInstrument->InstrumentID : "";
            const char* exchange_id = pInstrument ? pInstrument->ExchangeID : "";
            const char* instrument_name = pInstrument ? pInstrument->InstrumentName : "";
            const char* product_id = pInstrument ? pInstrument->ProductID : "";
            int volume_multiple = pInstrument ? pInstrument->VolumeMultiple : 0;
            double price_tick = pInstrument ? pInstrument->PriceTick : 0.0;
            double long_margin_ratio = pInstrument ? pInstrument->LongMarginRatio : 0.0;
            double short_margin_ratio = pInstrument ? pInstrument->ShortMarginRatio : 0.0;
            int is_trading = pInstrument ? pInstrument->IsTrading : 0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_instrument(
                instrument_id, exchange_id, instrument_name, product_id,
                volume_multiple, price_tick, long_margin_ratio, short_margin_ratio,
                is_trading,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryDepthMarketData(
        CThostFtdcDepthMarketDataField *pDepthMarketData,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_depth_market_data) {
            const char* instrument_id = pDepthMarketData ? pDepthMarketData->InstrumentID : "";
            const char* exchange_id = pDepthMarketData ? pDepthMarketData->ExchangeID : "";
            double last_price = pDepthMarketData ? pDepthMarketData->LastPrice : 0.0;
            double pre_settlement_price = pDepthMarketData ? pDepthMarketData->PreSettlementPrice : 0.0;
            double open_price = pDepthMarketData ? pDepthMarketData->OpenPrice : 0.0;
            double highest_price = pDepthMarketData ? pDepthMarketData->HighestPrice : 0.0;
            double lowest_price = pDepthMarketData ? pDepthMarketData->LowestPrice : 0.0;
            int volume = pDepthMarketData ? pDepthMarketData->Volume : 0;
            double turnover = pDepthMarketData ? pDepthMarketData->Turnover : 0.0;
            double open_interest = pDepthMarketData ? pDepthMarketData->OpenInterest : 0.0;
            double bid_price1 = pDepthMarketData ? pDepthMarketData->BidPrice1 : 0.0;
            int bid_volume1 = pDepthMarketData ? pDepthMarketData->BidVolume1 : 0;
            double ask_price1 = pDepthMarketData ? pDepthMarketData->AskPrice1 : 0.0;
            int ask_volume1 = pDepthMarketData ? pDepthMarketData->AskVolume1 : 0;
            const char* update_time = pDepthMarketData ? pDepthMarketData->UpdateTime : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_depth_market_data(
                instrument_id, exchange_id, last_price, pre_settlement_price,
                open_price, highest_price, lowest_price,
                volume, turnover, open_interest,
                bid_price1, bid_volume1, ask_price1, ask_volume1,
                update_time,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryInstrumentMarginRate(
        CThostFtdcInstrumentMarginRateField *pInstrumentMarginRate,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_instrument_margin_rate) {
            const char* broker_id = pInstrumentMarginRate ? pInstrumentMarginRate->BrokerID : "";
            const char* investor_id = pInstrumentMarginRate ? pInstrumentMarginRate->InvestorID : "";
            const char* instrument_id = pInstrumentMarginRate ? pInstrumentMarginRate->InstrumentID : "";
            double long_margin_ratio_by_money = pInstrumentMarginRate ? pInstrumentMarginRate->LongMarginRatioByMoney : 0.0;
            double long_margin_ratio_by_volume = pInstrumentMarginRate ? pInstrumentMarginRate->LongMarginRatioByVolume : 0.0;
            double short_margin_ratio_by_money = pInstrumentMarginRate ? pInstrumentMarginRate->ShortMarginRatioByMoney : 0.0;
            double short_margin_ratio_by_volume = pInstrumentMarginRate ? pInstrumentMarginRate->ShortMarginRatioByVolume : 0.0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_instrument_margin_rate(
                broker_id, investor_id, instrument_id,
                long_margin_ratio_by_money, long_margin_ratio_by_volume,
                short_margin_ratio_by_money, short_margin_ratio_by_volume,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryInstrumentCommissionRate(
        CThostFtdcInstrumentCommissionRateField *pInstrumentCommissionRate,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_instrument_commission_rate) {
            const char* broker_id = pInstrumentCommissionRate ? pInstrumentCommissionRate->BrokerID : "";
            const char* investor_id = pInstrumentCommissionRate ? pInstrumentCommissionRate->InvestorID : "";
            const char* instrument_id = pInstrumentCommissionRate ? pInstrumentCommissionRate->InstrumentID : "";
            double open_ratio_by_money = pInstrumentCommissionRate ? pInstrumentCommissionRate->OpenRatioByMoney : 0.0;
            double open_ratio_by_volume = pInstrumentCommissionRate ? pInstrumentCommissionRate->OpenRatioByVolume : 0.0;
            double close_ratio_by_money = pInstrumentCommissionRate ? pInstrumentCommissionRate->CloseRatioByMoney : 0.0;
            double close_ratio_by_volume = pInstrumentCommissionRate ? pInstrumentCommissionRate->CloseRatioByVolume : 0.0;
            double close_today_ratio_by_money = pInstrumentCommissionRate ? pInstrumentCommissionRate->CloseTodayRatioByMoney : 0.0;
            double close_today_ratio_by_volume = pInstrumentCommissionRate ? pInstrumentCommissionRate->CloseTodayRatioByVolume : 0.0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_instrument_commission_rate(
                broker_id, investor_id, instrument_id,
                open_ratio_by_money, open_ratio_by_volume,
                close_ratio_by_money, close_ratio_by_volume,
                close_today_ratio_by_money, close_today_ratio_by_volume,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }
    // ========== 扩展查询响应回调 ==========
    virtual void OnRspQryExchange(
        CThostFtdcExchangeField *pExchange,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_exchange) {
            const char* exchange_id = pExchange ? pExchange->ExchangeID : "";
            const char* exchange_name = pExchange ? pExchange->ExchangeName : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_exchange(
                exchange_id, exchange_name,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryProduct(
        CThostFtdcProductField *pProduct,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_product) {
            const char* product_id = pProduct ? pProduct->ProductID : "";
            const char* product_name = pProduct ? pProduct->ProductName : "";
            const char* exchange_id = pProduct ? pProduct->ExchangeID : "";
            int product_class = pProduct ? pProduct->ProductClass : 0;
            int volume_multiple = pProduct ? pProduct->VolumeMultiple : 0;
            double price_tick = pProduct ? pProduct->PriceTick : 0.0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_product(
                product_id, product_name, exchange_id, product_class,
                volume_multiple, price_tick,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryInvestorPositionDetail(
        CThostFtdcInvestorPositionDetailField *pDetail,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_investor_position_detail) {
            const char* broker_id = pDetail ? pDetail->BrokerID : "";
            const char* investor_id = pDetail ? pDetail->InvestorID : "";
            const char* instrument_id = pDetail ? pDetail->InstrumentID : "";
            const char* exchange_id = pDetail ? pDetail->ExchangeID : "";
            char direction = pDetail ? pDetail->Direction : '0';
            const char* open_date = pDetail ? pDetail->OpenDate : "";
            const char* trade_id = pDetail ? pDetail->TradeID : "";
            int volume = pDetail ? pDetail->Volume : 0;
            double open_price = pDetail ? pDetail->OpenPrice : 0.0;
            double margin = pDetail ? pDetail->Margin : 0.0;
            double close_profit = pDetail ? pDetail->CloseProfitByDate : 0.0;
            double position_profit = pDetail ? pDetail->PositionProfitByDate : 0.0;
            const char* trading_day = pDetail ? pDetail->TradingDay : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_investor_position_detail(
                broker_id, investor_id, instrument_id, exchange_id,
                direction, open_date, trade_id, volume,
                open_price, margin, close_profit, position_profit,
                trading_day,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryInvestor(
        CThostFtdcInvestorField *pInvestor,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_investor) {
            const char* broker_id = pInvestor ? pInvestor->BrokerID : "";
            const char* investor_id = pInvestor ? pInvestor->InvestorID : "";
            const char* investor_name = pInvestor ? pInvestor->InvestorName : "";
            const char* id_card_no = pInvestor ? pInvestor->IdentifiedCardNo : "";
            int investor_type = pInvestor ? pInvestor->InvestorType : 0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_investor(
                broker_id, investor_id, investor_name, id_card_no,
                investor_type,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryTradingCode(
        CThostFtdcTradingCodeField *pTradingCode,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_trading_code) {
            const char* broker_id = pTradingCode ? pTradingCode->BrokerID : "";
            const char* investor_id = pTradingCode ? pTradingCode->InvestorID : "";
            const char* exchange_id = pTradingCode ? pTradingCode->ExchangeID : "";
            const char* client_id = pTradingCode ? pTradingCode->ClientID : "";
            int client_id_type = pTradingCode ? pTradingCode->ClientIDType : 0;
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_trading_code(
                broker_id, investor_id, exchange_id, client_id,
                client_id_type,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRspQryInstrumentOrderCommRate(
        CThostFtdcInstrumentOrderCommRateField *pRate,
        CThostFtdcRspInfoField *pRspInfo,
        int nRequestID, bool bIsLast) override
    {
        if (callbacks.on_rsp_qry_instrument_order_comm_rate) {
            const char* broker_id = pRate ? pRate->BrokerID : "";
            const char* investor_id = pRate ? pRate->InvestorID : "";
            const char* instrument_id = pRate ? pRate->InstrumentID : "";
            double order_comm = pRate ? pRate->OrderCommByVolume : 0.0;
            double action_comm = pRate ? pRate->OrderActionCommByVolume : 0.0;
            const char* exchange_id = pRate ? pRate->ExchangeID : "";
            int error_id = pRspInfo ? pRspInfo->ErrorID : 0;
            const char* error_msg = pRspInfo ? pRspInfo->ErrorMsg : "";

            callbacks.on_rsp_qry_instrument_order_comm_rate(
                broker_id, investor_id, instrument_id,
                order_comm, action_comm, exchange_id,
                error_id, error_msg, nRequestID, bIsLast ? 1 : 0);
        }
    }

    virtual void OnRtnInstrumentStatus(
        CThostFtdcInstrumentStatusField *pStatus) override
    {
        if (callbacks.on_rtn_instrument_status) {
            const char* exchange_id = pStatus ? pStatus->ExchangeID : "";
            const char* instrument_id = pStatus ? pStatus->InstrumentID : "";
            int status = pStatus ? pStatus->InstrumentStatus : 0;
            const char* enter_time = pStatus ? pStatus->EnterTime : "";
            int enter_reason = pStatus ? pStatus->EnterReason : 0;

            callbacks.on_rtn_instrument_status(
                exchange_id, instrument_id, status, enter_time, enter_reason);
        }
    }
};

// ============================================================
// 内部包装结构：持有API和Spi实例
// ============================================================
struct ApiWrapper {
    CThostFtdcTraderApi* api;
    TraderSpiWrapper* spi;
};

// ============================================================
// C 接口实现 - 基础函数
// ============================================================

CTP_API void* CreateTraderApi(const char* flow_path) {
    ApiWrapper* wrapper = new ApiWrapper();
    wrapper->api = CThostFtdcTraderApi::CreateFtdcTraderApi(flow_path);
    wrapper->spi = new TraderSpiWrapper();
    wrapper->api->RegisterSpi(wrapper->spi);
    return wrapper;
}

CTP_API void ReleaseTraderApi(void* api) {
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->Release();
        }
        if (wrapper->spi) {
            delete wrapper->spi;
        }
        delete wrapper;
    }
}

CTP_API const char* GetApiVersion() {
    return CThostFtdcTraderApi::GetApiVersion();
}

CTP_API void RegisterCallbacks(void* api, TraderCallbacks* callbacks) {
    if (api && callbacks) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->spi) {
            wrapper->spi->callbacks = *callbacks;
        }
    }
}

CTP_API void RegisterFront(void* api, const char* front_address) {
    if (api && front_address) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->RegisterFront(const_cast<char*>(front_address));
        }
    }
}

CTP_API void SubscribePrivateTopic(void* api, int resume_type) {
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->SubscribePrivateTopic(static_cast<THOST_TE_RESUME_TYPE>(resume_type));
        }
    }
}

CTP_API void SubscribePublicTopic(void* api, int resume_type) {
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->SubscribePublicTopic(static_cast<THOST_TE_RESUME_TYPE>(resume_type));
        }
    }
}

CTP_API void Init(void* api) {
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            wrapper->api->Init();
        }
    }
}

CTP_API int Join(void* api) {
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            return wrapper->api->Join();
        }
    }
    return -1;
}

CTP_API const char* GetTradingDay(void* api) {
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            return wrapper->api->GetTradingDay();
        }
    }
    return "";
}

// ============================================================
// C 接口实现 - 认证登录
// ============================================================

CTP_API int ReqAuthenticate(void* api,
    const char* broker_id, const char* user_id,
    const char* app_id, const char* auth_code, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcReqAuthenticateField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.UserID, user_id, sizeof(req.UserID) - 1);
            strncpy(req.AppID, app_id, sizeof(req.AppID) - 1);
            strncpy(req.AuthCode, auth_code, sizeof(req.AuthCode) - 1);
            return wrapper->api->ReqAuthenticate(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqUserLogin(void* api,
    const char* broker_id, const char* user_id,
    const char* password, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
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

CTP_API int ReqUserLogout(void* api,
    const char* broker_id, const char* user_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcUserLogoutField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.UserID, user_id, sizeof(req.UserID) - 1);
            return wrapper->api->ReqUserLogout(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqUserPasswordUpdate(void* api,
    const char* broker_id, const char* user_id,
    const char* old_password, const char* new_password, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcUserPasswordUpdateField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.UserID, user_id, sizeof(req.UserID) - 1);
            strncpy(req.OldPassword, old_password, sizeof(req.OldPassword) - 1);
            strncpy(req.NewPassword, new_password, sizeof(req.NewPassword) - 1);
            return wrapper->api->ReqUserPasswordUpdate(&req, request_id);
        }
    }
    return -1;
}

// ============================================================
// C 接口实现 - 结算
// ============================================================

CTP_API int ReqSettlementInfoConfirm(void* api,
    const char* broker_id, const char* investor_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcSettlementInfoConfirmField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            return wrapper->api->ReqSettlementInfoConfirm(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQrySettlementInfo(void* api,
    const char* broker_id, const char* investor_id,
    const char* trading_day, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQrySettlementInfoField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (trading_day) {
                strncpy(req.TradingDay, trading_day, sizeof(req.TradingDay) - 1);
            }
            return wrapper->api->ReqQrySettlementInfo(&req, request_id);
        }
    }
    return -1;
}

// ============================================================
// C 接口实现 - 交易
// ============================================================

CTP_API int ReqOrderInsert(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    char direction, char offset_flag,
    double price, int volume,
    char order_price_type, char time_condition, char volume_condition,
    int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcInputOrderField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            strncpy(req.OrderRef, order_ref, sizeof(req.OrderRef) - 1);
            req.Direction = direction;
            req.CombOffsetFlag[0] = offset_flag;
            req.CombHedgeFlag[0] = THOST_FTDC_HF_Speculation;  // 投机
            req.LimitPrice = price;
            req.VolumeTotalOriginal = volume;
            req.OrderPriceType = order_price_type;
            req.TimeCondition = time_condition;
            req.VolumeCondition = volume_condition;
            req.MinVolume = 1;
            req.ContingentCondition = THOST_FTDC_CC_Immediately;
            req.ForceCloseReason = THOST_FTDC_FCC_NotForceClose;
            req.IsAutoSuspend = 0;
            req.UserForceClose = 0;
            return wrapper->api->ReqOrderInsert(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqOrderAction(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* exchange_id,
    const char* order_ref, int front_id, int session_id,
    const char* order_sys_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcInputOrderActionField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            if (exchange_id) {
                strncpy(req.ExchangeID, exchange_id, sizeof(req.ExchangeID) - 1);
            }
            if (order_ref) {
                strncpy(req.OrderRef, order_ref, sizeof(req.OrderRef) - 1);
            }
            req.FrontID = front_id;
            req.SessionID = session_id;
            if (order_sys_id) {
                strncpy(req.OrderSysID, order_sys_id, sizeof(req.OrderSysID) - 1);
            }
            req.ActionFlag = THOST_FTDC_AF_Delete;
            return wrapper->api->ReqOrderAction(&req, request_id);
        }
    }
    return -1;
}

// ============================================================
// C 接口实现 - 查询
// ============================================================

CTP_API int ReqQryOrder(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_sys_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryOrderField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            if (order_sys_id) {
                strncpy(req.OrderSysID, order_sys_id, sizeof(req.OrderSysID) - 1);
            }
            return wrapper->api->ReqQryOrder(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryTrade(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* trade_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryTradeField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            if (trade_id) {
                strncpy(req.TradeID, trade_id, sizeof(req.TradeID) - 1);
            }
            return wrapper->api->ReqQryTrade(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryInvestorPosition(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryInvestorPositionField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            return wrapper->api->ReqQryInvestorPosition(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryTradingAccount(void* api,
    const char* broker_id, const char* investor_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryTradingAccountField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            return wrapper->api->ReqQryTradingAccount(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryInstrument(void* api,
    const char* instrument_id, const char* exchange_id,
    const char* product_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryInstrumentField req = {0};
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            if (exchange_id) {
                strncpy(req.ExchangeID, exchange_id, sizeof(req.ExchangeID) - 1);
            }
            if (product_id) {
                strncpy(req.ProductID, product_id, sizeof(req.ProductID) - 1);
            }
            return wrapper->api->ReqQryInstrument(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryDepthMarketData(void* api,
    const char* instrument_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryDepthMarketDataField req = {0};
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            return wrapper->api->ReqQryDepthMarketData(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryInstrumentMarginRate(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryInstrumentMarginRateField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            req.HedgeFlag = THOST_FTDC_HF_Speculation;
            return wrapper->api->ReqQryInstrumentMarginRate(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryInstrumentCommissionRate(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryInstrumentCommissionRateField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            return wrapper->api->ReqQryInstrumentCommissionRate(&req, request_id);
        }
    }
    return -1;
}

// ============================================================
// C 接口实现 - 扩展查询
// ============================================================

CTP_API int ReqQryExchange(void* api,
    const char* exchange_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryExchangeField req = {0};
            if (exchange_id) {
                strncpy(req.ExchangeID, exchange_id, sizeof(req.ExchangeID) - 1);
            }
            return wrapper->api->ReqQryExchange(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryProduct(void* api,
    const char* product_id, const char* exchange_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryProductField req = {0};
            if (product_id) {
                strncpy(req.ProductID, product_id, sizeof(req.ProductID) - 1);
            }
            if (exchange_id) {
                strncpy(req.ExchangeID, exchange_id, sizeof(req.ExchangeID) - 1);
            }
            return wrapper->api->ReqQryProduct(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryInvestorPositionDetail(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryInvestorPositionDetailField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            return wrapper->api->ReqQryInvestorPositionDetail(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryInvestor(void* api,
    const char* broker_id, const char* investor_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryInvestorField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            return wrapper->api->ReqQryInvestor(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryTradingCode(void* api,
    const char* broker_id, const char* investor_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryTradingCodeField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            return wrapper->api->ReqQryTradingCode(&req, request_id);
        }
    }
    return -1;
}

CTP_API int ReqQryInstrumentOrderCommRate(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id)
{
    if (api) {
        ApiWrapper* wrapper = static_cast<ApiWrapper*>(api);
        if (wrapper->api) {
            CThostFtdcQryInstrumentOrderCommRateField req = {0};
            strncpy(req.BrokerID, broker_id, sizeof(req.BrokerID) - 1);
            strncpy(req.InvestorID, investor_id, sizeof(req.InvestorID) - 1);
            if (instrument_id) {
                strncpy(req.InstrumentID, instrument_id, sizeof(req.InstrumentID) - 1);
            }
            return wrapper->api->ReqQryInstrumentOrderCommRate(&req, request_id);
        }
    }
    return -1;
}
