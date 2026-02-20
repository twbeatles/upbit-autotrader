# 기능 구현 리스크 점검 리포트 (2026-02-20)

## 1. 점검 범위와 기준 문서
- 점검 기준 문서
  - `CLAUDE.md`
  - `README.md`
- 점검 대상 범위
  - 실거래/페이퍼 주문 라우팅
  - 체결 확인 및 pending 정리 안정성
  - 전략 엔진 진입/청산 루프 상태 전이
  - 거래 이력 저장/분석 연계
  - 배치 매수/매도/긴급청산 경로
- 점검 방식
  - 코드 정적 점검(핵심 함수/콜백 경로 추적)
  - 테스트 스위트 실행 결과 확인

## 2. 실행 검증 결과
- 실행 명령: `python -m pytest -q`
- 결과: `41 passed in 5.10s`
- 관찰 사항
  - 현재 테스트는 전반적으로 통과하지만, 아래 이슈들은 "현 테스트 커버리지 밖의 기능 리스크" 또는 "요구사항 대비 불일치" 성격으로 남아 있음

## 3. 심각도별 이슈 목록 (Critical/High/Medium/Low)

### Critical

#### C1) 배치 체결확인 콜백 `session_id` 누락
- 증거
  - `upbit_trader_batch_controller.py:295`
  - `upbit_trader_batch_controller.py:302`
  - `upbit_trader_batch_controller.py:412`
  - `upbit_trader_batch_controller.py:420`
  - `upbit_trader_trading_controller.py:1235`
  - `upbit_trader_trading_controller.py:1582`
- 영향
  - 세션 전환(재시작/중지 후 재시작) 상황에서 stale callback 차단 로직이 일부 경로에서 비활성화되어, 이전 세션 체결확인이 현재 세션 상태를 오염시킬 수 있음
- 재현 조건
  - 배치 주문 접수 후 체결확인 타이머 대기 중 세션 변경
  - 이후 기존 콜백이 `session_id=None` 상태로 실행
- 권장 수정
  - 배치 경로의 `QTimer.singleShot` 콜백에서 `session_id`를 캡처해 `check_buy_execution`, `check_sell_execution`, `_check_external_buy_execution`, `_check_external_sell_execution` 호출 시 전달
  - 세션 mismatch 발생 시 로그 레벨/메시지 표준화
- 필요 테스트
  - 배치 매수/매도/긴급청산 각각에 대해 세션 변경 후 stale callback 무시 여부 검증

### High

#### H1) 재진입 차단 상태 고착 (`매도완료`)
- 증거
  - `upbit_trader_trading_controller.py:1648`
  - `upbit_trader_trading_controller.py:945`
- 영향
  - 전량 매도 체결 후 상태가 `매도완료`로 고정되어, 자동매매 루프 조건(`감시중`)을 만족하지 않아 동일 세션 자동 재진입이 차단됨
- 재현 조건
  - `감시중 -> 보유중 -> 매도완료` 순으로 정상 청산 완료
  - 이후 가격이 재진입 조건 충족
- 권장 수정
  - 전량 매도 완료 시 상태를 `감시중`으로 복귀시키는 상태 전이 규약 적용
  - UI 표시와 내부 상태 전이를 분리(표시는 "청산완료" 로그/이력으로 대체 가능)
- 필요 테스트
  - 전량 매도 직후 다음 틱에서 재진입 조건 충족 시 `execute_buy` 재호출 여부

#### H2) 페이퍼 모드 무로그인 시작 미지원
- 증거
  - `upbit_trader_trading_controller.py:94`
  - `upbit_trader_ui_controller.py:273`
- 영향
  - 페이퍼 트레이딩 목적(실주문 차단 + 빠른 시뮬레이션) 대비 사용성이 낮고, API 로그인 실패 시 페이퍼 테스트 자체가 막힘
- 재현 조건
  - 페이퍼 모드 체크 상태에서 API 미연결 또는 로그인 미수행
  - `start_trading` 호출
- 권장 수정
  - 정책 확정: 페이퍼 모드에서는 무로그인 시작 허용
  - 기본 초기 시드 `10,000,000 KRW` 적용(설정값 우선)
- 필요 테스트
  - 무로그인 페이퍼 시작 가능 여부
  - 해당 모드에서 live API 주문 함수 호출 0회 보장

### Medium

#### M1) 분석 리포트 날짜 키 불일치 (`timestamp` vs `datetime`)
- 증거
  - `upbit_analytics.py:75`
  - `upbit_analytics.py:159`
  - `upbit_trader_history_controller.py:268`
- 영향
  - 저장은 `timestamp` 기준인데 분석은 `datetime`을 읽어 일별/월별 성과 집계가 누락되거나 왜곡될 수 있음
- 재현 조건
  - 기본 저장 포맷(`timestamp`)만 포함된 거래 이력 파일로 리포트 생성
- 권장 수정
  - 분석 모듈에서 `timestamp` 우선, `datetime` fallback으로 통일
  - 로드 시 키 정규화(호환 레이어) 추가
- 필요 테스트
  - `timestamp` 전용 데이터셋에서 일/월 집계 정상 동작

#### M2) 거래량 평균 계산 기간 불일치
- 증거
  - `upbit_trader_trading_controller.py:736`
- 영향
  - 거래량 필터가 설정 기간(`volume_period`)과 다르게 동작해 필터 민감도가 비의도적으로 변함
- 재현 조건
  - `volume_period`를 짧게/길게 변경해도 평균 산식이 사실상 전체 구간 평균으로 수렴
- 권장 수정
  - 평균 거래량 계산을 `df['volume'].iloc[-(volume_period+1):-1].mean()` 등 기간 고정 방식으로 변경
