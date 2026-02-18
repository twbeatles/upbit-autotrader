# STRATEGY_OPTIONS_IMPLEMENTATION_PLAN

## 1) 전략 옵션 목록(실주문 가능/연구전용)

### 실주문 가능 (현물 롱온리)
- `volatility_breakout`
- `donchian_breakout`
- `ema_cross_trend`
- `time_series_momentum`
- `rsi_reversion`
- `bollinger_reversion`
- `zscore_reversion`
- `volatility_targeting` (포지션 크기 보정)
- `regime_filter` (진입 허용 필터)
- `drawdown_guard` (진입 차단 필터)

### 연구전용
- `pairs_trading_research`
  - 현재 주문 엔진은 현물 롱온리 기준이라, 페어/숏 전략은 백테스트/연구 레이어에서만 사용

## 2) 전략별 핵심 수식/규칙

### 2.1 추세/모멘텀
- `volatility_breakout`
  - 진입: `price >= target_price && price >= ma5`
- `donchian_breakout`
  - 진입: `price > max(high[-N:-1])`
  - 청산: `price < min(low[-N:-1])`
- `ema_cross_trend`
  - 진입: `EMA_fast > EMA_slow && EMA_fast 상승기울기`
  - 청산: 추세 역전 또는 MA 이탈
- `time_series_momentum`
  - 진입: `((P_t / P_{t-L}) - 1) * 100 >= threshold`

### 2.2 평균회귀
- `rsi_reversion`
  - 진입: `RSI <= oversold`
  - 청산: `RSI >= exit_rsi`
- `bollinger_reversion`
  - 진입: `price <= BB_lower`
  - 청산: `price >= BB_middle`
- `zscore_reversion`
  - 진입: `zscore <= entry_z`
  - 청산: `zscore >= exit_z`

### 2.3 리스크/메타
- `volatility_targeting`
  - 포지션 스케일: `scale = target_vol / realized_vol`
  - clamp 범위: `[min_scale, max_scale]`
- `regime_filter`
  - 허용 조건: `ADX >= min_adx` (+ MTF 조건 선택 적용)
- `drawdown_guard`
  - 차단 조건:
    - `daily_loss_pct <= -max_daily_loss_pct` 또는
    - `consecutive_losses >= max_consecutive_losses`

## 3) 엔진 실행 모드
- `single`
  - 선택 전략 1개 점수로 진입/청산
- `ensemble`
  - 활성 전략 점수의 가중평균
  - 진입 조건: `weighted_score >= ensemble_threshold`

## 4) 입력/출력 인터페이스
- 입력 스냅샷 필수 필드
  - `rsi`, `macd`, `signal`, `avg_volume`, `bb_upper/middle/lower`
  - `ema_fast/slow`, `ema_fast_prev`
  - `donchian_upper/lower`
  - `zscore`, `adx`, `realized_vol_pct`, `ts_momentum_pct`
- 출력
  - `StrategySignal(strategy_id, action, score, reasons)`

## 5) 페이퍼 트레이딩 설계
- 주문 API와 분리된 모의 체결 서비스(`UpbitPaperOrderService`)
- 비용 모델
  - 수수료: `fee_rate`
  - 슬리피지: `slippage_bps`
- 체결 결과 포맷은 live와 호환되는 order dict를 생성하여 기존 체결확인 로직 재사용

## 6) 기본 파라미터(초기값)
- 엔진
  - `use_strategy_engine=false`
  - `strategy_mode=single`
  - `single_strategy=volatility_breakout`
  - `ensemble_threshold=60`
- 리스크
  - `target_vol_pct=2.0`
  - `regime_min_adx=18`
  - `drawdown_guard_pct=5.0`
  - `max_consecutive_losses=3`
- 페이퍼
  - `paper_trading=false`
  - `paper_fee_bps=5.0`
  - `paper_slippage_bps=5.0`

## 7) 검증 체크리스트
- 기본 설정(엔진 OFF)에서 기존 매매 동작 회귀 없음
- 엔진 ON single/ensemble 각각 진입/청산 신호 일관성 확인
- paper mode에서 live API 주문 함수 호출 0건
- 백테스트 메뉴에서 전략 선택/실행 가능
- 설정 저장/로드 시 신규 키 유지 + 기존 키 무손상

## 8) 웹 근거 링크
- Upbit API Rate Limits: https://docs.upbit.com/kr/reference/rate-limits
- Upbit 주문 생성 API: https://docs.upbit.com/kr/reference/new-order
- pyupbit 문서: https://pyupbit.readthedocs.io/en/latest/
- Time Series Momentum: https://www.sciencedirect.com/science/article/pii/S0304405X11002613
- Volatility-Managed Portfolios: https://www.nber.org/papers/w22208
- Risk and Return of Cryptocurrency: https://www.nber.org/papers/w24877
- Momentum crashes/regime risk: https://www.nber.org/papers/w16429
- Pairs Trading reference: https://academic.oup.com/rfs/article-abstract/19/3/797/1646694
