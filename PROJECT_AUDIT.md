# Project Audit

> 후속 조치(2026-09-29): 본 문서의 Phase 1~3 수정이 모두 반영됐으며 `tests/test_audit_fixes.py` 17건이 회귀를 커버한다. Fluent 빌드 범위는 `PROJECT_AUDIT_BUILD.md`를 볼 것. 아래 본문은 감사 시점 스냅샷으로 유지한다.

> 대상: Upbit Pro Algo-Trader (업비트 자동매매 데스크톱 앱)
> 감사일: 2026-09-28 (UTC) / 감사 방식: 읽기 전용 감사 (코드 수정 없음)
> 사용 도구: CodeGraph MCP 8회 호출 + 직접 파일 열람 + `python -m pytest -q` 1회 실행
> 기존 `PROJECT_AUDIT.md`(2026-09-19 작성, 구 양식)는 본 문서로 대체한다.

## 1. Executive Summary

* **프로젝트 전체 상태:** 핵심 매매 파이프라인(신호 → 리스크/레짐 게이트 → 실행 → 체결 확인 → 복구)은 CodeGraph 기준으로 완결성 있게 연결되어 있다. 주문 pending 생명주기, TWAP 폴백, 수동검토 큐, reconciliation 영속화, 레짐 fail-closed 등 안전 장치가 코드상으로 존재한다. 이전 감사(2026-09-19)에서 지적된 WebSocket 직접 호출 race와 `ctypes.windll` 가드는 현재 코드에서 **수정된 것으로 확인**된다 (`price_thread.py`는 시그널 emit만, `security.py`는 `getattr(ctypes, "windll", None)` 가드).
* **전체 위험도:** **High Risk** — Windows 단일 플랫폼에서는 동작하나, (a) 비-Windows 기동 불가 수준의 결함, (b) 실테스트 실패 1건, (c) 주문티켓의 지정가/최유리 무시(시장가로 체결) 문제가 확정적으로 확인되기 때문이다.
* **가장 중요한 문제 3~5개:**
  1. `settings_controller.py` 상단의 무조건 `import winreg`로 Linux/macOS에서 앱 자체가 import 단계에서 사망한다. (Critical, Confirmed)
  2. 주문 티켓에서 지정가/최유리를 선택해도 실제로는 시장가 주문이 나가며, 가격 입력값이 버려진다. 매도 dry-run은 항상 매수(bid)로 검증한다. (High, Confirmed)
  3. `UpbitProTrader()` 생성 경로에서 `QTimer(self)` 부모 타입 오류로 크래시가 발생하며, 자사 테스트 1건이 실패한다 (211건 중 210 통과). (High, Confirmed)
  4. `trade_history.json`이 비원자적 덮어쓰기로 저장되고, 로드 실패 시 전체 히스토리를 `[]`로 초기화한다. (High, Confirmed)
  5. Linux/macOS에서 설정 저장이 DPAPI 일변도라 키 포함 저장이 항상 실패하고, 일반 설정까지 함께 저장되지 않는다. (High, Likely-strong)
* **데이터 손상/유실 가능성 여부:** 있다. `trade_history.json` 쓰기 중 강제종료 시 파일 절단 + 다음 기동 시 전체 초기화(무결성 검사·백업 없음). reconciliation 상태는 원자적 저장이라 해당 범위에서는 안전하다.
* **가장 먼저 수정해야 할 영역:** 플랫폼 분기 (`winreg`/`os.startfile`/DPAPI 저장), 주문 티켓 실행 분기, 앱 초기화 순서(QTimer 부모), 거래 히스토리 원자적 저장 순이다.

## 2. Project Understanding

* **프로젝트 목적:** 업비트 OpenAPI 기반 24시간 퀀트 자동매매 데스크톱 앱. 7대 전략 단일/앙상블 엔진, 시장 레짐 필터, 리스크 예산·켈리·드로우다운 상태머신, 호가창 가드, 단일/TWAP/최유리 실행, 미체결 복구(reconciliation), 페이퍼 트레이딩·백테스팅을 제공한다.
* **주요 entrypoint:** `upbit_trader.py` → `upbit_autotrader/app/trader.py`의 `UpbitProTrader` + `main()` (QApplication 생성, HiDPI PassThrough, Fluent 셸 적용). 루트 진입점은 이 파일 하나로 유지된다.
* **핵심 모듈:**
  - `app/bootstrap_ops.py`, `app/runtime_ops.py` — 초기 상태·타이머·가격/레짐 스레드 수명주기·`closeEvent`.
  - `controllers/trading_controller.py` + `trading_parts/` (`session_ops`, `signal_ops`, `execution/{buy_flow,sell_flow,twap,reconcile,validation,ws_events}`, `order_api/{placement,chance,query,cancel,retry}`, `account_ops`, `lifecycle_ops`, `manual_review_ops`, `market_regime_ops`, `risk_ops`) — 매매 오케스트레이션. 공개 주문 경로는 `_place_buy_order` / `_place_sell_order`.
  - `runtime/price_thread.py` (QThread, WS→`price_updated`/`order_event_received` 시그널) + `runtime/market_regime_thread.py` (주기적 레짐 스냅샷, `regime_updated` 시그널).
  - `services/upbit/*` (auth/transport/account/orders/market/websocket) + `services/upbit_client.py` facade, `services/order_service.py` (pending 생명주기 상태머신), `services/paper_order_service.py`, `services/settings_store.py` (schema v2, DPAPI), `services/security.py`, `services/rate_limit.py`.
  - `strategies/engine.py` + 카탈로그, `strategies/meta_signal.py` (성과 추적·메타 점수), `risk/position_sizing.py`·`risk/portfolio_risk.py`, `execution/execution_model.py`·`execution/orderbook_guard.py`·`execution/reconciliation_store.py`, `market_regime/engine.py` + `providers/`, `controllers/history_controller.py` (거래 히스토리·리포트·백테스트 실행), `controllers/batch_controller.py` + `batch_parts/batch_ops.py` (일괄매수/매도·긴급청산).
