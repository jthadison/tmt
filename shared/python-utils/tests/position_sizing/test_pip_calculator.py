"""
Unit tests for PipCalculator

Tests pip value calculation for all instrument types.
"""

import pytest
from decimal import Decimal
import sys
import os

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from position_sizing.pip_calculator import PipCalculator, PipInfo


class TestPipCalculator:
    """Test suite for PipCalculator"""

    @pytest.fixture
    def calculator(self):
        """Create pip calculator instance"""
        return PipCalculator()

    def test_standard_forex_pair(self, calculator):
        """Test pip value for standard forex pair (EUR_USD)"""
        pip_info = calculator.get_pip_info("EUR_USD")

        assert pip_info.pip_value == Decimal("0.0001")
        assert pip_info.precision == 5
        assert pip_info.point_value == Decimal("0.00001")  # Pipette
        assert pip_info.pip_position == 4

    def test_jpy_pair(self, calculator):
        """Test pip value for JPY pair (USD_JPY)"""
        pip_info = calculator.get_pip_info("USD_JPY")

        assert pip_info.pip_value == Decimal("0.01")
        assert pip_info.precision == 3
        assert pip_info.pip_position == 2

    def test_eur_jpy_pair(self, calculator):
        """Test pip value for EUR_JPY pair"""
        pip_info = calculator.get_pip_info("EUR_JPY")

        assert pip_info.pip_value == Decimal("0.01")
        assert pip_info.precision == 3

    def test_gold_xau_usd(self, calculator):
        """Test pip value for gold (XAU_USD)"""
        pip_info = calculator.get_pip_info("XAU_USD")

        assert pip_info.pip_value == Decimal("0.01")
        assert pip_info.precision == 2

    def test_silver_xag_usd(self, calculator):
        """Test pip value for silver (XAG_USD)"""
        pip_info = calculator.get_pip_info("XAG_USD")

        assert pip_info.pip_value == Decimal("0.001")
        assert pip_info.precision == 3

    def test_btc_crypto(self, calculator):
        """Test pip value for Bitcoin (BTC_USD)"""
        pip_info = calculator.get_pip_info("BTC_USD")

        assert pip_info.pip_value == Decimal("1.0")
        assert pip_info.precision == 1

    def test_eth_crypto(self, calculator):
        """Test pip value for Ethereum (ETH_USD)"""
        pip_info = calculator.get_pip_info("ETH_USD")

        assert pip_info.pip_value == Decimal("0.01")
        assert pip_info.precision == 2

    def test_calculate_stop_distance_pips_eur_usd(self, calculator):
        """Test stop distance calculation for EUR_USD"""
        stop_distance = calculator.calculate_stop_distance_pips(
            instrument="EUR_USD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0800")
        )

        # 0.0050 / 0.0001 = 50 pips
        assert stop_distance == Decimal("50")

    def test_calculate_stop_distance_pips_usd_jpy(self, calculator):
        """Test stop distance calculation for USD_JPY"""
        stop_distance = calculator.calculate_stop_distance_pips(
            instrument="USD_JPY",
            entry_price=Decimal("149.50"),
            stop_loss=Decimal("150.00")
        )

        # 0.50 / 0.01 = 50 pips
        assert stop_distance == Decimal("50")

    def test_calculate_stop_distance_pips_gold(self, calculator):
        """Test stop distance calculation for gold"""
        stop_distance = calculator.calculate_stop_distance_pips(
            instrument="XAU_USD",
            entry_price=Decimal("1950.00"),
            stop_loss=Decimal("1945.00")
        )

        # 5.00 / 0.01 = 500 pips
        assert stop_distance == Decimal("500")

    def test_calculate_pip_value_in_quote_currency(self, calculator):
        """Test pip value calculation in quote currency"""
        pip_value = calculator.calculate_pip_value_in_quote_currency(
            instrument="EUR_USD",
            units=10000
        )

        # 10,000 units * 0.0001 = 1.0 USD per pip
        assert pip_value == Decimal("1.0")

    def test_calculate_pip_value_usd_jpy(self, calculator):
        """Test pip value for USD_JPY with 10k units"""
        pip_value = calculator.calculate_pip_value_in_quote_currency(
            instrument="USD_JPY",
            units=10000
        )

        # 10,000 units * 0.01 = 100 JPY per pip
        assert pip_value == Decimal("100")

    def test_get_instrument_type_forex(self, calculator):
        """Test instrument type detection for forex"""
        assert calculator.get_instrument_type("EUR_USD") == "forex"
        assert calculator.get_instrument_type("GBP_USD") == "forex"

    def test_get_instrument_type_jpy(self, calculator):
        """Test instrument type detection for JPY pairs"""
        assert calculator.get_instrument_type("USD_JPY") == "jpy_pair"
        assert calculator.get_instrument_type("EUR_JPY") == "jpy_pair"

    def test_get_instrument_type_metals(self, calculator):
        """Test instrument type detection for precious metals"""
        assert calculator.get_instrument_type("XAU_USD") == "gold"
        assert calculator.get_instrument_type("XAG_USD") == "silver"

    def test_get_instrument_type_crypto(self, calculator):
        """Test instrument type detection for crypto"""
        assert calculator.get_instrument_type("BTC_USD") == "crypto"
        assert calculator.get_instrument_type("ETH_USD") == "crypto"

    def test_case_insensitive_instrument(self, calculator):
        """Test that instrument parsing is case-insensitive"""
        pip_info_upper = calculator.get_pip_info("EUR_USD")
        pip_info_lower = calculator.get_pip_info("eur_usd")

        assert pip_info_upper.pip_value == pip_info_lower.pip_value

    def test_negative_stop_distance(self, calculator):
        """Test that stop distance is always positive"""
        # Entry below stop (short trade)
        stop_distance = calculator.calculate_stop_distance_pips(
            instrument="EUR_USD",
            entry_price=Decimal("1.0800"),
            stop_loss=Decimal("1.0850")
        )

        # Should be positive 50 pips
        assert stop_distance == Decimal("50")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
