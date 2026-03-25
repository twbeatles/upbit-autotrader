# Upbit AutoTrader 구조 분석 및 Market Regime 확장 설계

작성일: 2026-03-25  
기준 저장소: `upbit-autotrader`  
범위: market regime 설계 문서 + 2026-03-25 후속 구현 상태 메모

## 0. 후속 구현 상태 메모

- 본 문서의 설계안은 현재 코드에 반영되어 `upbit_autotrader/market_regime/`, `upbit_autotrader/runtime/market_regime_thread.py`, `upbit_autotrader/controllers/trading_parts/market_regime_ops.py`, `upbit_autotrader/controllers/ui_parts/advanced_tab/market_regime_group.py`가 실제 구현된 상태다.
- `upbit_autotrader/app/trader.py`, `upbit_autotrader/controllers/trading_controller.py`, `upbit_autotrader/controllers/ui_controller.py`, `upbit_autotrader/controllers/ui_sections.py`, `upbit_autotrader/controllers/trading_parts/indicator_ops.py`는 facade로 축소되었고 실제 책임은 `app/bootstrap_ops.py`, `app/runtime_ops.py`, `controllers/trading_parts/*`, `controllers/ui_parts/*`, `controllers/trading_parts/indicator_parts/*`로 분리되었다.
- 현재 구조 가드 기준은 `trading_controller<=1800`, `ui_controller<=500`, `ui_sections<=260`, `indicator_ops<=220`, `app/trader<=280`이다.
- `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`가 추가되어 `tests/test_docs_references.py`의 문서 참조 조건도 현재 충족한다.
- 아래 본문 중 대형 컨트롤러 line 수치, 미구현 표현, 문서 가드 실패 설명은 설계 시점 baseline을 남긴 부분이다. 현재 코드 해석은 이 메모와 `README.md`, `CLAUDE.md`, `GEMINI.md`를 우선 기준으로 본다.

## 1. 문서 목적

이 문서는 현재 프로젝트 구조를 실제 코드 기준으로 재정리하고, 코인시장 실시간 동향을 기존 자동매매 알고리즘에 안전하게 붙이기 위한 `market_regime` 확장 설계를 하나의 문서로 고정하기 위해 작성한다.

핵심 목표는 다음 3가지다.

1. 현재 프로젝트의 실행 흐름과 책임 분리를 빠르게 파악할 수 있게 한다.
2. 2026-03-25 기준 시장 레짐을 요약하고, 어떤 종류의 외부 신호를 붙여야 하는지 방향을 고정한다.
3. 기존 전략 엔진, 메타 시그널, 리스크 사이징 구조를 훼손하지 않고 `market_regime_score`를 통합하는 구현 계획을 결정 완료 상태로 남긴다.

## 2. 현재 프로젝트 구조 분석

### 2.1 전체 의존 흐름

현재 저장소의 주 실행 경로는 아래 흐름으로 이해하는 것이 가장 정확하다.

```text
upbit_trader.py
  -> upbit_autotrader/app/trader.py
    -> controllers/
      -> services/
      -> strategies/
      -> risk/
      -> execution/
      -> runtime/
      -> ui/
      -> analytics/
      -> backtesting/
```

실제 엔트리포인트는 루트 `upbit_trader.py` 하나만 유지되고, 앱 본체는 `upbit_autotrader/app/trader.py`의 `UpbitProTrader`가 담당한다. 이 클래스는 다음 믹스인 컨트롤러를 조합하는 퍼사드다.

- `TraderUIController`
- `TraderSettingsController`
- `TraderHistoryController`
- `TraderTradingController`
- `TraderBatchController`

즉, 앱 구조는 "단일 메인 윈도우 + 컨트롤러 믹스인 + 도메인 모듈" 패턴에 가깝다.

### 2.2 모듈별 책임

#### `app/`

- `app/trader.py`
  - `UpbitProTrader` 퍼사드
  - 서비스, 전략 엔진, 가격 스레드, 타이머, 트레이 아이콘, 종료 처리 관리
  - 런타임 상태 보관

#### `controllers/`

