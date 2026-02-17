# Upbit Pro Algo-Trader v3.1

업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 주요 기능

### 트레이딩 전략
- 변동성 돌파 전략 (K값 기반 목표가)
- MA5 추세 필터
- RSI, MACD, 거래량 필터
- 트레일링 스톱 / 손절
- 분할 익절 (3%/5%/8%)
- 진입 점수 필터 (UI 토글 + 임계값 설정)

### 고급 기능 (v3.x)
- 재진입 쿨다운
- 시간 기반 청산
- 동적 포지션 사이징 (Anti-Martingale)
- 다중 시간프레임(MTF) 분석
- 갭 분석 기반 K값 자동 조정
- 돌파 확인(N틱 유지)

### v3.1 핵심 개선
- API 키 DPAPI 암호화 저장 (`upbit_settings.json` 평문 키 미저장)
- 긴급 전량 청산 범위를 계좌 KRW 마켓 전체 보유로 확장
- 티커 단위 pending 주문 맵으로 중복 주문 방지
- 일괄 매수/매도도 `order_service` 경유 + 체결확인 루틴으로 통합
- 설정/주문/보유조회 로직 서비스 모듈 분리

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

### 방법 1: 실행 파일
1. `dist/UpbitTrader.exe` 실행
2. 최초 실행 시 `upbit_settings.json` 자동 생성

### 방법 2: 소스코드 실행
```bash
pip install -r requirements.txt
python upbit_trader.py
```

---

## 보안 및 설정 스키마 (v3.1)

v3.1부터 API 키는 Windows DPAPI로 암호화되어 저장됩니다.

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

- 레거시 평문 키(`access_key`, `secret_key`)는 읽기만 지원하며 저장 시 제거됩니다.
- 로드 우선순위: `v2(api_credentials) > legacy(access_key/secret_key)`.
- 복호화 실패 시 입력란은 비워지고 경고 로그가 남습니다.

---

## 운영 가이드

### 기본 순서
1. 업비트 Open API 키 입력
2. `시스템 접속`으로 연결 확인
3. 감시 코인 입력 (`KRW-BTC,KRW-ETH` 형식)
4. 전략/리스크 파라미터 조정
5. 자동매매 시작

### 진입 점수 필터
- `진입 점수 필터 사용` 체크 시에만 동작
- 임계값(`0~100`) 미만이면 진입 보류
- 보류 로그에 점수와 주요 근거가 함께 기록

### 긴급 전량 청산
- 고급 설정 탭의 `전량 긴급 청산` 버튼 사용
- 대상은 `현재 universe`가 아니라 `계좌 KRW 마켓 전체 보유`입니다.
- universe 밖 종목도 긴급 청산 주문 대상으로 포함됩니다.

### 일괄 매수/매도
- 일괄 주문도 직접 API 호출이 아니라 `order_service`를 통해 접수됩니다.
- universe 종목은 기존 체결확인/상태갱신 루틴을 재사용합니다.
- universe 밖 종목은 외부 체결확인 루틴으로 pending 정리와 거래기록을 처리합니다.

---

## 파일 구조 (v3.1)

```txt
업비트 자동매매/
├── upbit_trader.py            # 메인 UI + 오케스트레이션
├── upbit_config.py            # 설정 상수
├── upbit_strategy.py          # 전략 로직
├── upbit_dialogs.py           # 긴급청산/기타 다이얼로그 모듈
├── upbit_security.py          # DPAPI 암복호화
├── upbit_settings_store.py    # 설정 저장/마이그레이션
├── upbit_order_service.py     # 주문 중복 방지/상태 추적
├── upbit_holdings_service.py  # 계좌 보유조회
├── upbit_entry_filter.py      # 진입 점수 게이트
├── upbit_indicators.py        # 고급 기술지표
├── upbit_backtester.py        # 백테스팅 엔진
├── upbit_notifiers.py         # 알림
├── upbit_analytics.py         # 거래 분석
├── upbit_settings.json        # 사용자 설정
├── upbit_presets.json         # 프리셋
├── trade_history.json         # 거래 내역
├── upbit_trader.spec          # PyInstaller 빌드 스펙
└── tests/
    └── test_v31_features.py   # v3.1 단위 테스트
```

---

## 트러블슈팅

**Q: `ModuleNotFoundError`가 발생합니다.**  
A: `upbit_trader.py`와 같은 폴더에 모듈 파일(`upbit_config.py`, `upbit_strategy.py`, `upbit_dialogs.py` 등)이 모두 존재하는지 확인하세요.

**Q: API 키가 저장되지 않거나 복원되지 않습니다.**  
A: v3.1은 Windows DPAPI를 사용합니다. Windows 사용자 컨텍스트가 달라지면 복호화가 실패할 수 있습니다.

**Q: 긴급 청산 대상이 예상과 다릅니다.**  
A: v3.1부터 긴급 청산은 계좌 KRW 마켓 전체 보유를 기준으로 동작합니다.

---

## 변경 이력

### v3.1 (2026-02-13)
- API 키 DPAPI 암호화 저장 도입 (`settings_version: 2`)
- 진입 점수 UI 토글/임계값 적용 완료
- 긴급청산 범위: 계좌 KRW 마켓 전체로 확장
- pending 주문 맵 기반 중복 주문 방지
- 일괄 매수/매도 주문을 `order_service` + 체결확인 경로로 통합
- settings/order/holdings 서비스 모듈 분리

### v3.0 (2026-02-07)
- config/strategy/dialogs 모듈 분리
- 고급 리스크 관리(쿨다운/시간청산/동적포지션)
- 고급 알고리즘(MTF/갭/돌파확인)

### v2.7 이하
- 거래 분석/백테스트/지표 확장
- 분할 익절/일괄 매도·매수/거래 히스토리 기능 추가

### v3.1+ (Internal Refactor)
- `upbit_trader.py` is now a facade/orchestrator with lifecycle and startup wiring.
- responsibilities are split into:
  - `upbit_trader_ui_controller.py`
  - `upbit_trader_settings_controller.py`
  - `upbit_trader_history_controller.py`
  - `upbit_trader_trading_controller.py`
  - `upbit_trader_batch_controller.py`
  - `upbit_price_thread.py`
  - `upbit_dialog_fallbacks.py`
- Compatibility policy:
  - entrypoint stays `python upbit_trader.py`
  - `UpbitProTrader` class name is unchanged
  - settings schema (`settings_version: 2`, DPAPI credentials) is unchanged
