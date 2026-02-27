# Upbit Pro Algo-Trader v3.3.0

업비트 OpenAPI 기반 자동매매 프로그램 - Gemini 작업 가이드

## 현재 상태 요약
- 기준 버전: `v3.3.0` (2026-02-27)
- 메인 실행: `python upbit_trader.py`
- 내부 구조: `upbit_autotrader/` 패키지 기반
- 호환성: 루트는 `upbit_trader.py` 엔트리포인트만 유지, 기존 래퍼는 `legacy_wrappers/`로 이동
- 정책: 신규 기능 기본 `OFF`로 기존 동작 유지

## 패키지 구조(핵심)
```txt
upbit_autotrader/
  app/
  controllers/
  services/
  strategies/   # meta_signal 포함
  risk/
  execution/
  core/
  runtime/
  analytics/
  backtesting/
  notifications/
  ui/
```

## 핵심 기능
- 전략 엔진(`single`, `ensemble`) + 게이트 정책(`engine_gate_policy`)
- 리스크 예산 기반 사이징(ATR/Kelly/Drawdown state, opt-in)
- 실행 모델 + TWAP 시장가 분할(옵션)
- 메타 시그널 게이트(엔진 점수 + 전략 기대값 + 레짐 점수)
- 주문 상태머신 + timeout 복구 + manual review queue
- 세션 불일치 orphan 이벤트 기록 + 계좌 재동기화
- 거래기록 확장 필드 저장(수수료/슬리피지/세션/리스크/전략점수)
- Discord 웹훅 알림(옵션), 트레이 알림 기본

## 빌드(.spec)
- 파일: `upbit_trader.spec`
- 기준: `v3.3.0`
- 특징:
  - `collect_submodules("upbit_autotrader")`로 `risk/`, `execution/`, `strategies/meta_signal.py` 자동 수집

빌드 예시:
```bash
pyinstaller --noconfirm --clean upbit_trader.spec
```

## 테스트
실행:
```bash
python -m pytest -q
```

현재 기준:
- 전체 테스트 통과: `74 passed`

## 문서
- 사용자 문서: `README.md`
- 개발 가이드: `CLAUDE.md`
- 구조/구현 상태: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 옵션 계획: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`

## 작업 시 주의
1. 설정 변경 시 `settings_version=2` 호환성 유지
2. 주문/체결 로직 수정 시 lifecycle 전이와 pending 정리 동시 검증
3. 문서 수정 시 README/CLAUDE/GEMINI/구조문서 간 기능/기본값/테스트 수치 정합성 유지
