# STRATEGY_OPTIONS_IMPLEMENTATION_PLAN

## 1. 목적
v3.2 전략 엔진 옵션(`single`, `ensemble`)과 진입 정책(`engine_gate_policy`)의 운영 기준을 명확히 정의합니다.

## 2. 전략 분류
- 추세/모멘텀
  - `volatility_breakout`
  - `donchian_breakout`
  - `ema_cross_trend`
  - `time_series_momentum`
- 평균회귀
  - `rsi_reversion`
  - `bollinger_reversion`
  - `zscore_reversion`
- 메타 리스크
  - `volatility_targeting`
  - `regime_filter`
  - `drawdown_guard`

## 3. 실행 모드
- `single`
  - 단일 전략 점수로 매수 판정.
- `ensemble`
  - 활성 전략 점수의 가중 평균(`strategy_weights`)으로 매수 판정.
  - 임계값: `ensemble_threshold`.

## 4. 진입 게이트 정책
설정 키: `engine_gate_policy`

- `legacy_first`
  - 기존 target/MA 하드게이트 우선 적용.
- `engine_only`
  - 하드게이트 비활성, 전략 엔진 시그널만으로 진입.
- `strategy_aware` (기본값)
  - `single` + 추세 전략: 하드게이트 유지.
  - `single` + 평균회귀 전략: 하드게이트 비활성.
  - `ensemble`: 활성 전략 중 평균회귀가 1개라도 있으면 하드게이트 비활성.

## 5. 리스크 연동 옵션
- `enable_account_wide_sync`
  - 시작 시 watchlist + 계좌 전체 보유 동기화.
- `risk_include_unrealized`
  - 리스크 계산에 미실현 손익 포함.
- `risk_include_external_holdings`
  - watchlist 외 보유를 리스크 계산에 포함.
- `manual_review_on_timeout`
  - timeout unresolved 주문을 수동검토 큐로 보존.
- `price_feed_stale_sec`
  - 가격피드 stale 감지 임계값.

## 6. 운영 권장값
- 초반 운영:
  - `engine_gate_policy = strategy_aware`
  - `risk_include_unrealized = True`
  - `risk_include_external_holdings = True`
  - `manual_review_on_timeout = True`
- 공격적 연구 모드:
  - `engine_gate_policy = engine_only`
  - 별도 보호장치(최대보유, 손실한도, 알림) 강화 필수.

## 7. 테스트 기준
- 평균회귀 전략의 `strategy_aware` 진입 허용 검증.
- 추세 전략의 하드게이트 유지 검증.
- 혼합 ensemble에서 하드게이트 완화 검증.
- timeout unresolved 시 manual review queue 적재 검증.
- account-wide 동기화/리스크 계산 범위 검증.
