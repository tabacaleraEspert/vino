"""
Unit tests for app.utils.parse_utils.

Pure functions — no mocks needed.
Covers: parse_period, parse_date_flex, parse_money, parse_periodo_mes,
        parse_date_ddmmyyyy, periodo_mes_to_mes_anio, normalize_mes_anio.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.utils.parse_utils import (
    normalize_mes_anio,
    parse_date_ddmmyyyy,
    parse_date_flex,
    parse_money,
    parse_period,
    parse_periodo_mes,
    periodo_mes_to_mes_anio,
)


# ---------------------------------------------------------------------------
# parse_period
# ---------------------------------------------------------------------------

class TestParsePeriod:
    def test_should_return_first_and_last_day_of_month(self):
        fd, td = parse_period("2026-04")
        assert fd == date(2026, 4, 1)
        assert td == date(2026, 4, 30)

    def test_should_handle_december(self):
        fd, td = parse_period("2025-12")
        assert fd == date(2025, 12, 1)
        assert td == date(2025, 12, 31)

    def test_should_handle_january(self):
        fd, td = parse_period("2026-01")
        assert fd == date(2026, 1, 1)
        assert td == date(2026, 1, 31)

    def test_should_handle_february_non_leap(self):
        fd, td = parse_period("2025-02")
        assert td == date(2025, 2, 28)

    def test_should_handle_february_leap(self):
        fd, td = parse_period("2024-02")
        assert td == date(2024, 2, 29)

    def test_should_raise_for_empty_string(self):
        with pytest.raises(ValueError):
            parse_period("")

    def test_should_raise_for_wrong_format(self):
        with pytest.raises(ValueError):
            parse_period("04-2026")

    def test_should_raise_for_month_zero(self):
        with pytest.raises(ValueError):
            parse_period("2026-00")

    def test_should_raise_for_month_thirteen(self):
        with pytest.raises(ValueError):
            parse_period("2026-13")


# ---------------------------------------------------------------------------
# parse_date_flex
# ---------------------------------------------------------------------------

class TestParseDateFlex:
    def test_should_parse_iso_format(self):
        assert parse_date_flex("2026-04-15") == date(2026, 4, 15)

    def test_should_parse_ddmmyyyy_format(self):
        assert parse_date_flex("15/04/2026") == date(2026, 4, 15)

    def test_should_return_none_for_none_input(self):
        assert parse_date_flex(None) is None

    def test_should_return_none_for_empty_string(self):
        assert parse_date_flex("") is None

    def test_should_parse_iso_with_time_suffix(self):
        # "2026-04-15 00:00:00" should still parse date part
        assert parse_date_flex("2026-04-15 00:00:00") == date(2026, 4, 15)

    def test_should_parse_single_digit_day_and_month(self):
        assert parse_date_flex("1/4/2026") == date(2026, 4, 1)

    def test_should_return_none_for_completely_invalid_string(self):
        assert parse_date_flex("not-a-date") is None


# ---------------------------------------------------------------------------
# parse_date_ddmmyyyy
# ---------------------------------------------------------------------------

class TestParseDateDdmmyyyy:
    def test_should_parse_standard_format(self):
        assert parse_date_ddmmyyyy("01/12/2025") == date(2025, 12, 1)

    def test_should_parse_with_trailing_space(self):
        assert parse_date_ddmmyyyy("17/02/2026 ") == date(2026, 2, 17)

    def test_should_parse_with_time_suffix(self):
        assert parse_date_ddmmyyyy("6/02/2026 0:00:00") == date(2026, 2, 6)

    def test_should_return_none_for_none(self):
        assert parse_date_ddmmyyyy(None) is None

    def test_should_return_none_for_iso_format(self):
        # ISO "2026-04-01" has no slashes in right positions
        assert parse_date_ddmmyyyy("2026-04-01") is None

    def test_should_return_none_for_invalid_date(self):
        assert parse_date_ddmmyyyy("99/99/9999") is None


# ---------------------------------------------------------------------------
# parse_money
# ---------------------------------------------------------------------------

class TestParseMoney:
    def test_should_parse_plain_number(self):
        assert parse_money("1500") == 1500.0

    def test_should_parse_with_dollar_sign(self):
        assert parse_money("$ 1500") == 1500.0

    def test_should_parse_comma_as_thousands_separator(self):
        assert parse_money("48,146") == 48146.0

    def test_should_parse_decimal_with_dot(self):
        assert parse_money("1500.50") == 1500.50

    def test_should_return_zero_for_none(self):
        assert parse_money(None) == 0.0

    def test_should_return_zero_for_empty_string(self):
        assert parse_money("") == 0.0

    def test_should_handle_numeric_input(self):
        assert parse_money(250) == 250.0

    def test_should_handle_negative_values(self):
        assert parse_money("-100") == -100.0

    def test_should_return_zero_for_non_numeric_string(self):
        assert parse_money("abc") == 0.0

    # Argentine format: dot = thousands separator
    def test_should_parse_dot_as_thousands_separator(self):
        assert parse_money("$5.000") == 5000.0

    def test_should_parse_multiple_dots_as_thousands(self):
        assert parse_money("$1.500.000") == 1500000.0

    def test_should_parse_argentine_format_with_decimals(self):
        assert parse_money("$50.000,50") == 50000.50

    def test_should_parse_dot_thousands_plain(self):
        assert parse_money("5.000") == 5000.0

    def test_should_preserve_real_decimal(self):
        assert parse_money("48146.50") == 48146.50

    def test_should_parse_comma_as_decimal_two_digits(self):
        assert parse_money("48,50") == 48.50


# ---------------------------------------------------------------------------
# parse_periodo_mes
# ---------------------------------------------------------------------------

class TestParsePeriodoMes:
    def test_should_parse_mmyy_format(self):
        assert parse_periodo_mes("04/26") == date(2026, 4, 1)

    def test_should_parse_yyyy_mm_format(self):
        assert parse_periodo_mes("2026-04") == date(2026, 4, 1)

    def test_should_handle_yy_below_50(self):
        assert parse_periodo_mes("01/25") == date(2025, 1, 1)

    def test_should_handle_yy_50_and_above(self):
        assert parse_periodo_mes("01/50") == date(1950, 1, 1)

    def test_should_raise_for_empty_string(self):
        with pytest.raises(ValueError):
            parse_periodo_mes("")

    def test_should_raise_for_invalid_format(self):
        with pytest.raises(ValueError):
            parse_periodo_mes("2026/04/01")

    def test_should_raise_for_invalid_month_in_yyyy_mm(self):
        with pytest.raises(ValueError):
            parse_periodo_mes("2026-13")


# ---------------------------------------------------------------------------
# periodo_mes_to_mes_anio
# ---------------------------------------------------------------------------

class TestPeriodoMesToMesAnio:
    def test_should_format_date_to_mmyy(self):
        assert periodo_mes_to_mes_anio(date(2026, 4, 1)) == "04/26"

    def test_should_format_december(self):
        assert periodo_mes_to_mes_anio(date(2025, 12, 1)) == "12/25"

    def test_should_return_empty_string_for_none(self):
        assert periodo_mes_to_mes_anio(None) == ""


# ---------------------------------------------------------------------------
# normalize_mes_anio
# ---------------------------------------------------------------------------

class TestNormalizeMesAnio:
    def test_should_normalize_yyyy_mm(self):
        assert normalize_mes_anio("2025-10") == "2025-10"

    def test_should_normalize_mm_yyyy(self):
        assert normalize_mes_anio("10/2025") == "2025-10"

    def test_should_normalize_mmyy_format(self):
        assert normalize_mes_anio("10/25") == "2025-10"

    def test_should_pad_single_digit_month(self):
        assert normalize_mes_anio("4/2026") == "2026-04"

    def test_should_return_empty_string_for_none(self):
        assert normalize_mes_anio(None) == ""

    def test_should_return_empty_string_for_blank(self):
        assert normalize_mes_anio("") == ""
