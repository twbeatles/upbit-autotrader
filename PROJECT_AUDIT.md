# Project Audit

Upbit Pro Algo-Trader v3.3 기능 구현 및 아키텍처 관점 정밀 감사 보고서

---

## 1. Executive Summary

본 감사는 Upbit Pro Algo-Trader 프로젝트의 **기능 구현 안정성, 최신 업비트 API 정합성, 비동기 스레드 동시성, 상태 관리, OS/보안 호환성 및 테스트 커버리지**를 전방위적으로 점검한 결과입니다.

### 전체 위험도 평가: **LOW ~ MEDIUM (안정적, 일부 비동기 및 플랫폼 가드 보완 권장)**

- **전체적인 완성도**:
  - 프로젝트는 142개의 단위/통합 테스트를 100% 통과하고 있으며, `pyright` 정적 분석 0 error, UTF-8 인코딩 및 모듈 구조 가드를 엄격히 준수하고 있습니다.
  - 최신 2026 업비트 API 규격(포켓 단위 Rate Limit, SHA512 JWT unquote 해싱, `orders/open`, `orders/uuids`, `orders/chance` maker/taker 분리, 10단계 호가 규칙, Public/Private WebSocket)이 체계적으로 구현되어 있습니다.
- **주요 개선 권장 사항**:
  1. **WebSocket 콜백과 Qt 메인 스레드 간 직접 호출 분리**: 백그라운드 WebSocket 스레드에서 메인 주문 상태를 직접 수정하는 대신 Qt 시그널-슬롯으로 전달하여 동시성 레이스 컨디션을 원천 차단해야 합니다.
  2. **비-Windows(Linux/macOS) 환경에서의 DPAPI 예외 처리 안전성**: `ctypes.windll` 속성 접근 시 비-Windows 환경에서 발생할 수 있는 `AttributeError` 가드가 필요합니다.
  3. **신규 모듈(호가창 깊이 가드, 네이티브 캔들 엔진)의 실시간 매매 파이프라인 심층 결합**: 구현된 `orderbook_guard`를 매수 진입 게이트에 옵션으로 직결하면 슬리피지 방어 능력이 한층 강화됩니다.

---

## 2. Project Understanding

`README.md`, `CLAUDE.md`, `GEMINI.md` 및 CodeGraph 구조 분석을 바탕으로 파악한 프로젝트 아키텍처와 주요 실행 흐름은 다음과 같습니다.

### 1) 진입점 및 계층 구조
- **진입점**: `upbit_trader.py` (최상위 루트 진입점) ➔ `upbit_autotrader.app.trader.UpbitProTrader`
- **Presentation Layer**: `ui_controller.py`, `ui_parts/` (Qt 기반 대시보드, 전략 설정, 로그, 프리셋, 수동검토 큐)
- **Application & Trading Orchestration**: `trading_controller.py`, `trading_parts/` (`session_ops`, `order_api_ops`, `execution_flow_ops`, `lifecycle_ops`, `signal_ops`, `risk_budget_ops`)
- **Services Layer**: `services/`
  - `upbit_client.py` (네이티브 REST 클라이언트, JWT 서명, 캔들/호가창/주문)
  - `upbit_websocket.py` (Public/Private 실시간 스트림)
  - `order_service.py` (주문 생명주기 및 pending 추적)
  - `rate_limit.py` (포켓별 Remaining-Req 피드백 및 스로틀링)
  - `security.py` (Windows DPAPI 기반 API Key 암호화)
  - `settings_store.py` (설정 저장소 v2)
- **Domain Engine**: `strategies/` (전략 엔진, 단일/앙상블), `risk/` (Kelly, 포트폴리오 상관도, Drawdown), `execution/` (TWAP, 호가창 깊이 가드), `market_regime/` (시장 레짐)
- **Runtime**: `runtime/price_thread.py` (WebSocket 실시간 피드 + REST Fallback), `runtime/market_regime_thread.py`
- **Compatibility**: `legacy_wrappers/` (구버전 모듈 경로 호환 래퍼 유지)

### 2) 핵심 매매 실행 흐름 (Data & Order Flow)
```
[Upbit WebSocket / REST] ➔ [PriceUpdateThread] ➔ price_updated (Signal) ➔ [TradingController.on_price_updated]
                                                                                   │
                                                                         [Risk / Regime Gates]
                                                                         - Market Regime Filter
                                                                         - Drawdown State Guard
                                                                         - Portfolio Correlation
                                                                                   │
                                                                        [Strategy Engine / Signals]
                                                                         - Volatility Breakout
                                                                         - Single / Ensemble Signals
                                                                                   │
                                                                          [Execution Model]
                                                                         - Orderbook Guard (Spread/Depth)
                                                                         - Single Market / TWAP Slices
                                                                                   │
                                                                        [UpbitRestClient / Orders]
                                                                         - identifier 발급 & JWT 서명
                                                                         - POST /v1/orders
                                                                         - mark_pending (order_service)
                                                                                   │
                                                                   [Reconciliation / Lifecycle]
                                                                         - myOrder WebSocket Event / Polling
                                                                         - transition_pending (wait -> done)
                                                                         - save reconciliation_state.json
```

