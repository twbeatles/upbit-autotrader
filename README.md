# Upbit Pro Algo-Trader

Upbit OpenAPI 기반 자동매매 데스크톱 프로그램입니다. 실행 진입점은 `upbit_trader.py`이고, 메인 애플리케이션 클래스는 `upbit_autotrader.app.trader.UpbitProTrader`입니다.

## 주요 기능

- 실시간 WebSocket 초저지연 시세 및 private(`myOrder`, `myAsset`) 이벤트 연동
- 업비트 공식 REST 클라이언트(SHA512 JWT 서명, 포켓별 Rate Limit 실시간 피드백)
- 호가창 스프레드 및 잔량 깊이(Depth) 분석 기반 슬리피지 사전 가드
- 최유리 지정가(`best`) 및 분할 주문(TWAP) 실행 모델
- 10단계 호가단위(Tick Size) 규칙 및 거래소 미체결 주문 자동 감지/복구
- 변동성 돌파 기반 레거시 전략과 strategy engine(`single` / `ensemble`)
- 시장 레짐 점수 기반 신규 진입 필터와 주문 금액 스케일링
- 리스크 예산 기반 포지션 사이징, Kelly 보정, drawdown 상태 제어
- pending 주문 추적, 주문 복구 상태 저장, 수동 검토 큐
- 페이퍼 트레이딩, 거래 내역 저장, 분석 리포트, 백테스트
- Discord 및 운영 이벤트 알림

확장 기능은 기존 호환성을 위해 대부분 기본값이 OFF입니다. 실거래 전에는 페이퍼 트레이딩으로 충분히 검증하는 것을 권장합니다.

## 요구사항

```txt
Python >= 3.10
PyQt6 >= 6.0
pyupbit >= 0.2.30
pandas
numpy
requests
websocket-client >= 1.6.0
PyJWT >= 2.8.0
```

## 설치 및 실행

```bash
pip install -r requirements.txt
python upbit_trader.py
```

## 프로젝트 구조

```txt
upbit_autotrader/
  app/                  # 부트스트랩, 런타임 스레드, 공개 앱 클래스
  controllers/          # UI, 설정, 히스토리, 매매 컨트롤러
  controllers/trading_parts/
                        # 주문, 체결, 리스크, 신호, 세션, 레짐 로직
  services/             # 설정, 보안, 주문, 보유 자산, rate-limit helpers
  strategies/           # 전략 엔진, 카탈로그, 레거시 전략, 메타 신호
  risk/                 # 포지션 사이징과 포트폴리오 리스크
  execution/            # 실행 모델과 주문 복구 저장소
  market_regime/        # 시장 레짐 엔진과 데이터 provider
  runtime/              # 가격 및 시장 레짐 스레드
  analytics/, backtesting/, notifications/, ui/
legacy_wrappers/        # 이전 import 경로 호환 래퍼
tests/                  # 회귀 및 구조 테스트
```

## 설정 및 로컬 파일

- 설정 파일: `upbit_settings.json`
- 프리셋: `upbit_presets.json`
- 거래 기록: `trade_history.json`
- 주문 복구 상태: `reconciliation_state.json`
- 전략 성과: `strategy_performance.json`
- 로그: `logs/`

API 키는 settings schema v2에서 DPAPI로 암호화 저장됩니다. 이전 plain-text 키는 마이그레이션 용도로만 읽고 다시 저장하지 않습니다.

## 검증

```bash
python -m pytest -q
python -m pyright
```

pre-commit을 사용할 수 있습니다.

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

문서와 텍스트 품질은 `tests/test_docs_references.py`, `tests/test_text_integrity.py`에서 확인합니다.

## 배포 빌드

```bash
pyinstaller --noconfirm --clean upbit_trader.spec
pyinstaller --noconfirm --clean --distpath upbit_dist --workpath upbit_build upbit_trader.spec
```

`upbit_trader.spec`는 `collect_submodules("upbit_autotrader")`를 사용해 새 모듈을 수집합니다.

## 운영 주의사항

1. 실거래 전 페이퍼 트레이딩으로 주문, 체결, 수수료, 슬리피지를 검증하세요.
2. live 모드에서는 주문 복구 상태 저장을 켜는 것을 권장합니다.
3. 시장 레짐 데이터가 stale일 때 보수적으로 운영하려면 `fail_closed_on_stale_market_regime` 옵션을 켜세요.
4. 프로그램 종료 시 자동매매는 중지되지만, 거래소에 이미 제출된 주문은 계좌 상태와 pending 복구 화면에서 확인해야 합니다.

## 참고 문서

- 구현 개선 리뷰: `IMPLEMENTATION_GAP_REVIEW_2026-04-27.md`
- 개발 가이드: `CLAUDE.md`, `GEMINI.md`
- legacy wrapper 안내: `legacy_wrappers/README.md`
