# Architecture Market Regime Plan

문서 일자: 2026-03-25

## 목적
- 시장 레짐 점수를 별도 모듈로 분리해 매수 필터와 주문 비중 스케일링에 공통 사용
- 외부 데이터 실패 시에도 내부 지표만으로 중립/완화 fallback을 유지
- UI, 런타임 스레드, 매매 컨트롤러 간 결합도를 낮춤

## 현재 구현 기준 모듈
- 엔진: `upbit_autotrader/market_regime/engine.py`
- 데이터 제공자: `upbit_autotrader/market_regime/providers.py`
- 백그라운드 갱신: `upbit_autotrader/runtime/market_regime_thread.py`
- 컨트롤러 결합 지점: `upbit_autotrader/controllers/trading_parts/market_regime_ops.py`

## 데이터 소스 구성
### 1단계 기본 점수
- `local_breadth_score`
  - 업비트 KRW 마켓 상위 거래대금 종목의 MA20 상회 비율과 단기 상승 비율 사용
- `btc_trend_vol_score`
  - `KRW-BTC` EMA 추세와 실현 변동성 사용
- `fear_greed_score`
  - Alternative Fear & Greed Index 사용

### 2단계 overlay
- `etf_flow_score`
  - Farside BTC ETF flow
- `btc_dominance_score`
  - Alternative global dominance 데이터

## 출력 계약
- `market_regime_score`
- `risk_multiplier`
- `label`
- `stale_components`
- `details`

## 레이블과 리스크 배수
- `< 40`: `defensive`, `0.50`
- `< 55`: `neutral`, `0.75`
- `< 70`: `risk_on`, `1.00`
- `>= 70`: `risk_on`, `1.15`

## 런타임 동작
- 초기 fetch 전에는 중립값 사용
  - `score=50`
  - `label=neutral`
  - `risk_multiplier=1.0`
- 별도 QThread에서 주기적으로 갱신
- stale source는 `details`와 상태 로그에 남김

## 설계 원칙
- 외부 소스 실패는 치명 오류가 아니라 stale/fallback로 처리
- 매매 컨트롤러는 최종 output만 읽고, provider 세부 구현에 직접 의존하지 않음
- UI 토글로 filter/risk scaling/fear-greed/ETF overlay를 각각 켜고 끌 수 있어야 함
- 주문 기록에는 당시의 시장 레짐 값을 스냅샷처럼 남겨 사후 분석에 사용

## 후속 과제
- Quotation Rate Limit을 더 엄격히 고려한 breadth 캐시 최적화
- `Remaining-Req` 헤더 반영 또는 호출량 동적 제어
- breadth 계산 종목 수/주기 조합에 대한 운영 프리셋 분리