---

## 3. High-Risk Issues

실제 코드 분석을 통해 확인된 개선 및 위험 요소입니다.

### Issue 1: WebSocket 백그라운드 스레드와 메인 스레드 간 직접 상태 수정 (동시성 / Race Condition)
* **위치**: `upbit_autotrader/runtime/price_thread.py` (`_on_ws_my_order`), `upbit_autotrader/controllers/trading_parts/execution_flow_ops.py` (`_handle_ws_order_event`)
* **문제**:
  - `PriceUpdateThread` 내부에서 실행되는 `UpbitWebSocketClient`는 별도의 백그라운드 데몬 스레드(`UpbitWebSocketThread`)에서 수신 메시지를 처리합니다.
  - `_on_ws_my_order` 콜백에서 `parent._handle_ws_order_event(data)`를 직접 동기 호출하고 있으며, 이 과정에서 `order_service.pending_orders` 수정 및 `_mark_reconciliation_dirty()` 플래그 조작이 메인 GUI 스레드의 주기적 `check_signals()` / `_reconcile_orders()` 루프와 락 없이 동시에 실행될 수 있습니다.
* **영향**: 딕셔너리 순회 중 수정 에러(`RuntimeError: dictionary changed size during iteration`), 주문 상태 덮어쓰기 레이스 컨디션, 또는 드문 GUI 스레드 비정상 크래시 유발 가능.
* **근거**:
  - `price_thread.py`:
    ```python
    def _on_ws_my_order(self, data: dict):
        self.order_event_received.emit(data)
        parent = self.parent()
        handler = getattr(parent, "_handle_ws_order_event", None)
        if callable(handler):
            handler(data)  # <--- WebSocket 스레드에서 직접 호출됨!
    ```
* **권장 수정 방향**:
  - `_on_ws_my_order`에서 direct 호출(`handler(data)`)을 제거하고, 이미 정의된 Qt 시그널 `self.order_event_received.emit(data)`만을 사용.
  - 메인 컨트롤러(또는 trader 초기화 시)에서 `price_thread.order_event_received.connect(self._handle_ws_order_event)`로 연결하여 메인 이벤트 루프에서 안전하게(QueuedConnection) 처리하도록 개선.
* **우선순위**: **High**

---

### Issue 2: 비-Windows 환경에서 `ctypes.windll` 속성 접근 시 `AttributeError` 발생
* **위치**: `upbit_autotrader/services/security.py` (`encrypt_dpapi`, `decrypt_dpapi` 함수 Line 47, Line 81)
* **문제**:
  - Windows가 아닌 OS(Linux, macOS, Docker 컨테이너 등)에서는 `ctypes` 모듈에 `windll` 속성 자체가 존재하지 않습니다.
  - `hasattr(ctypes.windll, "crypt32")`를 직접 평가하면 `AttributeError: module 'ctypes' has no attribute 'windll'`이 발생하여 `DPAPIError` 예외로 감싸지지 못하고 크래시됩니다.
* **영향**: 비-Windows 환경이나 CI 파이프라인에서 설정 로드 시 예상치 못한 프로세스 중단 발생.
* **근거**:
  - `security.py`:
    ```python
    if not hasattr(ctypes.windll, "crypt32"):  # <--- Linux에서는 ctypes.windll 접근 시 AttributeError 발생
        raise DPAPIError("DPAPI is only available on Windows.")
    ```
* **권장 수정 방향**:
  ```python
  if not hasattr(ctypes, "windll") or not hasattr(getattr(ctypes, "windll", None), "crypt32"):
      raise DPAPIError("DPAPI is only available on Windows.")
  ```
* **우선순위**: **Medium**

---

### Issue 3: `README.md` 요구사항 명세 누락 및 의존성 불일치
* **위치**: `README.md` (Line 20~27)
* **문제**:
  - `requirements.txt`에는 `PyJWT>=2.8.0`과 `websocket-client>=1.6.0`이 정상 추가되어 있으나, `README.md`의 `## 요구사항` 코드 블록에는 해당 라이브러리가 누락되어 있습니다.
* **영향**: 사용자가 README 문서만 참조하여 수동 설치할 경우 `ModuleNotFoundError` 발생 위험.
* **근거**: `README.md` Line 23~27에 `pyupbit`, `pandas`, `numpy`, `requests`만 기술됨.
* **권장 수정 방향**: `README.md`의 요구사항 코드 블록에 `PyJWT>=2.8.0`, `websocket-client>=1.6.0`을 추가하여 `requirements.txt`와 정합성 일치.
* **우선순위**: **Low**

