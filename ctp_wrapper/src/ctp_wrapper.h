/**
 * CTP API C Wrapper Header
 * 将CTP C++ API封装为C接口，供Python ctypes调用
 *
 * 作者: CTP Wrapper
 * 版本: 2.0.0 (对应CTP v6.6.8) - 完整功能版
 */

#ifndef CTP_WRAPPER_H
#define CTP_WRAPPER_H

#ifdef _WIN32
    #ifdef CTP_WRAPPER_EXPORTS
        #define CTP_API __declspec(dllexport)
    #else
        #define CTP_API __declspec(dllimport)
    #endif
#else
    #define CTP_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================
// 回调函数类型定义 - 连接相关
// ============================================================
typedef void (*OnFrontConnectedCallback)();
typedef void (*OnFrontDisconnectedCallback)(int nReason);
typedef void (*OnHeartBeatWarningCallback)(int nTimeLapse);

// ============================================================
// 回调函数类型定义 - 认证登录
// ============================================================
typedef void (*OnRspAuthenticateCallback)(
    const char* broker_id, const char* user_id, const char* app_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspUserLoginCallback)(
    const char* trading_day, const char* login_time,
    const char* broker_id, const char* user_id,
    int front_id, int session_id, const char* max_order_ref,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspUserLogoutCallback)(
    const char* broker_id, const char* user_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspUserPasswordUpdateCallback)(
    const char* broker_id, const char* user_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspErrorCallback)(
    int error_id, const char* error_msg, int request_id, int is_last);

// ============================================================
// 回调函数类型定义 - 结算
// ============================================================
typedef void (*OnRspSettlementInfoConfirmCallback)(
    const char* broker_id, const char* investor_id,
    const char* confirm_date, const char* confirm_time,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQrySettlementInfoCallback)(
    const char* broker_id, const char* investor_id,
    const char* trading_day, const char* content,
    int error_id, const char* error_msg, int request_id, int is_last);

// ============================================================
// 回调函数类型定义 - 报单相关
// ============================================================
typedef void (*OnRspOrderInsertCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    char direction, char offset_flag, double price, int volume,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspOrderActionCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    int front_id, int session_id, const char* order_sys_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRtnOrderCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    const char* user_id, char direction, char offset_flag,
    double price, int volume_total, int volume_traded,
    char order_status, const char* order_sys_id,
    int front_id, int session_id,
    const char* insert_date, const char* insert_time,
    const char* status_msg);

typedef void (*OnRtnTradeCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    const char* user_id, const char* trade_id,
    char direction, char offset_flag,
    double price, int volume,
    const char* trade_date, const char* trade_time,
    const char* order_sys_id);

typedef void (*OnErrRtnOrderInsertCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    char direction, char offset_flag, double price, int volume,
    int error_id, const char* error_msg);

typedef void (*OnErrRtnOrderActionCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_sys_id,
    int error_id, const char* error_msg);

// ============================================================
// 回调函数类型定义 - 查询响应
// ============================================================
typedef void (*OnRspQryOrderCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    char direction, char offset_flag,
    double price, int volume_total, int volume_traded,
    char order_status, const char* order_sys_id,
    const char* insert_date, const char* insert_time,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryTradeCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* trade_id,
    char direction, char offset_flag,
    double price, int volume,
    const char* trade_date, const char* trade_time,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryInvestorPositionCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, char position_direction,
    int position, int yd_position,
    double position_cost, double open_cost,
    double use_margin, double frozen_margin,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryTradingAccountCallback)(
    const char* broker_id, const char* account_id,
    double balance, double available, double frozen_cash,
    double curr_margin, double close_profit, double position_profit,
    double commission, double withdraw_quota,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryInstrumentCallback)(
    const char* instrument_id, const char* exchange_id,
    const char* instrument_name, const char* product_id,
    int volume_multiple, double price_tick,
    double long_margin_ratio, double short_margin_ratio,
    int is_trading,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryDepthMarketDataCallback)(
    const char* instrument_id, const char* exchange_id,
    double last_price, double pre_settlement_price,
    double open_price, double highest_price, double lowest_price,
    int volume, double turnover, double open_interest,
    double bid_price1, int bid_volume1,
    double ask_price1, int ask_volume1,
    const char* update_time,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryInstrumentMarginRateCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id,
    double long_margin_ratio_by_money, double long_margin_ratio_by_volume,
    double short_margin_ratio_by_money, double short_margin_ratio_by_volume,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryInstrumentCommissionRateCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id,
    double open_ratio_by_money, double open_ratio_by_volume,
    double close_ratio_by_money, double close_ratio_by_volume,
    double close_today_ratio_by_money, double close_today_ratio_by_volume,
    int error_id, const char* error_msg, int request_id, int is_last);

