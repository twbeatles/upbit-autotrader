# Project Audit — Fluent Build / Dependencies / Packaging

> 대상: Upbit Pro Algo-Trader Fluent 빌드 범위 (Qt 바인딩·의존성·PyInstaller 패키징)
> 감사일: 2026-09-29 (UTC) / 방식: 읽기 전용 감사 + 빌드 활성화 작업 (테스트·빌드 산출물 제외 코드 수정은 README 1줄)
> 사용 도구: CodeGraph MCP 1회 + 직접 열람 + `.venv` 신규 구축 + `pytest` + `PyInstaller` 실빌드
> 본 문서는 `PROJECT_AUDIT.md`(기능/런타임 범위)의 후속 범위이며 양식을 공유한다.

## 1. Executive Summary

* **프로젝트 전체 상태:** Fluent 빌드는 **이제 가능하고 증명됐다.** 프로젝트 루트에 `.venv`를 신규 구축하고 `requirements.txt`를 설치하자 `FLUENT_AVAILABLE=True`, 실 `FluentWindow` 셸 기동(7페이지), `.venv`에서 229개 테스트 전부 통과, `PyInstaller` 실빌드(EXIT=0, 68.8MB, PySide6 마커 0)를 확인했다.
* **전체 위험도:** **Acceptable** — 치명적 구조 결함은 없고, 남은 것은 의존성 선언·잠금·산출물 위생 수준이다.
* **가장 중요한 문제 3~5개:**
  1. 시스템 인터프리터에 `PyQt6-Fluent-Widgets`가 없고 `PySide6-Fluent-Widgets`가 `qfluentwidgets` 네임스페이스를 점유 → 혼합 바인딩 크래시 (Confirmed, 수정 전 코드가드+이번 `.venv`로 해소).
  2. 혼합 환경에서 `upbit_trader.spec`가 `collect_submodules("qfluentwidgets")`로 PySide6 빌드를 그대로 얼려 깨진 exe를 만든다 (Confirmed, `.venv` 격리로 해소).
  3. 버전 잠금 파일 없음 (`requirements.txt` 하한만, Fluent 1.6→1.11.3 실설치) — 재현 빌드 비결정성 (Likely).
  4. `_pytest`가 빌드 그래프에 포함되어 exe가 비대해진다 (관찰, 무해).
  5. `dist/`, `upbit_dist/`에 stale 산출물이 남아 있으나 git-ignored라 실害 없음 (관찰).
* **데이터 손상/유실 가능성 여부:** 없다. 빌드 산출물은 전부 git-ignored 재생성 가능물이며, 이번에 `upbit_dist/`만 갱신했다.
* **가장 먼저 수정해야 할 영역:** 이미 했다 (`.venv` + PyQt6-Fluent 설치 + 빌드 증명). 남은 1순위는 버전 잠금(`requirements` 핀 또는 lock)이다.

## 2. Project Understanding

* **프로젝트 목적(본 범위):** PyQt6 + PyQt6-Fluent-Widgets 실셸로 동작하는 데스크톱 앱을 PyInstaller onefile exe로 패키징한다.
* **주요 entrypoint:** `upbit_trader.py` → `UpbitProTrader` (`app/trader.py`, `_FluentBase`는 `ui/qt_compat.py` 가드 통과 시에만 Fluent).
* **핵심 모듈:** `ui/qt_compat.py`(바인딩 가드), `controllers/ui_parts/layout_ops.py`(Fluent/네이티브 분기, 표면 일치), `ui/navigation.py`(네이티브 셸), `upbit_trader.spec`(Analysis-hiddenimports/datas/excludes), `requirements.txt`, `DESKTOP_UI_DESIGN_RULES.md`(혼합 금지 계약).
* **데이터 저장 방식:** 해당 없음. 빌드 입력(코드+`.venv` 패키지) → `upbit_dist/UpbitTrader.exe`, 부산물 `upbit_build/`. 런타임 JSON/로그는 번들에 포함되지 않는다(spec 명시).
* **외부 의존성:** `PyQt6==6.11.0`, `PyQt6-Fluent-Widgets==1.11.3`, `PyQt6-Frameless-Window==0.8.2`, `pyinstaller==6.22.3`, 그 외 `requirements.txt` 40여 종. 시스템 인터프리터에는 `PySide6(-Essentials/-Addons)==6.11.2`, `PySide6-Fluent-Widgets==1.11.3`이 공존한다.
* **핵심 실행 흐름:**

  `spec hiddenimports(collect upbit_autotrader/legacy/qfluentwidgets/qframelesswindow) + datas(qfluentwidgets 리소스) → Analysis → PYZ/EXE → upbit_dist/UpbitTrader.exe(PyQt6 132 / PySide6 0 마커, qfluentwidgets _rc 포함)`

