# Upbit Pro Algo-Trader 구현 리스크 리뷰

작성 기준일: 2026-03-08  
후속 반영 메모 업데이트: 2026-03-25

## 목적

이 문서는 자동매매 핵심 경로에서 지켜야 할 안정성 원칙과 주요 리스크를 정리한다. 현재 코드베이스는 시장 레짐 기능과 컨트롤러 분할 리팩토링까지 반영된 상태이며, 아래 항목은 그 기준으로 유지한다.

## 보호해야 하는 외부 계약

- 실행 진입점은 `python upbit_trader.py`로 유지한다.
- 공개 메인 클래스는 `upbit_autotrader.app.trader.UpbitProTrader`다.
- 설정 스키마는 `settings_version = 2`를 유지한다.
- `upbit_trader.spec`는 `collect_submodules("upbit_autotrader")` 기반 빌드 경로를 유지한다.
- 신규 기능은 기본값 `OFF` 정책을 유지한다.
- widget attribute 이름, legacy wrapper import 경로, trade history 저장 포맷은 호환성을 깨지 않도록 유지한다.

## 현재 구조에서 중요한 리스크

### 1. 주문/체결 경로

- 위험 구간: `controllers/trading_parts/order_api_ops.py`, `execution_flow_ops.py`, `lifecycle_ops.py`
- 핵심 리스크:
  - pending 상태와 실제 주문 상태 불일치
  - timeout 처리 중 중복 주문 또는 reserved KRW 누수
  - TWAP fallback 시 최소 주문 금액 위반
- 방어 원칙:
  - 주문 결과 변경은 lifecycle 전이와 함께 검토
  - timeout 복구, manual review, reconciliation state 저장 경로를 같이 확인
  - 실거래와 페이퍼 경로를 동시에 회귀 검증

### 2. 시장 레짐 외부 데이터

- 위험 구간: `market_regime/providers.py`, `runtime/market_regime_thread.py`, `controllers/trading_parts/market_regime_ops.py`
- 핵심 리스크:
  - 외부 API 실패가 매매 전체를 차단하는 문제
  - stale 데이터가 과도하게 오래 유지되는 문제
  - 필터와 리스크 스케일링이 서로 다른 snapshot을 참조하는 문제
- 방어 원칙:
  - 외부 fetch 실패는 internal-only fallback으로 degrade
  - 초기 fetch 전에는 중립값(`50 / neutral / 1.0`) 사용
  - market regime update는 thread에서 계산하고 controller는 마지막 성공 snapshot만 읽음

### 3. facade + helper 분리 구조

- 위험 구간: `app/trader.py`, `controllers/trading_controller.py`, `controllers/ui_controller.py`, `controllers/ui_sections.py`
- 핵심 리스크:
  - facade public surface 누락
  - 위젯 속성명 변경으로 settings/preset/history 동작이 깨지는 문제
  - helper 모듈 분리 중 import 경로가 바뀌어 legacy wrapper가 깨지는 문제
- 방어 원칙:
  - facade 파일은 공개 메서드 surface만 유지하고 구현은 helper에 위임
  - `tests/test_trader_surface_parity.py`, `tests/test_refactor_module_wrappers.py`, `tests/test_indicator_facade_parity.py`, `tests/test_trading_parts_facade_parity.py`, `tests/test_ui_advanced_tab_surface.py`를 함께 본다
  - 구조 가드 한도는 `tests/test_structure_guards.py`에 맞춘다

### 4. 설정/거래기록 호환성

- 위험 구간: `core/config.py`, `controllers/settings_field_specs.py`, `settings_controller.py`, `history_controller.py`
- 핵심 리스크:
  - 신규 키 누락으로 저장/로드 불일치
  - optional trade history field가 CSV export나 analytics 로더를 깨는 문제
  - 로컬 파일이 repo에 섞이는 문제
- 방어 원칙:
  - 설정 추가 시 `Config`, `settings_field_specs`, UI builder를 같이 수정
  - trade history extra field는 optional로만 추가
  - `.gitignore`에 `upbit_presets.json`, `analytics_report.html`, `backtest_report.html`, `trade_history_*.csv`까지 포함

### 5. 문서/spec 정합성

- 위험 구간: `README.md`, `CLAUDE.md`, `GEMINI.md`, `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`, `legacy_wrappers/README.md`, `upbit_trader.spec`
- 핵심 리스크:
  - 문서가 구 구조를 설명해 개발자가 잘못된 수정 지점을 선택하는 문제
  - 누락 문서로 `tests/test_docs_references.py`가 실패하는 문제
  - spec 설명이 오래되어 신규 모듈이 build에서 누락된다고 오해하는 문제
- 방어 원칙:
  - 가이드 문서에는 `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`, `legacy_wrappers/README.md`를 항상 명시
  - 구조 변경 시 문서와 spec 주석을 함께 갱신
  - 문서 변경 후 `tests/test_docs_references.py`와 `tests/test_text_integrity.py`를 우선 실행

## 권장 검증 순서

1. `python -m pytest -q tests/test_docs_references.py tests/test_text_integrity.py`
2. `python -m pytest -q tests/test_structure_guards.py`
3. `python -m pytest -q tests/test_market_regime_engine.py tests/test_market_regime_providers.py tests/test_market_regime_controller_integration.py tests/test_meta_signal.py`
4. `python -m pytest -q tests/test_trader_order_flows.py tests/test_order_stability.py tests/test_plan_implementation_fixes.py`
5. `python -m pytest -q tests/test_trader_surface_parity.py tests/test_refactor_module_wrappers.py tests/test_indicator_facade_parity.py tests/test_trading_parts_facade_parity.py tests/test_ui_advanced_tab_surface.py`
6. `python -m pyright`
7. `pre-commit run --all-files`

## 관련 문서

- 사용자 문서: `README.md`
- 개발 가이드: `CLAUDE.md`, `GEMINI.md`
- 시장 레짐 설계/구현 메모: `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`
- 레거시 래퍼 안내: `legacy_wrappers/README.md`