- `ui_controller.py`
  - 메인 화면 조립
  - 대시보드, 전략 탭, 고급 설정 탭, 통계 탭, 히스토리 탭, 운영 탭 생성
- `ui_sections.py`
  - 고급 설정 탭의 실제 위젯 구성
  - 신규 설정을 붙일 때 가장 먼저 수정해야 하는 UI 표면
- `settings_controller.py`
  - 설정 저장/로드
  - Discord/복구 등 런타임 통합 설정 반영
- `history_controller.py`
  - 거래 기록 저장, 테이블 표시, CSV 내보내기, 분석 리포트 생성
- `trading_controller.py`
  - 실시간 가격 수신
  - 진입/청산 판정
  - 주문 실행
  - pending/reconciliation/manual review/risk/eecution/meta 통합

#### `controllers/trading_parts/`

- `indicator_ops.py`
  - OHLCV 기반 지표 계산 및 스냅샷 캐시
- `risk_ops.py`
  - 포트폴리오 리스크 스냅샷 및 진입 차단 로직
- `session_ops.py`
  - 자동매매 시작/중지와 유니버스 초기화
- `manual_review_ops.py`
  - 수동검토 큐

`trading_controller.py`가 매우 크기 때문에 일부 기능만 `trading_parts/`로 분리되어 있다. 새 기능도 같은 방향으로 분리하는 것이 맞다.

#### `services/`

- `order_service.py`, `paper_order_service.py`
  - 실주문/페이퍼 주문 추상화
- `holdings_service.py`
  - 보유 종목 조회 보조
- `settings_store.py`
  - `upbit_settings.json` 저장
  - `settings_version = 2`
  - API 키는 DPAPI로 암호화 저장

#### `strategies/`

- `engine.py`
  - single / ensemble 전략 점수화
  - entry/exit evaluation
  - 변동성 타게팅, 레짐 필터, 드로우다운 가드 포함
- `catalog.py`
  - 전략 메타데이터
- `meta_signal.py`
  - 전략 성과 기반 기대값 추적
  - 메타 게이트 계산

#### `risk/`

- `portfolio_risk.py`
  - 포트폴리오 단위 리스크 스냅샷
  - 상관 익스포저, 드로우다운 상태 계산
- `position_sizing.py`
  - 리스크 예산 기반 사이징
  - Kelly 보정
  - 드로우다운 상태 배수

#### `execution/`

- `execution_model.py`
  - 예상 슬리피지
  - TWAP 분할 계획
  - 손익분기 비용 계산

#### `runtime/`

- `price_thread.py`
  - `pyupbit.get_current_price()` 기반 1초 폴링
  - WebSocket 아님

#### `analytics/`, `backtesting/`, `ui/`, `notifications/`

- 보고서/백테스트/다이얼로그/알림 채널 담당

#### `legacy_wrappers/`

- 과거 호환 래퍼 보관
- 신규 코드 기준 경로는 아님

### 2.3 핵심 실행 흐름

현재 매매 경로는 아래 순서로 읽는 것이 맞다.

1. `UpbitProTrader.start_trading()` 호출
2. `controllers/trading_parts/session_ops.py`에서 유니버스 초기화
3. `runtime/price_thread.py`가 1초마다 현재가 폴링
4. `TraderTradingController.on_price_update()`가 각 티커 현재가를 반영
5. `TraderTradingController._check_buy_condition()` 또는 `_check_sell_condition()` 실행
6. 진입 시 `execute_buy()`, 청산 시 `execute_sell()`
7. 주문 상태는 pending/reconciliation/manual review로 후속 관리

현재 구조에서 진입 의사결정의 병목은 명확하게 `upbit_autotrader/controllers/trading_controller.py`의 `_check_buy_condition()`이다. 여기에 아래 로직이 대부분 응축되어 있다.

- 기존 목표가/MA 하드 게이트
- RSI/MACD/거래량 필터
- 리스크 한도 체크
- 진입 점수 체크
- 전략 엔진(single/ensemble)
- 메타 시그널 게이트
- 최종 주문 실행

