# PROJECT_STRUCTURE_ANALYSIS

## 1. Scope
이 문서는 2026-02-25 기준 코드(`upbit_autotrader/` 패키지 중심)를 기반으로 자동매매 구조를 요약합니다.

## 2. Runtime Topology
- `upbit_autotrader/app/trader.py`
  - `UpbitProTrader` 퍼사드.
  - UI/설정/매매/배치/히스토리 컨트롤러를 Mixin으로 합성.
- `upbit_autotrader/controllers/ui_controller.py`
  - 위젯 생성, 프리셋 적용, 다이얼로그 라우팅.
- `upbit_autotrader/controllers/settings_controller.py`
  - 설정 저장/로드, 시스템 설정, 알림 연동.
- `upbit_autotrader/controllers/trading_controller.py`
  - 실시간 가격 콜백 기반 매매 판단/주문/체결확인/리스크 체크.
- `upbit_autotrader/controllers/batch_controller.py`
  - 일괄 매수/매도/긴급청산, 외부보유 체결확인.
- `upbit_autotrader/services/order_service.py`
  - pending 주문 추적, 주문 상태 전이, 체결 수치 계산 유틸.
- `upbit_autotrader/services/holdings_service.py`
  - 계좌 KRW 보유 조회/정규화.
- `upbit_autotrader/strategies/engine.py`
  - `single`/`ensemble` 전략 평가 및 메타 리스크 시그널.
- 루트 `upbit_*.py`
  - 기존 import 경로 호환을 위한 래퍼(하위 패키지 모듈 재노출).

## 3. Startup/Data Sync
- 시작 시 `watchlist + account holdings` 합집합으로 universe를 구성.
- `enable_account_wide_sync=True`일 때 watchlist 외 보유도 universe에 편입.
- 보유 종목은 `qty`, `buy_price`, `invest_amt`, `state=보유중`으로 복원.
- paper 모드도 동일 동기화 원칙 사용.

## 4. Entry Gate Policy
- 설정 키: `engine_gate_policy`
  - `legacy_first`: 기존 target/MA 하드게이트 유지.
  - `engine_only`: 하드게이트 비활성.
  - `strategy_aware`:
    - 평균회귀 전략 포함 시 하드게이트 비활성.
    - 추세 전략만 활성일 때 하드게이트 유지.

## 5. Order State Machine
`upbit_order_service.py` 기준 pending lifecycle 상태와 허용 전이:

| From | To |
| --- | --- |
| `submitted` | `wait`, `done`, `cancel`, `timeout` |
| `wait` | `done`, `cancel`, `timeout` |
| `timeout` | `wait`, `done`, `cancel`, `manual_review` |
| `manual_review` | `reconciled`, `done`, `cancel` |

- 불법 전이는 무시되며 `False` 반환.
- 각 전이는 `lifecycle_history`에 timestamp와 reason을 기록.

## 6. Reconciliation and Recovery
- 타임아웃 처리 순서:
  1. `cancel_order(uuid)` best-effort 시도
  2. `get_order(uuid)` 재조회
  3. `done/cancel`이면 체결 반영 후 정리
  4. 미해결이면 `manual_review_queue` 적재 + `needs_manual_review=True`
- 세션 불일치 콜백:
  - `orphan_events`에 기록
  - terminal state(`done/cancel`)는 pending 정리
  - account-wide sync 트리거로 포지션 재수렴

## 7. Risk Snapshot Model
`check_risk_limits()`는 `_get_risk_snapshot()` 결과를 사용합니다.

- `portfolio_pnl = realized_pnl + unrealized_pnl`
- `loss_rate = portfolio_pnl / initial_balance * 100`
- `unrealized_pnl` 계산 대상:
  - universe 보유
  - 옵션 활성 시 watchlist 외 외부보유 포함
- holdings 제한은 account-wide 기준 종목 수 사용.
- 스냅샷 TTL 캐시(`RISK_SNAPSHOT_TTL_SEC`)로 API 과호출 억제.

## 8. API Resilience
- live API는 중앙 helper 경로로 통일:
  - `_api_get_order`, `_api_get_balance`, `_api_get_balances`
  - `_api_cancel_order`, `_api_buy_market_order`, `_api_sell_market_order`
- `api_call_with_retry()`에 최소 호출 간격, 지수 백오프, jitter 적용.

## 9. Ops Alert Events
`_ops_alert(level, message, key, cooldown)`으로 트레이+로그 알림을 통합합니다.

자동 알림 대상:
- 체결확인 timeout/unresolved
- manual review queue 적재
- orphan 이벤트 감지
- 가격피드 stale 감지 및 재시작 시도

## 10. Testing Map
핵심 회귀 테스트:
- `tests/test_order_stability.py`
- `tests/test_trader_order_flows.py`
- `tests/test_reported_risk_fixes.py`
- `tests/test_strategy_engine_*`
- `tests/test_startup_position_sync.py`
- `tests/test_order_reconciliation_recovery.py`
- `tests/test_risk_limits_portfolio_scope.py`
