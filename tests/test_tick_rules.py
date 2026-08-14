"""Tests for Upbit tick size rules and price snapping."""

import pytest
from upbit_autotrader.core.tick_rules import get_tick_size, snap_to_tick_size


def test_krw_tick_sizes():
    # >= 2,000,000 : 1,000
    assert get_tick_size(3_000_000) == 1000.0
    assert get_tick_size(2_000_000) == 1000.0

    # 1,000,000 ~ 2,000,000 : 500
    assert get_tick_size(1_500_000) == 500.0
    assert get_tick_size(1_000_000) == 500.0

    # 500,000 ~ 1,000,000 : 100
    assert get_tick_size(750_000) == 100.0
    assert get_tick_size(500_000) == 100.0

    # 100,000 ~ 500,000 : 50
    assert get_tick_size(250_000) == 50.0
    assert get_tick_size(100_000) == 50.0

    # 10,000 ~ 100,000 : 10
    assert get_tick_size(50_000) == 10.0
    assert get_tick_size(10_000) == 10.0

    # 1,000 ~ 10,000 : 1
    assert get_tick_size(5_000) == 1.0
    assert get_tick_size(1_000) == 1.0

    # 100 ~ 1,000 : 0.1
    assert get_tick_size(500) == 0.1
    assert get_tick_size(100) == 0.1

    # 10 ~ 100 : 0.01
    assert get_tick_size(50) == 0.01
    assert get_tick_size(10) == 0.01

    # 1 ~ 10 : 0.001
    assert get_tick_size(5) == 0.001
    assert get_tick_size(1) == 0.001

    # < 1 : 0.0001
    assert get_tick_size(0.5) == 0.0001
    assert get_tick_size(0.01) == 0.0001


def test_snap_to_tick_size():
    # 50,000 won range (tick = 10)
    assert snap_to_tick_size(50003.4, method="round") == 50000.0
    assert snap_to_tick_size(50007.8, method="round") == 50010.0
    assert snap_to_tick_size(50007.8, method="floor") == 50000.0
    assert snap_to_tick_size(50003.4, method="ceil") == 50010.0

    # 1,500,000 won range (tick = 500)
    assert snap_to_tick_size(1_500_240, method="round") == 1_500_000.0
    assert snap_to_tick_size(1_500_260, method="round") == 1_500_500.0
    assert snap_to_tick_size(1_500_260, method="floor") == 1_500_000.0
    assert snap_to_tick_size(1_500_240, method="ceil") == 1_500_500.0

    # Edge cases
    assert snap_to_tick_size(0.0) == 0.0
    assert snap_to_tick_size(-10.0) == 0.0
