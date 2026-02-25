# Upbit Pro Algo-Trader v3.2.2

Claude/Codex 작업 가이드 문서입니다.

## 구조 요약
```txt
upbit_autotrader/
  app/trader.py                       # 퍼사드/오케스트레이터
  controllers/                        # UI/설정/매매/배치/히스토리 컨트롤러
  services/                           # 주문/보유/설정저장/보안 서비스
  strategies/                         # 전략 엔진/카탈로그/레거시 전략
  core/                               # config/entry_filter
  runtime/                            # price thread
  analytics/                          # 분석 리포트
  backtesting/                        # 백테스터
  ui/                                 # dialogs/fallbacks

루트 `upbit_*.py` 파일은 하위 패키지 모듈을 재노출하는 호환 래퍼입니다.
```

## 호환성 원칙
- 실행 진입점 유지: `python upbit_trader.py`
- 공개 클래스 유지: `UpbitProTrader`
- 설정 스키마: `settings_version = 2`
- 배포 스펙 유지: `upbit_trader.spec`

## 핵심 정책
### 주문 경로
- live: `UpbitOrderService`
- paper: `UpbitPaperOrderService`
- 컨트롤러 라우팅: `_place_buy_order`, `_place_sell_order`

### 전략 엔진/진입 게이트
- `strategy_mode`: `single` / `ensemble`
- `engine_gate_policy`
  - `legacy_first`
  - `engine_only`
  - `strategy_aware`

### 동기화/복구
- 시작 시 계좌 전체 보유 동기화(account-wide)
- timeout 주문: cancel/requery/manual-review queue
- session mismatch terminal 이벤트: orphan 기록 + 재동기화

### 리스크 계산
- `portfolio_pnl = realized + unrealized`
- 옵션에 따라 external holdings 반영
- holdings limit는 account-wide 기준

## 설정 키(주요)
- 엔진/전략
  - `use_strategy_engine`
  - `strategy_mode`
  - `single_strategy`
  - `ensemble_threshold`
  - `active_strategies`
  - `strategy_weights`
  - `engine_gate_policy`
- 리스크/복구
  - `enable_account_wide_sync`
  - `risk_include_unrealized`
  - `risk_include_external_holdings`
  - `manual_review_on_timeout`
  - `price_feed_stale_sec`
- 페이퍼
  - `paper_trading`
  - `paper_allow_without_login`
  - `paper_seed_krw`
  - `paper_fee_bps`
  - `paper_slippage_bps`

## 테스트
```bash
python -m pytest -q
```

빌드 확인(선택):
```bash
pyinstaller --noconfirm --clean upbit_trader.spec
```

신규 검증 파일:
- `tests/test_strategy_engine_gate_policy.py`
- `tests/test_order_reconciliation_recovery.py`
- `tests/test_startup_position_sync.py`
- `tests/test_risk_limits_portfolio_scope.py`
- `tests/test_analytics_units_and_types.py`
- `tests/test_docs_references.py`

## 작업 주의사항
- 주문/체결 수정 시 pending 정리와 lifecycle 전이 함께 검토
- paper 모드에서 live API 호출 금지
- 리스크 계산 변경 시 외부보유/미실현 포함 여부를 분리 검증

## 참고 문서
- 구조 분석: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 상세: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- 리스크 리뷰: `AUTO_TRADING_RISK_REVIEW_2026-02-25.md`
- 사용자 문서: `README.md`