* **데이터 저장 방식:** DB 없음. 전부 루트 상대경로 JSON/파일이다. `upbit_settings.json`(v2, 키 DPAPI), `trade_history.json`(직접 덮어쓰기), `reconciliation_state.json`(tmp+`os.replace` 원자적 저장), `strategy_performance.json`, `upbit_presets.json`, `logs/` + `logs/order_lifecycle.jsonl`.
* **외부 의존성:** 업비트 REST/WS, `pyupbit`(폴백 경로 포함), PyQt6 + qfluentwidgets, pandas/numpy, requests + websocket-client, PyJWT/cryptography, 공포탐욕·ETF 등 레짐 외부 소스, Discord 웹훅.
* **핵심 실행 흐름:**
  - 자동매수: `PriceUpdateThread(WsTicker→price_updated)` → `signal_ops.on_price_update` → `_check_buy_condition`(레짐 필터·전략/메타 점수·리스크 스냅샷) → `execute_buy`(포지션사이징→레짐 스케일→`_validate_live_order_request(chance)`→호가창 가드→`plan_execution`→TWAP/단일 분기→`_reserve_krw_for_buy`→`_place_buy_order`→`mark_pending`+`_transition_pending(wait)`+dirty) → `QTimer.singleShot(2000, check_buy_execution)` 폴링(최대 30회) → 체결 시 수량/평단 병합·`add_trade_record`·통계·잔고 갱신, 타임아웃 시 `_resolve_timeout_pending`→수동검토 큐.
  - 매도: `_check_sell_condition`(손절·보유시간·전략 청산·분할익절·TS) → `execute_sell`/`_execute_partial_sell` → 동일 pending/폴링 패턴.
  - 수동 주문: 주문티켓/행버튼/일괄작업 → `_place_*_order` → 동일 pending/재조회 체계. 긴급청산은 보유 전량 순회 매도(pending 종목은 건너뜀).
  - 종료: `closeEvent` → 설정 저장 → 히스토리 flush → 강제 reconcile → reconciliation 영속화 → 성과 저장 → 스레드 정지.

## 3. Audit Coverage & Limitations

* **실제 확인한 주요 모듈:** 진입점·부트스트랩·런타임 스레드, 주문 배치 2경로(live/paper), 실행 검증·호가창 가드·TWAP, pending 생명주기·reconcile·수동검토, 레짐 필터/스케일·포지션사이징·포트폴리오 리스크, 설정 저장/로드·DPAPI, 히스토리 flush/내보내기/리포트, WS/전송/재시도/레이트리밋, 세션 시작·일괄매수/매도·긴급청산, 주문티켓.
* **CodeGraph로 분석한 호출 관계:** entrypoint·부트스트랩·가격/레짐 스레드, `_place_buy/sell`→`UpbitOrderService`/`UpbitPaperOrderService`→`mark_pending`/`_transition_pending`, reconcile·수동검토, 레짐→리스크 스케일링→`compute_position_size`, DPAPI→settings_store, 히스토리 flush 타이머→`closeEvent`, WS 재접속·`api_call_with_retry`·레이트리밋, 신호→매수/매도→청산·배치 흐름의 caller/callee와 영향 모듈을 8회 탐색으로 확인했다. 탐색 중 일부 파일은 인덱스 stale 경고가 있어 해당 파일은 직접 열람으로 교차 확인했다.
* **실행한 테스트:** `python -m pytest -q` 1회. 결과 **210 passed, 1 failed** (`tests/test_fluent_ui_foundation.py::test_fluent_shell_registers_all_legacy_pages_without_emoji`, `QTimer` 부모 타입 오류). 그 외 개별 테스트 추가 실행 없음. `pyright`·`pre-commit`은 실행하지 않았다.
* **확인하지 못한 환경/외부 서비스:** Linux/macOS 실기동, 실거래 주문 체결, 업비트 점검·429·WS 단절 재현, 장시간 TWAP·재시작 복구 E2E, PyInstaller 빌드 산출물.
* **분석 한계:** 정적 분석 + 1회 테스트 실행 기반이며 런타임 재현은 실패 테스트 1건이 전부다. `Likely` 항목은 Linux 실측 없이 코드 경로 결정성으로만 판단했음을 각 항목에 표기했다. 구 감사서(2026-09-19)의 "완료" 표기는 현재 코드와 테스트 결과로 재검증했고, 이미 고쳐진 항목은 이슈에서 제외했다.

