# Upbit Pro Algo-Trader v3.3.0

업비트 OpenAPI 기반 자동매매 프로그램입니다.

## 주요 기능
- 실시간 자동매매(목표가/MA/리스크 관리)
- 전략 엔진(`single`/`ensemble`) + 전략 카탈로그
- 페이퍼 트레이딩(무로그인 시작, 시드/수수료/슬리피지 설정)
- 주문 pending/lifecycle 상태 추적 + timeout 복구 + manual review 큐
- 리스크 예산 기반 포지션 사이징(ATR/Kelly/Drawdown state, 옵션 기본 OFF)
- 실행 모델(`single_market`/`twap_market`) + 예상 슬리피지 가드(옵션 기본 OFF)
- 메타 시그널 게이트 + 전략 성과 기반 일일 가중치 리밸런싱(옵션 기본 OFF)
- 거래기록 확장 필드(수수료/슬리피지/리스크상태/세션/전략점수)
- 운영 알림(트레이 기본 + Discord 웹훅 옵션)
- 주문 복구 상태 영속화(JSON, 옵션 기본 OFF)

## v3.3.0 업데이트 (2026-02-27)
- `risk/position_sizing.py`: `risk_budget_pct`, `atr_stop_mult`, `kelly_scale`, `drawdown_state` 기반 사이징 추가
- `risk/portfolio_risk.py`: 포트폴리오 리스크 스냅샷(상관집중도 60캔들 기본) + 상태 전이(`normal/caution/defense/halt`)
- `execution/execution_model.py`: 손익분기 비용 계산, 슬리피지 추정, TWAP 스케줄링
- `execution/reconciliation_store.py`: pending/manual/orphan/reserved 상태 저장/복원
- `strategies/meta_signal.py`: 규칙+통계 하이브리드 메타 게이트 + 전략 성과 추적
- 고급 설정 탭에 확장 옵션 UI 추가(리스크/실행/메타/Discord/복구)
- `settings_version=2` 유지, 신규 키 확장(누락 키는 Config 기본값 적용)
- 기존 동작 호환성 유지: 신규 기능 기본값은 모두 `OFF`

## 요구사항
```txt
Python >= 3.10
PyQt6 >= 6.0
pyupbit >= 0.2.30
pandas
numpy
```

## 설치/실행
```bash
pip install -r requirements.txt
python upbit_trader.py
```

## 배포 빌드(PyInstaller)
```bash
pyinstaller --noconfirm --clean upbit_trader.spec
```

- 스펙 파일: `upbit_trader.spec`
- 엔트리포인트: `upbit_trader.py`
- 패키지 수집: `collect_submodules("upbit_autotrader")`

## 프로젝트 구조
```txt
upbit_autotrader/
  app/trader.py
  controllers/
    ui_controller.py
    settings_controller.py
    trading_controller.py
    batch_controller.py
    history_controller.py
  services/
    order_service.py
    paper_order_service.py
    holdings_service.py
    settings_store.py
    security.py
  strategies/
    engine.py
    catalog.py
    legacy_strategy.py
    meta_signal.py
  risk/
    position_sizing.py
    portfolio_risk.py
  execution/
    execution_model.py
    reconciliation_store.py
  core/
    config.py
    entry_filter.py
  runtime/price_thread.py
  analytics/trading_analytics.py
  backtesting/backtester.py
  notifications/notifiers.py
  ui/dialogs.py
  ui/dialog_fallbacks.py
```

루트 래퍼 파일은 정리되어 `upbit_trader.py`만 유지합니다.
기존 호환 래퍼들은 `legacy_wrappers/` 아래 기능별로 보관됩니다.

## 설정/호환성
- 설정 스키마: `settings_version = 2` (DPAPI 암호화 저장)
- 신규 확장 키는 v2 스키마에 추가 저장되며, 이전 저장파일과 혼용 가능
- 거래기록 확장 필드(`fee_krw`, `expected_slippage_bps`, `realized_slippage_bps`, `execution_mode`, `session_id`, `risk_state`, `strategy_score`, `meta_score`)는 optional 처리
- 실거래 전에는 페이퍼 선검증을 권장합니다. (7일 게이트는 운영 정책으로 권장되며 코드에서 강제하지는 않음)

## 테스트
```bash
python -m pytest -q
```

현재 기준:
- `74 passed`

추가된 핵심 테스트:
- `tests/test_position_sizing.py`
- `tests/test_portfolio_risk_engine.py`
- `tests/test_execution_model.py`
- `tests/test_meta_signal.py`

## 프로젝트 문서
- 구조 분석/구현 상태: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 옵션/운영 계획: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- 개발 가이드: `CLAUDE.md`, `GEMINI.md`

## 주의사항
1. 실거래 자금이 사용됩니다.
2. 소액/페이퍼로 먼저 검증 후 운영하세요.
3. 프로그램 종료 시 자동매매는 중지됩니다.
