/**
 * CTP MdApi C Wrapper Header
 * 将CTP行情API封装为C接口，供Python ctypes调用
 */

#ifndef CTP_MD_WRAPPER_H
#define CTP_MD_WRAPPER_H

#ifdef _WIN32
    #ifdef CTP_MD_WRAPPER_EXPORTS
        #define MD_WRAPPER_API __declspec(dllexport)
    #else
        #define MD_WRAPPER_API __declspec(dllimport)
    #endif
#else
    #define MD_WRAPPER_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================
// 回调函数类型定义
// ============================================================
typedef void (*MdOnFrontConnectedCallback)();
typedef void (*MdOnFrontDisconnectedCallback)(int nReason);
typedef void (*MdOnHeartBeatWarningCallback)(int nTimeLapse);

typedef void (*MdOnRspUserLoginCallback)(
    const char* trading_day, const char* login_time,
    const char* broker_id, const char* user_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*MdOnRspUserLogoutCallback)(
    const char* broker_id, const char* user_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*MdOnRspErrorCallback)(
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*MdOnRspSubMarketDataCallback)(
    const char* instrument_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*MdOnRspUnSubMarketDataCallback)(
    const char* instrument_id,
    int error_id, const char* error_msg, int request_id, int is_last);

typedef void (*MdOnRtnDepthMarketDataCallback)(
    const char* instrument_id, const char* exchange_id,
    double last_price, double pre_settlement_price,
    double pre_close_price, double pre_open_interest,
    double open_price, double highest_price, double lowest_price,
    int volume, double turnover, double open_interest,
    double close_price, double settlement_price,
    double upper_limit_price, double lower_limit_price,
    double bid_price1, int bid_volume1,
    double ask_price1, int ask_volume1,
    double bid_price2, int bid_volume2,
    double ask_price2, int ask_volume2,
    double bid_price3, int bid_volume3,
    double ask_price3, int ask_volume3,
    double bid_price4, int bid_volume4,
    double ask_price4, int ask_volume4,
    double bid_price5, int bid_volume5,
    double ask_price5, int ask_volume5,
    double average_price,
    const char* update_time, int update_millisec,
    const char* trading_day, const char* action_day);

// ============================================================
// 回调注册结构体
// ============================================================
typedef struct {
    MdOnFrontConnectedCallback on_front_connected;
    MdOnFrontDisconnectedCallback on_front_disconnected;
    MdOnHeartBeatWarningCallback on_heartbeat_warning;
    MdOnRspUserLoginCallback on_rsp_user_login;
    MdOnRspUserLogoutCallback on_rsp_user_logout;
    MdOnRspErrorCallback on_rsp_error;
    MdOnRspSubMarketDataCallback on_rsp_sub_market_data;
    MdOnRspUnSubMarketDataCallback on_rsp_unsub_market_data;
    MdOnRtnDepthMarketDataCallback on_rtn_depth_market_data;
} MdCallbacks;

// ============================================================
// API 函数声明
// ============================================================
MD_WRAPPER_API void* CreateMdApi(const char* flow_path);
MD_WRAPPER_API void ReleaseMdApi(void* api);
MD_WRAPPER_API const char* MdGetApiVersion();
MD_WRAPPER_API void MdRegisterCallbacks(void* api, MdCallbacks* callbacks);
MD_WRAPPER_API void MdRegisterFront(void* api, const char* front_address);
MD_WRAPPER_API void MdInit(void* api);
MD_WRAPPER_API int MdJoin(void* api);
MD_WRAPPER_API const char* MdGetTradingDay(void* api);

MD_WRAPPER_API int MdReqUserLogin(void* api,
    const char* broker_id, const char* user_id,
    const char* password, int request_id);

MD_WRAPPER_API int MdReqUserLogout(void* api,
    const char* broker_id, const char* user_id, int request_id);

MD_WRAPPER_API int MdSubscribeMarketData(void* api,
    const char** instrument_ids, int count);

MD_WRAPPER_API int MdUnSubscribeMarketData(void* api,
    const char** instrument_ids, int count);

#ifdef __cplusplus
}
#endif

#endif // CTP_MD_WRAPPER_H