## 4. High-Risk Issues

### [ISSUE-001] 비-Windows에서 `import winreg` 하나로 앱 전체가 기동 불가

* **위치:** `upbit_autotrader/controllers/settings_controller.py:1-3` (`import winreg` 무조건 수행) → `upbit_autotrader/app/trader.py`의 컨트롤러 import 체인.
* **우선순위:** Critical
* **신뢰도:** Confirmed (코드 흐름 확정, Linux 실측은 미수행)
* **문제:** `winreg`는 Windows 전용 표준모듈이라 Linux/macOS에서는 `import` 시점에 `ModuleNotFoundError`가 발생하고, 설정 컨트롤러를 상속하는 `UpbitProTrader` 자체를 import할 수 없다.
* **발생 조건:** Windows가 아닌 모든 환경에서 `python upbit_trader.py` 또는 해당 모듈 import 시 100% 발생.
* **영향:** README가 macOS/Linux를 지원 OS로 명시하는데 실제로는 앱이 전혀 실행되지 않는다. 테스트는 Windows에서만 통과하므로 이 결함을 감지하지 못한다.
* **근거:** 파일 선두 4줄에 플랫폼 분기·try/except 없이 `import winreg`가 존재한다. `set_startup_registry`에서만 쓰이는데 모듈 스코프로 올라와 있다.
* **반증 확인:** 호출자 측 보호 장치를 찾았으나 없음. 레지스트리 함수 내부 try/except는 import 실패 이후 단계라 도달 불가하다. 프레임워크가 보장하는 폴백도 없다. `GEMINI.md`·`CLAUDE.md`에도 플랫폼 분기 요구가 없다.
* **호출/영향 범위:** CodeGraph상 `TraderSettingsController`는 `UpbitProTrader`의 직접 베이스이며 `save/load_settings`, `configure_runtime_integrations`, 시작프로그램 등록까지 영향이 번진다. 즉 설정 전체가 플랫폼 리스크에 묶여 있다.
* **권장 수정 방향:** `winreg`를 함수 내 지연 import + `sys.platform` 가드로 격리하고, 비-Windows에서는 시작프로그램 등록 메뉴를 비활성화/안내 문구로 대체한다. import 시점에는 절대 실패하지 않게 한다.
* **필요한 회귀 테스트:** `winreg` 없는 import 시뮬레이션(모듈 블로킹 fixture)에서 `settings_controller` import 성공 + `UpbitProTrader` 클래스 로드 성공을 assert하는 unit 테스트. 기존 Windows 동작은 그대로 통과해야 한다.

### [ISSUE-002] 주문티켓의 지정가/최유리 선택이 무시되고 시장가로 체결된다

* **위치:** `upbit_autotrader/controllers/ui_parts/order_ticket_ops.py:204-227` (`submit_ticket_order`), `_ticket_values(:124-137)`.
* **우선순위:** High (재무적 영향)
* **신뢰도:** Confirmed
* **문제:** BUY 분기에서 `kind == "시장가"`와 그 외(지정가/최유리)가 **둘 다** `_place_buy_order`(시장가 전용)를 호출한다. 수집된 `price`는 어디에도 전달되지 않는다. 즉 사용자가 지정가를 입력해도 시장가로 체결된다. SELL은 수량/금액 스핀값을 그대로 수량으로 넘기며 주문형식을 구분하지 않는다. dry-run(`ticket_dry_run:167-193`)은 `side = "bid"` 고정이라 매도 검증을 매수로 검증한다.
* **발생 조건:** 주문티켓에서 지정가/최유리 선택 후 매수 클릭 시 항상. 매도 사전검증 클릭 시 항상(검증 방향 오류).
* **영향:** 사용자가 가격 제한 의도로 낸 주문이 시장가로 즉시 체결되어 슬리피지·체결가乖離가 발생한다. `order/test` 사전검증도 매도 조건을 검증하지 못하므로 통과 판정이 거짓 안전 신호가 된다.
* **근거:** 221~225행 두 분기가 동일한 호출이며, `_place_best_buy_order`/`buy_limit_order` 등 기존 함수가 같은 파일 어디에서도 호출되지 않는다. `_to_test_payload`는 종류를 구분하지만 호출부의 `side`가 하드코딩이라 무용지물이다.
* **반증 확인:** `_place_buy_order` 내부에 종류 분기가 있는지(`placement.py:24-63`), 컨트롤러 facade가 티켓 종류를 별도 인자로 받는지 확인했으나 없음. `order/test` 서버 측이 side를 무시하는지도 검토했으나 클라이언트가 처음부터 bid를 보내므로 반증 불가다.
* **호출/영향 범위:** `build_order_ticket`→`submit_ticket_order`→`_place_buy/sell_order`→`mark_pending`→체결 폴링으로 이어지는 실주문 경로 전체. 행 퀵버튼·트레이딩뷰도 동일 티켓 모듈을 재사용한다.
* **권장 수정 방향:** 종류별 분기를 실제 함수에 연결(시장가→`_place_buy_order`, 최유리→`_place_best_buy_order`, 지정가→지정가 경로 신설 또는 미지원 명시+차단). `price`/`amount` 의미(금액 vs 수량)를 종류별로 검증하고, dry-run side를 실버튼과 일치시킨다. 당장 고치기 전에는 지정가/최유리 옵션을 UI에서 비활성화하는 것도 차선이다.
* **필요한 회귀 테스트:** 종류별 submit이 호출한 하위 함수명을 fake으로 기록하는 unit 테스트(입력: 지정가+가격 100000+금액, 기대: 지정가 경로 호출 및 price 전달 / 현재 코드면 실패). 매도 dry-run이 `side="ask"` 페이로드를 보내는지 assert.

