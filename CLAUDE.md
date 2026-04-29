# Upbit Pro Algo-Trader 개발 가이드

이 문서는 Claude/Codex 작업자가 프로젝트를 수정할 때 따라야 할 기준입니다.

## 현재 구조 요약

```txt
upbit_autotrader/
  app/
    trader.py                  # 공개 앱 클래스
    bootstrap_ops.py           # 초기 상태, 로깅, 타이머
    runtime_ops.py             # 가격 및 시장 레짐 스레드 수명주기
  controllers/
    ui_controller.py           # UI facade
    trading_controller.py      # 매매 facade
    settings_controller.py
    history_controller.py
    batch_controller.py
    trading_parts/             # account, lifecycle, order, execution, signal, risk
    ui_parts/                  # layout, dashboard, strategy, menu, preset, advanced tab
  services/                    # settings, security, order, paper order, holdings, rate-limit
  strategies/                  # engine, catalog, legacy strategy, meta signal
  risk/, execution/, market_regime/, runtime/
  analytics/, backtesting/, notifications/, ui/
```

루트 실행 진입점은 `upbit_trader.py`만 유지합니다. 새 구현은 `upbit_autotrader.*` 경로에 추가하고, 이전 import 호환은 `legacy_wrappers/`에 둡니다.

## 호환성 원칙

- 실행 진입점: `python upbit_trader.py`
- 공개 클래스: `UpbitProTrader`
- 설정 schema: `settings_version = 2`
- 배포 spec: `upbit_trader.spec`
- 기존 attribute 이름, settings key, legacy wrapper import 경로를 가능한 유지합니다.
- 신규 안전 기능은 기본 OFF 또는 경고 중심으로 추가합니다.

## 주문 및 실행

- live 주문은 `UpbitOrderService`, paper 주문은 `UpbitPaperOrderService`를 사용합니다.
- 컨트롤러 공개 주문 경로는 `_place_buy_order`, `_place_sell_order`입니다.
- 실행 모델은 `single_market`과 `twap_market`을 지원합니다.
- pending 상태, reconciliation store, manual review 큐를 함께 갱신해야 합니다.
- 주문 가능 여부는 `orders/chance` 기반으로 시장 상태, 주문 타입, 최소 주문 금액, 수수료를 검증합니다.
- trade history에는 예상 수수료, 실제 수수료, 예상/실현 슬리피지, execution mode, strategy/meta/market regime 필드를 남깁니다.

## 리스크 및 시장 레짐

- 포지션 사이징과 daily loss는 현재 equity 기준을 사용합니다.
- equity는 KRW 현금, 예약 KRW, 보유 평가액을 합산해 계산합니다.
- `initial_balance`는 호환용으로 남기되 신규 리스크 계산의 주 기준으로 사용하지 않습니다.
- `use_market_regime_filter`가 켜져 있으면 시장 레짐 점수가 기준 미만일 때 BUY를 차단합니다.
- `fail_closed_on_stale_market_regime`이 켜져 있으면 핵심 레짐 데이터가 stale/error일 때 신규 진입을 차단합니다.
- 시장 레짐 관련 코드는 `market_regime/engine.py`, `market_regime/providers.py`, `runtime/market_regime_thread.py`, `controllers/trading_parts/market_regime_ops.py`에 분리되어 있습니다.

## UI 및 설정

- advanced tab 수정은 `controllers/ui_parts/advanced_tab/*` builder를 우선 수정합니다.
- settings key 추가 시 `controllers/settings_field_specs.py`에 반드시 FieldSpec을 추가합니다.
- tooltip은 `Config.TOOLTIPS`에 추가합니다.
- `ui_controller.py`와 `trading_controller.py`는 facade 역할을 유지합니다.

## 검증

```bash
python -m pytest -q
python -m pyright
pre-commit run --all-files
```

구조나 문서를 바꾸면 아래 테스트를 우선 확인합니다.

- `tests/test_docs_references.py`
- `tests/test_text_integrity.py`
- `tests/test_structure_guards.py`
- `tests/test_refactor_module_wrappers.py`
- `tests/test_trader_surface_parity.py`
- `tests/test_trading_parts_facade_parity.py`
- `tests/test_ui_advanced_tab_surface.py`

주문/리스크/시장 레짐을 바꾸면 아래 테스트도 함께 확인합니다.

- `tests/test_order_stability.py`
- `tests/test_trader_order_flows.py`
- `tests/test_order_reconciliation_recovery.py`
- `tests/test_execution_model.py`
- `tests/test_position_sizing.py`
- `tests/test_portfolio_risk_engine.py`
- `tests/test_market_regime_engine.py`
- `tests/test_market_regime_providers.py`
- `tests/test_market_regime_controller_integration.py`

## 작업 주의사항

- 주문 로직 변경 시 pending lifecycle, reserved KRW, reconciliation dirty flag를 함께 확인합니다.
- TWAP 변경 시 slice 최소 주문 금액과 fallback metadata를 검증합니다.
- 외부 데이터 실패는 neutral fallback과 fail-closed 옵션을 구분해서 처리합니다.
- 문서 수정 시 `README.md`, `CLAUDE.md`, `GEMINI.md`, `IMPLEMENTATION_GAP_REVIEW_2026-04-27.md` 간 참조가 깨지지 않게 유지합니다.
- `upbit_trader.spec`는 `collect_submodules("upbit_autotrader")` 기반이므로 대부분 새 모듈 추가는 자동 수집됩니다.

## 참고 문서

- `IMPLEMENTATION_GAP_REVIEW_2026-04-27.md`
- `legacy_wrappers/README.md`
