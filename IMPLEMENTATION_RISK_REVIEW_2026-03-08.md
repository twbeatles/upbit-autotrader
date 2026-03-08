# 기능 구현 리스크/보완점 점검 보고서 (2026-03-08)


## 0) ?? ?? ???? (2026-03-08, ???? ??)
- ?? ??: `C:\twbeatles-repos\backups\upbit-autotrader_20260308_231834`
- ?? ??: `git-status.txt`, `filelist.txt`, `sha256.txt`, `baseline_test_result.txt`
- ???? ?? ??:
  - ???? ??: `trading_parts`, `batch_parts`, `ui_sections`, `settings_field_specs`
  - ?? ??: `legacy_parts`
  - ???/?? ????? ??: ?? ???/??? ???? ??
- `.spec` ?? ??: `upbit_trader.spec`? `collect_submodules("upbit_autotrader")`? ?? ?? ?? ?? ?? (?? ???)
- ?? ??? ??: `python -m pytest -q` -> `90 passed`
- ??? ?? ???:
  - `tests/test_refactor_split_compatibility.py`
  - `tests/test_structure_guards.py`

## 1) 점검 범위
- 기준 문서: `README.md`, `CLAUDE.md`
- 핵심 코드: `upbit_autotrader/controllers/trading_controller.py` 중심으로 주문/체결/리스크/복구/설정 경로
- 보조 코드: `settings_controller.py`, `batch_controller.py`, `services/*`, `risk/*`, `execution/*`
- 테스트 확인: `python -m pytest -q`

## 2) 현재 상태 요약
- 테스트 결과: `1 failed, 73 passed`
- 실패 테스트: `tests/test_docs_references.py`
- 즉시 확인된 저장소 상태:
  - `PROJECT_STRUCTURE_ANALYSIS.md` 삭제 상태
  - `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md` 삭제 상태
  - 위 2개는 `README.md`/`CLAUDE.md`에서 필수 문서로 참조 중

## 3) 우선순위별 잠재 문제

### [Critical] C-01. 매도 체결 경로에서 미정의 변수 참조로 런타임 예외 발생 가능
- 위치:
  - `upbit_autotrader/controllers/trading_controller.py:2952`
  - `upbit_autotrader/controllers/trading_controller.py:2962`
  - `upbit_autotrader/controllers/trading_controller.py:2976`
  - `upbit_autotrader/controllers/trading_controller.py:2759`
  - `upbit_autotrader/controllers/trading_controller.py:2768`
- 증상:
  - `check_sell_execution()` 내부에서 `persist_strategy_performance`, `mark_reconciliation` 로컬 변수를 정의하지 않고 사용
  - `_check_partial_sell_execution()` 내부에서도 `mark_reconciliation` 미정의 상태로 사용
- 영향:
  - 정상 체결 이후에도 `NameError`가 발생해 `except` 경로로 빠질 수 있음
  - 수동검토 큐 오적재/불필요 에러로그/상태 전이 왜곡 가능
- 권장 조치:
  - 두 함수 시작부에서 `getattr`로 변수 초기화
  - 예외 블록이 실제 API 예외인지 코드 버그인지 구분 로깅
- 테스트 보강:
  - `done/cancel` 경로에서 예외 없이 종료되는지 검증하는 단위 테스트 추가
  - `_check_partial_sell_execution` 전용 테스트 추가

### [Critical] C-02. 문서 참조 무결성 깨짐 (필수 문서 파일 누락)
- 위치:
  - `README.md` (문서 참조 섹션)
  - `CLAUDE.md` (문서 참조 섹션)
  - `tests/test_docs_references.py:8-19`
- 증상:
  - 참조된 문서(`PROJECT_STRUCTURE_ANALYSIS.md`, `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`)가 워크트리에서 누락
- 영향:
  - CI/로컬 테스트 즉시 실패
  - 온보딩/운영 문서 동기화 깨짐
- 권장 조치:
  - 누락 문서 복구 또는 참조/테스트 동시 정리(둘 중 하나로 일관성 회복)

### [High] H-01. 페이퍼 모드 시작 실패 시 런타임 상태 불일치 가능
- 위치: `upbit_autotrader/controllers/trading_controller.py:136-148`
- 증상:
  - `self.is_running = True` 설정 후, 페이퍼 잔고 0이면 `return`
  - 중지 처리(`stop_trading`) 없이 빠져나가므로 상태가 부분적으로만 갱신됨
- 영향:
  - 타이머 기준으로는 실행 중으로 간주될 수 있음
  - stale feed 경고/복구 로직 등 부수 동작이 의도치 않게 작동 가능
- 권장 조치:
  - 사전 검증(잔고/시드) 완료 후 `is_running=True` 전환
  - 또는 early return 전에 명시적 rollback (`is_running=False`, 세션/버튼 복원)

### [High] H-02. 외부 보유종목 행 생성 시 UI 컬럼 초기화 누락
- 위치:
  - `upbit_autotrader/controllers/trading_controller.py:1038-1041`
  - `upbit_autotrader/controllers/trading_controller.py:1046-1050`
  - `upbit_autotrader/controllers/trading_controller.py:1079-1087`
