import xml.etree.ElementTree as ET
from datetime import date, datetime

import requests

TALLY_HOST = "localhost"
TALLY_PORT = 9000
TALLY_TIMEOUT = 30

_DATE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d%m%Y", "%d-%b-%Y"]


def build_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def parse_date_arg(s: str) -> date:
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Invalid date: {s!r}. Accepted formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY"
    )


def format_amount(raw: str) -> str:
    try:
        val = float(raw.replace(",", "").strip())
        return f"{abs(val):,.2f}"
    except ValueError:
        return raw.strip()


def _parse_tally_date(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%Y%m%d", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return raw


def _safe_text(element: ET.Element | None, default: str = "") -> str:
    if element is None:
        return default
    return (element.text or "").strip()


def _xml_company_info() -> str:
    return """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Companies</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _xml_sales_vouchers(from_date: date, to_date: date) -> str:
    fd = from_date.strftime("%Y%m%d")
    td = to_date.strftime("%Y%m%d")
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>$$CollectionName:PyTallySalesVouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVFROMDATE>{fd}</SVFROMDATE>
          <SVTODATE>{td}</SVTODATE>
        </STATICVARIABLES>
        <TDLMESSAGE>
          <COLLECTION NAME="PyTallySalesVouchers" ISMODIFY="No">
            <TYPE>Voucher</TYPE>
            <FILTER>PyIsSalesVoucher</FILTER>
          </COLLECTION>
          <SYSTEM TYPE="Formulae" NAME="PyIsSalesVoucher">
            $$VoucherTypeName = "Sales"
          </SYSTEM>
        </TDLMESSAGE>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _post_xml(xml_body: str, url: str) -> ET.Element:
    headers = {
        "Content-Type": "text/xml;charset=utf-8",
        "Content-Length": str(len(xml_body.encode("utf-8"))),
    }
    try:
        resp = requests.post(
            url, data=xml_body.encode("utf-8"), headers=headers, timeout=TALLY_TIMEOUT
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach TallyPrime at {url}. "
            "Ensure TallyPrime is running and the HTTP server is enabled on port 9000."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"Request timed out after {TALLY_TIMEOUT}s. TallyPrime may be busy."
        )
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"HTTP error: {exc}")

    try:
        return ET.fromstring(resp.content)
    except ET.ParseError as exc:
        raise RuntimeError(f"Could not parse Tally response as XML: {exc}")


def parse_vouchers(root: ET.Element) -> list[dict]:
    vouchers = []
    for voucher in root.iter("VOUCHER"):
        vtype = (
            _safe_text(voucher.find("VOUCHERTYPENAME")) or voucher.get("VCHTYPE", "")
        ).strip()
        if vtype.lower() != "sales":
            continue
        row = {
            "date":       _parse_tally_date(_safe_text(voucher.find("DATE"))),
            "voucher_no": _safe_text(voucher.find("VOUCHERNUMBER")),
            "party":      _safe_text(voucher.find("PARTYLEDGERNAME")),
            "amount":     format_amount(_safe_text(voucher.find("AMOUNT"))),
            "narration":  _safe_text(voucher.find("NARRATION")),
            "reference":  _safe_text(voucher.find("REFERENCE")),
            "vch_type":   vtype,
        }
        vouchers.append(row)
    vouchers.sort(key=lambda v: (v["date"], v["voucher_no"]))
    return vouchers


def check_connection(url: str) -> str:
    root = _post_xml(_xml_company_info(), url)
    for company in root.iter("COMPANY"):
        name = company.findtext("NAME") or company.get("NAME", "")
        if name:
            return name
    return root.findtext(".//COMPANYNAME") or root.findtext(".//NAME") or "Unknown"


def fetch_vouchers(url: str, from_date: date, to_date: date) -> list[dict]:
    root = _post_xml(_xml_sales_vouchers(from_date, to_date), url)
    return parse_vouchers(root)
