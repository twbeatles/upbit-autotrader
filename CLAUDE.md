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
- `tests/test_upbit_native_client.py`
- `tests/test_upbit_websocket.py`
- `tests/test_upbit_candles_orderbook.py`
- `tests/test_orderbook_guard.py`
- `tests/test_orderbook_guard_integration.py`
- `tests/test_price_thread_concurrency.py`
- `tests/test_security_cross_platform.py`
- `tests/test_tick_rules.py`
- `tests/test_order_api_extensions.py`

## 작업 주의사항

- 주문 로직 변경 시 pending lifecycle, reserved KRW, reconciliation dirty flag를 함께 확인합니다.
- TWAP 변경 시 slice 최소 주문 금액과 fallback metadata를 검증합니다.
- 외부 데이터 실패는 neutral fallback과 fail-closed 옵션을 구분해서 처리합니다.
- 문서 수정 시 `README.md`, `CLAUDE.md`, `GEMINI.md`, `IMPLEMENTATION_GAP_REVIEW_2026-04-27.md` 간 참조가 깨지지 않게 유지합니다.
- `upbit_trader.spec`는 `collect_submodules("upbit_autotrader")` 기반이므로 대부분 새 모듈 추가는 자동 수집됩니다.

## 참고 문서

- `IMPLEMENTATION_GAP_REVIEW_2026-04-27.md`
- `legacy_wrappers/README.md`

<!-- SPECKIT-AGENT-GUIDE:START -->

## Spec Kit / Spec-Driven Development (AI 에이전트 필독)

> 이 블록은 GitHub Spec Kit 활성화 및 기능 명세 작업 결과를 AI 에이전트가 바로 쓰도록 정리한 안내입니다.
> 수정 시 마커 주석을 유지하세요. 스크립트/후속 세션이 이 구간을 갱신합니다.

### 이 저장소 상태

- **프로젝트**: `upbit-autotrader`
- **Spec Kit 초기화**: `.specify/ 있음`
- **에이전트 스킬**: Grok=True, Claude=True, Codex/Agy(.agents)=True
- **활성 기능**: 아직 `specs/` 기능 명세 없음 — `.specify/` 만 준비된 상태

### 에이전트가 먼저 읽을 파일

1. `.specify/` 및 `.grok/skills` / `.claude/skills` / `.agents/skills` 의 `speckit-*`
2. 기능 작업 시작 시 `/speckit-specify` 로 `specs/00N-...` 생성

### 권장 워크플로 (스킬 / 슬래시 커맨드)

| 단계 | 커맨드 (Grok/Claude 등) | 산출 |
|------|-------------------------|------|
| 원칙 | `/speckit-constitution` | `.specify/memory/constitution.md` |
| 명세 | `/speckit-specify` | `specs/<id>/spec.md` |
| 계획 | `/speckit-plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 작업 | `/speckit-tasks` | `tasks.md` |
| 구현 | `/speckit-implement` | 코드 (tasks 순서) |
| 갭점검 | `/speckit-converge` | `tasks.md` 에 Phase Convergence **append-only** |

- Codex skills 모드: `$speckit-specify` 형태일 수 있음
- 스킬 파일: `.grok/skills/speckit-*/SKILL.md`, `.claude/skills/speckit-*/SKILL.md`

### 작업 규칙 (에이전트)

1. **새 기능/큰 변경 전** 활성 `spec.md`·`tasks.md` 를 읽고, 없으면 specify→plan→tasks 순으로 만든다.
2. **구현은 tasks.md 체크리스트**를 따른다. 완료 시 `- [ ]` → `- [x]`.
3. **`/speckit-converge` 는 tasks.md 를 rewrite 하지 않는다** — 잔여 갭만 하단 Phase 로 append.
4. brownfield 프로젝트는 상당 기능이 이미 있을 수 있다. 중복 구현 전에 코드·`[x]` 태스크를 확인한다.
5. 웹/데스크톱 패리티 등 **out-of-scope Assumptions** 는 새 feature 로 분리하는 것을 선호한다.
6. 기본 integration 은 **grok** 이며, 동일 레포에 claude / codex / agy 스킬도 multi-install 되어 있을 수 있다.

### 관련 링크

- Spec Kit: https://github.com/github/spec-kit
- 로컬 CLI: `specify` (uv tool, 버전은 `specify version`)

<!-- SPECKIT-AGENT-GUIDE:END -->