### [ISSUE-003] `UpbitProTrader()` 생성 경로에서 `QTimer(self)` 부모 타입 오류 (자사 테스트 실패)

* **위치:** `upbit_autotrader/controllers/history_controller.py:84-91` (`_ensure_history_flush_state`) ← `upbit_autotrader/app/bootstrap_ops.py:89-91` (`load_trade_history` → `_create_price_thread` 이전).
* **우선순위:** High
* **신뢰도:** Confirmed (자사 테스트 실패로 재현)
* **문제:** `UpbitProTrader()` 생성 중 `QTimer(self)`가 `TypeError: ... unexpected type 'UpbitProTrader'`로 실패한다. 실행한 전체 스위트에서 유일한 실패다.
* **발생 조건:** `tests/test_fluent_ui_foundation.py::test_fluent_shell_registers_all_legacy_pages_without_emoji`에서 확정 재현. 동일 코드는 `setup_timers`의 모든 `QTimer(self)`에도 잠재한다.
* **영향:** 앱 초기화가 깨지면 이후 가격 스레드·타이머·UI 바인딩 전부 도달 불가다. 실사용 Windows 경로에서는 정상 기동 로그가 남아 있어 상시 발현은 아니지만, 초기화 순서가 Qt 베이스 완성보다 앞서 있어 환경(QApplication/Fluent 베이스 초기화 상태)에 따라 기동 자체가 흔들린다.
* **근거:** 실패 traceback이 `trader.py:62 bootstrap_trader → history_controller.py:408 load_trade_history → :88 QTimer(self)`를 정확히 가리킨다. `ControllerTypeBase`가 런타임에는 빈 object라 MRO상 Qt 베이스 초기화가 뒤쪽(`_FluentBase`)에 있어, bootstrap이 그 완성 여부를 가정하고 타이머를 먼저 만드는 구조다.
* **반증 확인:** 상위에서 QApplication 존재를 보장하는지, `super().__init__()`이 Qt를 완성하는지 검토했다. `main()`은 QApplication을 만들지만 테스트 경로는 그렇지 않을 수 있어, 현재 구조는 호출 환경에 따라 깨지는 fragile 초기화에 해당한다. 프레임워크가 자동 보정하지 않는다.
* **호출/영향 범위:** `UpbitProTrader.__init__`→`bootstrap_trader`→거래 히스토리→가격 스레드→로깅→UI/트레이/타이머→설정/복구상태→레짐 스레드. 초기화 선두이므로 blast radius가 앱 전체다.
* **권장 수정 방향:** (1) Qt 베이스(`_FluentBase.__init__`)를 명시적으로 먼저 초기화하거나, (2) `QTimer(self)`에 부모를 주지 않고 `timer = QTimer()` + 필요 시 명시적 소유권 관리로 변경하거나, (3) 히스토리 로드를 Qt 완성 이후로 미룬다. 셋 중 하나만으로 해당 실패는 제거된다.
* **필요한 회귀 테스트:** 실패한 테스트 자체가 회귀 테스트다. 추가로 QApplication 없는 headless/offscreen 조건에서 `UpbitProTrader()` 생성 또는 최소한 `_ensure_history_flush_state`가 부모 타입 오류 없이 동작함을 assert.

### [ISSUE-004] `trade_history.json` 비원자적 저장 + 손상 시 전체 초기화

