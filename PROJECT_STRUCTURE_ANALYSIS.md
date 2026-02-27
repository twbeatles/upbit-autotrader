# PROJECT_STRUCTURE_ANALYSIS

## 1. 분석 범위
- 참조 문서: `README.md`, `CLAUDE.md`, `GEMINI.md`, `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- 코드 범위: `upbit_autotrader/` 전체, 루트 엔트리포인트(`upbit_trader.py`), `legacy_wrappers/`, `tests/`
- 목표: 현재 자동매매 구조를 면밀히 분석하고, 추가 가능한 기능/거래 계산 로직을 구조 기준으로 제안

## 2. 현재 아키텍처 요약

### 2.1 패키지 구조
```text
upbit_autotrader/
  app/                 # UpbitProTrader 퍼사드 + 앱 수명주기
  controllers/         # UI/설정/매매/배치/히스토리
  services/            # 주문/보유/설정/보안/페이퍼주문
  strategies/          # legacy 전략매니저 + 전략엔진 + 카탈로그
  core/                # Config, 진입필터
  runtime/             # 실시간 가격 polling thread
  analytics/           # 거래 분석 리포트
  backtesting/         # 백테스터 및 전략 레지스트리
  indicators/          # 고급 지표 모듈(현재 미연동)
  notifications/       # 멀티채널 알림 모듈(현재 미연동)
  ui/                  # 다이얼로그