- 필요 테스트
  - `volume_period` 변경 시 필터 통과율이 기대 방향으로 변하는지 검증

#### M3) 히스토리 레코드 스키마 내구성 부족
- 증거
  - `upbit_trader_history_controller.py:121`
  - `upbit_trader_history_controller.py:292`
- 영향
  - `timestamp` 키 누락 또는 비 ISO 형식 레코드 존재 시 오늘 기록 삭제/테이블 로드에서 예외 발생 가능
- 재현 조건
  - legacy 또는 외부 편집으로 오염된 `trade_history.json` 로드
- 권장 수정
  - 레코드 접근을 `dict.get()` 기반 방어형 처리로 변경
  - 파싱 실패 레코드 skip + 경고 로그 전략 적용
- 필요 테스트
  - malformed 레코드 혼재 파일 로드 시 앱 비정상 종료 없이 동작

#### M4) Universe 외부 청산 손익 0 고정 기록
- 증거
  - `upbit_trader_batch_controller.py:544`
- 영향
  - 외부 보유자산 배치 청산 시 거래 이력 손익이 0으로 저장되어 분석 정확도 저하
- 재현 조건
  - Universe에 없는 코인을 배치/긴급 청산
- 권장 수정
  - 가능한 범위에서 평균매입가 기반 손익 계산 또는 `profit=None`(미산출)로 명시 저장
  - 분석 단계에서 `None` 처리 규칙 분리
- 필요 테스트
  - 외부 청산 레코드가 분석 통계에 왜곡 없이 반영되는지 검증

### Low
- 현재 점검 범위 내 신규 Low 이슈는 별도 확정 없음

## 4. 추가 필요 기능 제안
- 결론: 본 요청(리스크 점검 문서화) 자체는 코드/API 변경이 아님
- 다만 권고안으로 다음 인터페이스 확장 제안
  1. 설정 키 `paper_seed_krw` 추가
  2. 설정 키 `paper_allow_without_login` 추가
  3. 상태 전이 규약 명시: 전량 매도 후 `매도완료` 고착 대신 `감시중` 복귀
- 권장 문서화 위치
  - `README.md`의 페이퍼 트레이딩/상태 전이 섹션
  - `CLAUDE.md`의 호환성/주문 경로 정책 섹션

## 5. 우선순위 실행 순서 (P0/P1/P2)
- P0
  - C1 배치 콜백 `session_id` 전달 누락 수정
  - H1 전량 매도 후 상태 전이(`감시중` 복귀) 정비
  - M1 분석 날짜 키 정규화(`timestamp` 우선)
- P1
  - H2 페이퍼 무로그인 시작 허용 + 초기 시드 정책 적용
  - M2 거래량 평균 기간 계산식 정합화
- P2
  - M3 히스토리 스키마 방어 로직 강화
  - M4 외부 청산 손익 기록 규약 개선

## 6. 회귀 방지 테스트 시나리오
1. 전량 매도 후 다음 틱에서 동일 종목 재진입 가능 여부
2. `timestamp`만 있는 히스토리로 일/월 분석 집계 정상 여부
3. 배치 매수/매도 후 세션 변경 시 stale callback 무시 여부
4. 거래량 평균이 `volume_period` 기준으로 계산되는지
5. malformed/legacy `trade_history` 레코드 로드 시 앱 비정상 종료 방지
6. 무로그인 페이퍼 모드 시작 및 주문 라우팅에서 live API 호출이 없는지
7. Universe 외부 청산 시 손익 계산/기록 정확성

## 7. 호환성/운영 영향
- 호환성
  - 진입점(`python upbit_trader.py`)과 공개 클래스(`UpbitProTrader`) 유지 가능
  - 설정 스키마는 `settings_version=2` 유지하되 키 추가 방식으로 확장 가능
- 운영 영향
  - 세션 안전성/상태 일관성 개선으로 실거래 오동작 리스크 감소
  - 분석 정확도 개선으로 운영 판단 지표 신뢰도 상승
- 확정 가정/기본값
  - 재진입 정책: 자동 재진입(`매도 후 감시중`)
  - 페이퍼 모드: 무로그인 허용
  - 무로그인 페이퍼 초기 시드: `10,000,000 KRW`

## 8. 즉시 작업 체크리스트
- [ ] P0-1: 배치 체결확인 콜백의 `session_id` 전달 누락 수정
- [ ] P0-2: 전량 매도 후 상태 전이를 `감시중`으로 복귀하도록 수정
- [ ] P0-3: 분석 모듈 날짜 키를 `timestamp` 우선으로 정규화

---

## 9. 반영 완료 내역 (2026-02-20)
- [x] P0-1: 배치 체결확인 콜백의 `session_id` 전달 누락 수정 완료
- [x] P0-2: 전량 매도 후 상태 전이를 `감시중` 복귀로 수정 완료
- [x] P0-3: 분석 모듈 날짜 키 `timestamp` 우선 정규화 완료
- [x] M2: 거래량 평균 계산을 `volume_period` 윈도우 기준으로 수정
- [x] M3: 이력 레코드(`timestamp`/`datetime`) 혼재 및 malformed 데이터 방어 처리 추가
- [x] H2: 페이퍼 모드 무로그인 시작 허용 + 초기 시드(기본 10,000,000 KRW) 반영
- [x] M4: Universe 외부 청산 손익 기록 개선(평균단가 기반 산출)

### 관련 코드 반영 파일
- `upbit_config.py`
- `upbit_trader_ui_controller.py`
- `upbit_trader_settings_controller.py`
- `upbit_trader_trading_controller.py`
- `upbit_trader_batch_controller.py`
- `upbit_analytics.py`
- `upbit_trader_history_controller.py`

### 회귀 검증
- `python -m pytest -q` 실행 결과: `45 passed`
