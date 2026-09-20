"""
Upbit Advanced Indicators v1.0
고급 기술지표 모듈 for Upbit Pro Algo-Trader

Williams %R, CCI, OBV, Ichimoku Cloud, Pivot Points, Parabolic SAR
"""

import pyupbit
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
from datetime import datetime


@dataclass
class IchimokuData:
    """일목균형표 데이터"""
    tenkan_sen: float       # 전환선 (9)
    kijun_sen: float        # 기준선 (26)
    senkou_span_a: float    # 선행스팬1
    senkou_span_b: float    # 선행스팬2 (52)
    chikou_span: float      # 후행스팬

@dataclass
class PivotPoints:
    """피봇 포인트 데이터"""
    pivot: float            # 피봇
    r1: float               # 저항선1
    r2: float               # 저항선2
    r3: float               # 저항선3
    s1: float               # 지지선1
    s2: float               # 지지선2
    s3: float               # 지지선3
