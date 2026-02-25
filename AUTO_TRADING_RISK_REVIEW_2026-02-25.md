# 자동매매 기능 리스크 점검 및 개선 이행 보고서 (2026-02-25)

## 1. 문서 목적
이 문서는 자동매매 리스크 점검 결과(P0/P1/P2)와 실제 개선 이행 상태를 기록합니다.

- 기준 문서: `README.md`, `CLAUDE.md`, `GEMINI.md`
- 기준 코드: `upbit_autotrader/` 패키지(루트 `upbit_*.py`는 호환 래퍼)
- 기준 테스트: `python -m pytest -q`
- 최신 결과: `60 passed`

> 주의: 테스트 통과는 품질 기준 충족을 의미하지만, 운영 안전을 100% 보장하지는 않습니다.

## 2. 우선순위 기준
- `P0`: 자금/포지션 불일치, 의도와 다른 실주문 가능성
- `P1`: 안정성/성능/분석 정확도 저하
- `P2`: 문서/운영성/유지보수 개선

## 3. 핵심 이슈 이행 현황

### P0-01 전략 엔진 진입 게이트 분리
- 상태: `완료`
- 조치:
  - `engine_gate_policy` 도입 (`legacy_first` / `engine_only` / `strategy_aware`)
  - 평균회귀 전략 포함 시 하드게이트 완화
- 반영 파일:
  - `upbit_autotrader/controllers/trading_controller.py`
  - `upbit_autotrader/strategies/engine.py`
  - `upbit_autotrader/controllers/ui_controller.py`
  - `upbit_autotrader/controllers/settings_controller.py`
  - `upbit_autotrader/core/config.py`
- 검증:
  - `tests/test_strategy_engine_gate_policy.py`

### P0-02 주문 timeout/장기대기 복구 강화
- 상태: `완료`
- 조치:
  - timeout 시 로컬 삭제 대신 `cancel -> requery -> terminal 반영` 우선
  - 미해결 건 `manual_review_queue` 적재 + `needs_manual_review=True`
- 반영 파일:
  - `upbit_autotrader/controllers/trading_controller.py`
  - `upbit_autotrader/services/order_service.py`
- 검증:
  - `tests/test_order_reconciliation_recovery.py`

### P0-03 session mismatch 체결 누락 방지
- 상태: `완료`
- 조치:
  - mismatch terminal 이벤트를 `orphan_events`로 기록
  - account-wide 동기화 루틴으로 포지션 재수렴
- 반영 파일:
  - `upbit_autotrader/controllers/trading_controller.py`
  - `upbit_autotrader/controllers/batch_controller.py`
- 검증:
  - `tests/test_order_reconciliation_recovery.py`

### P0-04 시작 시 계좌 전체 보유 동기화
- 상태: `완료`
- 조치:
  - 시작 시 `watchlist + account holdings` 합집합으로 universe 구성
  - watchlist 외 보유도 관리 대상 편입
  - paper/live 모두 동일 원칙 적용
- 반영 파일:
  - `upbit_autotrader/controllers/trading_controller.py`
  - `upbit_autotrader/controllers/batch_controller.py`
  - `upbit_autotrader/services/holdings_service.py`
- 검증:
  - `tests/test_startup_position_sync.py`

### P1-01 리스크 계산 확장(실현+미실현+외부보유)
- 상태: `완료`
- 조치:
  - `_get_risk_snapshot()` 기반 포트폴리오 손익 계산
  - 외부보유 포함 옵션 반영
  - holdings 제한 account-wide 기준 적용
- 반영 파일:
  - `upbit_autotrader/controllers/trading_controller.py`
- 검증:
  - `tests/test_risk_limits_portfolio_scope.py`

### P1-02 중앙 API retry/backoff/rate-limit
- 상태: `완료`
- 조치:
  - 공통 API helper 경로로 통일
  - 최소 호출 간격 + 지수 백오프 + jitter 적용
- 반영 파일:
  - `upbit_autotrader/controllers/trading_controller.py`
  - `upbit_autotrader/controllers/batch_controller.py`

### P1-03 analytics 단위/타입 정합성
- 상태: `완료`
- 조치:
  - profit 집계에 safe float 일관 적용
  - HTML 손익 단위를 KRW(`원`)로 명시
- 반영 파일:
  - `upbit_autotrader/analytics/trading_analytics.py`
- 검증:
  - `tests/test_analytics_units_and_types.py`

### P2-01 문서 드리프트 해소
- 상태: `완료`
- 조치:
  - 누락 문서 생성 및 링크 정합화
  - 구조 리팩토링 반영 문서 업데이트
- 반영 문서:
  - `PROJECT_STRUCTURE_ANALYSIS.md`
  - `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
  - `README.md`, `CLAUDE.md`, `GEMINI.md`
- 검증:
  - `tests/test_docs_references.py`

## 4. 추가 반영 사항
- 패키지 구조 리팩토링 완료:
  - 기존 단일 루트 모듈을 `upbit_autotrader/` 하위로 기능별 분리
  - 루트 `upbit_*.py`는 호환 래퍼 유지
- 빌드 스펙 보강:
  - `upbit_trader.spec`에 `collect_submodules("upbit_autotrader")` 반영
  - 패키지 분리 후 PyInstaller 누락 위험 감소

## 5. 잔여 권고(운영)
1. `manual_review_queue` 영속화(DB/파일) 및 UI 대시보드화
2. orphan/manual-review 이벤트 알림을 외부 채널(예: Slack/Telegram)로 확장
3. 배포 파이프라인에서 `pyinstaller build smoke test` 자동화

## 6. 변경 검증 요약
- 컴파일: `python -m py_compile` 통과
- 테스트: `python -m pytest -q` 통과 (`60 passed`)
- 호환성: 레거시 import 경로 유지(래퍼) + 신규 패키지 경로 병행 지원
