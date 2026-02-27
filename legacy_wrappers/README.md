# legacy_wrappers

루트에 있던 레거시 호환 래퍼(`upbit_*.py`)를 기능별로 정리한 보관 디렉터리입니다.

## 목적
- 루트 디렉터리 정리
- 내부 코드/테스트의 import 경로를 `upbit_autotrader.*`로 단일화
- 과거 래퍼 코드 이력 보존

## 구조
- `core/`
- `services/`
- `strategies/`
- `controllers/`
- `ui/`
- `runtime/`
- `analytics/`
- `backtesting/`
- `notifications/`
- `indicators/`

현재 실행 엔트리포인트는 루트 `upbit_trader.py`입니다.