```

### 2.2 실행/호환 구조
- 실제 실행 엔트리: `upbit_autotrader/app/trader.py`
- 루트 엔트리포인트는 `upbit_trader.py`만 유지
- 과거 호환 래퍼(`upbit_*.py`)는 `legacy_wrappers/`에 기능별로 정리
- 장점: 루트 가독성 개선, 내부 import 경로 단일화
- 리스크: 레거시 루트 import 의존 코드와의 직접 호환성은 축소됨

### 2.3 컨트롤러 중심 오케스트레이션
- `UpbitProTrader`가 다중 컨트롤러 믹스인 조합
- 핵심 실시간 매매 로직은 `controllers/trading_controller.py`에 집중(매우 큰 단일 파일)
- 배치/긴급/외부보유 주문 흐름은 `batch_controller.py`에서 보조

## 3. 현재 거래 흐름 상세

### 3.1 매수 흐름
1. 가격 업데이트(`on_price_update`)에서 감시중 종목에 대해 `_check_buy_condition` 실행
2. 엔진 게이트 정책(`legacy_first`/`engine_only`/`strategy_aware`)에 따라 하드게이트 적용 여부 결정
3. 필터 확인:
- 목표가/MA5
- RSI/MACD/거래량
- 리스크 한도(`check_risk_limits`)
- 진입점수(선택)
- 전략엔진 신호(선택)
4. `execute_buy`에서 포지션 비중 계산 후 주문
5. `check_buy_execution`에서 체결 확인, 보유 상태 반영

### 3.2 매도 흐름
1. 보유중 종목에 대해 `_check_sell_condition` 실행
2. 청산 우선순위:
- 절대 손절
- 시간 청산
- 전략엔진 청산 신호
- 분할익절
- 트레일링 스탑
3. `execute_sell` 또는 `_execute_partial_sell`
4. `check_sell_execution`/`_check_partial_sell_execution`에서 체결 반영

### 3.3 주문 안정성/복구
- `UpbitOrderService` lifecycle state:
  - `submitted -> wait -> done/cancel`
  - timeout 시 `manual_review` 분기 지원
- stale/timeout 주문에 대해 cancel + requery + manual review 큐
- 세션 mismatch terminal 이벤트를 orphan으로 기록 후 계좌 동기화

## 4. 현재 계산 로직(핵심 수식)

### 4.1 진입 점수
- 합산식(0~100): `target_break + ma_filter + rsi_optimal + macd_golden + volume_confirm + bb_position`
- 가중치: `Config.ENTRY_WEIGHTS`

### 4.2 전략엔진(싱글/앙상블)
- 단일 전략: 전략별 점수 >= 50이면 `BUY`
- 앙상블:
  - `score = sum(strategy_score_i * weight_i) / sum(weight_i)`
  - `score >= ensemble_threshold`면 `BUY`

### 4.3 포지션 사이즈(현재)
- 기본: `bet_cash = available_krw * betting_ratio`
- 변동성 타게팅 사용 시:
  - `scale = clamp(target_vol / realized_vol, 0.4, 1.8)`
  - `ratio = ratio * scale`

### 4.4 리스크 스냅샷
- `portfolio_pnl = realized_pnl + unrealized_pnl`
- `loss_rate = portfolio_pnl / initial_balance * 100`
- 보유 개수 제한은 account-wide holdings 기준

### 4.5 체결 단가/손익
- 매수 평균단가:
  - `total_cost = executed_funds + paid_fee`
  - `avg_buy = total_cost / executed_volume`
- 매도 순수익:
  - `net_proceeds = executed_funds - paid_fee`
  - `avg_net_sell = net_proceeds / executed_volume`
- 분할매도 원가배분:
  - `buy_portion = invest_amt * (executed_volume / total_qty_before_sell)`
  - `realized_profit = sell_amount - buy_portion`

## 5. 현재 강점
- 실거래/페이퍼 트레이딩 라우팅 분리
- pending 주문 lifecycle + timeout 복구 + 수동검토 큐
- account-wide 보유 동기화/리스크 계산 반영
- 전략엔진(single/ensemble) + 게이트 정책 분리
- 핵심 회귀 테스트 다수 확보

## 6. 현재 구조적 한계(추가 기능 관점)
- `trading_controller.py` 과대화: 전략/리스크/주문/동기화/UI 갱신이 강결합
- 고급지표(`indicators`)와 멀티채널 알림(`notifications`)이 실매매 경로에 거의 미연동
- 전략 파라미터가 UI/Config/엔진에 분산되어 동적 최적화 확장 난이도 높음
- 리스크는 일손실/보유종목수 중심으로, 포지션 단위 리스크 budget 체계가 약함
- 주문 재시도/복구는 강하지만, 체결 품질(슬리피지 모니터링/실행비용 추적) 계층이 약함

## 7. 자동매매 기능 확장 제안

### 7.1 1순위: 리스크 계산 고도화
1. 포지션 리스크 예산(R-multiple) 기반 사이징
- 제안식:
  - `risk_per_trade_krw = equity * risk_budget_pct`
  - `stop_distance_pct = max(atr_mult * ATR/price, min_stop_pct)`
  - `position_notional = risk_per_trade_krw / stop_distance_pct`
2. 포트폴리오 리스크 한도
- 총 익스포저, 코인군 상관집중도, 동시 손실 시나리오(Pseudo-VaR) 제한
3. 드로우다운 상태 머신
- `normal -> caution -> defense -> halt` 단계별로 자동 비중 축소

### 7.2 2순위: 체결/주문 품질 개선
1. 슬리피지 추정 및 주문 금액 동적 조정
- 예상 슬리피지 기반 실주문 금액 감산
2. 분할 진입/분할 청산 엔진
- 1회 시장가 대신 n회 분할/시간 분산
3. 주문 비용 대시보드
- 누적 수수료, 누적 슬리피지, 이론가 대비 실행가 추적

### 7.3 3순위: 전략 레이어 고도화
1. 전략별 신뢰도 가중치 자동 업데이트
- 최근 hit-rate, expectancy 기반 weight 리밸런싱
2. 레짐 기반 전략 전환
- 추세/횡보/고변동 구간별 활성 전략 세트 자동 스위칭
3. 메타 시그널(진입 확률 점수)
- 기존 rule score + 고급 지표 score를 통합한 확률형 진입 점수

### 7.4 4순위: 운영 기능
1. `notifications/notifiers.py` 실연동(Discord/Telegram/Email)
2. 재시작 복구 강화
- pending/manual-review/orphan 상태 영속화(JSON)
3. 헬스체크
- 가격피드 지연, API 지연, 주문 실패율, 연속 슬리피지 악화 알림

## 8. 신규 거래 계산 로직 제안(수식 중심)

### 8.1 기대값 기반 진입 필터
- `E = P(win) * AvgWin - (1 - P(win)) * AvgLoss`
- `E > 0`이고 `E`가 최소 임계치 이상일 때만 진입

### 8.2 Kelly Fraction(보수적 적용)
- `f* = p - (1-p)/b`
- 실제 적용: `f = clamp(0, f* * kelly_scale, max_betting_pct)`

### 8.3 ATR 기반 적응형 손절/추적손절
- `stop_price = entry * (1 - atr_mult * ATR/price)`
- `trail_stop = max(trail_stop_prev, high_since_entry - atr_trail_mult * ATR)`

### 8.4 체결비용 반영 손익분기점
- `breakeven_pct = fee_buy + fee_sell + expected_slippage_buy + expected_slippage_sell`
- 최소 목표수익률을 `breakeven_pct + alpha` 이상으로 강제

### 8.5 포트폴리오 변동성 타게팅(다자산)
- `target_gross_exposure = target_portfolio_vol / estimated_portfolio_vol`
- 종목별 비중은 신호강도와 공분산 페널티로 재분배

## 9. 구현 권장 리팩터링(파일 단위)

### 9.1 신규 모듈 제안
```text
upbit_autotrader/
  risk/
    portfolio_risk.py         # 리스크 스냅샷/한도/상태머신
    position_sizing.py        # ATR/Kelly/R-budget 계산
  execution/
    execution_model.py        # 슬리피지/수수료/분할주문
    reconciliation_store.py   # pending/manual/orphan 영속화
  strategies/
    meta_signal.py            # 확률형/기대값 기반 메타 신호
