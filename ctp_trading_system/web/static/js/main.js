/**
 * CTP程序化交易系统 - 前端JavaScript
 */

// ==================== 全局状态 ====================
const AppState = {
    connected: false,
    authenticated: false,
    loggedIn: false,
    tradingPaused: false,
    ws: null
};

// ==================== API调用封装 ====================
const API = {
    baseUrl: '/api',

    async request(method, endpoint, data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(this.baseUrl + endpoint, options);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // 连接管理
    connect: (data) => API.request('POST', '/connection/connect', data),
    authenticate: (data) => API.request('POST', '/connection/authenticate', data),
    login: (data) => API.request('POST', '/connection/login', data),
    getConnectionStatus: () => API.request('GET', '/connection/status'),

    // 交易操作
    openPosition: (data) => API.request('POST', '/trading/open', data),
    closePosition: (data) => API.request('POST', '/trading/close', data),
    cancelOrder: (data) => API.request('POST', '/trading/cancel', data),
    validateOrder: (data) => API.request('POST', '/trading/validate', data),
    getOrders: () => API.request('GET', '/trading/orders'),

    // 监测
    getConnectionMonitor: () => API.request('GET', '/monitor/connection'),
    getOrderStats: () => API.request('GET', '/monitor/orders'),
    getThresholds: () => API.request('GET', '/monitor/thresholds'),
    updateThresholds: (data) => API.request('PUT', '/monitor/thresholds', data),
    getAlerts: () => API.request('GET', '/monitor/alerts'),

    // 应急处置
    pauseTrading: (data) => API.request('POST', '/emergency/pause', data),
    resumeTrading: (data) => API.request('POST', '/emergency/resume', data),
    cancelByInstrument: (data) => API.request('POST', '/emergency/cancel-by-instrument', data),
    cancelAll: (data) => API.request('POST', '/emergency/cancel-all', data),
    emergencyStop: (data) => API.request('POST', '/emergency/stop', data),
    getEmergencyStatus: () => API.request('GET', '/emergency/status'),

    // 日志
    getLogs: (params) => API.request('GET', '/logs/?' + new URLSearchParams(params)),
    getRealtimeLogs: () => API.request('GET', '/logs/realtime'),

    // 策略控制
    startStrategy: (data) => API.request('POST', '/strategy/start', data),
    stopStrategy: () => API.request('POST', '/strategy/stop', {}),
    getStrategyStatus: () => API.request('GET', '/strategy/status'),

    // 行情
    subscribeMd: (data) => API.request('POST', '/market/subscribe', data),
    unsubscribeMd: (data) => API.request('POST', '/market/unsubscribe', data),
    getMdData: () => API.request('GET', '/market/data'),
    getMdStatus: () => API.request('GET', '/market/status'),

    // 综合查询
    getExchanges: () => API.request('GET', '/trading/exchanges'),
    getProducts: (exchangeId) => API.request('GET', '/trading/products' + (exchangeId ? '?exchange_id=' + exchangeId : '')),
    getInvestor: () => API.request('GET', '/trading/investor'),
    getTradingCodes: () => API.request('GET', '/trading/trading_codes'),
    getPositionDetails: (instId) => API.request('GET', '/trading/position_details' + (instId ? '?instrument_id=' + instId : '')),
    getTrades: (instId) => API.request('GET', '/trading/trades' + (instId ? '?instrument_id=' + instId : '')),
    getMarginRate: (instId) => API.request('GET', '/trading/margin_rate/' + instId),
    getCommissionRate: (instId) => API.request('GET', '/trading/commission_rate/' + instId),
    getOrderCommRate: (instId) => API.request('GET', '/trading/order_comm_rate/' + instId),
    getInstrumentStatus: () => API.request('GET', '/trading/instrument_status')
};

// ==================== WebSocket管理 ====================
const WebSocketManager = {
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/realtime`;

        this.ws = new WebSocket(wsUrl);
        AppState.ws = this.ws;

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.addRealtimeLog('SYSTEM', 'INFO', 'WebSocket连接成功');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            // 尝试重连
            setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        // 心跳
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    },

    handleMessage(data) {
        switch (data.type) {
            case 'log':
                this.addRealtimeLog(data.log_type, data.level, data.message);
                break;
            case 'alert':
                this.showAlert(data.level, data.title, data.message);
                break;
            case 'status':
                this.handleStatusUpdate(data);
                break;
            case 'order':
                this.handleOrderUpdate(data.order);
                break;
        }
    },

    addRealtimeLog(type, level, message) {
        const container = document.getElementById('realtime-log');
        const line = document.createElement('div');
        line.className = 'log-line';

        const time = new Date().toLocaleTimeString();
        line.innerHTML = `<span class="timestamp">${time}</span> [<span class="level-${level}">${level}</span>] ${message}`;

        container.insertBefore(line, container.firstChild);

        // 限制日志数量
        while (container.children.length > 100) {
            container.removeChild(container.lastChild);
        }
    },

    showAlert(level, title, message) {
        // 添加到预警容器
        const container = document.getElementById('alert-container');
        const item = document.createElement('div');
        item.className = `alert-item ${level.toLowerCase()}`;
        item.innerHTML = `
            <div class="d-flex justify-content-between">
                <strong>${title}</strong>
                <span class="alert-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div>${message}</div>
        `;
        container.insertBefore(item, container.firstChild);

        // 显示弹窗
        if (level === 'CRITICAL' || level === 'WARNING') {
            document.getElementById('alertModalTitle').textContent = title;
            document.getElementById('alertModalBody').textContent = message;
            new bootstrap.Modal(document.getElementById('alertModal')).show();
        }
    },

    handleStatusUpdate(data) {
        if (data.status_type === 'connection') {
            updateConnectionUI(data.data.status);
        } else if (data.status_type === 'trading') {
            AppState.tradingPaused = data.data.paused;
            updateTradingStatusUI();
        }
    },

    handleOrderUpdate(order) {
        refreshOrders();
    }
};

// ==================== UI更新函数 ====================
function updateConnectionUI(status) {
    if (status === 'connected') {
        AppState.connected = true;
        document.getElementById('status-connection').textContent = '已连接';
        document.getElementById('status-indicator-connection').className = 'status-indicator connected';
        document.getElementById('btn-authenticate').disabled = false;
    } else if (status === 'authenticated') {
        AppState.authenticated = true;
        document.getElementById('status-auth').textContent = '已认证';
        document.getElementById('status-indicator-auth').className = 'status-indicator connected';
        document.getElementById('btn-login').disabled = false;
    } else if (status === 'logged_in') {
        AppState.loggedIn = true;
        document.getElementById('status-login').textContent = '已登录';
        document.getElementById('status-indicator-login').className = 'status-indicator connected';
        document.getElementById('system-status').innerHTML = '<i class="bi bi-circle-fill text-success"></i> 已连接';
        document.getElementById('system-status').className = 'badge bg-success';
    } else if (status === 'disconnected' || status === 'logged_out') {
        // 重置所有连接状态为断开
        AppState.connected = false;
        AppState.authenticated = false;
        AppState.loggedIn = false;
        document.getElementById('status-connection').textContent = '未连接';
        document.getElementById('status-indicator-connection').className = 'status-indicator disconnected';
        document.getElementById('status-auth').textContent = '未认证';
        document.getElementById('status-indicator-auth').className = 'status-indicator disconnected';
        document.getElementById('status-login').textContent = '未登录';
        document.getElementById('status-indicator-login').className = 'status-indicator disconnected';
        document.getElementById('system-status').innerHTML = '<i class="bi bi-circle-fill text-danger"></i> 已断开';
        document.getElementById('system-status').className = 'badge bg-danger';
        document.getElementById('btn-authenticate').disabled = true;
        document.getElementById('btn-login').disabled = true;
    }
}

function updateTradingStatusUI() {
    const paused = AppState.tradingPaused;
    const elements = ['status-trading', 'rt-trading-status', 'footer-trading'];

    elements.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (paused) {
                el.textContent = '已暂停';
                el.className = 'badge bg-warning';
            } else {
                el.textContent = '交易中';
                el.className = 'badge bg-success';
            }
        }
    });
}

function updateMonitorStats(stats) {
    document.getElementById('monitor-total-orders').textContent = stats.total_orders || 0;
    document.getElementById('monitor-total-cancels').textContent = stats.total_cancels || 0;
    document.getElementById('rt-total-orders').textContent = stats.total_orders || 0;
    document.getElementById('rt-total-cancels').textContent = stats.total_cancels || 0;
    document.getElementById('footer-orders').textContent = stats.total_orders || 0;
    document.getElementById('footer-cancels').textContent = stats.total_cancels || 0;

    // 更新合约统计表格
    const tbody = document.querySelector('#table-instrument-stats tbody');
    tbody.innerHTML = '';
    if (stats.by_instrument) {
        stats.by_instrument.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.instrument_id}</td>
                <td id="monitor-open-count-${item.instrument_id}">${item.open_count}</td>
                <td id="monitor-close-count-${item.instrument_id}">${item.close_count}</td>
                <td id="monitor-cancel-count-${item.instrument_id}">${item.cancel_count}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

async function refreshOrders() {
    try {
        const result = await API.getOrders();
        const tbody = document.querySelector('#table-orders tbody');
        tbody.innerHTML = '';

        if (result.orders) {
            result.orders.forEach(order => {
                const tr = document.createElement('tr');
                tr.id = `order-row-${order.order_ref}`;
                tr.innerHTML = `
                    <td>${order.order_ref}</td>
                    <td>${order.instrument_id}</td>
                    <td>${order.direction === 'buy' ? '买' : '卖'}</td>
                    <td>${order.offset === 'open' ? '开' : '平'}</td>
                    <td>${order.price}</td>
                    <td>${order.volume}</td>
                    <td class="order-status-${order.status}">${getOrderStatusText(order.status)}</td>
                    <td>
                        ${order.status === 'not_traded' || order.status === 'part_traded' ?
                        `<button class="btn btn-sm btn-outline-danger btn-cancel-order"
                                 data-instrument="${order.instrument_id}"
                                 data-ref="${order.order_ref}">撤单</button>` : ''}
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // 绑定撤单按钮事件
            document.querySelectorAll('.btn-cancel-order').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const instrument = btn.dataset.instrument;
                    const ref = btn.dataset.ref;
                    await API.cancelOrder({ instrument_id: instrument, order_ref: ref });
                });
            });
        }
    } catch (error) {
        console.error('Error refreshing orders:', error);
    }
}