즉, 외부 시장 동향을 매수에 반영하려면 `_check_buy_condition()` 앞뒤로 억지로 흩뿌리기보다, "전략 엔진 이후, 메타 시그널 이전" 또는 "메타 시그널 내부 입력값 확장"으로 넣는 것이 가장 자연스럽다.

### 2.4 현재 구조에서 중요한 구현 포인트

#### 가격 피드

`runtime/price_thread.py`는 WebSocket이 아니라 REST 폴링이다.

- 장점: 단순함, 구현 난도 낮음
- 단점: 초당 반복 호출 구조라 시장 전체 레짐 신호까지 같은 스레드에 얹으면 API 비용과 지연이 커짐

따라서 시장 레짐 데이터는 기존 `price_thread.py`에 얹지 않고 별도 `market_regime_thread.py`로 분리하는 것이 맞다.

#### 설정 저장 경로

설정은 다음 흐름으로 저장된다.

```text
TraderSettingsController.save_settings()
  -> collect_settings_from_specs()
  -> services/settings_store.py::save_settings()
  -> upbit_settings.json
```

즉, 신규 설정 키는 최소 아래 3곳을 맞추면 된다.

- `core/config.py`
- `controllers/settings_field_specs.py`
- `controllers/ui_sections.py`

#### 거래 기록 확장성

`history_controller.py`의 `add_trade_record()`는 `**extra_fields`를 받아 optional 필드를 그대로 저장한다. 또한 CSV export도 기본 필드 외 추가 필드를 자동 확장한다.

따라서 아래 필드는 낮은 리스크로 추가 가능하다.

- `market_regime_score`
- `market_regime_label`
- `market_regime_ts`

#### 컨트롤러 크기 한계

후속 리팩토링 반영 후 facade 파일 길이는 다음과 같다.

- `upbit_autotrader/controllers/trading_controller.py`: 375 lines
- `upbit_autotrader/controllers/ui_controller.py`: 125 lines
- `upbit_autotrader/controllers/ui_sections.py`: 45 lines
- `upbit_autotrader/controllers/trading_parts/indicator_ops.py`: 67 lines
- `upbit_autotrader/app/trader.py`: 59 lines

구조 가드 테스트 기준은 아래다.

- `trading_controller.py` 최대 1800 lines
- `ui_controller.py` 최대 500 lines
- `ui_sections.py` 최대 260 lines
- `indicator_ops.py` 최대 220 lines
- `app/trader.py` 최대 280 lines

즉, 시장 레짐과 후속 기능은 facade 안에 직접 누적하지 않고 helper 패키지로 계속 분리해야 한다.

### 2.5 현재 테스트/문서 가드 상태

최근 정합성 점검 기준으로 아래 테스트 묶음을 통과하는 구성을 유지한다.

- `tests/test_docs_references.py`
- `tests/test_text_integrity.py`
- `tests/test_structure_guards.py`
- `tests/test_market_regime_engine.py`
- `tests/test_market_regime_providers.py`
- `tests/test_market_regime_controller_integration.py`
- `tests/test_meta_signal.py`
- `tests/test_trader_order_flows.py`
- `tests/test_order_stability.py`
- `tests/test_plan_implementation_fixes.py`
- `tests/test_trader_surface_parity.py`
- `tests/test_refactor_module_wrappers.py`
- `tests/test_indicator_facade_parity.py`
- `tests/test_trading_parts_facade_parity.py`
- `tests/test_ui_advanced_tab_surface.py`

## 3. 2026-03-25 시장 컨텍스트 요약

### 3.1 요약 판단

2026-03-25 기준 시장 해석은 다음 문장으로 고정한다.

`BTC 주도, 알트 확산 둔화, 레버리지 완화`

이 판단은 감성적 문장이 아니라 아래 수치를 묶은 운영 해석이다.

### 3.2 근거 수치

#### CoinMarketCap 기준

- 글로벌 크립토 시가총액: 약 `2.43T USD`
- 24시간 거래대금: 약 `55.52B USD`
- stablecoin 24시간 거래대금 비중: `95.91%`
- BTC dominance: `58.81%`

