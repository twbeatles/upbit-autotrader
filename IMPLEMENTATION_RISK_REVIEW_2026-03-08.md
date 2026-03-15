# 기능 구현 리스크/보완점 점검 보고서 (2026-03-08)

## 0. 문서 성격
- 이 문서는 2026-03-08 기준 구현 리스크 점검 결과를 정리한 보고서입니다.
- 2026-03-09 문서/정적 타입 정합성 후속 점검과 2026-03-15 Pylance/인코딩 재발 방지 조치를 함께 반영했습니다.
- 과거 이슈는 보존하되, 현재 저장소 상태와 충돌하는 stale 정보는 제거했습니다.

## 1. 2026-03-15 후속 정합성 결과
- 문서/텍스트 무결성 재정비 완료
  - 손상된 한국어 문자열을 `settings_controller.py`, `trading_controller.py`, `trading_parts/indicator_ops.py`, `ui_controller.py`에서 복구
  - 신규 무결성 테스트 `tests/test_text_integrity.py` 추가
  - 문서 참조 검증 `tests/test_docs_references.py`를 현재 유지 문서 기준으로 보강
- 테스트 재검증
  - `python -m pytest -q` -> `93 passed`
  - `python -m pytest -q tests/test_docs_references.py tests/test_text_integrity.py` -> `5 passed`
- 정적 타입 재검증
  - `python -m pyright` -> `0 errors, 0 warnings, 0 informations`
  - 루트 `pyrightconfig.json` 추가로 VS Code Pylance와 CLI pyright 기준 일치
- 로컬 품질 가드 재점검
  - `python -m pre_commit run --all-files` -> passed
  - pre-commit 훅: `tests/test_docs_references.py`, `tests/test_text_integrity.py`, `python -m pyright`
- PyInstaller 스펙 재점검
  - `upbit_trader.spec`는 계속 `collect_submodules("upbit_autotrader")` 기준으로 유지
  - 2026-03-15 기준 추가 수정 필요 사항 없음

## 2. 현재 코드베이스 기준 유지 사실
- 실행 엔트리포인트: `upbit_trader.py`
- 앱 퍼사드/수명주기: `upbit_autotrader/app/trader.py`
- 설정 스키마: `settings_version = 2`
- 신규 기능 기본값: 기존 동작 호환을 위해 기본 `OFF`
- 컨트롤러 믹스인 타입 정합성:
  - `ui_controller.py`, `trading_controller.py`, `settings_controller.py`, `batch_controller.py`, `history_controller.py`
  - 공통 타입 지원: `upbit_autotrader/controllers/_type_support.py`
- 문서/품질 가드 기준 파일:
  - `pyrightconfig.json`
  - `.pre-commit-config.yaml`
  - `tests/test_docs_references.py`
  - `tests/test_text_integrity.py`

## 3. 문서/배포 관련 체크 포인트
- `README.md`
  - 사용자 기준 실행/테스트/빌드 명령을 최신 상태로 유지
  - 테스트 수치, pyright 결과, pre-commit 절차를 실제 실행 결과와 맞출 것
- `CLAUDE.md`, `GEMINI.md`
  - 저장소 구조, 검증 명령, 문서 참조 목록, 품질 가드 절차를 함께 갱신할 것
  - 컨트롤러 구조 변경 시 `_type_support.py` 언급 누락 여부를 점검할 것
- `legacy_wrappers/README.md`
  - 레거시 보관 디렉터리라는 목적만 유지
  - 신규 코드가 이 경로를 직접 참조하지 않도록 안내할 것
- `upbit_trader.spec`
  - 기본 빌드 명령과 `collect_submodules("upbit_autotrader")` 수집 방식 유지
  - repo-local 빌드 산출물 경로(`upbit_dist/`, `upbit_build/`)는 `.gitignore`와 함께 관리
- `.gitignore`
  - 2026-03-15 기준 `logs/`, `upbit_dist/`, `upbit_build/`, `dist/`, `build/`, `*.exe`, 로컬 런타임 JSON 경로가 이미 정리되어 있음
  - 이번 후속 점검에서는 추가 ignore 항목 필요 없음

## 4. 현재도 추적할 운영 리스크
- 주문 재정합/수동검토 큐
  - pending lifecycle과 manual review 승격 규칙은 계속 회귀 테스트 대상이어야 함
- 페이퍼 모드 시작/중지 경로
  - 조기 반환 시 실행 상태 rollback이 누락되지 않는지 점검 필요
- 외부 보유종목 동기화 UI
  - universe 행 생성과 계좌 동기화 시 컬럼 초기화 누락 여부를 계속 확인
- 일괄 매수 경로
  - 자동매매 경로와 동일한 리스크 가드가 적용되는지 검증 필요
- 문서/정적 타입 회귀
  - 문서에서 참조하는 현재 문서가 실제로 존재하는지, 품질 명령이 최신 상태인지 계속 검증 필요

## 5. 권장 검증 명령
```bash
python -m pytest -q
python -m pyright
python -m pre_commit run --all-files
pyinstaller --noconfirm --clean upbit_trader.spec
```

## 6. 비고
- 본 후속 점검에서는 PyInstaller 실제 빌드까지 수행하지 않았고, 스펙과 경로 정합성만 확인했습니다.
- `python -m pre_commit run --all-files` 검증을 위해 로컬에 `pre-commit` 패키지를 설치했습니다.
