# PROJECT_STRUCTURE_ANALYSIS

## 1) 프로젝트 개요
- 메인 진입점: `upbit_trader.py`
- 공개 클래스: `UpbitProTrader`
- UI/설정/거래/이력/배치 기능은 컨트롤러 믹스인으로 분리되어 있고, `upbit_trader.py`가 퍼사드 역할을 수행한다.
- 기본 주문 경로는 `UpbitOrderService` 기반이며, v3.2부터 `UpbitPaperOrderService`로 페이퍼 모드를 지원한다.

## 2) 핵심 모듈 책임
- `upbit_trader.py`
  - 앱 라이프사이클, 컨트롤러 결합, 타이머/스레드/로깅 초기화
- `upbit_trader_ui_controller.py`
  - 화면 구성, 탭/메뉴/프리셋 UI, 사용자 입력 위젯 정의
- `upbit_trader_settings_controller.py`
  - 설정 저장/불러오기, 시스템 트레이/시작프로그램 연동
- `upbit_trader_trading_controller.py`
  - 실시간 가격 수신, 진입/청산 판정, 주문 실행, 체결 확인, 리스크 체크
- `upbit_trader_batch_controller.py`
  - 일괄 매수/매도/긴급청산, 외부(universe 밖) 종목 체결 확인
- `upbit_trader_history_controller.py`
  - 거래내역 기록/저장/내보내기, 분석 리포트, 백테스트 실행
- `upbit_strategy.py`
  - 기존 고급 로직(쿨다운/시간청산/동적포지션/MTF/갭/돌파확인)
- `upbit_strategy_engine.py` (신규)
  - 단일/앙상블 전략 신호 평가, 포지션 사이즈 평가, 메타 리스크 필터
- `upbit_strategy_catalog.py` (신규)
  - 전략 ID/메타/기본 파라미터/활성 기본값
- `upbit_order_service.py`
  - pending 주문 추적/중복 방지 + 체결 메트릭 유틸
- `upbit_paper_order_service.py` (신규)
  - 모의 체결/수수료/슬리피지/모의 잔고/보유 관리
- `upbit_settings_store.py`
  - 설정 스키마(v2) 저장/로드 + DPAPI 키 보관

## 3) 데이터/제어 흐름

### 3.1 실시간 가격 흐름
1. `PriceUpdateThread`가 티커별 현재가를 폴링
2. `on_price_update`에서 universe 상태 갱신
3. 상태가 `감시중`이면 `_check_buy_condition`, `보유중`이면 `_check_sell_condition`

### 3.2 매수 흐름
1. 기존 필터(목표가/MA/RSI/MACD/거래량/리스크/진입점수)
2. 전략 엔진 사용 시 `StrategyEngine.evaluate_entry`
3. 주문 라우팅
   - live: `UpbitOrderService.place_buy_market` → Upbit API
   - paper: `UpbitPaperOrderService.place_buy_market` + `order_service.mark_pending`
4. `check_buy_execution`에서 체결 확인 및 포지션 반영

### 3.3 매도 흐름
1. 손절/시간청산/전략청산/분할익절/트레일링스탑 판정
2. 주문 라우팅(live/paper)
3. `check_sell_execution`에서 손익 확정 및 통계/히스토리 반영

### 3.4 설정 흐름
1. UI 위젯 값 수집 (`save_settings`)
2. `upbit_settings_store.save_settings`로 v2 포맷 저장
3. API 키는 DPAPI 암호화 저장
4. 로드 시 v2 우선, 레거시 평문키는 마이그레이션 용도로만 읽음

## 4) 전략 엔진 구조(v3.2)
- 모드
  - `single`: 단일 전략 스코어 기반 진입
  - `ensemble`: 활성 전략 가중 평균 점수 기반 진입
- 전략군
  - 추세/모멘텀: `volatility_breakout`, `donchian_breakout`, `ema_cross_trend`, `time_series_momentum`
  - 평균회귀: `rsi_reversion`, `bollinger_reversion`, `zscore_reversion`
  - 리스크/메타: `volatility_targeting`, `regime_filter`, `drawdown_guard`
- 출력 타입
  - `StrategySignal(strategy_id, action, score, reasons)`

## 5) 주문 안정성
- 티커 단위 pending 맵 유지
- 세션 ID를 통한 stale callback 무시
- 재시도/타임아웃 후 pending 정리 경로 보유
- `reserved_krw`로 과주문 방지

## 6) 테스트 구조
- 기존 테스트
  - `tests/test_v31_features.py`: 설정/보안/서비스 핵심
  - `tests/test_order_stability.py`: pending/세션/주문 안정성
  - `tests/test_performance_optimizations.py`: 캐시/호출량/스레드 종료
  - `tests/test_trader_order_flows.py`: 매수/매도/배치 플로우
- 신규 테스트(v3.2)
  - `tests/test_strategy_engine_signals.py`
  - `tests/test_strategy_engine_ensemble.py`
  - `tests/test_paper_order_service.py`

## 7) 기술부채/리스크 포인트
- `upbit_analytics.py`는 거래일자를 `trade['datetime']` 키에서 읽는데, 실제 저장은 `timestamp` 키를 사용한다.
  - 영향: 일/월 성과 집계가 누락될 수 있음
  - 권장: 로드 시 `timestamp` 우선 fallback 처리
- 백테스터는 단일 종목/단순 체결 모델 중심이며 실제 주문 제약(호가단위/최소수량/지연)을 완전 반영하지 않음.
- 일부 로직은 컨트롤러 내부에 집중되어 있어, 장기적으로는 주문 라우터/신호 엔진 분리를 더 명확히 하는 편이 안전하다.

## 9) v3.2.1 안정화 반영 사항 (2026-02-20)
- 세션 안정성
  - 배치/긴급청산 체결확인 콜백에 `session_id` 전달을 명시해 stale callback 차단 일관성을 강화
- 상태 전이
  - 전량 매도 완료 시 상태를 `감시중`으로 복귀하여 동일 세션 재진입 루프가 동작하도록 조정
- 분석/이력 스키마
  - 분석 모듈은 `timestamp` 우선(`datetime` fallback)으로 집계
  - 이력 테이블/오늘기록삭제는 legacy/malformed 레코드에 방어적으로 동작
- 거래량 필터 정합성
  - 평균 거래량 계산을 `volume_period` 윈도우 기준으로 정렬
- 페이퍼 모드 UX
  - 무로그인 시작 허용 옵션 및 초기 시드(기본 10,000,000 KRW) 설정 키 도입
- 외부 청산 기록
  - Universe 외부 자산 배치 청산 시 평균단가 기반 손익 기록 지원

## 8) 호환성 상태
- 유지됨
  - 실행 진입점: `python upbit_trader.py`
  - 공개 클래스: `UpbitProTrader`
  - 설정 스키마 버전: `settings_version = 2`
- 확장됨
  - 전략 엔진 관련 신규 설정키 추가
  - 페이퍼 트레이딩 관련 신규 설정키 추가
