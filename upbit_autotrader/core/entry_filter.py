"""Entry score gating helpers."""


def should_enter_by_score(use_entry_scoring: bool, score: float, threshold: int) -> bool:
    if not use_entry_scoring:
        return True
    return score >= threshold

