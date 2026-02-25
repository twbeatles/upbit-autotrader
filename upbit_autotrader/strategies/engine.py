"""Strategy engine for single/ensemble decisioning."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple

from upbit_strategy_catalog import get_default_active_strategies, get_default_weights


@dataclass
class StrategySignal:
    strategy_id: str
    action: str
    score: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class StrategyConfig:
    enabled: bool = False
    mode: str = "single"
    single_strategy: str = "volatility_breakout"
    entry_gate_policy: str = "strategy_aware"
    ensemble_threshold: float = 60.0
    active_strategies: List[str] = field(default_factory=get_default_active_strategies)
    weights: Dict[str, float] = field(default_factory=get_default_weights)
    use_volatility_targeting: bool = True
    use_regime_filter: bool = True
    use_drawdown_guard: bool = True


class StrategyEngine:
    def __init__(self, trader):
        self.trader = trader

    def evaluate_entry(self, ticker: str, price: float, info: Dict[str, Any], snapshot: Dict[str, Any], config: StrategyConfig) -> StrategySignal:
        if not config.enabled:
            return StrategySignal("legacy", "HOLD", 0.0, ["전략 엔진 비활성"])

        if config.use_regime_filter and not self._pass_regime_filter(ticker, snapshot):
            return StrategySignal("regime_filter", "HOLD", 0.0, ["레짐 필터 미통과"])

        if config.use_drawdown_guard and not self._pass_drawdown_guard():
            return StrategySignal("drawdown_guard", "HOLD", 0.0, ["손실 가드 발동"])

        if config.mode == "ensemble":
            return self._evaluate_ensemble_entry(ticker, price, info, snapshot, config)

        signal = self._evaluate_single_entry(config.single_strategy, price, info, snapshot)
        signal.action = "BUY" if signal.score >= 50 else "HOLD"
        return signal

    def evaluate_exit(self, ticker: str, price: float, info: Dict[str, Any], snapshot: Dict[str, Any], config: StrategyConfig) -> StrategySignal:
        if not config.enabled:
            return StrategySignal("legacy", "HOLD", 0.0, [])

        strategies = [config.single_strategy] if config.mode == "single" else list(config.active_strategies)
        for sid in strategies:
            action, reason = self._check_exit_signal(sid, price, info, snapshot)
            if action == "SELL":
                return StrategySignal(sid, "SELL", 100.0, [reason])

        return StrategySignal("none", "HOLD", 0.0, [])

    def evaluate_position_size(self, base_ratio: float, snapshot: Dict[str, Any], config: StrategyConfig) -> float:
        ratio = float(base_ratio)
        if not config.enabled:
            return ratio
        if config.use_volatility_targeting:
            realized_vol = float(snapshot.get("realized_vol_pct", 0.0) or 0.0)
            target_vol = float(getattr(self.trader, "spin_target_vol", None).value()) if hasattr(self.trader, "spin_target_vol") else 2.0
            if realized_vol > 0:
                scale = target_vol / realized_vol
                scale = min(max(scale, 0.4), 1.8)
                ratio *= scale
        return max(1.0, min(100.0, ratio))

    def _evaluate_ensemble_entry(self, ticker: str, price: float, info: Dict[str, Any], snapshot: Dict[str, Any], config: StrategyConfig) -> StrategySignal:
        selected = [sid for sid in config.active_strategies if sid in config.weights]
        if not selected:
            selected = list(get_default_active_strategies())

        weighted_sum = 0.0
        total_weight = 0.0
        reasons: List[str] = []
        for sid in selected:
            sig = self._evaluate_single_entry(sid, price, info, snapshot)
            w = float(config.weights.get(sid, 1.0))
            if w <= 0:
                continue
            weighted_sum += sig.score * w
            total_weight += w
            reasons.extend(sig.reasons[:1])

        score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
        action = "BUY" if score >= float(config.ensemble_threshold) else "HOLD"
        reasons.append(f"앙상블 점수 {score:.1f}/{config.ensemble_threshold:.1f}")
        return StrategySignal("ensemble", action, score, reasons)

    def _evaluate_single_entry(self, strategy_id: str, price: float, info: Dict[str, Any], snapshot: Dict[str, Any]) -> StrategySignal:
        sid = str(strategy_id or "volatility_breakout")
        score = 0.0
        reasons: List[str] = []

        target = float(info.get("target", 0.0) or 0.0)
        ma5 = float(info.get("ma5", 0.0) or 0.0)
        if sid == "volatility_breakout":
            if price >= target:
                score += 60
                reasons.append("목표가 돌파")
            if price >= ma5:
                score += 40
                reasons.append("MA5 상향")

        elif sid == "donchian_breakout":
            upper = float(snapshot.get("donchian_upper", 0.0) or 0.0)
            if upper > 0 and price > upper:
                score += 75
                reasons.append("돈치안 상단 돌파")
            if price >= ma5:
                score += 25

        elif sid == "ema_cross_trend":
            ema_fast = float(snapshot.get("ema_fast", 0.0) or 0.0)
            ema_slow = float(snapshot.get("ema_slow", 0.0) or 0.0)
            ema_fast_prev = float(snapshot.get("ema_fast_prev", 0.0) or 0.0)
            if ema_fast > ema_slow:
                score += 65
                reasons.append("EMA 골든")
            if ema_fast > ema_fast_prev:
                score += 35
                reasons.append("EMA 기울기 양수")

        elif sid == "time_series_momentum":
            mom = float(snapshot.get("ts_momentum_pct", 0.0) or 0.0)
            if mom >= 1.0:
                score += min(100.0, 50.0 + (mom * 10.0))
                reasons.append(f"모멘텀 {mom:.2f}%")

        elif sid == "rsi_reversion":
            rsi = float(snapshot.get("rsi", 50.0) or 50.0)
            bb_lower = float(snapshot.get("bb_lower", 0.0) or 0.0)
            if rsi <= 30:
                score += 70
                reasons.append("RSI 과매도")
            if bb_lower > 0 and price <= bb_lower * 1.01:
                score += 30
                reasons.append("밴드 하단 근접")

        elif sid == "bollinger_reversion":
            bb_lower = float(snapshot.get("bb_lower", 0.0) or 0.0)
            bb_middle = float(snapshot.get("bb_middle", 0.0) or 0.0)
            if bb_lower > 0 and price <= bb_lower:
                score += 75
                reasons.append("BB 하단 이탈")
            if bb_middle > 0 and price < bb_middle:
                score += 25

        elif sid == "zscore_reversion":
            z = float(snapshot.get("zscore", 0.0) or 0.0)
            if z <= -1.8:
                score += min(100.0, 60.0 + abs(z) * 15.0)
                reasons.append(f"z-score {z:.2f}")

        else:
            reasons.append("지원하지 않는 전략")

        action = "BUY" if score >= 50.0 else "HOLD"
        return StrategySignal(sid, action, float(score), reasons)

    def _check_exit_signal(self, strategy_id: str, price: float, info: Dict[str, Any], snapshot: Dict[str, Any]) -> Tuple[str, str]:
        sid = str(strategy_id or "")
        if sid == "rsi_reversion":
            rsi = float(snapshot.get("rsi", 50.0) or 50.0)
            if rsi >= 55:
                return "SELL", "RSI 평균회귀 청산"
        elif sid == "bollinger_reversion":
            bb_middle = float(snapshot.get("bb_middle", 0.0) or 0.0)
            if bb_middle > 0 and price >= bb_middle:
                return "SELL", "BB 중단 복귀 청산"
        elif sid == "zscore_reversion":
            z = float(snapshot.get("zscore", 0.0) or 0.0)
            if z >= -0.3:
                return "SELL", "z-score 정상화 청산"
        elif sid in {"volatility_breakout", "donchian_breakout", "ema_cross_trend", "time_series_momentum"}:
            ma5 = float(info.get("ma5", 0.0) or 0.0)
            if ma5 > 0 and price < ma5:
                return "SELL", "추세 이탈 청산"
        return "HOLD", ""

    def _pass_regime_filter(self, ticker: str, snapshot: Dict[str, Any]) -> bool:
        adx = float(snapshot.get("adx", 0.0) or 0.0)
        min_adx = float(getattr(self.trader, "spin_regime_min_adx", None).value()) if hasattr(self.trader, "spin_regime_min_adx") else 18.0
        if adx < min_adx:
            return False
        if hasattr(self.trader, "strategy") and self.trader.strategy and hasattr(self.trader.strategy, "check_mtf_condition"):
            try:
                return bool(self.trader.strategy.check_mtf_condition(ticker))
            except Exception:
                return True
        return True

    def _pass_drawdown_guard(self) -> bool:
        max_daily_loss = float(getattr(self.trader, "spin_drawdown_guard", None).value()) if hasattr(self.trader, "spin_drawdown_guard") else 5.0
        initial = float(getattr(self.trader, "initial_balance", 0.0) or 0.0)
        pnl = float(getattr(self.trader, "total_realized_profit", 0.0) or 0.0)
        if initial > 0:
            loss_rate = (pnl / initial) * 100.0
            if loss_rate <= -abs(max_daily_loss):
                return False

        max_consecutive = int(getattr(self.trader, "spin_max_consecutive_losses", None).value()) if hasattr(self.trader, "spin_max_consecutive_losses") else 3
        strategy = getattr(self.trader, "strategy", None)
        if strategy is not None:
            losses = int(getattr(strategy, "consecutive_losses", 0) or 0)
            if losses >= max_consecutive:
                return False
        return True
