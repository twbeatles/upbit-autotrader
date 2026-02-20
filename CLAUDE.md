# Upbit Pro Algo-Trader v3.2

업비트 OpenAPI 기반 자동매매 프로그램 - Claude/Codex 작업 가이드

---

## 현재 구조 요약

```txt
업비트 자동매매/
├── upbit_trader.py                       # 퍼사드/오케스트레이터
├── upbit_trader_ui_controller.py         # UI/메뉴/프리셋
├── upbit_trader_settings_controller.py   # 설정 저장/로드/시스템 설정
├── upbit_trader_trading_controller.py    # 실시간 매매/주문/체결
├── upbit_trader_batch_controller.py      # 일괄 매수/매도/긴급청산
├── upbit_trader_history_controller.py    # 거래내역/분석/백테스트
├── upbit_strategy.py                     # 기존 고급 전략/리스크 상태
├── upbit_strategy_engine.py              # v3.2 전략 엔진
├── upbit_strategy_catalog.py             # v3.2 전략 메타/기본값
├── upbit_order_service.py                # live 주문 추적/중복 방지
├── upbit_paper_order_service.py          # v3.2 paper 주문 서비스
├── upbit_settings_store.py               # v2 설정 + DPAPI 키 저장
├── upbit_security.py                     # DPAPI 유틸
├── upbit_backtester.py                   # 전략 레지스트리 기반 백테스트
├── PROJECT_STRUCTURE_ANALYSIS.md         # 구조 분석 문서
├── STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md
└── tests/
```

---

## 핵심 포인트

### 1) 호환성 정책
- 진입점: `python upbit_trader.py` 유지
- 공개 클래스: `UpbitProTrader` 유지
- 설정 스키마: `settings_version = 2` 유지 (키 추가만 허용)

### 2) 주문 경로
- Live: `UpbitOrderService`
- Paper: `UpbitPaperOrderService`
- 컨트롤러에서는 `_place_buy_order`, `_place_sell_order`로 라우팅

### 3) 전략 실행
- 엔진 비활성 시 기존 필터 로직 유지
- 엔진 활성 시
  - `single`: 단일 전략
  - `ensemble`: 가중 평균 점수
- 메타 리스크
  - `regime_filter`, `drawdown_guard`, `volatility_targeting`

### 4) 백테스트
- `upbit_backtester.py`의 `STRATEGY_REGISTRY`를 통해 전략 선택/파라미터 주입 실행

---

## 설정 키(v3.2 추가)
- `use_strategy_engine`
- `strategy_mode`
- `single_strategy`
- `ensemble_threshold`
- `active_strategies`
- `strategy_weights`
- `use_volatility_targeting`
- `target_vol_pct`
- `use_regime_filter`
- `regime_min_adx`
- `use_drawdown_guard`
- `drawdown_guard_pct`
- `max_consecutive_losses`
- `paper_trading`
- `paper_fee_bps`
- `paper_slippage_bps`

## 설정 키(v3.2.1 추가)
- `paper_allow_without_login`
- `paper_seed_krw`

## 설정 키(v3.2.1 추가)
- `paper_allow_without_login`
- `paper_seed_krw`

---

## 테스트

```bash
python -m pytest -q
```

v3.2 신규 테스트:
- `tests/test_strategy_engine_signals.py`
- `tests/test_strategy_engine_ensemble.py`
- `tests/test_paper_order_service.py`

v3.2.1 안정화 테스트:
- `tests/test_reported_risk_fixes.py`

v3.2.1 안정화 테스트:
- `tests/test_reported_risk_fixes.py`

---

## 작업 시 주의사항
- 주문/체결 코드 수정 시 pending 정리 경로 누락 금지
- `paper mode`에서는 live API 주문 함수가 호출되지 않아야 함
- `upbit_analytics.py`는 기록 키(`timestamp` vs `datetime`) 불일치 위험이 있어 수정 시 주의

## v3.2.1 반영 요약 (2026-02-20)
- 배치 체결확인 경로(`execute_batch_buy`, `execute_batch_sell`, `execute_emergency_close`)에서 `session_id` 전달 누락 보완
- 전량 매도 체결 후 상태를 `매도완료`가 아닌 `감시중`으로 복귀해 재진입 루프 정합성 확보
- `upbit_analytics.py`는 `timestamp` 우선, `datetime` fallback 방식으로 집계 키 정규화 적용
- 페이퍼 모드 무로그인 시작 및 초기 시드 정책(기본 10,000,000 KRW) 반영

## v3.2.1 반영 요약 (2026-02-20)
- 배치 체결확인 경로(`execute_batch_buy`, `execute_batch_sell`, `execute_emergency_close`)에서 `session_id` 전달 누락 보완
- 전량 매도 체결 후 상태를 `매도완료`가 아닌 `감시중`으로 복귀해 재진입 루프 정합성 확보
- `upbit_analytics.py`는 `timestamp` 우선, `datetime` fallback 방식으로 집계 키 정규화 적용
- 페이퍼 모드 무로그인 시작 및 초기 시드 정책(기본 10,000,000 KRW) 반영

---

## 참고 문서
- 구조 분석: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 상세: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- 사용자 문서: `README.md`
