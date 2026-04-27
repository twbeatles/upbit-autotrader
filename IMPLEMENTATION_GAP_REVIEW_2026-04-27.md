# Upbit Pro Algo-Trader 구현 개선 리뷰

점검일: 2026-04-27

## 요약

기존 구현 리스크 리뷰와 시장 레짐 설계 메모를 통합해 현재 기준 문서로 정리했습니다. 삭제된 문서 참조는 제거하고, 실제 코드에 반영된 안전성 개선 사항을 이 문서에 남깁니다.

## 반영된 개선 사항

- 실시간 equity 기준 리스크 계산
- live `orders/chance` 수수료의 execution model 전파
- `Remaining-Req` 기반 adaptive throttle helper
- 시장 레짐 stale/error 시 선택형 fail-closed 정책
- TWAP fallback 추적 metadata
- live 주문 복구 상태 저장 OFF 경고
- `pyupbit` 선택 의존성 fallback과 pyright stub
- UTF-8 문서 무결성 점검

## 현재 기준 문서

- `README.md`: 사용자 실행, 검증, 운영 안내
- `CLAUDE.md`: 개발자 작업 기준
- `GEMINI.md`: 보조 작업자 메모
- `legacy_wrappers/README.md`: legacy import wrapper 안내
- `IMPLEMENTATION_GAP_REVIEW_2026-04-27.md`: 구현 개선 리뷰

## 배포 및 ignore 정합성

- `upbit_trader.spec`는 `collect_submodules("upbit_autotrader")`를 사용하므로 `services/rate_limit.py`와 `services/pyupbit_compat.py`는 자동 수집됩니다.
- `typings/`는 pyright 전용 stub 경로이므로 PyInstaller data에 포함하지 않습니다.
- `.gitignore`는 빌드 산출물, 캐시, 런타임 설정/거래 기록/복구 상태, 임시 파일을 제외합니다.
- 삭제된 이전 문서 참조는 `tests/test_docs_references.py`에서 제거 여부를 검증합니다.

## 검증

```bash
python -m pytest -q
python -m pyright
pre-commit run --all-files
```

문서 품질은 `tests/test_docs_references.py`와 `tests/test_text_integrity.py`에서 확인합니다.