* **위치:** `upbit_autotrader/controllers/history_controller.py:98-107` (`_flush_trade_history`, `_save_trade_history_now`), `406-415` (`load_trade_history`).
* **우선순위:** High (데이터 무결성)
* **신뢰도:** Confirmed
* **문제:** 저장이 `open(..., 'w')` 직접 덮어쓰기이며 예외 처리·tmp+rename이 없다. 쓰기 중 강제종료·정전·디스크 부족 시 파일이 절단된다. 로드는 `json.load` 실패 시 예외를 삼키고 `self.trade_history = []`로 전체를 버린다. 백업·무결성 검사·부분 복구가 없다.
* **발생 조건:** 자동 flush(debounce 타이머)·`closeEvent`의 이중 flush·CSV 내보내기와 무관하게, 쓰기 도중 프로세스가 죽거나 JSON이 깨지면 다음 기동에서 확정 발현한다.
* **영향:** 실현손익·승률·청산사유 등 감사 추적의 원천이 통째로 사라진다. 동일 앱의 `ReconciliationStore.save`는 tmp+`os.replace` 원자적 저장을 하므로, 주문 복구 상태는 살고 거래 근거만 날아가는 불일치가 생긴다.
* **근거:** `_save_trade_history_now` 2줄이 전부이며 호출자인 `_flush`에도 try가 없다. `load`의 except는 로깅 후 `[]` 대입이 명시되어 있다. `closeEvent`는 `_flush`와 `save_trade_history`를 연달아 호출해 같은 비원자 저장을 두 번 수행한다.
* **반증 확인:** 상위 타이머 슬롯·종료 경로에 별도 보호가 있는지, OS/파일시스템이 원자성을 보장하는지 검토했다. 단일 `open('w')+dump`는 어느 쪽도 보장하지 않으며, DB 트랜잭션도 없다. 데드코드가 아니라 매 체결(`add_trade_record`→스케줄 저장)마다 도달하는 production 경로다.
* **호출/영향 범위:** `add_trade_record`(매수/매도 체결 전부)→`_schedule→_flush→_save_now`, `closeEvent`, 분석 리포트·백테스트 입력(`UpbitTradingAnalytics`가 같은 파일을 읽음). 즉 기록-분석-리포트 체인 전체의 신뢰도가 이 2줄에 의존한다.
* **권장 수정 방향:** `ReconciliationStore`와 동일한 tmp+`os.replace` 원자적 저장으로 교체, 저장 실패를 로그+상태바에 남기고 dirty를 유지(다음 flush에서 재시도), 로드 실패 시 `[]` 대입 전에 `.corrupt-<ts>.bak`로 보존 후 빈 상태로 시작한다.
* **필요한 회귀 테스트:** dump 중 예외 주입 시 원본 파일이 그대로 보존되는지(크기·바이트 동일), 깨진 JSON 로드 시 백업 파일 생성 + 빈 히스토리로 기동하는지, flush 실패 후 dirty가 유지되어 재시도되는지를 assert하는 unit 테스트 3건.

### [ISSUE-005] 비-Windows에서 설정 저장 전체가 실패한다 (DPAPI 단일 경로)

* **위치:** `upbit_autotrader/services/settings_store.py:45-58` (`save_settings`), `upbit_autotrader/controllers/settings_controller.py:20-43` (`save_settings`).
* **우선순위:** High
* **신뢰도:** Likely (코드 경로상 확정적이나 Linux 실측 미수행)
* **문제:** 저장은 키 유무와 무관하게 항상 `encrypt_dpapi`를 호출하고, 비-Windows에서는 `DPAPIError`를 던진다. 컨트롤러는 이를 잡아 로그만 남기고 저장을 중단하므로, 비밀키가 아닌 일반 전략·리스크 설정까지 함께 저장되지 않는다. 로드 측은 `DPAPIError`를 잡아 빈 키+경고로 계속 가동하므로 읽기/쓰기 비대칭이다.
* **발생 조건:** Linux/macOS에서 키가 비어 있더라도 설정 저장 버튼을 누르면 확정 발생(빈 문자열이면 `encrypt` 호출을 건너뛰므로, 키 입력 상태에서 발생).
* **영향:** 크로스플랫폼 지원 주장과 정면으로 충돌한다. 키를 입력한 Linux 사용자가 설정을 저장할 수 없고, 저장 실패를 로그 한 줄로만 알 수 있다.
* **근거:** `save_settings`에 플랫폼 분기·평문 폴백·비밀키 분리 저장이 없다. `security.py`의 가드는 `DPAPIError`를 던지는 것으로 끝나며 호출자가 복구하지 않는다.
* **반증 확인:** 호출자가 키를 분리 저장하는지, 프레임워크가 키체인을 제공하는지, 빈 키일 때 회피되는지로 반증을 시도했다. 빈 키일 때는 회피되지만, 키가 있는 정상 사용 조건에서는 보호 장치가 없다. production 도달 가능 코드는 맞다(설정 저장은 핵심 경로).
* **호출/영향 범위:** 설정 저장→런타임 통합 적용→재기동 로드 체인. 키 저장 실패가 전략 파라미터 영속화까지 막는 연쇄 구조다.
* **권장 수정 방향:** 비-Windows에서는 (a) 일반 설정은 그대로 저장하고 비밀키만 OS 키체인 또는 권한 600 평문 분리 파일로 저장하되 경고 배지를 표시하거나, (b) 최소한 일반 설정 저장과 키 저장을 분리해 한쪽 실패가 다른 쪽을 막지 않게 한다. 보안 정책상 평문이 불가하면 "이 플랫폼에서는 키 저장 미지원"을 저장 전에 명시적으로 차단한다.
* **필요한 회귀 테스트:** `encrypt_dpapi`가 `DPAPIError`를 던지도록 모킹한 상태에서 `save_settings` 호출 시 일반 설정 파일이 생성되고 키 필드가 안전하게 처리(또는 명시적 실패 메시지)되는지를 assert. 현재 코드면 파일 미생성으로 실패한다.

