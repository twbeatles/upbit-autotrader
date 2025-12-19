# Upbit Pro Algo-Trader v1.0

업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 주요 기능

### 트레이딩 전략
- **변동성 돌파 전략**: 전 캔들 고저 변동폭 × K값으로 목표가 계산
- **MA5 추세 필터**: 5봉 이동평균선 위에서만 매수 진입
- **RSI 과매수 필터**: RSI 상한선 초과 시 진입 방지
- **트레일링 스톱**: 고점 대비 하락 시 자동 이익 실현
- **손절 기능**: 설정 손실률 초과 시 자동 손절 매도

### 24시간 코인 마켓 최적화
- 시간 청산 없이 연속 운영
- 다양한 캔들 간격 지원 (1분 ~ 일봉)
- 코인 변동성 반영 기본 설정값

### GUI 기능
- 다크 테마 PyQt6 인터페이스
- 전략 설정 / 고급 설정 / 통계 탭
- 실시간 포트폴리오 테이블
- 거래 로그 실시간 표시

## 📋 요구사항

```
Python >= 3.10
PyQt6 >= 6.0
pyupbit >= 0.2.30
```

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install PyQt6 pyupbit
```

### 2. 프로그램 실행
```bash
python upbit_trader.py
```

### 3. 업비트 API 키 설정
1. [업비트 Open API 관리](https://upbit.com/mypage/open_api_management)에서 API 키 발급
2. 프로그램에서 Access Key, Secret Key 입력
3. "🔌 시스템 접속" 버튼 클릭

## ⚙️ 설정 가이드

### 기본 설정
| 항목 | 기본값 | 설명 |
|------|--------|------|
| 캔들 간격 | 4시간 | 변동성 계산 기준 캔들 |
| K값 | 0.4 | 변동성 돌파 계수 |
| 투자비중 | 10% | 종목당 투자 비율 |
| TS 발동 | 5% | 트레일링 스톱 시작 수익률 |
| TS 하락폭 | 2% | 고점 대비 매도 트리거 |
| 손절률 | 3% | 강제 손절 기준 |

### 전략 프리셋
- **공격적**: K=0.5, TS발동=3%, 손절=5%
- **표준**: K=0.4, TS발동=5%, 손절=3%
- **보수적**: K=0.3, TS발동=7%, 손절=2%

## 📁 파일 구조

```
업비트 자동매매/
├── upbit_trader.py      # 메인 프로그램
├── upbit_trader.spec    # PyInstaller 빌드 설정
├── upbit_settings.json  # 설정 파일 (자동 생성)
├── README.md            # 문서
└── logs/                # 로그 디렉토리 (자동 생성)
    └── upbit_YYYYMMDD.log
```

## 🔧 EXE 빌드 (PyInstaller)

```bash
pip install pyinstaller
pyinstaller upbit_trader.spec
```

빌드된 실행파일: `dist/UpbitTrader/UpbitTrader.exe`

## ⚠️ 주의사항

> **경고**: 이 프로그램은 실제 자금을 거래합니다. 사용 전 반드시 소액으로 충분히 테스트하세요.

- API 키 발급 시 "주문" 권한 필요
- 24시간 운영 시 안정적인 인터넷 연결 필수
- 투자 손실에 대한 책임은 사용자에게 있습니다

## 📜 라이선스

MIT License