// ============================================================
// 回调函数类型定义 - 扩展查询响应
// ============================================================
typedef void (*OnRspQryExchangeCallback)(
    const char* exchange_id, const char* exchange_name,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryProductCallback)(
    const char* product_id, const char* product_name,
    const char* exchange_id, int product_class,
    int volume_multiple, double price_tick,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryInvestorPositionDetailCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* exchange_id,
    char direction, const char* open_date,
    const char* trade_id, int volume,
    double open_price, double margin,
    double close_profit, double position_profit,
    const char* trading_day,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryInvestorCallback)(
    const char* broker_id, const char* investor_id,
    const char* investor_name, const char* id_card_no,
    int investor_type,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryTradingCodeCallback)(
    const char* broker_id, const char* investor_id,
    const char* exchange_id, const char* client_id,
    int client_id_type,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRspQryInstrumentOrderCommRateCallback)(
    const char* broker_id, const char* investor_id,
    const char* instrument_id,
    double order_comm_by_volume, double order_action_comm_by_volume,
    const char* exchange_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*OnRtnInstrumentStatusCallback)(
    const char* exchange_id, const char* instrument_id,
    int instrument_status, const char* enter_time,
    int enter_reason);

// ============================================================
// 回调注册结构体
// ============================================================
typedef struct {
    // 连接相关
    OnFrontConnectedCallback on_front_connected;
    OnFrontDisconnectedCallback on_front_disconnected;
    OnHeartBeatWarningCallback on_heartbeat_warning;

    // 认证登录
    OnRspAuthenticateCallback on_rsp_authenticate;
    OnRspUserLoginCallback on_rsp_user_login;
    OnRspUserLogoutCallback on_rsp_user_logout;
    OnRspUserPasswordUpdateCallback on_rsp_user_password_update;
    OnRspErrorCallback on_rsp_error;

    // 结算
    OnRspSettlementInfoConfirmCallback on_rsp_settlement_info_confirm;
    OnRspQrySettlementInfoCallback on_rsp_qry_settlement_info;

    // 报单相关
    OnRspOrderInsertCallback on_rsp_order_insert;
    OnRspOrderActionCallback on_rsp_order_action;
    OnRtnOrderCallback on_rtn_order;
    OnRtnTradeCallback on_rtn_trade;
    OnErrRtnOrderInsertCallback on_err_rtn_order_insert;
    OnErrRtnOrderActionCallback on_err_rtn_order_action;

    // 查询响应
    OnRspQryOrderCallback on_rsp_qry_order;
    OnRspQryTradeCallback on_rsp_qry_trade;
    OnRspQryInvestorPositionCallback on_rsp_qry_investor_position;
    OnRspQryTradingAccountCallback on_rsp_qry_trading_account;
    OnRspQryInstrumentCallback on_rsp_qry_instrument;
    OnRspQryDepthMarketDataCallback on_rsp_qry_depth_market_data;
    OnRspQryInstrumentMarginRateCallback on_rsp_qry_instrument_margin_rate;
    OnRspQryInstrumentCommissionRateCallback on_rsp_qry_instrument_commission_rate;

    // 扩展查询响应
    OnRspQryExchangeCallback on_rsp_qry_exchange;
    OnRspQryProductCallback on_rsp_qry_product;
    OnRspQryInvestorPositionDetailCallback on_rsp_qry_investor_position_detail;
    OnRspQryInvestorCallback on_rsp_qry_investor;
    OnRspQryTradingCodeCallback on_rsp_qry_trading_code;
    OnRspQryInstrumentOrderCommRateCallback on_rsp_qry_instrument_order_comm_rate;
    OnRtnInstrumentStatusCallback on_rtn_instrument_status;
} TraderCallbacks;

