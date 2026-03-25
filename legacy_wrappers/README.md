# legacy_wrappers

루트에 있던 레거시 호환 래퍼(`upbit_*.py`)를 기능별로 정리한 보관 디렉터리입니다.

## 목적
- 루트 디렉터리 정리
- 내부 코드/테스트의 import 경로를 `upbit_autotrader.*`로 단일화
- 과거 래퍼 코드 이력 보존
- 신규 코드와 문서는 이 디렉터리를 참조하지 않고 `upbit_autotrader.*`와 루트 `upbit_trader.py`만 사용

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
PyInstaller 스펙(`upbit_trader.spec`)도 `upbit_autotrader` 패키지만 기준으로 수집합니다.
현재 본 코드베이스의 실구현은 `upbit_autotrader.app.bootstrap_ops` / `runtime_ops`, `controllers/trading_parts`, `controllers/ui_parts`, `market_regime`까지 세분화되어 있지만 공개 진입점과 호환 경로는 그대로 유지됩니다.