운영 해석:

- BTC dominance가 높은 수준에 있고
- stablecoin 비중이 높으며
- 전체 거래대금이 약한 구간이면
- 시장 전체가 강한 알트 확산장보다 "선별적 위험 선호"에 가깝다

#### Farside BTC ETF 흐름 기준

2026년 3월 중순 데이터에서 확인 가능한 흐름:

- 2026-03-16: `+199.4M`
- 2026-03-17: `+199.4M`
- 2026-03-18: `-163.5M`
- 2026-03-19: `-90.2M`

운영 해석:

- 3월 중순에 순유입이 유지되다가
- 2026-03-18 이후 순유출로 반전
- 현물 ETF 자금 흐름이 위험자산 확산보다는 방어적으로 전환되는 신호로 읽힌다

#### Farside Basis 기준

- 2026년 3월 aggregate BTC futures basis annualised rate: `0.3%`

운영 해석:

- 선물 프리미엄이 낮다
- 공격적 레버리지 확장이 아닌, 과열이 식은 상태에 가깝다

### 3.3 운영 결론

현재 시장 해석상 단순 추세 돌파 신호만으로 알트 진입 크기를 키우는 것은 보수적으로 봐야 한다. 따라서 기존 알고리즘에 필요한 것은 뉴스 요약 자체가 아니라 다음 2가지다.

1. 시장이 `risk_on / neutral / defensive` 중 어디인지 점수화하는 전역 레짐 신호
2. 그 점수를 매수 게이트와 포지션 크기 조절에 함께 반영하는 구조

## 4. Market Regime 확장 설계

### 4.1 설계 원칙

- 기본 동작 유지: 신규 기능 기본값은 모두 `OFF`
- 무료 공개 소스 우선
- 외부 데이터 실패 시 매매 전체를 멈추지 않고 internal-only 계산으로 degrade
- 가격 피드와 시장 레짐 피드를 분리
- 새 기능은 기존 `strategy_engine`, `meta_signal`, `position_sizing`과 충돌하지 않게 overlay 방식으로 추가

### 4.2 1단계와 2단계 범위

#### 1단계: 기본 레짐 점수

아래 3개만 사용한다.

- `Upbit 시장 폭(local breadth)`
- `KRW-BTC 추세/실현변동성`
- `Fear & Greed`

#### 2단계: 선택적 외부 오버레이

아래 2개를 추가한다.

- `BTC ETF net flow`
- `BTC dominance`

2단계는 스크래핑/외부 페이지 구조 변경 리스크가 있으므로 선택 기능으로만 둔다.

### 4.3 신규 패키지/모듈 구조

신규 기능은 아래 경로로 분리하는 것이 맞다.

```text
upbit_autotrader/
  market_regime/
    __init__.py
    engine.py
    providers.py
  runtime/
    market_regime_thread.py
```

각 파일 책임은 아래처럼 고정한다.

#### `upbit_autotrader/market_regime/engine.py`

- `MarketRegimeSnapshot`
- `MarketRegimeOutput`
- 점수 계산 함수
- stale component 재가중치 로직
- 라벨/리스크 배수 결정 로직

#### `upbit_autotrader/market_regime/providers.py`

- Upbit breadth provider
- KRW-BTC trend/vol provider
- Alternative.me Fear & Greed fetcher
- 선택적 ETF flow / BTC dominance fetcher

#### `upbit_autotrader/runtime/market_regime_thread.py`

- 60초 주기 비동기 갱신
- UI/주문 흐름과 분리된 백그라운드 캐시 갱신
- 실패 시 마지막 정상 스냅샷 유지

## 5. 데이터 계약과 점수 계산

### 5.1 `MarketRegimeSnapshot`

아래 형태로 고정한다.

```python
@dataclass
class MarketRegimeSnapshot:
    as_of: str
    local_breadth_score: float
    btc_trend_vol_score: float
    fear_greed_score: float | None
    etf_flow_score: float | None = None
    btc_dominance_score: float | None = None
    stale_components: list[str] = field(default_factory=list)
    source_status: dict[str, str] = field(default_factory=dict)
```