### [ISSUE-006] `os.startfile` 4곳이 비-Windows에서 전부 실패한다

* **위치:** `history_controller.py:304, 371, 401`, `ui_parts/menu_tray_ops.py:38`.
* **우선순위:** Medium
* **신뢰도:** Likely (Windows 전용 API라는 점은 확정, Linux 클릭 실측은 미수행)
* **문제:** 리포트 생성·백테스트 결과·내보내기 폴더 열기·로그 폴더 열기가 모두 `os.startfile` 직접 호출이다. Linux/macOS에는 이 속성이 없어 `AttributeError`가 발생한다. 3곳은 try 안에 있어 "리포트 생성 실패"로 오인 표시되고, 메뉴 람다 1곳은 슬롯에서 그대로 터진다.
* **발생 조건:** 비-Windows에서 해당 메뉴/버튼 클릭 시.
* **영향:** 분석 리포트·백테스트 결과 확인·로그 열람이 크로스플랫폼에서 동작하지 않는다. 파일 자체는 생성될 수 있는데 열기 단계에서 실패하므로 사용자는 생성 실패로 오해한다.
* **근거:** 4개 호출점에 플랫폼 분기가 없으며, `os` 모듈에 대한 대체 열기(`xdg-open`/`open`/`explorer`) 유틸이 repo에 존재하지 않는다.
* **반증 확인:** 상위 try가 사용자 경험을 구제하는지 검토했으나, 에러 메시지가 원인을 가리고 폴더 자동 열기라는 부가 기능이 핵심 리포트 확인 동선을 막는다. Qt의 `QDesktopServices.openUrl` 같은 프레임워크 대안이 있으나 사용되지 않았다.
* **호출/영향 범위:** 히스토리 컨트롤러의 리포트 3동선 + 메뉴/트레이 1동선. 주문·체결 경로와는 분리되어 있어 자금 직접 영향은 없다.
* **권장 수정 방향:** `QDesktopServices.openUrl(QUrl.fromLocalFile(...))` 또는 `sys.platform` 분기(`os.startfile`/`open`/`xdg-open`, `subprocess` 리스트형·셸 금지)로 교체하고, 열기 실패는 "파일은 생성됨 + 경로 표시"로 격하한다.
* **필요한 회귀 테스트:** `os.startfile` 부재 환경 시뮬레이션에서 리포트 생성 함수가 파일 생성까지 성공하고 열기 실패를 파일 경로 안내로 처리하는지를 assert하는 integration 테스트.

## 5. Potential Functional Gaps

* **Confirmed Gap — 실거래 reconciliation 영속화 기본 OFF:** `DEFAULT_PERSIST_RECONCILIATION_STATE = False`이며 live 시작 시 경고만 나온다 (`session_ops.py:83-92`, `lifecycle_ops.py:126-139`). 재시작 복구가 설계상 제한되는데 기본값이 복구 불능 쪽이다. 크래시 후 거래소 잔존 주문을 수동으로 대조해야 한다. 기본 ON 또는 live 시작 시 1회 확인 프롬프트가 필요하다.
* **Confirmed Gap — 종료 경로에서 네트워크 재조회:** `closeEvent`가 `save → flush → _reconcile_pending_orders(force=True)` 순으로 종료 시점에 실조회를 수행한다 (`runtime_ops.py:133-140`). `api_call_with_retry`는 GUI 스레드에서 sleep하므로 종료가 수초~수십초 멈추거나, 실패 시 종료가 지연된다. 종료 시에는 조회 대신 상태만 영속화하고 조회는 다음 기동 시로 미루는 편이 안전하다.
* **Likely Gap — 일괄매수가 `chance` 검증을 우회:** `execute_buy`는 `_validate_live_order_request`(마켓 상태·주문 타입·최소금액)를 거치지만, `execute_batch_buy`(`batch_ops.py:214-251`)는 최소금액·pending·예약만 보고 `chance`를 조회하지 않는다. 거래정지·최소금액 상향 종목에서 일괄매수만 실패하거나 부분 체결된다. 자동매매와 동일한 검증 함수 재사용이 필요하다.
* **Likely Gap — 단일 티커당 pending 1건 제한과 TWAP/수동의 상호작용:** `has_pending`가 티커 키 단일 슬롯이라 TWAP 진행 중 수동 개입·부분매도가 전부 "대기 중"으로 거부된다. 긴급청산도 pending 종목은 건너뛴다. 거부 자체는 안전하나, TWAP 장기 실행 중 긴급 상황 대응이 막힐 수 있어 취소 후 재주문 동선과 연결이 필요하다.
* **추정 — 프리셋·히스토리 파일의 동시쓰기/스키마 방어 부재:** `upbit_presets.json`·히스토리 저장은 단일 GUI 스레드라 race는 낮지만, 스키마 버전 검사·원자적 저장·손상 백업이 reconciliation보다 약하다. 장기 운용 시 설정 스키마가 어긋나면 조용히 기본값으로 대체될 수 있다.
* **추정 — 가격 피드 stale 감지와 자동매매 차단의 연결:** `_last_price_update_ts`·`_price_feed_recovery_attempted` 상태는 있으나, WS 4초 REST 폴백 외에 피드 장기 단절 시 신규 진입을 멈추는 fail-closed가 레짐 stale만큼 명시적이지 않다. 점검 시간대에는 신호가 낡은 가격으로 평가될 여지가 있다.

