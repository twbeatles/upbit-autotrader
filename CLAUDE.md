# Upbit Pro Algo-Trader

Claude/Codex 작업 가이드 문서입니다.

## 현재 구조 요약
```txt
upbit_autotrader/
  app/
    trader.py                 # 공개 퍼사드
    bootstrap_ops.py          # 로거/타이머/초기 상태
    runtime_ops.py            # price thread / market regime thread 수명주기
  controllers/
    ui_controller.py          # UI 퍼사드
    ui_sections.py            # advanced tab 조합기
    trading_controller.py     # 매매 퍼사드
    trading_parts/            # 책임 분리(account/lifecycle/api/execution/signal/market_regime)
    ui_parts/                 # layout/dashboard/strategy/menu/preset/advanced_tab builders
  services/
  strategies/                # engine / catalog / legacy_strategy / meta_signal
  risk/
  execution/
  market_regime/             # engine / providers
  runtime/                   # price_thread / market_regime_thread
  analytics/, backtesting/, ui/, notifications/
```

루트 엔트리포인트는 `upbit_trader.py`만 유지합니다. 기존 호환 래퍼는 `legacy_wrappers/`로 정리되어 있으며 신규 구현 기준 경로는 `upbit_autotrader.*`입니다.

## 호환성 원칙
- 실행 진입점 유지: `python upbit_trader.py`
- 공개 클래스 유지: `UpbitProTrader`
- 설정 스키마 유지: `settings_version = 2`
- 배포 스펙 유지: `upbit_trader.spec`
- 위젯 attribute 이름, settings key, legacy wrapper import 경로 유지
- 신규 기능 기본값: 모두 `OFF`

## 핵심 정책
### 주문/실행
- live: `UpbitOrderService`
- paper: `UpbitPaperOrderService`
- 컨트롤러 라우팅: `_place_buy_order`, `_place_sell_order`
- 실행 모델은 `single_market` / `twap_market`
- 주문 lifecycle 변경 시 pending 상태, reconciliation store, manual review 큐를 함께 검토

### 전략/게이트
- `strategy_mode`: `single` / `ensemble`
- `engine_gate_policy`: `legacy_first` / `engine_only` / `strategy_aware`
- 매수 경로 기준 순서: 전략 엔진 -> market regime filter -> meta signal -> `execute_buy()`
- `MetaSignalInput`은 `technical_regime_score`와 `market_regime_score`를 함께 받음

### 리스크/시장 레짐
- `use_risk_budget_sizing` 활성 시 ATR 기반 리스크 예산 사이징
- `use_market_regime_filter` 활성 시 전역 시장 레짐 점수 하한 미달 BUY 차단
- `use_market_regime_risk_scaling` 활성 시 최종 주문 금액에 `0.50 / 0.75 / 1.00 / 1.15` 배수 적용
- 시장 레짐은 `market_regime/engine.py`, `market_regime/providers.py`, `runtime/market_regime_thread.py`, `controllers/trading_parts/market_regime_ops.py`로 분리됨

### UI/리팩토링
- `ui_controller.py`와 `trading_controller.py`는 facade 역할만 유지
- advanced tab 수정은 `controllers/ui_parts/advanced_tab/*` builder에서 우선 처리
- indicator 계산 변경은 `controllers/trading_parts/indicator_parts/*`를 우선 수정하고 `indicator_ops.py` public surface는 유지

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
- 시장 레짐
  - `use_market_regime_filter`, `use_market_regime_risk_scaling`
  - `market_regime_min_score`, `market_regime_refresh_sec`, `market_regime_top_n`
  - `market_regime_use_fear_greed`, `market_regime_use_etf_flow`
- 운영
  - `enable_discord_alerts`, `discord_webhook`
  - `persist_reconciliation_state`

## 테스트
```bash
python -m pytest -q
```

구조나 문서를 건드렸다면 아래 검증 묶음을 우선 사용합니다.

- `tests/test_docs_references.py`
- `tests/test_text_integrity.py`
- `tests/test_structure_guards.py`
- `tests/test_market_regime_engine.py`
- `tests/test_market_regime_providers.py`
- `tests/test_market_regime_controller_integration.py`
- `tests/test_meta_signal.py`
- `tests/test_trader_surface_parity.py`
- `tests/test_refactor_module_wrappers.py`
- `tests/test_indicator_facade_parity.py`
- `tests/test_trading_parts_facade_parity.py`
- `tests/test_ui_advanced_tab_surface.py`
- `tests/test_trader_order_flows.py`
- `tests/test_order_stability.py`
- `tests/test_plan_implementation_fixes.py`

## 정적 타입 검사
```bash
python -m pyright
```

- 루트 `pyrightconfig.json` 기준으로 VS Code Pylance와 CLI pyright를 동일 설정으로 유지합니다.
- 컨트롤러 믹스인 구조를 수정할 때는 `controllers/_type_support.py`도 함께 확인합니다.

## 로컬 품질 점검
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

- pre-commit 훅은 `tests/test_docs_references.py`, `tests/test_text_integrity.py`, `python -m pyright` 검사를 수행합니다.

## 작업 주의사항
- 주문/체결 로직 수정 시 pending 정리와 lifecycle 전이를 함께 검토합니다.
- TWAP 경로 수정 시 최소주문금액과 잔여 slice 재계산을 검증합니다.
- 외부 시장 데이터 실패는 비치명 경로로 유지하고 internal-only fallback을 보장합니다.
- 문서 수정 시 `README.md`, `CLAUDE.md`, `GEMINI.md`, `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`, `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`, `legacy_wrappers/README.md` 정합성을 함께 맞춥니다.
- `upbit_trader.spec`는 `collect_submodules("upbit_autotrader")` 기반이라 신규 모듈 추가 시 보통 build 설정 변경은 필요 없지만, spec 주석과 배포 문구는 함께 갱신합니다.

## 참고 문서
- 기능 구현 리스크 리뷰: `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`
- 시장 레짐 설계/구현 메모: `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`
- 사용자 문서: `README.md`
- 레거시 래퍼 안내: `legacy_wrappers/README.md`
