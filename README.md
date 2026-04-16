# Upbit Pro Algo-Trader

업비트 OpenAPI 기반 자동매매 프로그램입니다. 공개 엔트리포인트는 `upbit_trader.py`, 메인 윈도우 퍼사드는 `upbit_autotrader.app.trader.UpbitProTrader`입니다.

## 주요 기능
- 실시간 자동매매(목표가/이평선 기반 기본 게이트 + 전략 엔진)
- 전략 엔진(`single` / `ensemble`)과 전략 카탈로그
- 시장 레짐 점수(`market_regime_score`) 기반 진입 필터와 주문 금액 스케일링
- 메타 시그널 게이트 + 전략 성과 기반 일일 가중치 리밸런싱
- 리스크 예산 기반 포지션 사이징(ATR/Kelly/Drawdown state)
- 실행 모델(`single_market` / `twap_market`)과 예상 슬리피지 가드
- 주문 pending/lifecycle 추적, timeout 복구, manual review 큐
- 페이퍼 트레이딩(무로그인 시작, 시드/수수료/슬리피지 설정)
- 거래기록 확장 필드(수수료/슬리피지/리스크상태/세션/전략점수/시장레짐)
- 트레이 알림 + Discord 웹훅 옵션

모든 확장 기능은 기존 호환성 원칙대로 기본값이 `OFF`입니다. 초기 market regime fetch 전에는 중립값(`score=50`, `label=neutral`, `risk_multiplier=1.0`)을 사용합니다.

## 요구사항
```txt
Python >= 3.10
PyQt6 >= 6.0
pyupbit >= 0.2.30
pandas
numpy
requests
```

## 설치/실행
```bash
pip install -r requirements.txt
python upbit_trader.py
```

## 배포 빌드(PyInstaller)
```bash
pyinstaller --noconfirm --clean upbit_trader.spec
pyinstaller --noconfirm --clean --distpath upbit_dist --workpath upbit_build upbit_trader.spec
```

- 스펙 파일: `upbit_trader.spec`
- 엔트리포인트: `upbit_trader.py`
- 패키지 수집: `collect_submodules("upbit_autotrader")`
- `app/bootstrap_ops.py`, `app/runtime_ops.py`, `controllers/trading_parts/*`, `controllers/ui_parts/*`, `market_regime/*`도 자동 수집됩니다.
- `dist/`, `build/`, `upbit_dist/`, `upbit_build/`는 빌드 산출물 경로로 `.gitignore`에 포함됩니다.

## 프로젝트 구조
```txt
upbit_autotrader/
  app/
    trader.py                  # 공개 퍼사드
    bootstrap_ops.py           # 초기 상태/로거/타이머 설정
    runtime_ops.py             # price thread / market regime thread 수명주기
  controllers/
    ui_controller.py           # UI 조립 퍼사드
    ui_sections.py             # 고급 설정 탭 조합
    settings_controller.py
    trading_controller.py      # 매매 퍼사드
    batch_controller.py
    history_controller.py
    _type_support.py
    trading_parts/
      indicator_ops.py
      indicator_parts/
      account_ops.py
      lifecycle_ops.py
      order_api_ops.py
      execution_flow_ops.py
      signal_ops.py
      strategy_config_ops.py
      market_regime_ops.py
      risk_ops.py
      session_ops.py
      manual_review_ops.py
    ui_parts/
      layout_ops.py
      dashboard_ops.py
      strategy_tab_ops.py
      menu_tray_ops.py
      preset_ops.py
      advanced_tab/
  services/
  strategies/
  risk/
  execution/
  market_regime/
    engine.py
    providers.py
  runtime/
    price_thread.py
    market_regime_thread.py
  analytics/
  backtesting/
  notifications/
  ui/
```

루트에서는 `upbit_trader.py`만 실행 진입점으로 유지합니다. 기존 호환 래퍼들은 `legacy_wrappers/` 아래 기능별로 보관되며 신규 코드의 기준 경로는 `upbit_autotrader.*`입니다.

## 설정/로컬 파일
- 설정 스키마: `settings_version = 2` (DPAPI 암호화 저장)
- 로컬 상태 파일: `upbit_settings.json`, `upbit_presets.json`, `trade_history.json`, `reconciliation_state.json`, `strategy_performance.json`
- 사용자 생성 산출물: `analytics_report.html`, `backtest_report.html`, `trade_history_*.csv`
- 거래기록 확장 필드는 optional 처리되며 기존 CSV/JSON 로더와 호환됩니다.
- 실거래 전에는 페이퍼 트레이딩으로 선검증하는 것을 권장합니다.

## 테스트
```bash
python -m pytest -q
```

최근 정합성 점검 시 핵심 회귀 묶음으로 아래 테스트를 사용합니다.

- `tests/test_docs_references.py`
- `tests/test_text_integrity.py`
- `tests/test_structure_guards.py`
- `tests/test_market_regime_engine.py`
- `tests/test_market_regime_providers.py`
- `tests/test_market_regime_controller_integration.py`
- `tests/test_meta_signal.py`
- `tests/test_trader_order_flows.py`
- `tests/test_order_stability.py`
- `tests/test_plan_implementation_fixes.py`
- `tests/test_trader_surface_parity.py`
- `tests/test_refactor_module_wrappers.py`
- `tests/test_indicator_facade_parity.py`
- `tests/test_trading_parts_facade_parity.py`
- `tests/test_ui_advanced_tab_surface.py`

## 정적 타입 검사
```bash
python -m pyright
```

- 루트 `pyrightconfig.json`으로 VS Code Pylance와 CLI pyright 기준을 동일하게 맞춥니다.
- 컨트롤러 믹스인/Qt 동적 속성 타입 지원은 `upbit_autotrader/controllers/_type_support.py`에서 관리합니다.

## 프로젝트 문서
- 기능 구현 리스크 리뷰: `IMPLEMENTATION_RISK_REVIEW_2026-04-16.md`
- 시장 레짐 설계 및 구현 메모: `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`
- 개발 가이드: `CLAUDE.md`, `GEMINI.md`
- 레거시 래퍼 안내: `legacy_wrappers/README.md`

## 로컬 품질 가드 (pre-commit)
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

- 커밋 시 `tests/test_docs_references.py`, `tests/test_text_integrity.py`, `python -m pyright` 검사가 자동 실행됩니다.

## 주의사항
1. 실거래 자금이 사용됩니다.
2. 소액 또는 페이퍼 계정으로 먼저 검증 후 운영하세요.
3. 프로그램 종료 시 자동매매는 중지됩니다.
