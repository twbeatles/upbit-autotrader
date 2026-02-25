# Upbit Pro Algo-Trader v3.2.2

업비트 OpenAPI 기반 자동매매 프로그램 - Gemini 작업 가이드

## 현재 상태 요약
- 버전: `v3.2.2` (2026-02-25)
- 메인 실행: `python upbit_trader.py`
- 내부 구조: `upbit_autotrader/` 패키지 기반으로 리팩토링 완료
- 호환성: 루트 `upbit_*.py`는 하위 패키지를 재노출하는 래퍼

## 패키지 구조
```txt
upbit_autotrader/
  app/trader.py
  controllers/
  services/
  strategies/
  core/
  runtime/
  analytics/
  backtesting/
  ui/
```

## 핵심 기능
- 전략 엔진(`single`, `ensemble`) + 진입 정책(`engine_gate_policy`)
- 주문 상태머신(`submitted`, `wait`, `done`, `cancel`, `timeout`, `manual_review`, `reconciled`)
- 타임아웃 복구(cancel/requery/manual review)
- 세션 불일치 orphan 이벤트 기록 + 계좌 재동기화
- 계좌 전체 보유 동기화(account-wide)
- 리스크 계산 확장(실현 + 미실현 + 외부보유)
- 페이퍼 트레이딩(무로그인 시작/시드/비용모델)

## 빌드(.spec)
- 파일: `upbit_trader.spec`
- 기준: `v3.2.2`
- 특징:
  - 레거시 래퍼 hiddenimports 유지
  - `collect_submodules("upbit_autotrader")`로 패키지 하위 모듈 자동 수집

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
- 전체 테스트 통과: `60 passed`

## 문서
- 사용자 문서: `README.md`
- 개발 가이드: `CLAUDE.md`
- 구조 문서: `PROJECT_STRUCTURE_ANALYSIS.md`
- 전략 문서: `STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md`
- 리스크 리뷰: `AUTO_TRADING_RISK_REVIEW_2026-02-25.md`

## 작업 시 주의
1. 컨트롤러/서비스 수정 시 루트 래퍼 import 호환성 유지 여부를 함께 확인
2. 주문/체결 로직 수정 시 lifecycle 전이와 pending 정리 경로를 동시에 검증
3. 문서 수정 시 README/CLAUDE/GEMINI/구조문서 간 경로·버전 정합성을 유지
