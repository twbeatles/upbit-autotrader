# Upbit Pro Algo-Trader 작업 메모

이 문서는 자동화 작업자가 프로젝트를 이해하기 위한 보조 가이드입니다. 상세 개발 기준은 `CLAUDE.md`를 우선합니다.

## 핵심 원칙

- 실행 진입점은 `upbit_trader.py`입니다.
- 새 코드는 `upbit_autotrader.*`에 둡니다.
- 이전 import 호환은 `legacy_wrappers/`에서 유지합니다.
- 주문, 리스크, 설정 schema 변경은 테스트를 함께 추가합니다.

## 주요 검증

```bash
python -m pytest -q
python -m pyright
pre-commit run --all-files
```

문서와 텍스트 파일은 UTF-8을 사용하며 `tests/test_text_integrity.py`로 확인합니다.

## 참고 문서

- `IMPLEMENTATION_GAP_REVIEW_2026-04-27.md`
- `legacy_wrappers/README.md`