---

## 4. Potential Functional Gaps

현재 구현상 추가로 보완하거나 고도화할 수 있는 잠재적 기능 갭입니다.

1. **[추정] `orderbook_guard`의 실시간 매수 진입 파이프라인 옵션 연동**:
   - `upbit_autotrader/execution/orderbook_guard.py`에 호가 스프레드(Spread bps) 및 호가 깊이(Market Depth) 기반 슬리피지 분석 로직이 완벽히 구현되어 있으나, `signal_ops._check_buy_condition`이나 `execution_flow_ops._place_buy_order`에서 주문 발주 직전 자동으로 호가창을 사전 검사하여 차단하는 통합 게이트 플래그(`use_orderbook_spread_guard`)를 추가하면 대형 주문 시 슬리피지 방어 능력이 한층 극대화될 수 있습니다.
2. **[추정] `indicator_ops.py`의 네이티브 캔들 클라이언트 우선 바인딩**:
   - 현재 보조지표 계산(`calculate_target_price`, `calculate_rsi`, `calculate_macd` 등)은 `pyupbit.get_ohlcv`를 기본 호출하고 있습니다. `UpbitRestClient.get_ohlcv`가 완성되었으므로, `login()` 이후에는 네이티브 클라이언트를 우선 사용하여 `Remaining-Req` 피드백을 공유받도록 바인딩을 개선할 수 있습니다.
3. **[추정] Private WebSocket `myAsset` 실시간 잔고 테이블 연동**:
   - 현재 Private WebSocket에서 `myOrder` 체결 이벤트는 실시간 상태 전이와 연동되어 있으나, `myAsset` 자산 변동 이벤트는 로그 수신 단계에 머물러 있습니다. 수신 시 `holdings_service` 잔고 캐시를 즉시 갱신하도록 연결하면 REST API 계좌 조회 빈도를 대폭 줄일 수 있습니다.

---

## 5. Recommended Fix Plan

| 단계 | 작업 내용 | 목표 및 기대 효과 |
|---|---|---|
| **1단계 (즉시 개선)** | • `price_thread.py`의 `_on_ws_my_order` direct handler 호출 제거 및 Qt Signal(`order_event_received`) 연결 방식으로 일원화<br>• `security.py`의 `ctypes.windll` 속성 접근 안전 가드 추가<br>• `README.md` 요구사항 블록에 `PyJWT`, `websocket-client` 추가 | 스레드 동시성 안전성 확보, 비-Windows 환경 크래시 방지, 문서 정합성 일치 |
| **2단계 (안정성 강화)** | • `indicator_ops.py`에서 `self.upbit`의 `get_ohlcv` 우선 활용하도록 바인딩 개선<br>• `execution_flow_ops.py` 매수 진입 전 `orderbook_guard` 사전 점검 옵션 활성화 지원 | Quotation Rate Limit 피드백 일원화, 실시간 슬리피지 사전 방어 |
| **3단계 (구조 고도화)** | • `myAsset` 실시간 자산 변동 이벤트를 `holdings_service` 및 UI 잔고 테이블에 즉시 반영<br>• 미체결 주문 일괄 취소(`cancel_orders_by_uuids`) UI 액션 버튼 연동 | 계좌 조회 REST 부하 0화, 비상 정지 시 일괄 주문 취소 편의성 증대 |

---

## 6. Test Recommendations

향후 회귀 방지 및 안정성 보증을 위해 추가/보강을 권장하는 테스트 항목입니다:

1. **WebSocket 이벤트 시그널 전달 스레드 안전성 테스트 (`tests/test_price_thread_concurrency.py`)**:
   - `PriceUpdateThread`에서 발생하는 `order_event_received` 시그널이 Qt 메인 루프를 거쳐 `TraderTradingController._handle_ws_order_event`에 전달될 때 동시 다발적 이벤트에서도 `pending_orders`의 무결성이 유지되는지 검증.
2. **비-Windows 환경 `security.py` Fallback 테스트 (`tests/test_security_cross_platform.py`)**:
   - `ctypes.windll`이 `None`이거나 속성이 없는 모의(mock) 환경에서 `encrypt_dpapi`, `decrypt_dpapi`가 `AttributeError` 없이 `DPAPIError`를 정상 발생시키는지 검증.
3. **호가창 가드 통합 매매 흐름 테스트 (`tests/test_orderbook_guard_integration.py`)**:
   - 스프레드가 비정상적으로 벌어진 호가창 데이터가 주어졌을 때 매수 주문이 안전하게 차단되거나 TWAP으로 분할되는지 검증.