- 증상:
  - `_ensure_universe_row()`에서 0~4열만 생성하고, 5~9열은 `None` 참조만 저장
  - `_sync_account_holdings_to_universe()`는 `None`이면 텍스트 업데이트를 건너뜀
- 영향:
  - 외부 보유 유입 시 수량/매입가/투입금 표시가 누락될 수 있음
  - 수동 모니터링/운영 판단 오류 가능성
- 권장 조치:
  - `_ensure_universe_row()`에서 5~9열 기본 `QTableWidgetItem` 생성
  - `ui_items`가 `None`일 때 즉석 생성하는 방어 코드 추가

### [High] H-03. 재정합 루프에서 `order=None` 상태가 장시간 고착될 수 있음
- 위치: `upbit_autotrader/controllers/trading_controller.py:1540-1549`
- 증상:
  - `_safe_get_order(uuid)`가 계속 `None`이어도 `force=False`이면 manual review로 승격되지 않음
  - 주기 타이머는 기본적으로 `force=False` 호출
- 영향:
  - pending/reserved 금액이 장기간 남아 신규 주문을 막을 수 있음
- 권장 조치:
  - `None` 응답 누적 횟수/경과시간 기반 승격 규칙 추가
  - 재시도 한도 초과 시 `timeout -> manual_review` 자동 전환

### [Medium] M-01. 포트폴리오 리스크 스냅샷에서 계좌 최신값 반영이 부분적으로 누락될 수 있음
- 위치: `upbit_autotrader/controllers/trading_controller.py:3052-3063`
- 증상:
  - `account_wide_positions.setdefault(ticker, payload)` 사용으로
  - 동일 티커가 `universe`에 있으면 계좌 실측 qty/가격으로 갱신되지 않음
- 영향:
  - 리스크 스냅샷이 화면 캐시 값에 끌려가 정확도 저하 가능
- 권장 조치:
  - 동일 티커는 `setdefault` 대신 최신 계좌 기준으로 merge/override 정책 명시

### [Medium] M-02. 상관집중도 계산 대상이 최대 10종목으로 제한
- 위치: `upbit_autotrader/controllers/trading_controller.py:3070`
- 증상:
  - `for ticker in list(account_wide_positions.keys())[:10]`
- 영향:
  - 10종목 초과 보유 시 상관집중도 과소평가 가능
- 권장 조치:
  - 상위 노출 기준(노셔널 상위 N) 명시
  - 또는 전체 계산 + 캐시/비동기화로 성능 보완

### [Medium] M-03. 일괄 매수 경로는 리스크 한도 체크를 우회
- 위치: `upbit_autotrader/controllers/batch_controller.py:196-320`
- 증상:
  - `execute_batch_buy()` 내부에서 `check_risk_limits()` 호출 없음
- 영향:
  - 운영자가 버튼으로 일괄매수 시 자동매매의 리스크 가드를 우회 가능
- 권장 조치:
  - 옵션 토글로라도 리스크 체크 연동
  - 최소한 최대보유수/일손실 트리거는 공통 적용

### [Low] L-01. `meta_score_threshold` 로드 시 정밀도 손실 가능
- 위치: `upbit_autotrader/controllers/settings_controller.py:234`
- 증상:
  - `setValue(int(...))`로 강제 형변환
- 영향:
  - 소수점 임계값 저장 시 재로딩 시 값 변경 가능
- 권장 조치:
  - UI 위젯 타입(`QDoubleSpinBox` 가정)과 맞춘 float 로드

## 4) 추가하면 좋은 기능/운영 보강

### A-01. 주문 상태 감사(Observability) 강화
- 제안:
  - pending lifecycle 전이 로그를 구조화(JSON line)로 별도 파일 저장
  - `uuid`, `session_id`, `state_from/to`, `reason`, `source` 필수 필드화
- 기대효과:
  - 장애/체결 불일치 원인 추적 시간 단축

### A-02. 수동검토 큐 운영성 강화
- 제안:
  - `manual_review_queue` UI 탭 제공(필터/재시도/해제)
  - 큐 항목 aging 알림(예: 10분 이상 미처리)
- 기대효과:
  - unresolved 주문이 방치되는 운영 리스크 감소

### A-03. 회귀 테스트 확대
- 우선 추가 케이스:
  - `check_sell_execution` 성공/취소 시 예외 미발생 보장
  - `_check_partial_sell_execution` done/cancel 경로
  - 페이퍼 시작 실패 시 `is_running` rollback 보장
  - 외부 보유종목 행 생성 후 5~9열 UI 값 반영 검증

### A-04. 문서 무결성 자동복구 가드
- 제안:
  - 릴리즈 파이프라인에서 필수 문서 누락 시 실패(이미 테스트 있음)
  - 추가로 `pre-commit` 훅에서 참조 문서 존재 여부 검증

## 5) 즉시 조치 권장 순서
1. `C-01` (매도/분할매도 미정의 변수) 수정
2. `C-02` (누락 문서 복구 또는 참조 정리)로 테스트 정상화
3. `H-01` (페이퍼 시작 early-return rollback) 수정
4. `H-02` (외부 보유 UI 컬럼 초기화) 수정
5. `H-03` (재정합 `order=None` 장기 고착 해소) 수정

