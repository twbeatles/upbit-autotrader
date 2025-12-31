# Upbit Pro Algo-Trader v3.0

업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ v3.0 주요 업데이트

### 🎨 UI/UX 전면 개편
- **글래스모피즘 디자인**: 반투명 그룹박스, 그라데이션 효과
- **통계 카드 대시보드**: 잔고/손익/거래수/승률 실시간 표시
- **호버 애니메이션**: 버튼, 테이블, 메뉴 인터랙션 강화
- **모던 컬러 팔레트**: 시안/핑크/퍼플 테마

### 📱 텔레그램 알림
- 매수/매도/손절 체결 알림
- 일일 리포트 자동 발송
- 자동매매 시작/중지 알림

### 🔐 보안 강화
- API 키 암호화 저장 (Fernet)
- 마스터 비밀번호 잠금

### ⏰ 예약 매매 스케줄러
- 매매 허용 시간/요일 설정
- 자동 시작/중지

### 📈 시각화 & 분석
- **수익 차트**: 누적 수익률, 종목별 손익, 일별 손익
- **백테스팅**: 과거 데이터 전략 시뮬레이션
- **페이퍼 트레이딩**: 가상 자금 모의투자 (완전 구현)

### 🎯 다중 전략 지원
- 변동성 돌파 (기본)
- 골든크로스
- 그리드 매매
- RSI 역추세

---

## 🔥 핵심 트레이딩 기능

- **변동성 돌파 전략**: 래리 윌리엄스 전략 기반
- **MA5 추세 필터**: 상승 추세 확인
- **RSI/MACD/거래량 필터**: 과매수/모멘텀/거래량 확인
- **트레일링 스톱**: 고점 대비 자동 이익 실현
- **손절 기능**: 설정 손실률 자동 매도
- **일괄 매도/매수**: 포트폴리오 전체 거래

---

## 📋 시스템 요구사항

```
Python >= 3.10
PyQt6 >= 6.0
pyupbit >= 0.2.30
pandas
```

### 선택 라이브러리 (권장)
```
python-telegram-bot  # 텔레그램 알림
cryptography         # API 암호화
matplotlib           # 차트 시각화
```

---

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
# 필수
pip install PyQt6 pyupbit pandas

# 선택 (권장)
pip install python-telegram-bot cryptography matplotlib
```

### 2. 프로그램 실행
```bash
python upbit_trader.py
```

### 3. API 연결
1. [업비트 Open API 관리](https://upbit.com/mypage/open_api_management)에서 API 키 발급
2. **주문** 권한 포함 필수
3. Access Key, Secret Key 입력 → "🔌 시스템 접속"

### 4. 텔레그램 설정 (선택)
1. [@BotFather](https://t.me/botfather)에서 봇 토큰 발급
2. [@userinfobot](https://t.me/userinfobot)에서 Chat ID 확인
3. 📱 텔레그램 탭에서 설정

---

## 🗂️ 프로젝트 구조

```
업비트 자동매매/
├── upbit_trader.py        # 메인 프로그램 (약 4000줄)
├── telegram_notifier.py   # 텔레그램 알림 모듈
├── crypto_utils.py        # 암호화 유틸리티
├── backtest_engine.py     # 백테스팅 엔진
├── strategies.py          # 다중 전략 모듈
├── upbit_trader.spec      # PyInstaller 빌드
└── README.md
```

---

## ⚙️ 전략 프리셋

| 프리셋 | K값 | TS발동 | 손절 | 투자비중 |
|--------|-----|--------|-----|---------|
| 🔥 공격적 | 0.5 | 3% | 5% | 15% |
| ⚖️ 표준 | 0.4 | 5% | 3% | 10% |
| 🛡️ 보수적 | 0.3 | 7% | 2% | 5% |

---

## 🔧 EXE 빌드

```bash
pip install pyinstaller
pyinstaller upbit_trader.spec
```

결과: `dist/UpbitTrader/UpbitTrader.exe`

---

## ⚠️ 주의사항

> **경고**: 실제 자금이 거래됩니다. 반드시 소액으로 테스트하세요.

- 처음 사용 시 **페이퍼 트레이딩** 모드 권장
- **백테스트** 결과가 미래 수익을 보장하지 않음
- 투자 손실에 대한 책임은 사용자에게 있음

---

## 📝 변경 이력

### v3.0 (2025-12-31)
- 🎨 UI/UX 전면 개편 (글래스모피즘, 그라데이션)
- ✨ 통계 카드 대시보드
- ✨ 텔레그램 알림 연동
- ✨ API 키 암호화
- ✨ 예약 매매 스케줄러
- ✨ 수익 차트 시각화
- ✨ 백테스팅 시스템
- ✨ 페이퍼 트레이딩 (완전 구현)
- ✨ 다중 전략 지원
- 🐛 대시보드 통계 카드 연동 수정

### v2.6
- 일괄 매도/매수 기능

### v2.5
- 거래 히스토리, 진입 스코어링
