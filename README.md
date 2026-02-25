# Upbit Pro Algo-Trader v3.2.2

업비트 OpenAPI 기반 자동매매 프로그램입니다.

## 주요 기능
- 실시간 자동매매(목표가/MA/리스크 관리)
- 전략 엔진(`single`/`ensemble`) + 전략 카탈로그
- 페이퍼 트레이딩(무로그인 시작, 시드/수수료/슬리피지 설정)
- 주문 pending/lifecycle 상태 추적 및 중복주문 방지
- 배치 매수/매도, 긴급 청산
- 운영 알림(트레이+로그)

## v3.2.2 리스크/복구 업데이트 (2026-02-25)
- `engine_gate_policy` 추가: `legacy_first` / `engine_only` / `strategy_aware`
- 시작 시 계좌 전체 보유 동기화 + watchlist 외 보유 편입
- timeout 주문 복구: cancel/requery/manual-review queue
- 세션 불일치 terminal 콜백 orphan 이벤트 기록 + 재동기화
- 리스크 계산 확장: 실현 + 미실현 + 외부보유 포트폴리오 기준
- API 호출 중앙 retry/backoff/rate-limit 경로 통합
- 주문 lifecycle 상태머신 도입
- analytics 손익 단위 KRW(`원`) 정합화

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
- 엔트리포인트: `upbit_trader.py` (호환 래퍼)
- 패키지 수집: `collect_submodules("upbit_autotrader")`

## 전략 엔진
- 모드
  - `single`: 단일 전략
  - `ensemble`: 활성 전략 가중 평균 점수
- 평균회귀 전략
  - `rsi_reversion`, `bollinger_reversion`, `zscore_reversion`
- 추세/모멘텀 전략
  - `volatility_breakout`, `donchian_breakout`, `ema_cross_trend`, `time_series_momentum`

## 페이퍼 트레이딩
- `페이퍼 트레이딩 사용` 활성 시 실주문 대신 모의 체결
- `무로그인 시작 허용` 활성 시 API 로그인 없이 시작 가능
- `초기 시드(KRW)` 기본값: 10,000,000

## 보안/설정
- API 키는 Windows DPAPI 암호화 저장(`settings_version=2`)
- 레거시 평문 키는 저장 시 제거

## 프로젝트 문서
- 구조 분석: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 옵션 계획: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- 리스크 리뷰: `AUTO_TRADING_RISK_REVIEW_2026-02-25.md`
- 개발 가이드: `CLAUDE.md`, `GEMINI.md`

## 프로젝트 구조(리팩토링)
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
  core/
    config.py
    entry_filter.py
  runtime/price_thread.py
  analytics/trading_analytics.py
  backtesting/backtester.py
  ui/dialogs.py
  ui/dialog_fallbacks.py

루트의 기존 `upbit_*.py` 파일은 하위 패키지로 포워딩하는 호환 래퍼입니다.
```

## 테스트
```bash
python -m pytest -q
```

주요 테스트:
- `tests/test_order_stability.py`
- `tests/test_trader_order_flows.py`
- `tests/test_strategy_engine_signals.py`
- `tests/test_strategy_engine_ensemble.py`
- `tests/test_paper_order_service.py`
- `tests/test_reported_risk_fixes.py`
- `tests/test_strategy_engine_gate_policy.py`
- `tests/test_order_reconciliation_recovery.py`
- `tests/test_startup_position_sync.py`
- `tests/test_risk_limits_portfolio_scope.py`
- `tests/test_analytics_units_and_types.py`
- `tests/test_docs_references.py`

## 변경 이력
### v3.2.2 (2026-02-25)
- 리스크/정합성 복구 기능 일괄 반영
- 계좌 동기화/주문 복구/운영 알림 강화
- 문서 드리프트 해소 문서 2종 추가

### v3.2.1 (2026-02-20)
- 배치/긴급청산 session_id 안정화
- 체결/히스토리/페이퍼 모드 안정화

### v3.2 (2026-02-18)
- 전략 엔진 및 페이퍼 트레이딩 도입

## 주의사항
1. 실거래 자금이 사용됩니다.
2. 소액/페이퍼로 먼저 검증 후 운영하세요.
3. 프로그램 종료 시 자동매매는 중지됩니다.