function getOrderStatusText(status) {
    const statusMap = {
        'submitted': '已提交',
        'not_traded': '未成交',
        'part_traded': '部分成交',
        'all_traded': '全部成交',
        'canceled': '已撤销',
        'cancelling': '撤单中'
    };
    return statusMap[status] || status;
}

// ==================== 初始化检查 ====================
async function checkAndRestoreSession() {
    try {
        const status = await API.getConnectionStatus();
        if (status.logged_in) {
            updateConnectionUI('connected');
            updateConnectionUI('authenticated');
            updateConnectionUI('logged_in');
            WebSocketManager.addRealtimeLog('SYSTEM', 'INFO', '检测到已登录会话，自动恢复');
            refreshOrders();
        } else if (status.authenticated) {
            updateConnectionUI('connected');
            updateConnectionUI('authenticated');
        } else if (status.connected) {
            updateConnectionUI('connected');
        }
    } catch (error) {
        console.log('检查会话状态失败:', error);
    }
}

// ==================== 事件绑定 ====================
document.addEventListener('DOMContentLoaded', function() {
    // 初始化WebSocket
    WebSocketManager.connect();

    // 检查并恢复已有会话
    checkAndRestoreSession();

    // ===== 连接登录 =====
    document.getElementById('btn-connect').addEventListener('click', async () => {
        const result = await API.connect({
            broker_id: document.getElementById('input-broker-id').value,
            trade_front: document.getElementById('input-trade-front').value
        });
        if (result.success) {
            updateConnectionUI('connected');
        } else {
            alert('连接失败: ' + result.message);
        }
    });

    document.getElementById('btn-authenticate').addEventListener('click', async () => {
        const result = await API.authenticate({
            investor_id: document.getElementById('input-investor-id').value,
            app_id: document.getElementById('input-app-id').value,
            auth_code: document.getElementById('input-auth-code').value
        });
        if (result.success) {
            updateConnectionUI('authenticated');
        } else {
            alert('认证失败: ' + result.message);
        }
    });

    document.getElementById('btn-login').addEventListener('click', async () => {
        const result = await API.login({
            investor_id: document.getElementById('input-investor-id').value,
            password: document.getElementById('input-password').value
        });
        if (result.success) {
            updateConnectionUI('logged_in');
        } else {
            alert('登录失败: ' + result.message);
        }
    });

    // ===== 交易操作 =====
    function getSkipValidation() {
        return document.getElementById('chk-skip-validation').checked;
    }

    document.getElementById('btn-buy-open').addEventListener('click', async () => {
        const result = await API.openPosition({
            instrument_id: document.getElementById('input-instrument').value,
            price: parseFloat(document.getElementById('input-price').value),
            volume: parseInt(document.getElementById('input-volume').value),
            direction: 'buy',
            offset: 'open',
            skip_validation: getSkipValidation()
        });
        if (!result.success) {
            alert(result.message);
        }
        refreshOrders();
    });

    document.getElementById('btn-sell-open').addEventListener('click', async () => {
        const result = await API.openPosition({
            instrument_id: document.getElementById('input-instrument').value,
            price: parseFloat(document.getElementById('input-price').value),
            volume: parseInt(document.getElementById('input-volume').value),
            direction: 'sell',
            offset: 'open',
            skip_validation: getSkipValidation()
        });
        if (!result.success) {
            alert(result.message);
        }
        refreshOrders();
    });

    document.getElementById('btn-buy-close').addEventListener('click', async () => {
        const result = await API.closePosition({
            instrument_id: document.getElementById('input-instrument').value,
            price: parseFloat(document.getElementById('input-price').value),
            volume: parseInt(document.getElementById('input-volume').value),
            direction: 'buy',
            offset: 'close',
            skip_validation: getSkipValidation()
        });
        if (!result.success) {
            alert(result.message);
        }
        refreshOrders();
    });

    document.getElementById('btn-sell-close').addEventListener('click', async () => {
        const result = await API.closePosition({
            instrument_id: document.getElementById('input-instrument').value,
            price: parseFloat(document.getElementById('input-price').value),
            volume: parseInt(document.getElementById('input-volume').value),
            direction: 'sell',
            offset: 'close',
            skip_validation: getSkipValidation()
        });
        if (!result.success) {
            alert(result.message);
        }
        refreshOrders();
    });

    // ===== 阈值设置 =====
    document.getElementById('btn-save-thresholds').addEventListener('click', async () => {
        const result = await API.updateThresholds({
            open_threshold: parseInt(document.getElementById('input-threshold-open').value),
            close_threshold: parseInt(document.getElementById('input-threshold-close').value),
            cancel_threshold: parseInt(document.getElementById('input-threshold-cancel').value),
            total_order_threshold: parseInt(document.getElementById('input-threshold-total-order').value),
            total_cancel_threshold: parseInt(document.getElementById('input-threshold-total-cancel').value)
        });
        if (result.success) {
            alert('阈值设置已保存');
        }
    });

    // ===== 错误防范测试 =====
    async function testValidation(testType, resultId) {
        let testData = {};
        switch(testType) {
            case 'invalid-instrument':
                testData = { instrument_id: 'INVALID_CODE', direction: 'buy', offset: 'open', price: 1000, volume: 1 };
                break;
            case 'invalid-price':
                testData = { instrument_id: 'IF2401', direction: 'buy', offset: 'open', price: 1000.123, volume: 1 };
                break;
            case 'invalid-volume':
                testData = { instrument_id: 'IF2401', direction: 'buy', offset: 'open', price: 1000, volume: -1 };
                break;
            case 'insufficient-margin':
                testData = { instrument_id: 'IF2401', direction: 'buy', offset: 'open', price: 999999, volume: 9999 };
                break;
            case 'insufficient-pos':
                testData = { instrument_id: 'IF2401', direction: 'sell', offset: 'close', price: 1000, volume: 9999 };
                break;
            case 'non-trading-time':
                testData = { instrument_id: 'IF2401', direction: 'buy', offset: 'open', price: 1000, volume: 1 };
                break;
        }

        const result = await API.validateOrder(testData);
        const resultEl = document.getElementById(resultId);
        const errorEl = document.getElementById('error-message');

        if (!result.valid && result.errors.length > 0) {
            resultEl.textContent = '通过';
            resultEl.className = 'badge bg-success me-2';
            errorEl.textContent = result.errors.map(e => e.message).join('; ');
        } else {
            resultEl.textContent = '未触发';
            resultEl.className = 'badge bg-warning me-2';
            errorEl.textContent = '未触发错误提示';
        }
    }

    document.getElementById('btn-test-invalid-instrument').addEventListener('click', () => testValidation('invalid-instrument', 'test-result-14'));
    document.getElementById('btn-test-invalid-price').addEventListener('click', () => testValidation('invalid-price', 'test-result-15'));
    document.getElementById('btn-test-invalid-volume').addEventListener('click', () => testValidation('invalid-volume', 'test-result-16'));
    document.getElementById('btn-test-insufficient-margin').addEventListener('click', () => testValidation('insufficient-margin', 'test-result-17'));
    document.getElementById('btn-test-insufficient-pos').addEventListener('click', () => testValidation('insufficient-pos', 'test-result-18'));
    document.getElementById('btn-test-non-trading-time').addEventListener('click', () => testValidation('non-trading-time', 'test-result-19'));

    // ===== CTP柜台错误测试 (测试点22-24) =====
    async function testCtpError(testType, resultId) {
        const instrument = document.getElementById('ctp-test-instrument').value;
        const errorEl = document.getElementById('error-message');
        const resultEl = document.getElementById(resultId);
        let data = {};

        switch(testType) {
            case 'margin':
                // 资金不足: 发超大手数委托
                data = { instrument_id: instrument, price: 99999, volume: 9999, direction: 'buy', offset: 'open', skip_validation: true };
                break;
            case 'position':
                // 持仓不足: 对无持仓合约平仓
                data = { instrument_id: instrument, price: 1, volume: 1, direction: 'sell', offset: 'close', skip_validation: true };
                break;
            case 'market':
                // 市场状态错误: 直接发委托（非交易时段会被柜台拒绝）
                data = { instrument_id: instrument, price: 1, volume: 1, direction: 'buy', offset: 'open', skip_validation: true };
                break;
        }

        resultEl.textContent = '测试中...';
        resultEl.className = 'badge bg-info me-2';
        errorEl.textContent = '已发送委托到CTP柜台，等待柜台返回错误...（请查看实时日志）';

        try {
            let result;
            if (testType === 'position') {
                result = await API.closePosition(data);
            } else {
                result = await API.openPosition(data);
            }

            if (!result.success) {
                resultEl.textContent = '已触发';
                resultEl.className = 'badge bg-success me-2';
                errorEl.textContent = 'CTP返回: ' + result.message;
            } else {
                resultEl.textContent = '已发送';
                resultEl.className = 'badge bg-warning me-2';
                errorEl.textContent = '委托已发送到柜台，请在实时日志中查看CTP返回的错误信息';
            }
        } catch (error) {
            resultEl.textContent = '异常';
            resultEl.className = 'badge bg-danger me-2';
            errorEl.textContent = '测试异常: ' + error.message;
        }
    }

    document.getElementById('btn-test-ctp-margin').addEventListener('click', () => testCtpError('margin', 'test-result-22'));
    document.getElementById('btn-test-ctp-position').addEventListener('click', () => testCtpError('position', 'test-result-23'));
    document.getElementById('btn-test-ctp-market').addEventListener('click', () => testCtpError('market', 'test-result-24'));

    // ===== 应急处置 =====
    document.getElementById('btn-pause-trading').addEventListener('click', async () => {
        const result = await API.pauseTrading({ reason: '手动暂停' });
        if (result.success) {
            AppState.tradingPaused = true;
            updateTradingStatusUI();
        }
    });

    document.getElementById('btn-resume-trading').addEventListener('click', async () => {
        const result = await API.resumeTrading({ reason: '手动恢复' });
        if (result.success) {
            AppState.tradingPaused = false;
            updateTradingStatusUI();
        }
    });

    document.getElementById('btn-cancel-by-instrument').addEventListener('click', async () => {
        const instrument = document.getElementById('input-cancel-instrument').value;
        if (!instrument) {
            alert('请输入合约代码');
            return;
        }
        const result = await API.cancelByInstrument({ instrument_id: instrument });
        alert(result.message);
        refreshOrders();
    });

    document.getElementById('btn-cancel-all').addEventListener('click', async () => {
        if (confirm('确定要撤销所有订单吗？')) {
            const result = await API.cancelAll({ reason: '手动全部撤单' });
            alert(result.message);
            refreshOrders();
        }
    });

    document.getElementById('btn-emergency-stop').addEventListener('click', async () => {
        if (confirm('确定要执行紧急停止吗？这将暂停交易并撤销所有订单！')) {
            const result = await API.emergencyStop({ reason: '紧急停止' });
            if (result.success) {
                AppState.tradingPaused = true;
                updateTradingStatusUI();
            }
        }
    });

    // ===== 日志查看 =====
    document.getElementById('btn-refresh-logs').addEventListener('click', refreshLogs);
    document.getElementById('btn-export-logs').addEventListener('click', () => {
        const logType = document.getElementById('select-log-type').value;
        window.open(`/api/logs/export?log_type=${logType}`, '_blank');
    });

    async function refreshLogs() {
        const logType = document.getElementById('select-log-type').value;
        const logLevel = document.getElementById('select-log-level').value;

        const result = await API.getLogs({
            log_type: logType,
            level: logLevel,
            page: 1,
            page_size: 100
        });

        const container = document.getElementById('log-container');
        container.innerHTML = '';

        if (result.logs) {
            result.logs.forEach(log => {
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.innerHTML = `
                    <span class="timestamp">${log.timestamp}</span>
                    [<span class="level-${log.level}">${log.level}</span>]
                    [<span class="type">${log.type}</span>]
                    ${log.message}
                `;
                container.appendChild(entry);
            });
        }
    }

    // ===== 策略控制 =====
    document.getElementById('btn-start-strategy').addEventListener('click', async () => {
        const config = {
            instrument_id: document.getElementById('strategy-instrument').value,
            volume: parseInt(document.getElementById('strategy-volume').value),
            open_timeout: parseInt(document.getElementById('strategy-open-timeout').value),
            hold_duration: parseInt(document.getElementById('strategy-hold-duration').value)
        };

        try {
            document.getElementById('strategy-status').innerHTML = '<span class="badge bg-warning">启动中...</span>';
            const result = await API.startStrategy(config);
            if (result.success) {
                document.getElementById('strategy-status').innerHTML = '<span class="badge bg-success">运行中</span>';
                WebSocketManager.addRealtimeLog('STRATEGY', 'INFO', '策略启动成功');
            } else {
                document.getElementById('strategy-status').innerHTML = '<span class="badge bg-danger">启动失败</span>';
                WebSocketManager.addRealtimeLog('STRATEGY', 'ERROR', result.message || '策略启动失败');
            }
        } catch (error) {
            document.getElementById('strategy-status').innerHTML = '<span class="badge bg-danger">错误</span>';
            WebSocketManager.addRealtimeLog('STRATEGY', 'ERROR', '策略启动异常: ' + error.message);
        }
    });

    document.getElementById('btn-stop-strategy').addEventListener('click', async () => {
        try {
            const result = await API.stopStrategy();
            if (result.success) {
                document.getElementById('strategy-status').innerHTML = '<span class="badge bg-secondary">已停止</span>';
                WebSocketManager.addRealtimeLog('STRATEGY', 'INFO', '策略已停止');
            }
        } catch (error) {
            WebSocketManager.addRealtimeLog('STRATEGY', 'ERROR', '停止策略异常: ' + error.message);
        }
    });

    // 定时更新策略状态
    setInterval(async () => {
        try {
            const result = await API.getStrategyStatus();
            if (result.data) {
                const state = result.data.state;
                let badgeClass = 'bg-secondary';
                let stateText = '未启动';

                switch(state) {
                    case 'running': badgeClass = 'bg-success'; stateText = '运行中'; break;
                    case 'waiting_open': badgeClass = 'bg-info'; stateText = '等待开仓'; break;
                    case 'waiting_cancel': badgeClass = 'bg-warning'; stateText = '等待撤单'; break;
                    case 'holding': badgeClass = 'bg-primary'; stateText = '持仓中'; break;
                    case 'waiting_close': badgeClass = 'bg-info'; stateText = '等待平仓'; break;
                    case 'completed': badgeClass = 'bg-success'; stateText = '已完成'; break;
                    case 'stopped': badgeClass = 'bg-secondary'; stateText = '已停止'; break;
                }
                document.getElementById('strategy-status').innerHTML = `<span class="badge ${badgeClass}">${stateText}</span>`;
            }
        } catch (error) {
            // 忽略状态更新错误
        }
    }, 2000);

    // ===== 定时刷新 =====
    setInterval(async () => {
        if (AppState.loggedIn) {
            try {
                const stats = await API.getOrderStats();
                updateMonitorStats(stats);

                const connStatus = await API.getConnectionMonitor();
                document.getElementById('monitor-connection-status').textContent = connStatus.status;
                document.getElementById('monitor-heartbeat').textContent = connStatus.heartbeat || '--';
                document.getElementById('monitor-disconnect-count').textContent = connStatus.disconnect_count || 0;
            } catch (error) {
                console.error('Error refreshing stats:', error);
            }
        }
    }, 5000);

    // 初始加载阈值设置
    setTimeout(async () => {
        try {
            const thresholds = await API.getThresholds();
            if (thresholds.settings) {
                document.getElementById('input-threshold-open').value = thresholds.settings.open_threshold || 10;
                document.getElementById('input-threshold-close').value = thresholds.settings.close_threshold || 10;
                document.getElementById('input-threshold-cancel').value = thresholds.settings.cancel_threshold || 10;
                document.getElementById('input-threshold-total-order').value = thresholds.settings.total_order_threshold || 500;
                document.getElementById('input-threshold-total-cancel').value = thresholds.settings.total_cancel_threshold || 400;
            }
        } catch (error) {
            console.error('Error loading thresholds:', error);
        }
    }, 1000);

    // ==================== 行情数据页 ====================
    const btnSubscribe = document.getElementById('btn-subscribe');
    const btnUnsubscribe = document.getElementById('btn-unsubscribe');

    if (btnSubscribe) {
        btnSubscribe.addEventListener('click', async () => {
            const input = document.getElementById('input-subscribe-instruments').value.trim();
            if (!input) return;
            const ids = input.split(',').map(s => s.trim()).filter(s => s);
            const result = await API.subscribeMd({ instrument_ids: ids });
            WebSocketManager.addRealtimeLog('MARKET', result.success ? 'INFO' : 'ERROR', result.message);
        });
    }

    if (btnUnsubscribe) {
        btnUnsubscribe.addEventListener('click', async () => {
            const input = document.getElementById('input-subscribe-instruments').value.trim();
            if (!input) return;
            const ids = input.split(',').map(s => s.trim()).filter(s => s);
            const result = await API.unsubscribeMd({ instrument_ids: ids });
            WebSocketManager.addRealtimeLog('MARKET', result.success ? 'INFO' : 'ERROR', result.message);
        });
    }

    // 定时刷新行情数据
    setInterval(async () => {
        const marketTab = document.getElementById('market');
        if (!marketTab || !marketTab.classList.contains('active')) return;
        try {
            const result = await API.getMdData();
            if (result.success && result.data) {
                const tbody = document.getElementById('market-data-body');
                if (!tbody) return;
                tbody.innerHTML = '';
                for (const [id, d] of Object.entries(result.data)) {
                    const row = document.createElement('tr');
                    row.innerHTML = `<td>${d.instrument_id}</td>` +
                        `<td>${d.last_price?.toFixed(2) || '--'}</td>` +
                        `<td>${d.upper_limit_price?.toFixed(2) || '--'}</td>` +
                        `<td>${d.lower_limit_price?.toFixed(2) || '--'}</td>` +
                        `<td>${d.bid_price1?.toFixed(2) || '--'}</td>` +
                        `<td>${d.bid_volume1 || 0}</td>` +
                        `<td>${d.ask_price1?.toFixed(2) || '--'}</td>` +
                        `<td>${d.ask_volume1 || 0}</td>` +
                        `<td>${d.volume || 0}</td>` +
                        `<td>${d.open_interest?.toFixed(0) || 0}</td>` +
                        `<td>${d.update_time || '--'}</td>`;
                    tbody.appendChild(row);
                }
            }
        } catch (e) {}
    }, 1000);

    // ==================== 综合查询页 ====================
    function showQueryResult(data) {
        const el = document.getElementById('query-result');
        if (el) el.textContent = JSON.stringify(data, null, 2);
    }

    const qryHandlers = {
        'btn-qry-exchanges': () => API.getExchanges(),
        'btn-qry-products': () => API.getProducts(''),
        'btn-qry-investor': () => API.getInvestor(),
        'btn-qry-trading-codes': () => API.getTradingCodes(),
        'btn-qry-position-detail': () => {
            const inst = document.getElementById('input-qry-instrument')?.value || '';
            return API.getPositionDetails(inst);
        },
        'btn-qry-trades': () => {
            const inst = document.getElementById('input-qry-instrument')?.value || '';
            return API.getTrades(inst);
        },
        'btn-qry-instrument-status': () => API.getInstrumentStatus(),
        'btn-qry-margin-rate': () => {
            const inst = document.getElementById('input-qry-instrument')?.value;
            if (!inst) { showQueryResult({error: '请输入合约代码'}); return null; }
            return API.getMarginRate(inst);
        },
        'btn-qry-commission-rate': () => {
            const inst = document.getElementById('input-qry-instrument')?.value;
            if (!inst) { showQueryResult({error: '请输入合约代码'}); return null; }
            return API.getCommissionRate(inst);
        },
        'btn-qry-order-comm-rate': () => {
            const inst = document.getElementById('input-qry-instrument')?.value;
            if (!inst) { showQueryResult({error: '请输入合约代码'}); return null; }
            return API.getOrderCommRate(inst);
        },
    };

    for (const [btnId, handler] of Object.entries(qryHandlers)) {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', async () => {
                try {
                    const promise = handler();
                    if (promise) {
                        const result = await promise;
                        showQueryResult(result);
                    }
                } catch (e) {
                    showQueryResult({error: e.message});
                }
            });
        }
    }
});