## 3. Audit Coverage & Limitations

* **실제 확인한 주요 모듈:** `upbit_trader.spec` 전체, `requirements.txt`, `.gitignore`(산출물 무시 확인), `DESKTOP_UI_DESIGN_RULES.md` 혼합 금지 조항, `app/trader.py`·`layout_ops.py`·`navigation.py` 셸 분기, `pip freeze` 실측, 빌드 로그·warn 파일·TOC·exe 바이너리 마커.
* **CodeGraph로 분석한 호출 관계:** Fluent/네이티브 셸 표면(`init_ui`→`_is_fluent_window`→`_register_pages`/`nav_shell`, `stackedWidget`/`switchTo` 일치, `qt_compat.fluent_window_base` 호출자 2곳) 1회 탐색 + 직접 열람 교차 확인.
* **실행한 테스트:** `.venv` 구축 후 `pytest -q`(229 passed), 실셸 기동 프로브(`isinstance FluentWindow True`, 7페이지), `PyInstaller` 실빌드 2회(EXIT=0), exe 마커 검사, TOC 리소스 확인. 시스템 인터프리터 스위트(229 passed)는 전일 확인분으로 재인용.
* **확인하지 못한 환경/외부 서비스:** 빌드된 exe의 GUI 실기동(콘솔 없는 GUI라 헤드리스 실행 불가), macOS/Linux 빌드, UPX 압축 경로, 바이러스 백신 오탐 여부.
* **한계:** exe 내부 동작은 실행하지 못해 패키징 정합성까지만 증명한다. warn 파일의 선택적 의존 경고는 benign 판정이나 mac 실기 검증은 없다.

## 4. High-Risk Issues

### [BUILD-001] 시스템 환경에 PyQt6-Fluent 미설치 + PySide-Fluent의 네임스페이스 점유

* **위치:** `requirements.txt:10-11` vs 시스템 `pip freeze` 실측.
* **우선순위:** High
* **신뢰도:** Confirmed
* **문제:** `requirements.txt`가 요구하는 `PyQt6-Fluent-Widgets`·`PyQt6-Frameless-Window`가 시스템 인터프리터에 없고, 대신 `PySide6-Fluent-Widgets 1.11.3`이 동일 `qfluentwidgets` 네임스페이스를 점유했다. 결과적으로 `import qfluentwidgets`가 PySide6 빌드를 돌려줘 PyQt6 앱과 혼합 바인딩 `TypeError`를 일으켰다(전일 `QTimer`/`QThread` 실패의 근본 원인).
* **발생 조건:** 프로젝트 `.venv` 없이 시스템 인터프리터로 실행/테스트할 때 확정 발생.
* **영향:** Fluent 셸 기동 불가(네이티브 폴백으로만 동작), 테스트 1건 실패(전일, 현재 코드가드로 해소됨).
* **근거:** `pip freeze`에 `PySide6-Fluent-Widgets==1.11.3` 존재·`PyQt6-Fluent-Widgets` 부재, 프로브 MRO의 `PySide6.QtWidgets.QWidget` 확인 기록.
* **반증 확인:** 단순 누락이 아니라 네임스페이스 충돌임을 `DESKTOP_UI_DESIGN_RULES.md:57`의 경고와 MRO 실측으로 확정. 프레임워크 자동 해소 없음.
* **호출/영향 범위:** `app/trader.py` 진입점 → 셸 전체. 현재 `qt_compat` 가드가 혼합 바인딩 탑재를 원천 차단하므로 크래시는 재발하지 않는다.
* **권장 수정 방향:** 완료 — 프로젝트 `.venv`에 `requirements.txt` 설치(PyQt6-Fluent 1.11.3 확인). 시스템 해석기에 손대지 않았다.
* **필요한 회귀 테스트:** `test_qt_binding_guard_rejects_foreign_binding`, `test_trader_window_is_pyqt6_object` (추가됨, 통과).

