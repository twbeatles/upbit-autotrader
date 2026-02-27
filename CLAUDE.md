# Upbit Pro Algo-Trader v3.3.0

Claude/Codex 작업 가이드 문서입니다.

## 구조 요약
```txt
upbit_autotrader/
  app/trader.py                       # 퍼사드/앱 수명주기
  controllers/                        # UI/설정/매매/배치/히스토리
  services/                           # 주문/보유/설정저장/보안/페이퍼주문
  strategies/                         # 엔진/카탈로그/레거시/메타시그널
  risk/                               # 포지션 사이징/포트폴리오 리스크
  execution/                          # 실행 모델/TWAP/복구 상태저장
  core/                               # config/entry_filter
  runtime/                            # price thread
  analytics/, backtesting/, ui/, notifications/
```

루트 `upbit_*.py` 파일은 하위 패키지 모듈을 재노출하는 호환 래퍼입니다.

## 호환성 원칙
- 실행 진입점 유지: `python upbit_trader.py`
- 공개 클래스 유지: `UpbitProTrader`
- 설정 스키마 유지: `settings_version = 2`
- 배포 스펙 유지: `upbit_trader.spec`
- 신규 기능 기본값: 모두 `OFF` (기존 동작 유지)

## 핵심 정책
### 주문 경로
- live: `UpbitOrderService`
- paper: `UpbitPaperOrderService`
- 컨트롤러 라우팅: `_place_buy_order`, `_place_sell_order`

### 전략/게이트
- `strategy_mode`: `single` / `ensemble`
- `engine_gate_policy`: `legacy_first` / `engine_only` / `strategy_aware`
- `use_meta_signal` 활성 시 메타 게이트(`expected_value`, `meta_score`) 추가

### 리스크/사이징
- `use_risk_budget_sizing` 활성 시 ATR 기반 손절거리 + 리스크 예산 사이징
- `use_kelly_adjustment`로 Kelly 보정 상한 적용
- `drawdown_state_enabled` 활성 시 `normal/caution/defense/halt` 상태별 비중 스케일
- 포트폴리오 스냅샷: realized + (옵션)unrealized + 상관집중도/익스포저

### 실행/체결
- `use_execution_model` 활성 시 슬리피지 추정 + 주문 계획
- `execution_mode`: `single_market` / `twap_market`
- 거래기록에 수수료/예상-실현 슬리피지/실행모드/세션/리스크상태 저장

### 복구/운영
- timeout 주문 복구(cancel/requery/manual-review queue)
- orphan 이벤트 기록 + 세션 불일치 재동기화
- `persist_reconciliation_state` 활성 시 상태 JSON 주기 저장/복원
- 알림: 트레이 + (옵션)Discord 웹훅

## 설정 키(확장)
- 리스크 사이징
  - `use_risk_budget_sizing`, `risk_budget_pct`, `atr_stop_mult`, `min_stop_pct`, `max_betting_pct`
  - `use_kelly_adjustment`, `kelly_scale`
  - `drawdown_state_enabled`, `dd_caution_pct`, `dd_defense_pct`, `dd_halt_pct`
  - `portfolio_corr_window`, `max_correlation_exposure_pct`
- 실행 모델
  - `use_execution_model`, `execution_mode`, `expected_slippage_guard_bps`
  - `twap_slices`, `twap_interval_sec`
- 메타 시그널/가중치
  - `use_meta_signal`, `meta_min_expectancy`, `meta_score_threshold`
  - `weight_rebalance_daily`, `weight_min`, `weight_max`
- 운영
  - `enable_discord_alerts`, `discord_webhook`
  - `persist_reconciliation_state`

## 테스트
```bash
python -m pytest -q
```

현재 기준:
- `74 passed`

신규 검증 파일:
- `tests/test_position_sizing.py`
- `tests/test_portfolio_risk_engine.py`
- `tests/test_execution_model.py`
- `tests/test_meta_signal.py`

## 작업 주의사항
- 주문/체결 로직 수정 시 pending 정리와 lifecycle 전이를 함께 검토
- TWAP 경로 수정 시 최소주문금액 및 잔여 slice 재계산 검증
- 리스크 계산 변경 시 external holdings/unrealized 포함 여부를 분리 검증
- Discord 실패는 비치명 경로 유지(매매 차단 금지)

## 참고 문서
- 구조 분석/구현 상태: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 옵션 계획: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- 사용자 문서: `README.md`
