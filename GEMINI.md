# Upbit Pro Algo-Trader v3.1

업비트 OpenAPI 기반 자동매매 프로그램 - Gemini AI 가이드

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10+ |
| GUI | PyQt6 |
| API | pyupbit |
| 버전 | v3.1 (2026-02-13) |
| 메인 파일 | `upbit_trader.py` |

---

## 모듈 구성

| 파일 | 역할 |
|------|------|
| `upbit_trader.py` | UI/오케스트레이션/상태관리 |
| `upbit_config.py` | 단일 설정 상수 |
| `upbit_strategy.py` | 전략/고급 리스크 로직 |
| `upbit_dialogs.py` | 긴급청산 포함 다이얼로그 |
| `upbit_security.py` | DPAPI 암복호화 |
| `upbit_settings_store.py` | 설정 저장소(v2 스키마, 마이그레이션) |
| `upbit_order_service.py` | pending 주문 추적/중복 차단 |
| `upbit_holdings_service.py` | 계좌 KRW 보유조회 |
| `upbit_entry_filter.py` | 진입 점수 게이트 |

---

## 핵심 임포트 예시

```python
from upbit_config import Config
from upbit_strategy import UpbitStrategyManager
from upbit_order_service import UpbitOrderService
from upbit_settings_store import load_settings, save_settings
from upbit_holdings_service import get_account_holdings
from upbit_entry_filter import should_enter_by_score
from upbit_trader import UpbitProTrader
```

---

## v3.1 주요 동작

### 1) API 키 저장
- `upbit_settings_store.save_settings()`에서 DPAPI 암호화 저장
- 파일에는 평문 `access_key`, `secret_key`를 남기지 않음

### 2) 진입 점수 필터
- UI 옵션:
  - `chk_use_entry_scoring`
  - `spin_entry_score_threshold`
- 필터 ON일 때만 임계값 기준 진입 허용

### 3) 긴급 전량 청산 범위
- `universe` 기준이 아닌 계좌 KRW 마켓 전체 보유 기준
- universe 밖 종목도 청산 대상

### 4) 주문 안정성
- `pending_orders` 맵으로 동일 티커 중복 주문 차단
- 체결 성공/취소/타임아웃/예외 경로 모두 pending 정리
- 일괄 매수/매도도 `order_service` 경유 + 체결확인 루틴으로 처리

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

- 레거시 평문 키는 읽기만 지원(마이그레이션 용도)

---

## 테스트

`tests/test_v31_features.py`

- 설정 마이그레이션/복호화 실패 처리
- 진입 점수 게이트
- 주문 중복 방지
- 보유조회 범위
- 부분익절 원가배분 정합성

실행:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 주의사항

1. 실거래 자금이 사용되므로 소액 테스트 후 운영
2. 업비트 API 주문 권한 필요
3. 프로그램 종료 시 자동매매 중지
4. Windows 환경 기준(DPAPI/시작프로그램 레지스트리)
