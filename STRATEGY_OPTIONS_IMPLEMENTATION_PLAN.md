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

## 8. v3.3 확장 옵션 (구현 반영)

### 8.1 리스크 사이징
- `use_risk_budget_sizing` (기본 `False`)
- `risk_budget_pct` (기본 `0.5`)
- `atr_stop_mult` (기본 `2.0`)
- `min_stop_pct` (기본 `0.3`)
- `max_betting_pct` (기본 `15.0`)
- `use_kelly_adjustment` (기본 `False`)
- `kelly_scale` (기본 `0.25`)

### 8.2 드로우다운 상태
- `drawdown_state_enabled` (기본 `False`)
- `dd_caution_pct` (기본 `3.0`)
- `dd_defense_pct` (기본 `5.0`)
- `dd_halt_pct` (기본 `8.0`)

### 8.3 실행 모델/TWAP
- `use_execution_model` (기본 `False`)
- `execution_mode`: `single_market` / `twap_market`
- `expected_slippage_guard_bps` (기본 `30.0`)
- `twap_slices` (기본 `3`)
- `twap_interval_sec` (기본 `8`)

### 8.4 메타 시그널/가중치
- `use_meta_signal` (기본 `False`)
- `meta_min_expectancy` (기본 `0.0`)
- `meta_score_threshold` (기본 `60.0`)
- `weight_rebalance_daily` (기본 `True`)
- `weight_min` (기본 `0.5`)
- `weight_max` (기본 `1.5`)

### 8.5 운영 알림/복구
- `enable_discord_alerts` (기본 `False`)
- `discord_webhook`
- `persist_reconciliation_state` (기본 `False`)
- 이벤트: `BUY`, `SELL`, `WARNING`, `ERROR`, `EMERGENCY`

## 9. 운영 권장 프로파일
- 보수형(기본 권장):
  - `risk_budget_pct=0.5`, `atr_stop_mult=2.0`, `kelly_scale=0.25`, `max_betting_pct=15.0`
- 안정성 검증 단계:
  - 실거래 전 `use_execution_model=True` + `use_meta_signal=True`를 페이퍼 모드에서 먼저 검증
- 롤아웃 원칙:
  - 신규 옵션은 순차적으로 `ON`하고, 회귀 테스트 및 페이퍼 검증 후 실거래 반영

## 10. 구현 상태 (2026-02-27)
- 계획 문서의 핵심 옵션은 코드에 반영 완료
- 신규 옵션은 모두 고급 탭 UI 및 설정 저장/복원 경로와 연결됨
- 전체 테스트 통과: `74 passed`
