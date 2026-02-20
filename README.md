# Upbit Pro Algo-Trader v3.2

업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 주요 기능

### 기본/안정화 기능
- 변동성 돌파 + MA 필터 + 트레일링 스탑 + 손절
- RSI/MACD/거래량 필터
- 진입 점수 필터
- 티커 단위 pending 주문 맵 기반 중복 주문 방지
- 일괄 매수/매도 및 긴급 청산
- API 키 DPAPI 암호화 저장 (`settings_version: 2`)

### v3.2 신규 기능
- 전략 엔진 추가 (`single` / `ensemble`)
- 전략 카탈로그 추가 (`upbit_strategy_catalog.py`)
- 10개 전략 옵션(추세/모멘텀/평균회귀/리스크 메타)
- 페이퍼 트레이딩 모드 추가 (`upbit_paper_order_service.py`)
- 전략 엔진 설정 UI 추가
  - 실행모드, 단일전략 선택, 앙상블 임계값
  - 활성 전략 목록, 전략 가중치
  - 변동성 타게팅, 레짐 필터, 드로우다운 가드
- 백테스트 전략 레지스트리/선택 실행 지원

### v3.2.1 안정화 업데이트 (2026-02-20)
- 배치/긴급청산 체결확인 콜백에 `session_id` 전달 경로를 보강하여 stale callback 오염 가능성 완화
- 전량 매도 체결 후 상태를 `감시중`으로 복귀시켜 자동 재진입 루프 정상화
- 분석 모듈에서 거래일시 키를 `timestamp` 우선(`datetime` fallback)으로 정규화
- 거래량 필터 평균 계산을 `volume_period` 윈도우 기준으로 정합화
- 히스토리 로딩/표시/오늘기록삭제 경로에 레거시/오염 레코드 방어 처리 추가
- 페이퍼 모드에 무로그인 시작 옵션 및 초기 시드(`paper_seed_krw`) 설정 추가
- Universe 외부 자산 배치 청산 시 평균단가 기반 손익 기록 지원

---

## 요구사항

```txt
Python >= 3.10
PyQt6 >= 6.0
pyupbit >= 0.2.30
pandas
numpy
```

---

## 설치 및 실행

### 1) 소스코드 실행
```bash
pip install -r requirements.txt
python upbit_trader.py
```

### 2) 실행 파일
- `dist/UpbitTrader.exe` 실행

---

## v3.2 전략 엔진 개요

### 실행 모드
- `single`: 선택한 전략 1개로 진입 판정
- `ensemble`: 활성 전략들의 가중 평균 점수 기반 판정

### 전략 옵션
- 추세/모멘텀
  - `volatility_breakout`
  - `donchian_breakout`
  - `ema_cross_trend`
  - `time_series_momentum`
- 평균회귀
  - `rsi_reversion`
  - `bollinger_reversion`
  - `zscore_reversion`
- 리스크/메타
  - `volatility_targeting`
  - `regime_filter`
  - `drawdown_guard`
- 연구전용
  - `pairs_trading_research` (실주문 미연결)

---

## 페이퍼 트레이딩

- UI에서 `페이퍼 트레이딩 사용` 활성화 시 실주문 대신 모의 체결 수행
- `무로그인 시작 허용` 활성화 시 API 로그인 없이 페이퍼 모드 시작 가능
- `초기 시드(KRW)`로 무로그인 시작 시 모의 잔고 초기값 지정 가능 (기본 10,000,000 KRW)
- 수수료(bps), 슬리피지(bps) 조정 가능
- 기존 체결확인/거래기록 루틴과 호환되도록 order dict 형식 유지

---

## 보안 및 설정 스키마

API 키는 v3.1부터 Windows DPAPI로 암호화 저장됩니다.

```json
{
  "settings_version": 2,
  "api_credentials": {
    "storage": "dpapi",
    "access_enc": "<base64>",
    "secret_enc": "<base64>"
  }
}
```

- 레거시 `access_key`, `secret_key`는 마이그레이션 용도로만 읽고 저장 시 제거됩니다.

---

## 프로젝트 문서

- 구조 분석: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 설계/옵션: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- AI 가이드: `CLAUDE.md`, `GEMINI.md`

---

## 파일 구조 (핵심)

```txt
업비트 자동매매/
├── upbit_trader.py
├── upbit_trader_ui_controller.py
├── upbit_trader_settings_controller.py
├── upbit_trader_trading_controller.py
├── upbit_trader_batch_controller.py
├── upbit_trader_history_controller.py
├── upbit_strategy.py
├── upbit_strategy_engine.py          # v3.2 전략 엔진
├── upbit_strategy_catalog.py         # v3.2 전략 카탈로그
├── upbit_order_service.py
├── upbit_paper_order_service.py      # v3.2 페이퍼 주문 서비스
├── upbit_backtester.py
├── upbit_settings_store.py
├── upbit_security.py
├── PROJECT_STRUCTURE_ANALYSIS.md     # v3.2 문서
├── STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md
└── tests/
```

---

## 테스트

```bash
python -m pytest -q
```

현재 기준 주요 테스트 파일:
- `tests/test_v31_features.py`
- `tests/test_order_stability.py`
- `tests/test_performance_optimizations.py`
- `tests/test_trader_order_flows.py`
- `tests/test_strategy_engine_signals.py` (v3.2)
- `tests/test_strategy_engine_ensemble.py` (v3.2)
- `tests/test_paper_order_service.py` (v3.2)
- `tests/test_reported_risk_fixes.py` (v3.2.1)

---

## 주의사항

1. 실거래 자금이 사용됩니다. 소액 테스트 후 운영하세요.
2. 업비트 API 주문 권한이 필요합니다.
3. 프로그램 종료 시 자동매매는 중지됩니다.
4. 페이퍼 모드 여부를 항상 확인 후 실행하세요.

---

## 변경 이력

### v3.2.1 (2026-02-20)
- 세션 안정성: 배치/긴급청산 체결확인 콜백의 `session_id` 전달 누락 보강
- 상태 전이: 전량 매도 후 `매도완료` 고착 대신 `감시중` 복귀
- 분석 정확도: `timestamp` 우선 집계로 일/월 리포트 누락 리스크 완화
- 필터 정합성: 거래량 평균 계산을 `volume_period` 기준으로 수정
- 히스토리 내구성: malformed/legacy 레코드 방어 로직 추가
- 페이퍼 UX: 무로그인 시작 허용 + 초기 시드 설정(`paper_allow_without_login`, `paper_seed_krw`)
- 외부 청산 기록: Universe 외부 자산 청산 손익 기록 개선

### v3.2 (2026-02-18)
- 전략 엔진(`single`/`ensemble`) 추가
- 전략 카탈로그/전략 메타 타입 추가
- 페이퍼 트레이딩 모드 및 비용모델(수수료/슬리피지) 추가
- UI/설정/프리셋에 전략 엔진 키 추가
- 백테스트 전략 레지스트리 및 선택 실행 지원
- 구조/전략 문서 2종 추가
- 전략 엔진/페이퍼 서비스 테스트 추가

### v3.1 (2026-02-13)
- API 키 DPAPI 암호화 저장 도입 (`settings_version: 2`)
- 긴급청산 범위: 계좌 KRW 마켓 전체 보유
- pending 주문 맵 기반 중복 주문 방지
- 일괄 매수/매도 주문을 `order_service` 경유로 통합
- settings/order/holdings 서비스 모듈 분리
