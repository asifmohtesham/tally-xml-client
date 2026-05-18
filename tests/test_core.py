import pytest
from datetime import date
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
import requests as req_lib

from tally_xml_client import core


class TestBuildUrl:
    def test_localhost(self):
        assert core.build_url("localhost", 9000) == "http://localhost:9000"

    def test_ip_and_custom_port(self):
        assert core.build_url("192.168.1.10", 9002) == "http://192.168.1.10:9002"


class TestParseDateArg:
    def test_dd_mm_yyyy(self):
        assert core.parse_date_arg("01-04-2025") == date(2025, 4, 1)

    def test_dd_slash_mm_yyyy(self):
        assert core.parse_date_arg("01/04/2025") == date(2025, 4, 1)

    def test_yyyy_mm_dd(self):
        assert core.parse_date_arg("2025-04-01") == date(2025, 4, 1)

    def test_dd_mon_yyyy(self):
        assert core.parse_date_arg("01-Apr-2025") == date(2025, 4, 1)

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date"):
            core.parse_date_arg("not-a-date")

    def test_strips_whitespace(self):
        assert core.parse_date_arg("  01-04-2025  ") == date(2025, 4, 1)


class TestFormatAmount:
    def test_negative_becomes_positive(self):
        assert core.format_amount("-45000.00") == "45,000.00"

    def test_strips_existing_commas_before_parsing(self):
        assert core.format_amount("1,12,500") == "112,500.00"

    def test_positive_passthrough(self):
        assert core.format_amount("45000") == "45,000.00"

    def test_invalid_returns_stripped_string(self):
        assert core.format_amount("  N/A  ") == "N/A"