// ============================================================
// API 函数声明 - 基础
// ============================================================
CTP_API void* CreateTraderApi(const char* flow_path);
CTP_API void ReleaseTraderApi(void* api);
CTP_API const char* GetApiVersion();
CTP_API void RegisterCallbacks(void* api, TraderCallbacks* callbacks);
CTP_API void RegisterFront(void* api, const char* front_address);
CTP_API void SubscribePrivateTopic(void* api, int resume_type);
CTP_API void SubscribePublicTopic(void* api, int resume_type);
CTP_API void Init(void* api);
CTP_API int Join(void* api);
CTP_API const char* GetTradingDay(void* api);

// ============================================================
// API 函数声明 - 认证登录
// ============================================================
CTP_API int ReqAuthenticate(void* api,
    const char* broker_id, const char* user_id,
    const char* app_id, const char* auth_code, int request_id);

CTP_API int ReqUserLogin(void* api,
    const char* broker_id, const char* user_id,
    const char* password, int request_id);

CTP_API int ReqUserLogout(void* api,
    const char* broker_id, const char* user_id, int request_id);

CTP_API int ReqUserPasswordUpdate(void* api,
    const char* broker_id, const char* user_id,
    const char* old_password, const char* new_password, int request_id);

// ============================================================
// API 函数声明 - 结算
// ============================================================
CTP_API int ReqSettlementInfoConfirm(void* api,
    const char* broker_id, const char* investor_id, int request_id);

CTP_API int ReqQrySettlementInfo(void* api,
    const char* broker_id, const char* investor_id,
    const char* trading_day, int request_id);

// ============================================================
// API 函数声明 - 交易
// ============================================================
CTP_API int ReqOrderInsert(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_ref,
    char direction, char offset_flag,
    double price, int volume,
    char order_price_type, char time_condition, char volume_condition,
    int request_id);

CTP_API int ReqOrderAction(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* exchange_id,
    const char* order_ref, int front_id, int session_id,
    const char* order_sys_id, int request_id);

// ============================================================
// API 函数声明 - 查询
// ============================================================
CTP_API int ReqQryOrder(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* order_sys_id, int request_id);

CTP_API int ReqQryTrade(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, const char* trade_id, int request_id);

CTP_API int ReqQryInvestorPosition(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id);

CTP_API int ReqQryTradingAccount(void* api,
    const char* broker_id, const char* investor_id, int request_id);

CTP_API int ReqQryInstrument(void* api,
    const char* instrument_id, const char* exchange_id,
    const char* product_id, int request_id);

CTP_API int ReqQryDepthMarketData(void* api,
    const char* instrument_id, int request_id);

CTP_API int ReqQryInstrumentMarginRate(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id);

CTP_API int ReqQryInstrumentCommissionRate(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id);

// ============================================================
// API 函数声明 - 扩展查询
// ============================================================
CTP_API int ReqQryExchange(void* api,
    const char* exchange_id, int request_id);

CTP_API int ReqQryProduct(void* api,
    const char* product_id, const char* exchange_id, int request_id);

CTP_API int ReqQryInvestorPositionDetail(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id);

CTP_API int ReqQryInvestor(void* api,
    const char* broker_id, const char* investor_id, int request_id);

CTP_API int ReqQryTradingCode(void* api,
    const char* broker_id, const char* investor_id, int request_id);

CTP_API int ReqQryInstrumentOrderCommRate(void* api,
    const char* broker_id, const char* investor_id,
    const char* instrument_id, int request_id);

#ifdef __cplusplus
}
#endif

#endif // CTP_WRAPPER_H