설계 원칙:

- 점수는 모두 `0~100`
- 외부 신호는 없을 수 있으므로 `None` 허용
- stale 여부는 명시적으로 남긴다

### 5.2 `MarketRegimeOutput`

```python
@dataclass
class MarketRegimeOutput:
    market_regime_score: float
    risk_multiplier: float
    label: str
    stale_components: list[str] = field(default_factory=list)
    details: dict[str, float] = field(default_factory=dict)
```

필수 산출물:

- `market_regime_score`
- `risk_multiplier`
- `label`
- `stale_components`

### 5.3 1단계 점수 구성

1단계 기본 가중치는 아래로 고정한다.

- `local_breadth`: `40%`
- `btc_trend_vol`: `35%`
- `fear_greed`: `25%`

수식:

```text
market_regime_score
  = 0.40 * local_breadth_score
  + 0.35 * btc_trend_vol_score
  + 0.25 * fear_greed_score
```

단, 일부 컴포넌트가 stale 이거나 fetch 실패이면 정상 컴포넌트만으로 재정규화한다.

예시:

- Fear & Greed 실패 시
  - 사용 가중치 합 = `0.75`
  - 최종 점수 = `(0.40 * breadth + 0.35 * btc) / 0.75`
  - `stale_components = ["fear_greed"]`

### 5.4 `local_breadth_score` 산식

아래 규칙으로 고정한다.

1. Upbit KRW 마켓 티커를 조회한다.
2. 24시간 거래대금 기준 상위 `market_regime_top_n` 종목을 선택한다. 기본값은 `20`.
3. 각 종목에 대해 `minute240` 기준 최근 30캔들을 조회한다.
4. 각 종목에 대해 아래 두 조건을 계산한다.
   - 최근 종가가 20기간 이동평균 위인지
   - 최근 1캔들 수익률이 양수인지
5. 폭 점수는 아래로 계산한다.

```text
above_ma_ratio = MA20 위 종목 비율
positive_ratio = 직전 4시간 수익률 양수 종목 비율

local_breadth_score = 60 * above_ma_ratio + 40 * positive_ratio
```

이 산식을 택한 이유:

- 너무 복잡하지 않다
- 외부 API 없이 계산 가능하다
- 시장 확산 여부를 직관적으로 반영한다

### 5.5 `btc_trend_vol_score` 산식

`KRW-BTC`의 `minute240` 기준으로 아래 룰을 고정한다.

점수 요소:

- EMA12 > EMA26 이면 `55점`, 아니면 `20점`
- EMA12 기울기 양수면 `20점`, 아니면 `0점`
- 20구간 실현변동성 보정 `25점 만점`

실현변동성 점수 룰:

- `<= 4.0%`: `25점`
- `<= 6.0%`: `15점`
- `<= 8.0%`: `5점`
- `> 8.0%`: `0점`

최종:

```text
btc_trend_vol_score = trend_score + slope_score + volatility_score
```

해석:

- BTC 추세가 살아 있고
- 단기 기울기가 양수이며
- 변동성이 과열되지 않았을수록 높은 점수

### 5.6 `fear_greed_score`

Alternative.me의 Fear & Greed Index를 그대로 `0~100` 점수로 사용한다.

단, 아래 기준으로 stale 처리한다.

- fetch 실패
- 응답 파싱 실패
- 마지막 업데이트 기준 `12시간` 초과

### 5.7 2단계 오버레이

2단계는 아래 방식으로만 추가한다.

#### `etf_flow_score`

- 최근 3거래일 BTC ETF net flow의 부호와 방향성만 사용
- 점수 규칙:
  - 3일 합계 양수: `70`
  - 3일 합계 중립: `50`
  - 3일 합계 음수: `30`

#### `btc_dominance_score`

- dominance 해석은 "무조건 높을수록 좋다"가 아니다
- 설계 기준:
  - `50~58%`: `60`
  - `58~62%`: `55`
  - `< 50%`: `45`
  - `> 62%`: `40`

이유:

