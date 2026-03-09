from upbit_autotrader.services.paper_order_service import UpbitPaperOrderService


def test_paper_buy_and_sell_updates_balances_and_holdings():
    svc = UpbitPaperOrderService(fee_rate=0.0005, slippage_bps=0)
    svc.seed_balance(100000)

    ok_buy, buy_result, msg_buy = svc.place_buy_market("KRW-BTC", 50000, 1000)
    assert ok_buy, msg_buy
    assert buy_result and "uuid" in buy_result

    holding = svc.get_holdings()["KRW-BTC"]
    qty = holding["qty"]
    assert qty > 0
    assert svc.get_krw_balance() < 100000

    ok_sell, sell_result, msg_sell = svc.place_sell_market("KRW-BTC", qty / 2, 1200)
    assert ok_sell, msg_sell
    assert sell_result and "uuid" in sell_result
    assert svc.get_krw_balance() > 50000


def test_paper_rejects_overbudget_and_oversell():
    svc = UpbitPaperOrderService(fee_rate=0.0005, slippage_bps=0)
    svc.seed_balance(10000)

    ok_buy, _, _ = svc.place_buy_market("KRW-BTC", 20000, 1000)
    assert not ok_buy

    ok_sell, _, _ = svc.place_sell_market("KRW-BTC", 1.0, 1000)
    assert not ok_sell


def test_paper_order_can_be_queried():
    svc = UpbitPaperOrderService(fee_rate=0.0005, slippage_bps=0)
    svc.seed_balance(50000)

    ok, result, _ = svc.place_buy_market("KRW-ETH", 10000, 2000)
    assert ok
    assert result is not None
    order = svc.get_order(result["uuid"])
    assert order is not None
    assert order["state"] == "done"