### [BUILD-002] 혼합 환경에서 spec이 PySide-Fluent를 그대로 동결한다

* **위치:** `upbit_trader.spec:66-88` (`collect_submodules("qfluentwidgets")` + datas).
* **우선순위:** High
* **신뢰도:** Confirmed
* **문제:** spec은 `PySide6`를 excludes에 넣지만, `collect_submodules("qfluentwidgets")`는 **현재 환경의** `qfluentwidgets`를 수집한다. 혼합/오염 환경에서 빌드하면 PySide6-Fluent 모듈+리소스가 PyQt6 앱과 함께 얼려져 깨진 exe가 나온다. excludes는 모듈명 기준이라 네임스페이스 충돌 자체를 막지 못한다.
* **발생 조건:** `.venv` 없이 시스템 인터프리터(또는 PySide-Fluent 혼재 venv)에서 빌드할 때.
* **영향:** 실행 즉시 크래시하는 배포 산출물. `dist/`·`upbit_dist/`의 기존 exe가 언제 어떤 환경에서 빌드됐는지 provenance도 없다.
* **근거:** spec 수집 구조 + 시스템 env 실측(PySide-Fluent 점유). 역으로 이번 `.venv` 빌드 산출물은 exe 마커 `PyQt6=132/PySide6=0`, TOC의 `.venv` 경로 `qfluentwidgets/_rc` 포함으로 순수성이 증명됐다.
* **반증 확인:** excludes만으로 충분한지 검토했으나, excludes는 `PySide6` 모듈명을 가릴 뿐 `qfluentwidgets` 안의 PySide 바인딩 코드를 가리지 못하므로 반증 불가. 빌드 환경 격리만이 해결책이다.
* **호출/영향 범위:** 배포 파이프라인 전체. 런타임 코드 영향 없음.
* **권장 수정 방향:** 완료 — `.venv`에서 빌드(문서화된 `--distpath upbit_dist` 경로). 추가 권장: README에 ".venv에서만 빌드" 명시(이번에 1줄 추가함).
* **필요한 회귀 테스트:** 빌드 후 마커 검사(`PySide6` 0건)를 릴리스 체크리스트에 추가. 자동화는 exe 크기상 CI 부적합이므로 수동 게이트로 둔다.

### [BUILD-003] 버전 잠금 없음 — 재현 빌드 비결정성

* **위치:** `requirements.txt` (전부 하한 범위, 상한 없음).
* **우선순위:** Medium
* **신뢰도:** Likely
* **문제:** `PyQt6-Fluent-Widgets>=1.6`로 설치되는 1.11.3에서 동작 확인했으나, 다음 해결 시점에 다른 메이저가 들어오면 셸 API(`FluentWindow`, `NavigationItemPosition`, `setThemeColor`)가 깨질 수 있다. `uv.lock`·`pip freeze` 스냅샷이 없다.
* **발생 조건:** 시간 경과 후 fresh install 시.
* **영향:** "내 머신에선 되는데" 류의 빌드 drift. 당장 장애 아님.
* **근거:** 실설치 버전과 선언 하한의 gap, lock 파일 부재 확인.
* **반증 확인:** 현시점 빌드 성공이 미래 재현성을 보장하지 않으므로 유지한다.
* **호출/영향 범위:** 빌드 입력 전체.
* **권장 수정 방향:** 동작 확인된 버전으로 상한 핀(`PyQt6-Fluent-Widgets~=1.11`, 등) 또는 lock 파일 도입. 이번 턴에는 설치 결과만 기록하고 핀 변경은 하지 않았다(의존성 정책 결정이므로 소유자 확인 권장).
* **필요한 회귀 테스트:** `pip install -r requirements.txt` fresh install 후 `FLUENT_AVAILABLE is True` + `pytest -q` 통과를 릴리스 게이트에 추가.

## 5. Potential Functional Gaps

