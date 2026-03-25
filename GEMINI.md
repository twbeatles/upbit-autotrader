# Upbit Pro Algo-Trader

업비트 OpenAPI 기반 자동매매 프로그램용 Gemini 작업 가이드입니다.

## 현재 상태 요약
- 메인 실행: `python upbit_trader.py`
- 공개 퍼사드: `upbit_autotrader.app.trader.UpbitProTrader`
- 호환성: 루트 엔트리포인트, 공개 클래스, settings schema, legacy wrapper 경로 유지
- 정책: 신규 기능 기본 `OFF`
- 타입 정합성: `upbit_autotrader/controllers/_type_support.py`에서 관리

## 패키지 구조(핵심)
```txt
upbit_autotrader/
  app/                # trader.py / bootstrap_ops.py / runtime_ops.py
  controllers/        # facade + trading_parts/ + ui_parts/
  services/
  strategies/         # meta_signal 포함
  risk/
  execution/
  market_regime/      # engine.py / providers.py
  core/
  runtime/            # price_thread.py / market_regime_thread.py
  analytics/
  backtesting/
  notifications/
  ui/
```

## 핵심 기능
- 전략 엔진(`single`, `ensemble`) + 게이트 정책(`engine_gate_policy`)
- 리스크 예산 기반 사이징과 포트폴리오 리스크 스냅샷
- 실행 모델 + TWAP 시장가 분할
- 메타 시그널 게이트(`technical_regime_score` + `market_regime_score`)
- 시장 레짐 필터/비중 스케일링과 외부 데이터 fallback
- 주문 상태머신 + timeout 복구 + manual review queue
- 거래기록 확장 필드 저장(수수료/슬리피지/세션/리스크/전략점수/시장레짐)

## 빌드(.spec)
- 파일: `upbit_trader.spec`
- 특징:
  - `collect_submodules("upbit_autotrader")`로 `app/`, `controllers/trading_parts/`, `controllers/ui_parts/`, `market_regime/`, `risk/`, `execution/`, `strategies/meta_signal.py` 등을 자동 수집

빌드 예시:
```bash
pyinstaller --noconfirm --clean upbit_trader.spec
pyinstaller --noconfirm --clean --distpath upbit_dist --workpath upbit_build upbit_trader.spec
```

## 테스트
실행:
```bash
python -m pytest -q
```

문서/구조/시장 레짐 정합성을 볼 때 우선 확인할 테스트:

- `tests/test_docs_references.py`
- `tests/test_text_integrity.py`
- `tests/test_structure_guards.py`
- `tests/test_market_regime_engine.py`
- `tests/test_market_regime_providers.py`
- `tests/test_market_regime_controller_integration.py`
- `tests/test_indicator_facade_parity.py`
- `tests/test_trading_parts_facade_parity.py`
- `tests/test_ui_advanced_tab_surface.py`

## 정적 타입 검사
실행:
```bash
python -m pyright
```

- 루트 `pyrightconfig.json`으로 VS Code Pylance와 CLI pyright 기준을 동일하게 유지합니다.

## 로컬 품질 점검
실행:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

- pre-commit 훅은 `tests/test_docs_references.py`, `tests/test_text_integrity.py`, `python -m pyright` 검사를 수행합니다.

## 문서
- 사용자 문서: `README.md`
- 개발 가이드: `CLAUDE.md`
- 리스크/정합성 점검: `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`
- 시장 레짐 설계/구현 메모: `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`
- 레거시 래퍼 안내: `legacy_wrappers/README.md`

## 작업 시 주의
1. 설정 변경 시 `settings_version=2` 호환성을 유지합니다.
2. 주문/체결 로직 수정 시 lifecycle 전이와 pending 정리를 같이 검증합니다.
3. 문서 수정 시 `README.md`, `CLAUDE.md`, `GEMINI.md`, `IMPLEMENTATION_RISK_REVIEW_2026-03-08.md`, `ARCHITECTURE_MARKET_REGIME_PLAN_2026-03-25.md`, `legacy_wrappers/README.md`를 함께 확인합니다.