- dominance가 너무 낮으면 BTC 리더십 약화
- dominance가 너무 높으면 알트 확산 부재
- 중간 구간을 상대적으로 선호

#### 2단계 합성 방식

2단계는 1단계 점수를 덮어쓰지 않고 `global_overlay_score`로만 추가한다.

```text
global_overlay_score = 0.60 * etf_flow_score + 0.40 * btc_dominance_score
final_market_regime_score = 0.85 * phase1_score + 0.15 * global_overlay_score
```

활성 조건:

- `market_regime_use_etf_flow = True`

이 플래그 하나로 ETF flow와 BTC dominance 오버레이를 함께 켠다.

## 6. 라벨과 리스크 배수

최종 점수에 따른 레이블과 주문 비중 배수는 아래로 고정한다.

| 점수 구간 | label | risk_multiplier |
|---|---|---|
| `< 40` | `defensive` | `0.50` |
| `40 <= score < 55` | `neutral` | `0.75` |
| `55 <= score < 70` | `risk_on` | `1.00` |
| `>= 70` | `risk_on` | `1.15` |

운영 정책:

- `use_market_regime_filter`가 켜져 있으면 `market_regime_score < market_regime_min_score`에서 BUY 차단
- `use_market_regime_risk_scaling`이 켜져 있으면 포지션 사이징 이후 `risk_multiplier`를 한 번 더 곱한다

## 7. 코드 통합 지점

### 7.1 `app/trader.py`

다음 상태를 `UpbitProTrader.__init__()`에 추가하는 방향으로 설계한다.

- `self.market_regime_snapshot = None`
- `self.market_regime_snapshot_ts = 0.0`
- `self.market_regime_thread = None`

수명주기:

- 앱 초기화 시 thread 객체 생성
- `start_trading()`에서 시작
- `stop_trading()`과 `closeEvent()`에서 안전 종료

### 7.2 `runtime/market_regime_thread.py`

동작 규칙:

- 기본 주기 `60초`
- 내부적으로 provider 호출 후 `MarketRegimeOutput` 계산
- 성공 시 최신 결과 emit
- 실패 시 예외를 로그하고 이전 결과 유지
- 가격 스레드와 별도 동작

이 스레드는 `price_thread.py`를 대체하지 않는다. 역할이 다르다.

### 7.3 `trading_controller.py`

#### 매수 경로 통합 순서

`_check_buy_condition()`의 통합 순서는 아래로 고정한다.

1. 기존 목표가/MA 하드 게이트
2. RSI/MACD/거래량 필터
3. `check_risk_limits()`
4. 진입 점수 체크
5. 전략 엔진 체크
6. `market_regime_filter` 체크
7. 메타 시그널 체크
8. `execute_buy()`

#### 이유

- 전략 엔진이 먼저 개별 종목의 국지적 신호를 만든다
- market regime는 그 신호에 대한 전역 overlay 역할을 한다
- 메타 시그널은 전략 성과와 시장 레짐을 함께 묶는 최종 게이트가 된다

### 7.4 `meta_signal.py`

기존 `MetaSignalInput`에는 `regime_score`가 있다. 현재는 ADX/실현변동성 기반의 기술적 레짐 점수만 들어간다.

확장 후에는 아래 형태로 고정한다.

```python
@dataclass
class MetaSignalInput:
    strategy_id: str
    engine_score: float
    technical_regime_score: float = 50.0
    market_regime_score: float = 50.0
    min_expectancy: float = 0.0
    score_threshold: float = 60.0
```

메타 점수 가중치는 아래로 재정의한다.

```text
meta_score
  = 0.50 * engine_score
  + 0.20 * expectancy_score
  + 0.15 * technical_regime_score
  + 0.15 * market_regime_score
```

이렇게 하면 현재 기술적 레짐 점수를 유지하면서도, 외부 시장 상태를 15% 비중으로 명시적으로 반영할 수 있다.

### 7.5 `execute_buy()`에서의 비중 축소/확대

현재 `execute_buy()`는 아래 순서로 주문금액을 정한다.

1. 기본 betting ratio
2. 전략 엔진 변동성 타게팅
3. 리스크 예산 기반 사이징
4. 실행 모델 슬리피지 가드

