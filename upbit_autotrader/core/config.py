"""
Upbit Pro Algo-Trader - configuration constants.
"""


class Config:
    """Application-wide constants."""

    # ---------------------------------------------------------------------
    # Core defaults
    # ---------------------------------------------------------------------
    DEFAULT_COINS = "KRW-BTC,KRW-ETH,KRW-XRP"
    DEFAULT_CANDLE = "4시간"

    CANDLE_INTERVALS = {
        "1분": "minute1",
        "5분": "minute5",
        "15분": "minute15",
        "30분": "minute30",
        "1시간": "minute60",
        "4시간": "minute240",
        "일봉": "day",
    }

    DEFAULT_BETTING_RATIO = 10.0
    DEFAULT_K_VALUE = 0.4
    DEFAULT_TS_START = 5.0
    DEFAULT_TS_STOP = 2.0
    DEFAULT_LOSS_CUT = 3.0

    # Indicator/filter defaults
    DEFAULT_RSI_PERIOD = 14
    DEFAULT_RSI_UPPER = 70
    DEFAULT_USE_RSI = True

    DEFAULT_MACD_FAST = 12
    DEFAULT_MACD_SLOW = 26
    DEFAULT_MACD_SIGNAL = 9
    DEFAULT_USE_MACD = True

    DEFAULT_BB_PERIOD = 20
    DEFAULT_BB_STD = 2.0
    DEFAULT_USE_BB = False

    DEFAULT_ATR_PERIOD = 14
    DEFAULT_ATR_MULTIPLIER = 2.0
    DEFAULT_USE_ATR = False

    DEFAULT_VOLUME_MULTIPLIER = 1.5
    DEFAULT_VOLUME_PERIOD = 20
    DEFAULT_USE_VOLUME = True

    # Risk defaults
    DEFAULT_MAX_DAILY_LOSS = 5.0
    DEFAULT_MAX_HOLDINGS = 5
    DEFAULT_USE_RISK_MGMT = True

    # Partial take-profit
    PARTIAL_TAKE_PROFIT = [
        {"rate": 3.0, "sell_ratio": 30},
        {"rate": 5.0, "sell_ratio": 30},
        {"rate": 8.0, "sell_ratio": 20},
    ]
    DEFAULT_PARTIAL_PROFIT_1 = 5.0
    DEFAULT_PARTIAL_RATIO_1 = 50.0
    DEFAULT_PARTIAL_PROFIT_2 = 10.0
    DEFAULT_USE_PARTIAL = False
    DEFAULT_USE_PARTIAL_PROFIT = False

    # Entry scoring
    ENTRY_SCORE_THRESHOLD = 60
    USE_ENTRY_SCORING = False
    ENTRY_WEIGHTS = {
        "target_break": 20,
        "ma_filter": 15,
        "rsi_optimal": 20,
        "macd_golden": 20,
        "volume_confirm": 15,
        "bb_position": 10,
    }

    # ---------------------------------------------------------------------
    # Strategy engine (v3.2+)
    # ---------------------------------------------------------------------
    DEFAULT_USE_STRATEGY_ENGINE = False
    DEFAULT_STRATEGY_MODE = "single"  # single | ensemble
    DEFAULT_SINGLE_STRATEGY = "volatility_breakout"
    DEFAULT_ENGINE_GATE_POLICY = "strategy_aware"  # legacy_first | engine_only | strategy_aware
    ENGINE_GATE_POLICIES = ("legacy_first", "engine_only", "strategy_aware")
    DEFAULT_ENSEMBLE_THRESHOLD = 60
    DEFAULT_ACTIVE_STRATEGIES = [
        "volatility_breakout",
        "donchian_breakout",
        "ema_cross_trend",
        "time_series_momentum",
        "rsi_reversion",
        "bollinger_reversion",
        "zscore_reversion",
    ]
    DEFAULT_STRATEGY_WEIGHTS = {
        "volatility_breakout": 1.0,
        "donchian_breakout": 1.0,
        "ema_cross_trend": 1.0,
        "time_series_momentum": 1.0,
        "rsi_reversion": 1.0,
        "bollinger_reversion": 1.0,
        "zscore_reversion": 1.0,
    }
    DEFAULT_USE_VOLATILITY_TARGETING = True
    DEFAULT_TARGET_VOL_PCT = 2.0
    DEFAULT_USE_REGIME_FILTER = True
    DEFAULT_REGIME_MIN_ADX = 18.0
    DEFAULT_USE_DRAWDOWN_GUARD = True
    DEFAULT_DRAWDOWN_GUARD_PCT = 5.0
    DEFAULT_MAX_CONSECUTIVE_LOSSES = 3

    # Risk/reconciliation extensions
    DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC = True
    DEFAULT_RISK_INCLUDE_UNREALIZED = True
    DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS = True
    DEFAULT_PRICE_FEED_STALE_SEC = 15
    DEFAULT_MANUAL_REVIEW_ON_TIMEOUT = True

    # ---------------------------------------------------------------------
    # Paper trading
    # ---------------------------------------------------------------------
    DEFAULT_PAPER_TRADING = False
    DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN = True
    DEFAULT_PAPER_SEED_KRW = 10_000_000
    DEFAULT_PAPER_FEE_BPS = 5.0
    DEFAULT_PAPER_SLIPPAGE_BPS = 5.0

    # ---------------------------------------------------------------------
    # Advanced strategy settings (legacy v3.0)
    # ---------------------------------------------------------------------
    DEFAULT_COOLDOWN_MINUTES = 30
    DEFAULT_USE_COOLDOWN = False

    DEFAULT_MAX_HOLDING_HOURS = 24
    DEFAULT_USE_TIME_EXIT = False

    DEFAULT_USE_DYNAMIC_POSITION = False
    DYNAMIC_POSITION_LOSS_THRESHOLD = 3
    DYNAMIC_POSITION_WIN_THRESHOLD = 3
    DYNAMIC_POSITION_LOSS_RATIO = 0.5
    DYNAMIC_POSITION_WIN_RATIO = 1.5
    DYNAMIC_POSITION_MAX_RATIO = 20.0

    DEFAULT_BREAKOUT_CONFIRM_TICKS = 3
    DEFAULT_USE_BREAKOUT_CONFIRM = False

    DEFAULT_USE_MTF = False
    MTF_SHORT_INTERVAL = "minute60"
    MTF_LONG_INTERVAL = "day"

    DEFAULT_USE_GAP_ANALYSIS = False
    GAP_UP_K_ADJUST = 0.8
    GAP_DOWN_K_ADJUST = 1.2
    GAP_THRESHOLD = 2.0

    # ---------------------------------------------------------------------
    # Files
    # ---------------------------------------------------------------------
    SETTINGS_FILE = "upbit_settings.json"
    PRESETS_FILE = "upbit_presets.json"
    TRADE_HISTORY_FILE = "trade_history.json"
    LOG_DIR = "logs"

    # ---------------------------------------------------------------------
    # Runtime/system
    # ---------------------------------------------------------------------
    PRICE_UPDATE_INTERVAL = 1
    API_MAX_RETRIES = 3
    API_RETRY_DELAY = 1
    API_MIN_INTERVAL_SEC = 0.12
    API_BACKOFF_BASE_SEC = 0.4
    API_BACKOFF_JITTER_SEC = 0.2

    MAX_LOG_LINES = 500
    INDICATOR_CACHE_TTL_BY_INTERVAL = {
        "minute1": 2,
        "minute5": 3,
        "minute15": 5,
        "minute30": 7,
        "minute60": 10,
        "minute240": 20,
        "day": 30,
    }

    HISTORY_FLUSH_DEBOUNCE_MS = 1000
    PENDING_RECONCILE_INTERVAL_MS = 10000
    PENDING_STALE_TIMEOUT_SEC = 90
    ORDER_STATUS_RETRY_DELAYS_SEC = (0.3, 0.6, 1.2)
    RISK_SNAPSHOT_TTL_SEC = 5

    # ---------------------------------------------------------------------
    # Built-in presets
    # ---------------------------------------------------------------------
    DEFAULT_PRESETS = {
        "aggressive": {
            "name": "공격형",
            "description": "높은 수익률 추구, 높은 변동성 허용",
            "k": 0.5,
            "ts_start": 3.0,
            "ts_stop": 1.5,
            "loss": 5.0,
            "betting": 15.0,
            "rsi_upper": 75,
            "max_holdings": 7,
            "use_strategy_engine": True,
            "strategy_mode": "ensemble",
            "single_strategy": "ema_cross_trend",
            "ensemble_threshold": 55,
            "engine_gate_policy": "strategy_aware",
        },
        "normal": {
            "name": "균형형",
            "description": "균형 잡힌 수익/리스크 프로파일",
            "k": 0.4,
            "ts_start": 5.0,
            "ts_stop": 2.0,
            "loss": 3.0,
            "betting": 10.0,
            "rsi_upper": 70,
            "max_holdings": 5,
            "use_strategy_engine": False,
            "strategy_mode": "single",
            "single_strategy": "volatility_breakout",
            "ensemble_threshold": 60,
            "engine_gate_policy": "legacy_first",
        },
        "conservative": {
            "name": "보수형",
            "description": "안정성 우선, 낮은 리스크",
            "k": 0.3,
            "ts_start": 7.0,
            "ts_stop": 2.5,
            "loss": 2.0,
            "betting": 5.0,
            "rsi_upper": 65,
            "max_holdings": 3,
            "use_strategy_engine": True,
            "strategy_mode": "ensemble",
            "single_strategy": "rsi_reversion",
            "ensemble_threshold": 65,
            "engine_gate_policy": "strategy_aware",
        },
    }

    # ---------------------------------------------------------------------
    # Tooltips/help
    # ---------------------------------------------------------------------
    TOOLTIPS = {
        "coins": "감시할 코인을 콤마(,)로 구분해 입력하세요. 예: KRW-BTC,KRW-ETH",
        "candle": "목표가/지표 계산에 사용할 캔들 간격입니다.",
        "betting": "총 잔고 대비 종목당 투자 비율(%)입니다.",
        "k_value": "변동성 돌파의 K 계수입니다.",
        "ts_start": "트레일링 스탑 추적 시작 수익률(%)",
        "ts_stop": "고점 대비 하락 허용폭(%)",
        "loss_cut": "절대 손절 기준(%)",
        "max_loss": "일일 최대 허용 손실률(%)",
        "max_holdings": "동시 보유 가능한 최대 종목 수",
        "cooldown": "매도 후 재진입 제한 시간(분)",
        "holding_time": "최대 보유 시간(시간)",
        "strategy_engine": "전략 엔진(single/ensemble) 활성화",
        "engine_gate_policy": "전략 엔진 활성 시 기존 목표가/MA 하드 게이트 적용 정책",
        "account_wide_sync": "시작 시 워치리스트 + 계좌 보유를 합쳐 유니버스를 구성",
        "risk_include_unrealized": "리스크 계산에 미실현 손익 포함",
        "risk_include_external_holdings": "리스크 계산에 워치리스트 외 보유 포함",
        "price_feed_stale_sec": "가격 업데이트가 이 시간(초) 이상 멈추면 stale 경고",
        "manual_review_on_timeout": "주문 타임아웃 해소 실패 시 수동검토 큐 적재",
        "paper_trading": "실주문 대신 모의 체결로 테스트합니다.",
        "paper_allow_without_login": "페이퍼 모드에서 API 로그인 없이 시작 허용",
        "paper_seed_krw": "무로그인 페이퍼 시작 시 초기 KRW 시드",
    }

    HELP_CONTENT = {
        "quick_start": """
## 빠른 시작

1. API 키를 입력하고 연결합니다.
2. 감시 코인을 입력합니다.
3. 리스크 설정을 확인합니다.
4. 자동매매를 시작합니다.
""",
        "strategy": """
## 전략 개요

- 변동성 돌파 + MA 필터 기반 진입
- RSI/MACD/거래량 필터 옵션
- 트레일링 스탑/손절/분할익절 지원
- 전략 엔진(single/ensemble) 옵션 지원
""",
        "faq": """
## FAQ

Q. 프로그램 종료 시 자동매매는?
A. 즉시 중지됩니다.

Q. 페이퍼 모드는 실주문을 보내나요?
A. 보내지 않습니다.
""",
    }
