# 기능 구현 리스크/보완점 점검 보고서 (2026-03-08)

## 0. 문서 성격
- 이 문서는 2026-03-08 기준 구현 리스크 점검 결과를 정리한 보고서입니다.
- 2026-03-09에 문서/정적 타입 정합성 후속 점검을 반영했습니다.
- 과거 이슈를 보존하되, 현재 저장소 상태와 충돌하는 stale 정보는 제거했습니다.

## 1. 2026-03-09 후속 정합성 결과
- 문서 참조 무결성 정리 완료
  - 삭제된 `PROJECT_STRUCTURE_ANALYSIS.md`, `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md` 참조 제거
  - 현재 유지 문서: `README.md`, `CLAUDE.md`, `GEMINI.md`, `legacy_wrappers/README.md`
- 테스트 재검증
  - `python -m pytest -q` -> `90 passed`
- 정적 타입 재검증
  - `python -m pyright` -> `0 errors, 0 warnings, 0 informations`
- PyInstaller 스펙 재점검
  - `upbit_trader.spec`는 계속 `collect_submodules("upbit_autotrader")` 기준으로 유지
  - 컨트롤러 타입 지원 모듈 `upbit_autotrader/controllers/_type_support.py`는 패키지 수집 경로와 충돌하지 않음

## 2. 현재 코드베이스 기준 유지 사실
- 실행 엔트리포인트: `upbit_trader.py`
- 앱 퍼사드/수명주기: `upbit_autotrader/app/trader.py`
- 설정 스키마: `settings_version = 2`
- 신규 기능 기본값: 기존 동작 호환을 위해 기본 `OFF`
- 컨트롤러 믹스인 타입 정합성:
  - `ui_controller.py`, `trading_controller.py`, `settings_controller.py`, `batch_controller.py`, `history_controller.py`
  - 공통 타입 지원: `upbit_autotrader/controllers/_type_support.py`

## 3. 문서/배포 관련 체크 포인트
- `README.md`
  - 사용자 기준 실행/테스트/빌드 명령을 최신 상태로 유지
  - 테스트 수치와 정적 타입 수치를 실제 실행 결과와 맞출 것
- `CLAUDE.md`, `GEMINI.md`
  - 작업 가이드 문서이므로 저장소 구조, 검증 명령, 문서 참조 목록을 함께 갱신할 것
  - 컨트롤러 구조 변경 시 `_type_support.py` 언급 누락 여부를 점검할 것
- `legacy_wrappers/README.md`
  - 레거시 보관 디렉터리라는 목적만 유지
  - 신규 코드가 이 경로를 직접 참조하지 않도록 안내할 것
- `upbit_trader.spec`
  - 기본 빌드 명령은 유지
  - repo-local 빌드 산출물 경로(`upbit_dist/`, `upbit_build/`)는 `.gitignore`와 함께 관리

## 4. 현재도 추적할 운영 리스크
- 주문 재정합/수동검토 큐
  - pending lifecycle과 manual review 승격 규칙은 계속 회귀 테스트 대상이어야 함
- 페이퍼 모드 시작/중지 경로
  - 조기 반환 시 실행 상태 rollback이 누락되지 않는지 점검 필요
- 외부 보유종목 동기화 UI
  - universe 행 생성과 계좌 동기화 시 컬럼 초기화 누락 여부를 계속 확인
- 일괄 매수 경로
  - 자동매매 경로와 동일한 리스크 가드가 적용되는지 검증 필요

## 5. 권장 검증 명령
```bash
python -m pytest -q
python -m pyright
pyinstaller --noconfirm --clean upbit_trader.spec
```

## 6. 비고
- 본 후속 점검에서는 PyInstaller 실제 빌드까지 수행하지 않았고, 스펙과 경로 정합성만 확인했습니다.
- Python 3.14 환경에서 `langsmith`의 `pydantic.v1` 경고가 출력될 수 있으나 현재 테스트 실패 원인은 아닙니다.