여기에 `market_regime`를 붙일 위치는 아래로 고정한다.

```text
리스크 예산 기반 사이징 완료
  -> market regime risk multiplier 적용
  -> execution_model.plan_execution()
```

이 배치를 택한 이유:

- 리스크 예산 계산 결과를 존중한다
- 시장 레짐이 최종 주문 크기를 조절한다
- 이후 슬리피지 가드가 마지막 안전장치 역할을 한다

## 8. 설정/UI 변경 계획

신규 설정은 아래 키로 고정한다.

- `use_market_regime_filter = False`
- `use_market_regime_risk_scaling = False`
- `market_regime_min_score = 55.0`
- `market_regime_refresh_sec = 60`
- `market_regime_top_n = 20`
- `market_regime_use_fear_greed = True`
- `market_regime_use_etf_flow = False`

### 8.1 수정 대상 파일

- `upbit_autotrader/core/config.py`
- `upbit_autotrader/controllers/settings_field_specs.py`
- `upbit_autotrader/controllers/ui_sections.py`

### 8.2 UI 배치

고급 설정 탭에 신규 그룹 박스를 추가한다.

권장 그룹명:

- `🌐 시장 레짐 / 외부 신호`

포함 항목:

- 시장 레짐 필터 사용
- 시장 레짐 비중 스케일링 사용
- 최소 레짐 점수
- 갱신 주기(초)
- breadth 상위 종목 수
- Fear & Greed 사용
- ETF/Dominance 오버레이 사용

기존 구조상 이 그룹을 `메타 시그널 / 가중치 리밸런싱` 그룹 앞에 두는 편이 읽기 좋다. 이유는 시장 레짐이 메타 시그널의 입력이기 때문이다.

## 9. 거래 기록과 분석 필드

거래 기록 optional 필드는 아래 3개를 추가한다.

- `market_regime_score`
- `market_regime_label`
- `market_regime_ts`

추가 저장 위치:

- 매수 체결 기록
- 부분 매도 체결 기록
- 전체 매도 체결 기록

기존 `history_controller.py`가 extra field를 자동 직렬화하므로 저장 포맷 리스크는 낮다.

향후 `analytics/trading_analytics.py`에서 레짐별 성과 분석을 붙일 수 있는 여지가 생긴다.

## 10. 장애/리스크 설계

### 10.1 외부 데이터 실패

필수 정책:

- 외부 데이터 실패는 매매 엔진 전체 실패로 승격하지 않는다
- 실패 시 stale 표시만 남기고 internal-only score로 degrade 한다

예시:

- Fear & Greed 실패
  - breadth + BTC trend/vol만 사용
- ETF overlay 실패
  - 1단계 점수만 사용

### 10.2 스레드 분리

시장 레짐 fetch는 가격 스레드와 분리해야 한다.

이유:

- 가격 피드는 1초 주기
- 시장 레짐은 60초 주기
- 실패 성격과 재시도 전략이 다르다

### 10.3 API 사용량

폭 계산은 다수 종목 OHLCV를 조회하므로 호출량이 증가한다. 따라서 아래 제한을 함께 둔다.

- 기본 주기 `60초`
- 기본 상위 종목 수 `20`
- breadth 계산용 고정 타임프레임 `minute240`
- 실패 시 다음 주기까지 재시도 보류

### 10.4 문서 가드 상태

후속 문서 정리 반영 후 현재 문서 가드는 아래 기준으로 유지한다.

- `tests/test_docs_references.py`
- `tests/test_text_integrity.py`

즉, `README.md`, `CLAUDE.md`, `GEMINI.md`는 `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`, `legacy_wrappers/README.md`를 함께 참조하고, 텍스트 인코딩/깨짐 가드도 같이 통과하는 상태를 목표 기준으로 둔다.

## 11. 테스트 계획

추가 테스트 파일은 아래 3개로 고정한다.

- `tests/test_market_regime_engine.py`
- `tests/test_market_regime_providers.py`
- `tests/test_market_regime_controller_integration.py`

