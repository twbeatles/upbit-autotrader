import json
import os
import tempfile
import unittest
from unittest.mock import patch

from upbit_autotrader.core.entry_filter import should_enter_by_score
from upbit_autotrader.services.holdings_service import get_account_holdings
from upbit_autotrader.services.order_service import UpbitOrderService
from upbit_autotrader.services.settings_store import load_settings, save_settings


class FakeUpbit:
    def __init__(self):
        self.sell_calls = 0
        self.buy_calls = 0
        self._balances = []

    def buy_market_order(self, ticker, amount):
        self.buy_calls += 1
        return {"uuid": f"buy-{self.buy_calls}"}

    def sell_market_order(self, ticker, qty):
        self.sell_calls += 1
        return {"uuid": f"sell-{self.sell_calls}"}

    def get_balances(self):
        return self._balances


class SettingsStoreTests(unittest.TestCase):
    def test_legacy_migration_and_v2_save(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "settings.json")
            legacy = {
                "coins": "KRW-BTC",
                "access_key": "ACCESS_LEGACY",
                "secret_key": "SECRET_LEGACY",
            }
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(legacy, fp, ensure_ascii=False, indent=2)

            loaded = load_settings(path)
            self.assertEqual(loaded["access_key"], "ACCESS_LEGACY")
            self.assertEqual(loaded["secret_key"], "SECRET_LEGACY")

            save_settings(path, loaded)

            with open(path, "r", encoding="utf-8") as fp:
                saved = json.load(fp)

            self.assertEqual(saved["settings_version"], 2)
            self.assertIn("api_credentials", saved)
            self.assertEqual(saved["api_credentials"]["storage"], "dpapi")
            self.assertNotIn("access_key", saved)
            self.assertNotIn("secret_key", saved)

            reloaded = load_settings(path)
            self.assertEqual(reloaded["access_key"], "ACCESS_LEGACY")
            self.assertEqual(reloaded["secret_key"], "SECRET_LEGACY")

    def test_decrypt_failure_returns_empty_credentials(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "settings.json")
            broken = {
                "settings_version": 2,
                "api_credentials": {
                    "storage": "dpapi",
                    "access_enc": "not-a-valid-base64",
                    "secret_enc": "not-a-valid-base64",
                },
            }
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(broken, fp, ensure_ascii=False, indent=2)

            loaded = load_settings(path)
            self.assertEqual(loaded["access_key"], "")
            self.assertEqual(loaded["secret_key"], "")
            self.assertTrue(loaded.get("_credential_error"))


class EntryFilterTests(unittest.TestCase):
    def test_entry_filter_off_does_not_block_low_score(self):
        self.assertTrue(should_enter_by_score(False, 10, 60))

    def test_entry_filter_on_applies_threshold(self):
        self.assertFalse(should_enter_by_score(True, 59, 60))
        self.assertTrue(should_enter_by_score(True, 60, 60))


class OrderServiceTests(unittest.TestCase):
    def test_prevent_duplicate_sell_order(self):
        upbit = FakeUpbit()
        service = UpbitOrderService()

        ok1, result1, _ = service.place_sell_market(upbit, "KRW-BTC", 0.1)
        ok2, result2, msg2 = service.place_sell_market(upbit, "KRW-BTC", 0.1)

        self.assertTrue(ok1)
        self.assertIsNotNone(result1.get("uuid"))
        self.assertFalse(ok2)
        self.assertIsNone(result2)
        self.assertIn("대기 중", msg2)
        self.assertEqual(upbit.sell_calls, 1)

    def test_partial_accounting_consistency(self):
        service = UpbitOrderService()
        new_invest, profit = service.apply_partial_sell_accounting(
            invest_amt=100000.0,
            remaining_qty=0.7,
            executed_volume=0.3,
            executed_price=120000.0,
        )
        # sold amount = 36,000
        # buy portion = 30,000
        self.assertAlmostEqual(new_invest, 70000.0, places=2)
        self.assertAlmostEqual(profit, 6000.0, places=2)

    def test_buy_fill_metrics_use_trade_sum_and_fee(self):
        order = {
            "executed_volume": "0.01",
            "paid_fee": "100",
            "trades": [{"price": "50000000", "volume": "0.01"}],
        }
        executed_volume, total_cost, avg_price = UpbitOrderService.get_buy_fill_metrics(order)
        self.assertAlmostEqual(executed_volume, 0.01, places=8)
        self.assertAlmostEqual(total_cost, 500100.0, places=2)
        self.assertAlmostEqual(avg_price, 50010000.0, places=2)

    def test_sell_fill_metrics_use_executed_funds_fallback(self):
        order = {
            "executed_volume": "2",
            "executed_funds": "20000",
            "paid_fee": "10",
            "trades": [],
        }
        executed_volume, net_proceeds, avg_net_price = UpbitOrderService.get_sell_fill_metrics(order)
        self.assertAlmostEqual(executed_volume, 2.0, places=8)
        self.assertAlmostEqual(net_proceeds, 19990.0, places=2)
        self.assertAlmostEqual(avg_net_price, 9995.0, places=2)


class HoldingsScopeTests(unittest.TestCase):
    @patch("upbit_autotrader.services.holdings_service.pyupbit.get_current_price")
    def test_account_holdings_include_all_krw_assets(self, mock_prices):
        upbit = FakeUpbit()
        upbit._balances = [
            {"currency": "KRW", "balance": "1000000", "avg_buy_price": "0"},
            {"currency": "BTC", "balance": "0.01", "avg_buy_price": "50000000"},
            {"currency": "ETH", "balance": "0.1", "avg_buy_price": "3000000"},
        ]
        mock_prices.return_value = {
            "KRW-BTC": 51000000.0,
            "KRW-ETH": 2900000.0,
        }

        holdings = get_account_holdings(upbit)
        tickers = {h["ticker"] for h in holdings}

        self.assertIn("KRW-BTC", tickers)
        self.assertIn("KRW-ETH", tickers)
        self.assertEqual(len(holdings), 2)


if __name__ == "__main__":
    unittest.main()