* **관찰 — `_pytest`가 빌드 그래프에 포함:** warn 파일에 `_pytest` 체인이 보인다. 런타임 코드에 `import pytest`는 없으므로(검색 확인) 무해한 bloat로 추정. exe 68.8MB 중 일부. 추정.
* **관찰 — `dist/`·`upbit_dist/` stale 산출물:** 둘 다 git-ignored라 위험은 없으나 어떤 env/버전 산출물인지 알 수 없다. 이번에 `upbit_dist/`만 새로 빌드했다. Confirmed Gap은 아니고 위생 관찰.
* **관찰 — UPX:** spec `upx=True`이나 빌드 로그에 UPX 관련 라인이 없어 미설치로 추정, 경고만으로 통과. 압축률 이슈 외 기능 영향 없음. 추정.
* **Likely Gap — exe GUI 실기동 미검증:** `console=False`라 헤드리스 smoke test가 불가하다. 첫 실행은 실머신에서 수동 확인이 필요하다.

## 6. Documentation Mismatches

* `README.md` 설치 절차는 venv 기준이라 정확했으나, 바인딩 혼합 금지 주의가 없어 1줄 추가했다(이번 턴).
* 구 `PROJECT_AUDIT.md`의 "`pyright` 0 error" 서술과 달리 본 범위 착수 전 실측은 달랐을 수 있다 — 현재는 `pyright` 0 errors로 확인했으므로 결과적으로 일치한다.
* 그 외 spec↔README 빌드 경로 서술 일치, `.gitignore` 산출물 무시 일치. 다른 불일치 없음.

## 7. Recommended Fix Plan

### Phase 1 — Immediate

완료: `.venv` 구축, `requirements.txt`+`pytest/pytest-qt` 설치, Fluent 실셸 기동 확인, 229 테스트 통과, `PyInstaller` 실빌드(EXIT=0), README 주의 1줄.

### Phase 2 — Stability

1. 의존성 상한 핀 또는 lock 도입(소유자 결정 필요).
2. 릴리스 체크리스트 문서화: fresh-install → `FLUENT_AVAILABLE` 확인 → `pytest` → 빌드 → exe 마커 검사.
3. `dist/`·`upbit_dist/` stale 산출물 정리 정책(무시되므로 선택).

### Phase 3 — Structural

4. 릴리스 자동화는 exe 크기·서명 이슈로 보류, 수동 게이트 유지.
5. GUI smoke test는 별도 Windows 실머신 절차로 분리.

## 8. Test Recommendations

* **Unit:** `is_pyqt6_widget_class`가 PySide6 위젯을 거부하는지(추가됨). `fluent_window_base()`가 혼합 env에서 None을 돌려주는지 — 현 env가 바로 그 케이스라 매일 증명됨.
* **Integration:** `UpbitProTrader`가 Fluent env(`.venv`)에서는 `FluentWindow` 인스턴스, 혼합 env(시스템)에서는 `QMainWindow` 인스턴스로 기동하는지 양쪽에서 assert(수동 확인 완료, 테스트는 후자만 커버).
* **End-to-End:** fresh `.venv` + `requirements.txt` → `FLUENT_AVAILABLE True` → `pytest -q` 229 → `PyInstaller` EXIT=0 → exe `PySide6` 마커 0. 이번 턴 수행 순서 그대로가 E2E 절차다.
* **Concurrency/Platform-specific:** 해당 없음(빌드 범위는 단일 머신 결정적 작업).

## 9. Final Assessment

| 영역 | 평가 | 근거 |
|---|---|---|
| Functional Correctness | Good | Fluent/네이티브 양 셸에서 229 테스트 전부 통과. |
| Runtime Stability | Good | 혼합 바인딩 탑재 불가 구조(`qt_compat`) + 양 env 검증. |
| Data Integrity | Good | 산출물 전부 ignored, 소스 오염 없음. |
| Error Resilience | Acceptable | spec 수집 실패는 경고 후 필터로 흡수, exe 실기동 미검증 1건 잔류. |
| Cross-platform Robustness | Acceptable | Windows 빌드 증명, mac/Linux 빌드는 미확인. |
| Test Confidence | Good | 양쪽 인터프리터에서 동일 229 통과. |

**실제로 먼저 수정할 문제 3개:** 모두 이번 턴에 했다 — (1) `.venv` 격리, (2) PyQt6-Fluent 설치 및 실셸 확인, (3) 실빌드 증명. 남은 것은 의존성 핀 결정 1건이다.
