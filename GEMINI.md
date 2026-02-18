# Upbit Pro Algo-Trader v3.2

업비트 OpenAPI 기반 자동매매 프로그램 - Gemini AI 가이드

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10+ |
| GUI | PyQt6 |
| API | pyupbit |
| 버전 | v3.2 (2026-02-18) |
| 메인 파일 | `upbit_trader.py` |

---

## 모듈 구성 (핵심)

| 파일 | 역할 |
|------|------|
| `upbit_trader.py` | 앱 초기화, 컨트롤러 결합, 라이프사이클 |
| `upbit_trader_ui_controller.py` | 화면/메뉴/전략 UI |
| `upbit_trader_settings_controller.py` | 설정 저장/로드 |
| `upbit_trader_trading_controller.py` | 진입/청산/주문/체결 |
| `upbit_trader_batch_controller.py` | 일괄 주문/긴급 청산 |
| `upbit_trader_history_controller.py` | 거래 내역/분석/백테스트 |
| `upbit_strategy.py` | 기존 고급 리스크 상태 머신 |
| `upbit_strategy_engine.py` | v3.2 전략 엔진 |
| `upbit_strategy_catalog.py` | v3.2 전략 메타 |
| `upbit_order_service.py` | live 주문 pending/중복 방지 |
| `upbit_paper_order_service.py` | paper 모의 체결 서비스 |
| `upbit_backtester.py` | 전략 레지스트리 기반 백테스트 |

---

## v3.2 핵심 동작

### 1) 전략 엔진
- 모드
  - `single`
  - `ensemble`
- 전략군
  - 추세/모멘텀 4
  - 평균회귀 3
  - 리스크/메타 3

### 2) 페이퍼 트레이딩
- 실제 주문 API 대신 모의 체결
- 수수료/슬리피지 파라미터 지원
- live 체결 루틴과 호환되는 order dict 형식 사용

### 3) 백테스트 확장
- `STRATEGY_REGISTRY` 기반 전략 선택
- 전략별 파라미터 주입 실행

---

## 설정 스키마

`settings_version: 2` 유지 + 신규 키 추가 방식

신규 설정 예:
- `use_strategy_engine`
- `strategy_mode`
- `single_strategy`
- `ensemble_threshold`
- `active_strategies`
- `strategy_weights`
- `paper_trading`
- `paper_fee_bps`
- `paper_slippage_bps`

---

## 테스트

실행:

```bash
python -m pytest -q
```

v3.2 신규:
- `tests/test_strategy_engine_signals.py`
- `tests/test_strategy_engine_ensemble.py`
- `tests/test_paper_order_service.py`

---

## 주의사항

1. 실거래 전 페이퍼 모드로 전략을 검증할 것
2. 주문/체결 변경 시 pending 정리 경로를 반드시 유지할 것
3. 설정 변경은 `settings_version`를 유지한 상태에서 키 추가만 권장

---

## 참고 문서

- `README.md`
- `PROJECT_STRUCTURE_ANALYSIS.md`
- `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
