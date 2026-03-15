# Upbit Pro Algo-Trader v3.3.0

Claude/Codex 작업 가이드 문서입니다.

## 구조 요약
```txt
upbit_autotrader/
  app/trader.py                       # 퍼사드/앱 수명주기
  controllers/                        # UI/설정/매매/배치/히스토리 + _type_support.py
  services/                           # 주문/보유/설정저장/보안/페이퍼주문
  strategies/                         # 엔진/카탈로그/레거시/메타시그널
  risk/                               # 포지션 사이징/포트폴리오 리스크
  execution/                          # 실행 모델/TWAP/복구 상태저장
  core/                               # config/entry_filter
  runtime/                            # price thread
  analytics/, backtesting/, ui/, notifications/
```

루트 엔트리포인트는 `upbit_trader.py`만 유지합니다.
기존 호환 래퍼는 `legacy_wrappers/`로 기능별 정리되었습니다.

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
- `93 passed`

신규 검증 파일:
- `tests/test_docs_references.py`
- `tests/test_position_sizing.py`
- `tests/test_portfolio_risk_engine.py`
- `tests/test_execution_model.py`
- `tests/test_meta_signal.py`
- `tests/test_text_integrity.py`
- `tests/test_structure_guards.py`
- `tests/test_refactor_split_compatibility.py`
- `tests/test_plan_implementation_fixes.py`

## 정적 타입 검사
```bash
python -m pyright
```

현재 기준:
- `0 errors, 0 warnings, 0 informations`
- 루트 `pyrightconfig.json` 기준으로 VS Code Pylance와 CLI pyright를 동일 설정으로 유지
- 컨트롤러 믹스인 구조를 수정할 때는 `controllers/_type_support.py`도 함께 갱신해 Pylance/Pyright 정합성을 유지

## 로컬 품질 점검
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

- pre-commit 훅은 `tests/test_docs_references.py`, `tests/test_text_integrity.py`, `python -m pyright` 검사를 수행

## 작업 주의사항
- 주문/체결 로직 수정 시 pending 정리와 lifecycle 전이를 함께 검토
- TWAP 경로 수정 시 최소주문금액 및 잔여 slice 재계산 검증
- 리스크 계산 변경 시 external holdings/unrealized 포함 여부를 분리 검증
- Discord 실패는 비치명 경로 유지(매매 차단 금지)
- 문서 수정 시 `README.md`, `CLAUDE.md`, `GEMINI.md`, `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`의 테스트 수치와 참조 문서 정합성 유지

## 참고 문서
- 기능 구현 리스크 리뷰: `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`
- 사용자 문서: `README.md`
- 레거시 래퍼 안내: `legacy_wrappers/README.md`
