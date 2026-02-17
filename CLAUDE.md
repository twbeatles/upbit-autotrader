# Upbit Pro Algo-Trader v3.1

업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램 - AI 어시스턴트 가이드

---

## 현재 구조 요약

```txt
업비트 자동매매/
├── upbit_trader.py            # 메인 UI + 오케스트레이션
├── upbit_config.py            # 단일 Config 소스 (설정 상수)
├── upbit_strategy.py          # 고급 전략/리스크 로직
├── upbit_dialogs.py           # 긴급청산 포함 UI 다이얼로그
├── upbit_security.py          # DPAPI 암복호화 유틸
├── upbit_settings_store.py    # 설정 저장/로드 + 레거시 마이그레이션
├── upbit_order_service.py     # pending 주문 관리/중복 주문 방지
├── upbit_holdings_service.py  # 계좌 KRW 보유조회 서비스
├── upbit_entry_filter.py      # 진입 점수 게이트
├── upbit_indicators.py        # 고급 지표
├── upbit_backtester.py        # 백테스팅
├── upbit_notifiers.py         # 알림
├── upbit_analytics.py         # 거래 분석
└── tests/test_v31_features.py # v3.1 단위 테스트
```

---

## 핵심 클래스/서비스

### `UpbitProTrader` (`upbit_trader.py`)
- UI 생성/시그널 연결/상태 표시 중심 오케스트레이터
- 주요 상태:
  - `self.universe`
  - `self.trade_history`
  - `self.order_service`
  - `self.pending_orders` (order_service와 공유)

### `UpbitStrategyManager` (`upbit_strategy.py`)
- 목표가/지표 계산
- 쿨다운/시간청산/동적 포지션/MTF/갭/돌파확인

### `UpbitOrderService` (`upbit_order_service.py`)
- 티커 단위 pending 주문 상태 추적
- 중복 주문 차단
- 체결 금액/평단 계산 보조(`get_buy_fill_metrics`, `get_sell_fill_metrics`)
- 부분익절 원가배분(`apply_partial_sell_accounting`)

### `upbit_settings_store.py`
- `load_settings(path)`:
  - v2 DPAPI 복호화
  - 레거시 평문키 로딩
- `save_settings(path, settings)`:
  - `settings_version = 2`
  - `api_credentials` DPAPI 저장
  - 평문 `access_key/secret_key` 제거

---

## 설정 스키마 (v2)

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

- 레거시 평문 키는 마이그레이션 용도로만 읽고, 저장 시 제거
- 복호화 실패 시 키 입력란 비움 + 경고 로그

---

## 매매 로직 핵심 포인트 (v3.1)

### 매수
1. 목표가/MA 조건
2. RSI/MACD/거래량 필터
3. 리스크 체크
4. 진입 점수 필터(UI 켠 경우만)
5. `execute_buy()` → pending 검사 후 주문

### 매도
1. 손절
2. 시간청산
3. 분할익절
4. 트레일링 스톱
5. `execute_sell()` → pending 검사 후 주문

### 주문 체결 처리
- 성공/취소/타임아웃/예외 경로 모두 pending 정리
- 상태 전이:
  - 감시중 -> 주문중 -> 보유중
  - 보유중 -> 매도주문중 -> 매도완료(또는 체결확인실패)
- 일괄 매수/매도도 동일한 서비스 경유 + 체결확인 루틴 사용

---

## 긴급 전량 청산 (중요 변경)

- v3.1부터 긴급청산 대상은 `universe`가 아니라 `계좌 KRW 마켓 전체 보유`
- universe 외부 코인도 주문 대상
- 외부 코인은 전용 체결확인 루틴으로 pending/로그 정리

---

## 수정 가이드

### 새 전략/필터 추가
1. `upbit_strategy.py` 또는 `upbit_entry_filter.py` 확장
2. `upbit_trader.py` UI 입력 + 저장키 연결
3. `tests/test_v31_features.py` 케이스 추가

### 설정 키 추가
1. `upbit_trader.py` `save_settings/load_settings` 연결
2. 필요 시 `upbit_settings_store.py` 마이그레이션 규칙 갱신

### 주문 관련 변경
1. `UpbitOrderService` 중심으로 구현
2. pending 정리 경로 누락 없는지 점검

---

## 파일 수정 위험도

| 파일 | 위험도 | 이유 |
|------|--------|------|
| `upbit_trader.py` | 높음 | UI/실주문/상태전이 중심 |
| `upbit_order_service.py` | 높음 | 중복주문/손익정합 핵심 |
| `upbit_settings_store.py` | 중간 | 보안/호환성 영향 |
| `upbit_security.py` | 중간 | DPAPI 의존 |
| `upbit_config.py` | 낮음 | 상수 중심 |

---

## 운영 주의사항

> 실거래 자금이 사용됩니다.  
> API에 주문 권한이 필요합니다.  
> 소액 테스트 후 운영하세요.  
> 24시간 자동매매는 프로그램 상시 실행이 필요합니다.

---

## Internal Refactor Notes (v3.1+)

- `upbit_trader.py` 역할: 퍼사드/오케스트레이터(초기화 순서, 앱 수명주기, 종료 처리).
- 기능별 분리 모듈:
  - `upbit_trader_ui_controller.py`
  - `upbit_trader_settings_controller.py`
  - `upbit_trader_history_controller.py`
  - `upbit_trader_trading_controller.py`
  - `upbit_trader_batch_controller.py`
  - `upbit_price_thread.py`
  - `upbit_dialog_fallbacks.py`
- 호환성 원칙:
  - 실행 진입점은 계속 `upbit_trader.py`
  - 공개 클래스명 `UpbitProTrader` 유지
  - 설정 저장 포맷(v2 + DPAPI) 유지
