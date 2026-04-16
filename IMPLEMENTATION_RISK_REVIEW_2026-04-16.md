# Upbit Pro Algo-Trader Implementation Risk Review

검토 일자: 2026-04-16

## 검토 범위
- 루트 문서: `README.md`, `CLAUDE.md`, `GEMINI.md`, `upbit_trader.spec`, `.gitignore`
- 실거래 핵심 경로:
  - `upbit_autotrader/controllers/trading_parts/order_api_ops.py`
  - `upbit_autotrader/controllers/trading_parts/execution_flow_ops.py`
  - `upbit_autotrader/controllers/batch_controller.py`
  - `upbit_autotrader/market_regime/providers.py`

## 이번 반영 내용
- `cancel` 상태지만 실제 체결 수량이 존재하는 주문을 체결로 반영하도록 보강
- 주문 전 `orders/chance` 기반으로 마켓 상태, 지원 주문 유형, 최소 주문 금액을 검증
- 업비트 Rate Limit 그룹별 최소 호출 간격을 분리
- 시장 레짐 breadth 수집 시 캔들 호출 사이에 간격을 두어 Quotation `candle` 그룹 초과 위험 완화
- 루트 문서/참조 테스트를 현재 파일 구조에 맞게 정리

## 업비트 API 기준으로 본 주요 위험과 대응 상태
### 1. 주문 종료 상태 해석
- 업비트 주문 조회 응답은 `state` 외에도 `executed_volume`, `remaining_volume`, `paid_fee`, `trades`를 제공합니다.
- `state == cancel`만으로 미체결로 간주하면 부분 체결된 주문을 놓칠 수 있습니다.
- 대응 상태: 반영 완료

### 2. 주문 가능 정보(`orders/chance`) 미검증
- 업비트 공식 문서는 주문 전 `market.state`, `bid_types`, `ask_types`, `bid.min_total`, `ask.min_total`, 계정 잔고를 확인할 수 있게 제공합니다.
- 기존 구현은 KRW 5,000원 상수와 로컬 잔고만 확인했기 때문에 마켓 비활성/주문 유형 비지원 케이스를 사전에 막지 못했습니다.
- 대응 상태: 반영 완료

### 3. 그룹별 Rate Limit 차이
- 업비트 공식 요청 수 제한 문서 기준:
  - Exchange `default`: 초당 최대 30회
  - Exchange `order`: 초당 최대 8회
  - Quotation `ticker` / `candle`: 초당 최대 10회
- 기존 구현은 단일 최소 간격만 사용했습니다.
- 대응 상태: 반영 완료

### 4. 시장 레짐 수집의 연속 OHLCV 호출
- breadth 계산은 상위 KRW 마켓을 대상으로 연속 캔들 조회를 수행합니다.
- 간격 없이 연속 호출하면 Quotation `candle` 제한에 걸릴 가능성이 있습니다.
- 대응 상태: 반영 완료

## 남은 후속 권장 사항
### 높음
- 리스크 사이징의 `equity_krw`가 여전히 `initial_balance` 기준입니다.
  - 실현손익/외부 보유/미실현 손익을 반영한 실시간 자산 기준으로 바꾸는 것이 더 안전합니다.

- execution model의 수수료 입력을 실제 계정 `bid_fee`/`ask_fee`와 연결하는 것이 필요합니다.
  - 현재는 기본 5bps 가정이 남아 있습니다.

### 중간
- `Remaining-Req` 헤더 기반 적응형 throttling은 아직 미구현입니다.
- 시장 레짐 breadth는 호출 완화는 되었지만 캐시/샘플링 최적화 여지가 남아 있습니다.

### 낮음
- `pyright`는 현재 환경의 의존성 미설치와 기존 타입 이슈 때문에 실패합니다.

## 문서/빌드 정합성 메모
- 루트 문서들은 현재 기준 문서로 아래 파일들을 참조합니다.
  - `IMPLEMENTATION_RISK_REVIEW_2026-04-16.md`
  - `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`
  - `legacy_wrappers/README.md`
- `upbit_trader.spec` 기준 기본 빌드 산출물은 `dist/`, `build/`이고, repo-local fallback은 `upbit_dist/`, `upbit_build/`입니다.
- 위 산출물 경로는 `.gitignore`에 반영되어 있어야 합니다.

## 검증 결과
- `python -m pytest -q`: 통과
- `python -m pyright`: 실패
  - 주 원인: `PyQt6`, `pandas`, `numpy`, `pyupbit`, `pytest` 등 로컬 타입/패키지 미해결과 기존 테스트 타입 이슈

## 참고 링크
- 업비트 주문 가능 정보: https://docs.upbit.com/kr/kr/reference/available-order-information
- 업비트 요청 수 제한: https://docs.upbit.com/kr/reference/rate-limits
- 업비트 현재가 정보: https://docs.upbit.com/kr/reference/ticker%ED%98%84%EC%9E%AC%EA%B0%80-%EC%A0%95%EB%B3%B4