```

### 9.2 기존 파일 역할 축소
- `trading_controller.py`:
  - 의사결정 오케스트레이션만 담당
  - 계산식/리스크/실행비용 계산은 신규 모듈 호출
- `settings_controller.py`:
  - 신규 리스크/실행 옵션 설정 키 직렬화

## 10. 테스트 확장 권장
- 리스크 계산 단위테스트:
  - ATR 사이징, Kelly clamp, drawdown state 전이
- 주문 품질 테스트:
  - 슬리피지 급증 시 주문축소/거부
- 회귀 테스트:
  - 기존 `tests/test_*` 동작 유지 + 신규 옵션 off 시 완전 동일 결과

## 11. 즉시 실행 가능한 구현 우선순위
1. `PROJECT_STRUCTURE_ANALYSIS.md` 기준으로 `risk/position_sizing.py` 먼저 추가
2. `trading_controller.execute_buy`에서 현재 비중 계산을 신규 사이징 함수로 교체
3. `check_risk_limits`를 `portfolio_risk.py`로 추출
4. 슬리피지/비용 로그를 trade history에 필드로 저장
5. notifications 모듈을 실제 이벤트(`BUY/SELL/ERROR/TIMEOUT`)에 연결

## 12. 결론
- 현재 프로젝트는 주문 안정성/복구, 전략 엔진, 페이퍼 트레이딩 등 자동매매 핵심 기반이 이미 잘 구축되어 있음
- 다음 단계의 핵심은 "리스크 계산 체계화 + 실행비용 모델링 + 전략 메타화"이며, 이를 위해 계산 로직을 컨트롤러에서 분리하는 구조 개편이 가장 높은 투자 대비 효과를 가짐

## 13. 구현 반영 상태 (2026-02-27)

### 13.1 제안 대비 구현 완료 항목
1. 리스크/사이징 도메인 모듈
- `upbit_autotrader/risk/position_sizing.py` 구현 완료
- `upbit_autotrader/risk/portfolio_risk.py` 구현 완료
- `trading_controller.execute_buy`, `check_risk_limits` 경로에서 신규 엔진 호출 반영

2. 실행비용/분할주문 엔진
- `upbit_autotrader/execution/execution_model.py` 구현 완료
- `single_market` / `twap_market` 분기 반영
- 체결 후 expected/realized slippage 계산 및 기록 반영

3. 전략 메타화/가중치 자동조정
- `upbit_autotrader/strategies/meta_signal.py` 구현 완료
- 메타 게이트(`expected_value`, `meta_score`) 반영
- 전략 성과 추적 + 일 단위 가중치 리밸런싱 로직 반영

4. 주문복구 상태 영속화
- `upbit_autotrader/execution/reconciliation_store.py` 구현 완료
- 앱 시작 시 복원, 주기적 플러시 타이머, 종료 시 강제 저장 반영
- 손상/읽기 실패 시 graceful fallback 처리

5. 알림/운영 헬스체크
- `notifications/notifiers.py` 기반 Discord 채널 설정 연동
- `BUY/SELL/WARNING/ERROR/EMERGENCY` 이벤트 라우팅 연동
- `_ops_alert` cooldown 재사용으로 중복 알림 완화

6. UI/설정 통합
- 고급 탭에 리스크/실행/메타/Discord/복구 설정 그룹 추가
- `settings_controller` 저장/복원 키 확장 완료
- `settings_version=2` 유지 + 신규 키 누락 시 기본값 fallback

7. 거래 기록 스키마 확장
- `add_trade_record(..., **extra_fields)`로 확장 필드 optional 저장
- CSV 내보내기 시 동적 필드 자동 포함

8. 테스트 확장
- 신규 단위 테스트 4종 추가
  - `tests/test_position_sizing.py`
  - `tests/test_portfolio_risk_engine.py`
  - `tests/test_execution_model.py`
  - `tests/test_meta_signal.py`
- 전체 테스트: `74 passed`

### 13.2 현재 운영 제약/가정
1. 신규 기능은 모두 opt-in이며 기본값은 OFF
2. TWAP는 `pyupbit` 시장가 주문 반복 전송 방식
3. Discord 전송 실패는 비치명 처리(매매 흐름 중단 없음)
4. 7일 페이퍼 게이트는 운영 정책 권고이며 코드 차원의 강제 차단 로직은 미구현

### 13.3 다음 유지보수 권장점
1. UI 내부 버전 문자열(`v2.7`, `v3.0`) 정리로 사용자 표시 버전 일원화
2. 페이퍼 게이트(7일/치명오류 0건/복구성공률) 자동 판정 모듈화
3. trade history 확장 필드 기반 운영 대시보드 추가
