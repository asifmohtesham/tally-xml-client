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


class TestParseVouchers:
    def test_filters_to_sales_only(self):
        xml = """<ENVELOPE>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>SAL/001</VOUCHERNUMBER>
            <PARTYLEDGERNAME>XYZ Traders</PARTYLEDGERNAME>
            <AMOUNT>-45000</AMOUNT>
          </VOUCHER>
          <VOUCHER>
            <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>PUR/001</VOUCHERNUMBER>
            <AMOUNT>-5000</AMOUNT>
          </VOUCHER>
        </ENVELOPE>"""
        result = core.parse_vouchers(ET.fromstring(xml))
        assert len(result) == 1
        assert result[0]["voucher_no"] == "SAL/001"

    def test_amount_is_absolute_value(self):
        xml = """<ENVELOPE>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>SAL/001</VOUCHERNUMBER>
            <AMOUNT>-45000</AMOUNT>
          </VOUCHER>
        </ENVELOPE>"""
        result = core.parse_vouchers(ET.fromstring(xml))
        assert result[0]["amount"] == "45,000.00"

    def test_sorted_by_date_then_voucher_number(self):
        xml = """<ENVELOPE>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250402</DATE>
            <VOUCHERNUMBER>SAL/002</VOUCHERNUMBER>
            <AMOUNT>-1000</AMOUNT>
          </VOUCHER>
          <VOUCHER>
            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
            <DATE>20250401</DATE>
            <VOUCHERNUMBER>SAL/001</VOUCHERNUMBER>
            <AMOUNT>-2000</AMOUNT>
          </VOUCHER>
        </ENVELOPE>"""
        result = core.parse_vouchers(ET.fromstring(xml))
        assert result[0]["voucher_no"] == "SAL/001"
        assert result[1]["voucher_no"] == "SAL/002"

    def test_empty_envelope_returns_empty_list(self):
        root = ET.fromstring("<ENVELOPE></ENVELOPE>")
        assert core.parse_vouchers(root) == []


class TestPostXml:
    def test_connection_error_raises_runtime_error(self):
        with patch("tally_xml_client.core.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.ConnectionError()
            with pytest.raises(RuntimeError, match="Cannot reach"):
                core._post_xml("<XML/>", "http://localhost:9000")

    def test_timeout_raises_runtime_error(self):
        with patch("tally_xml_client.core.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.Timeout()
            with pytest.raises(RuntimeError, match="timed out"):
                core._post_xml("<XML/>", "http://localhost:9000")

    def test_invalid_xml_response_raises_runtime_error(self):
        mock_resp = MagicMock()
        mock_resp.content = b"not xml <<<>>>"
        mock_resp.raise_for_status = MagicMock()
        with patch("tally_xml_client.core.requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="parse"):
                core._post_xml("<XML/>", "http://localhost:9000")

    def test_valid_response_returns_element(self):
        mock_resp = MagicMock()
        mock_resp.content = b"<ROOT><DATA>ok</DATA></ROOT>"
        mock_resp.raise_for_status = MagicMock()
        with patch("tally_xml_client.core.requests.post", return_value=mock_resp):
            root = core._post_xml("<XML/>", "http://localhost:9000")
        assert root.tag == "ROOT"


class TestCheckConnection:
    def test_returns_company_name_from_name_element(self):
        mock_resp = MagicMock()
        mock_resp.content = (
            b"<ENVELOPE><COMPANY><NAME>ABC Pvt Ltd</NAME></COMPANY></ENVELOPE>"
        )
        mock_resp.raise_for_status = MagicMock()
        with patch("tally_xml_client.core.requests.post", return_value=mock_resp):
            name = core.check_connection("http://localhost:9000")
        assert name == "ABC Pvt Ltd"

    def test_propagates_runtime_error_on_connection_failure(self):
        with patch("tally_xml_client.core.requests.post") as mock_post:
            mock_post.side_effect = req_lib.exceptions.ConnectionError()
            with pytest.raises(RuntimeError):
                core.check_connection("http://localhost:9000")


class TestCredsXml:
    def test_empty_username_returns_empty_string(self):
        assert core._creds_xml("", "") == ""
        assert core._creds_xml("", "secret") == ""

    def test_username_only_includes_svcusername(self):
        result = core._creds_xml("admin", "")
        assert "<SVCUSERNAME>admin</SVCUSERNAME>" in result
        assert "SVCPASSWORD" not in result

    def test_username_and_password_includes_both(self):
        result = core._creds_xml("admin", "secret")
        assert "<SVCUSERNAME>admin</SVCUSERNAME>" in result
        assert "<SVCPASSWORD>secret</SVCPASSWORD>" in result

    def test_credentials_injected_into_company_info_xml(self):
        xml = core._xml_company_info("admin", "secret")
        assert "<SVCUSERNAME>admin</SVCUSERNAME>" in xml
        assert "<SVCPASSWORD>secret</SVCPASSWORD>" in xml

    def test_no_credentials_in_xml_when_username_empty(self):
        xml = core._xml_company_info("", "")
        assert "SVCUSERNAME" not in xml
        assert "SVCPASSWORD" not in xml