## 6. Documentation Mismatches

* **없지 않다. 다음 불일치가 확인된다:**
  1. `AGENTS.md` 부재: 감사 지시문에 지정된 `AGENTS.md` 파일이 repo에 존재하지 않는다. `CLAUDE.md`·`GEMINI.md`·`README.md`만 있다.
  2. 크로스플랫폼 주장 vs 실제 구현: `README.md` 시스템 요구사항이 "Windows 10/11 (권장), macOS, Linux"를 명시하지만, ISSUE-001/005/006으로 인해 비-Windows에서는 기동·설정 저장·리포트 열람이 깨진다.
  3. 실행 모드 설명: `CLAUDE.md`는 실행 모델을 `single_market`·`twap_market`만 기재하지만, 코드·README·주문티켓에는 `best`(최유리)가 존재한다. 단 티켓의 `best`는 ISSUE-002로 실제로 시장가로 나가므로 문서·UI·구현 셋이 서로 다르게 어긋나 있다.
  4. 구 감사서의 현재성: 루트 `PROJECT_AUDIT.md`(구본)는 "3단계 전부 완료", "142개 테스트 100% 통과", 잔여 권고만 남은 것처럼 기술하지만, 현재 스위트는 211건 중 1건 실패이며 본 감사의 ISSUE-002~004는 구본에 없다. 구본을 최신 상태로 인용하면 안 된다.
  5. 경미: `README.md` 아키텍처 트리와 `CLAUDE.md` 구조 요약의 모듈명粒度가 서로 다르다(예: `services/upbit_client.py` vs `services/upbit/` 패키지). 둘 다 큰 틀은 맞지만 파일 단위 추적 시 혼선이 있다.

## 7. Recommended Fix Plan

### Phase 1 — Immediate

1. ISSUE-001 `winreg` 지연 import + 비-Windows 시작프로그램 경로 비활성화 (기동 불가 해소).
2. ISSUE-002 주문티켓 종류 분기 연결 또는 지정가/최유리 UI 임시 비활성화 + dry-run side 수정 (오체결 방지).
3. ISSUE-003 초기화 순서 수정 (`_FluentBase` 명시 초기화 또는 QTimer 무부모화) 후 실패 테스트를 게이트로 고정.
4. ISSUE-004 히스토리 원자적 저장 + 손상 백업 (유실 방지).

### Phase 2 — Stability

5. ISSUE-005 설정 저장 분리 (일반 설정은 항상 저장, 키 저장은 플랫폼별 처리) + 저장 실패 UI 명시.
6. ISSUE-006 파일/폴더 열기 크로스플랫폼 유틸 (`QDesktopServices` 또는 플랫폼 분기) 교체.
7. `closeEvent`에서 네트워크 재조회 제거 (상태만 저장, 조회는 다음 기동).
8. 일괄매수에 `chance` 검증 추가 (자동매매와 동일 함수).
9. reconciliation 영속화 기본값 재검토 (live 기본 ON 또는 시작 시 명시적 선택).

### Phase 3 — Structural

10. 초기화 순서 계약 문서화 + headless/offscreen 생성 테스트를 CI 게이트에 포함.
11. 파일 저장 규격 통일 (모든 JSON 영속화는 tmp+rename, 손상 시 `.bak`, 스키마 버전 검사).
12. 주문 경로 단일화 (자동·수동·일괄·티켓이 동일한 검증→예약→발주→pending 파이프를 공유하도록 리팩터링하되 동작 변경은 테스트 동반).
13. 구 감사서 인용 금지: 본 문서를 최신으로 두고, 수정 시마다 실패 테스트 수와 함께 갱신한다.