### 11.1 `test_market_regime_engine.py`

검증 항목:

- 1단계 점수 계산이 `40/35/25` 비중으로 동작하는지
- stale component 발생 시 가중치가 재정규화되는지
- 점수 구간별 `risk_multiplier`와 `label`이 정확한지
- 2단계 overlay 활성 시 최종 점수 보정이 적용되는지

### 11.2 `test_market_regime_providers.py`

검증 항목:

- Fear & Greed 응답 파싱
- 응답 누락/실패 시 stale 처리
- Upbit breadth 계산이 top N 기준으로 동작하는지
- 내부-only fallback 경로가 예외 없이 결과를 반환하는지

### 11.3 `test_market_regime_controller_integration.py`

검증 항목:

- `market_regime_score`가 최소 점수 미달이면 BUY가 차단되는지
- `use_market_regime_risk_scaling=True`일 때 주문금액이 배수만큼 조정되는지
- `MetaSignalInput` 확장 후 메타 점수에 `market_regime_score`가 반영되는지
- 설정 저장/로드 round-trip
- 거래기록 optional 필드 직렬화

## 12. 구현 순서 권장안

실제 구현은 아래 순서가 가장 안전하다.

1. `market_regime/engine.py` 단위 계산 로직과 테스트 작성
2. `market_regime/providers.py` 작성
3. `runtime/market_regime_thread.py` 작성
4. `app/trader.py`에 thread lifecycle 연결
5. `trading_controller.py`에 filter/risk scaling 연결
6. `meta_signal.py` 확장
7. `config.py`, `settings_field_specs.py`, `ui_sections.py` 수정
8. 거래 기록 extra field 반영
9. 통합 테스트 보강

이 순서를 택하면 계산 로직과 외부 fetch를 먼저 고정한 뒤 UI/컨트롤러는 마지막에 얹을 수 있다.

## 13. 후속 개선 권고

### 13.1 `price_thread.py`의 WebSocket 전환

권장 후속 작업:

- 현재 `runtime/price_thread.py`를 Upbit WebSocket 기반으로 교체
- REST 폴링은 fallback 또는 안전 모드로 유지

이 작업은 이번 설계와 분리해야 한다. 이유는 아래와 같다.

- 가격 피드 전환만으로도 영향 범위가 큼
- 주문/리스크/레짐 기능 추가와 동시에 진행하면 원인 분리가 어려움
- 운영 장애 시 rollback 지점이 불명확해짐

### 13.2 레짐별 성과 분석

거래기록에 레짐 필드가 추가되면 이후 아래 보고서가 가능하다.

- `defensive` 구간 승률
- `risk_on` 구간 평균 손익
- 전략별 레짐 적합도

이는 현재 `analytics/` 구조와 자연스럽게 연결된다.

## 14. 결론

현재 프로젝트는 이미 전략 엔진, 메타 시그널, 리스크 사이징, 실행 모델, 주문 복구까지 모듈화가 상당히 진행된 상태다. 따라서 "시장 동향 반영"의 정답은 뉴스 요약 기능 추가가 아니라, 전역 시장 상태를 정량 점수로 정규화해 기존 진입/사이징/메타 게이트에 얹는 것이다.

가장 적합한 확장 지점은 아래 3곳이다.

- `runtime`에 별도 `market_regime_thread`
- `strategies/meta_signal.py`의 입력 확장
- `trading_controller.execute_buy()`의 최종 주문금액 조절

이 설계는 현재 구조 가드 한계를 넘지 않으면서도, 2026-03-25 기준의 시장 특성인 `BTC 주도, 알트 확산 둔화, 레버리지 완화`를 실제 주문 판단에 반영할 수 있는 최소 확장안이다.

## 15. 참고 출처

- [CoinMarketCap](https://coinmarketcap.com/)
- [Farside BTC ETF flows](https://farside.co.uk/btc)
- [Farside basis](https://farside.co.uk/basis/)
- [Alternative.me API](https://alternative.me/crypto/api/)
- [Upbit WebSocket docs](https://docs.upbit.com/kr/docs/upbit-quotation-websocket)
