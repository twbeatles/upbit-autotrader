from PyQt6.QtWidgets import QCheckBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSpinBox


def build_legacy_advanced_groups(self):
    groups = []
    if getattr(self, "strategy", None) is None:
        return groups

    group_adv_risk = QGroupBox("🚀 고급 리스크 관리 (v3.0)")
    adv_risk_layout = QGridLayout()
    self.chk_use_cooldown = QCheckBox("재진입 쿨다운 사용")
    self.chk_use_cooldown.setToolTip("매도 후 일정 시간 동안 동일 코인 재매수 방지\n휩쏘에 휘둘리지 않도록 보호")
    adv_risk_layout.addWidget(self.chk_use_cooldown, 0, 0)
    adv_risk_layout.addWidget(QLabel("쿨다운 시간:"), 0, 1)
    self.spin_cooldown = QSpinBox()
    self.spin_cooldown.setRange(5, 120)
    self.spin_cooldown.setValue(30)
    self.spin_cooldown.setSuffix(" 분")
    adv_risk_layout.addWidget(self.spin_cooldown, 0, 2)
    self.chk_use_time_exit = QCheckBox("시간 기반 청산")
    self.chk_use_time_exit.setToolTip("일정 시간 경과 시 자동 청산")
    adv_risk_layout.addWidget(self.chk_use_time_exit, 1, 0)
    adv_risk_layout.addWidget(QLabel("최대 보유:"), 1, 1)
    self.spin_max_holding_hours = QSpinBox()
    self.spin_max_holding_hours.setRange(1, 72)
    self.spin_max_holding_hours.setValue(24)
    self.spin_max_holding_hours.setSuffix(" 시간")
    adv_risk_layout.addWidget(self.spin_max_holding_hours, 1, 2)
    self.chk_use_dynamic_position = QCheckBox("동적 포지션 사이징 (Anti-Martingale)")
    self.chk_use_dynamic_position.setToolTip("연속 이익 시 투자비중 확대, 연속 손실 시 축소")
    adv_risk_layout.addWidget(self.chk_use_dynamic_position, 2, 0, 1, 3)
    group_adv_risk.setLayout(adv_risk_layout)
    groups.append(group_adv_risk)

    group_adv_algo = QGroupBox("🧠 고급 알고리즘 (v3.0)")
    adv_algo_layout = QGridLayout()
    self.chk_use_mtf = QCheckBox("다중 시간프레임(MTF) 분석")
    self.chk_use_mtf.setToolTip("일봉과 단기봉 추세 일치 시에만 매수")
    adv_algo_layout.addWidget(self.chk_use_mtf, 0, 0)
    self.chk_use_gap = QCheckBox("갭 분석 및 K값 자동 조정")
    self.chk_use_gap.setToolTip("갭업 시 K값 축소(신중), 갭다운 시 K값 확대(적극)")
    adv_algo_layout.addWidget(self.chk_use_gap, 0, 1)
    self.chk_use_breakout_confirm = QCheckBox("돌파 확인 (N틱 유지)")
    self.chk_use_breakout_confirm.setToolTip("목표가 돌파 후 일정 틱 동안 유지되어야 매수")
    adv_algo_layout.addWidget(self.chk_use_breakout_confirm, 1, 0)
    adv_algo_layout.addWidget(QLabel("확인 틱수:"), 1, 1)
    self.spin_breakout_ticks = QSpinBox()
    self.spin_breakout_ticks.setRange(1, 10)
    self.spin_breakout_ticks.setValue(3)
    adv_algo_layout.addWidget(self.spin_breakout_ticks, 1, 2)
    group_adv_algo.setLayout(adv_algo_layout)
    groups.append(group_adv_algo)

    group_emergency = QGroupBox("🚨 긴급 조치")
    emergency_layout = QHBoxLayout()
    self.btn_emergency_close = QPushButton("🚨 전량 긴급 청산")
    self.btn_emergency_close.setStyleSheet(
        """
            QPushButton {
                background-color: #e63946;
                font-weight: bold;
                font-size: 14px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #d62839;
            }
        """
    )
    self.btn_emergency_close.clicked.connect(self.show_emergency_dialog)
    self.btn_emergency_close.setToolTip("모든 보유 코인을 시장가로 즉시 매도합니다")
    emergency_layout.addWidget(self.btn_emergency_close)
    emergency_layout.addStretch(1)
    group_emergency.setLayout(emergency_layout)
    groups.append(group_emergency)
    return groups