## 8. Test Recommendations

* **Unit — `winreg` 없는 import:** `sys.modules["winreg"]`를 블로킹한 상태에서 `settings_controller` import 성공을 assert. 기대: `ModuleNotFoundError` 없음. 현재 코드면 실패.
* **Unit — 티켓 종류 분기:** fake `_place_buy_order`/`_place_best_buy_order`/지정가 경로를 주입하고 지정가+가격 입력 후 `submit_ticket_order("BUY")` 호출. 기대: 지정가 경로 호출 + price 전달. 현재 코드면 시장가 경로 호출로 실패.
* **Unit — dry-run 방향:** 매도 버튼 상태에서 `ticket_dry_run`이 발생시킨 `test_order` 페이로드의 `side`가 `"ask"`인지 assert. 현재 코드면 `"bid"`로 실패.
* **Unit — 히스토리 원자성:** `json.dump` 중 예외 주입 후 원본 바이트 동일 assert + `_history_dirty` 유지 assert. 깨진 JSON 로드 시 `.bak` 생성 + 빈 히스토리 기동 assert.
* **Unit — 설정 저장 분리:** `encrypt_dpapi`를 강제 실패시킨 뒤 `save_settings` 호출. 기대: 일반 설정 파일 존재 + 키 미저장 사유 명시. 현재 코드면 파일 미생성.
* **Integration — 초기화 순서:** 실패한 `test_fluent_shell_registers_all_legacy_pages_without_emoji` 자체를 게이트로 유지 + offscreen `QApplication`에서 `UpbitProTrader()` 생성 성공 assert.
* **Integration — 종료 경로:** `closeEvent`에서 외부 네트워크 호출 횟수가 0인지 fake transport로 assert. 현재 코드면 reconcile 호출로 실패.
* **Integration — 일괄매수 검증:** 마켓 상태 `halt`인 fake `chance`에서 `execute_batch_buy`가 주문을 내지 않고 경고 로그를 남기는지 assert. 현재 코드면 주문 시도로 실패.
* **E2E — 페이퍼 매수→체결→매도:** 페이퍼 모드에서 감시 시작→가격 주입→`check_buy_execution(done)`→보유 확인→손절/TS 매도→`trade_history.json` 기록 존재 + 잔고 정합을 assert.
* **Concurrency — WS 이벤트 폭주:** `order_event_received` 시그널을 100건 연속 emit한 뒤 `pending_orders` 크기·uuid 정합 assert (현재 시그널 일원화 이후 회귀 방지용).
* **Regression — 레짐 fail-closed:** stale 컴포넌트 포함 출력에서 신규 매수 차단 + `fail_closed` OFF 시 경고만 하고 진행하는 경우를 각각 assert.
* **Platform-specific — 파일 열기:** `os.startfile` 삭제 fixture에서 리포트 생성 함수가 파일 생성 성공 + 경로 안내로 종료되는지 assert (Windows에서는 기존 동작 유지).

## 9. Final Assessment

| 영역 | 평가 | 근거 |
|---|---|---|
| Functional Correctness | Needs Work | 주문티켓 종류 무시(ISSUE-002)는 핵심 주문 정확도 결함이며 테스트 실패(ISSUE-003)가 동반된다. |
| Runtime Stability | Needs Work | 초기화 순서 fragility + 종료 시 네트워크 재조회 + 비-Windows 기동 불가. Windows 정상 경로에서는 안정적이다. |
| Data Integrity | Needs Work | 히스토리 비원자 저장+전체 초기화(ISSUE-004)가 확정적. reconciliation은 원자적이라 양호. |
| Error Resilience | Acceptable | 재시도·백오프·레이트리밋·수동검토 큐·TWAP 폴백·레짐 fail-closed가 갖춰져 있으나 저장/종료 경로의 예외 처리가 약하다. |
| Cross-platform Robustness | High Risk | `winreg`·`os.startfile`·DPAPI 3중으로 비-Windows 지원 주장이 성립하지 않는다. |
| Test Confidence | Acceptable | 211건 중 210건 통과로 커버리지는 넓으나, 실패 1건이 방치되어 있고 플랫폼·티켓 분기·원자성 회귀 테스트가 비어 있다. |

**실제로 먼저 수정할 문제 3개:**

1. **[ISSUE-001] `import winreg` 격리** — 비-Windows 기동 불가이므로 다른 수정보다 먼저. 수정 후 해당 플랫폼에서 import 성공을 확인한다.
2. **[ISSUE-002] 주문티켓 종류 분기** — 자금이 직접 걸린 오체결 경로이므로 즉시 차단 또는 연결한다.
3. **[ISSUE-004] 히스토리 원자적 저장** — 한 번의 강제종료로 감사 근거 전체가 날아가는 구조이므로, 수정량이 작고 효과가 확실하다.
