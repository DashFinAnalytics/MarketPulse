"""
SEC EDGAR data fetcher — filings browser and insider activity (Form 4).
All endpoints are free and require no API key.
"""

import logging
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "GlobalFinanceDashboard research@example.com"}
EFTS_BASE = "https://efts.sec.gov"
DATA_BASE = "https://data.sec.gov"


def _get(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"SEC EDGAR request failed {url}: {e}")
        return None


def search_filings(query: str, form_types=None, days_back=90, limit=20):
    """
    Full-text search across SEC EDGAR filings.
    form_types: list of form types e.g. ['10-K','10-Q','8-K']
    """
    if form_types is None:
        form_types = ["10-K", "10-Q", "8-K"]
    start = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end = datetime.utcnow().strftime("%Y-%m-%d")
    params = {
        "q": f'"{query}"',
        "dateRange": "custom",
        "startdt": start,
        "enddt": end,
        "forms": ",".join(form_types),
        "_source": "file_date,period_of_report,entity_name,file_num,form_type,file_id",
        "from": 0,
        "size": limit,
    }
    data = _get(f"{EFTS_BASE}/LATEST/search-index", params=params)
    if not data:
        return []
    hits = data.get("hits", {}).get("hits", [])
    results = []
    for h in hits:
        s = h.get("_source", {})
        results.append(
            {
                "company": s.get("entity_name", "N/A"),
                "form_type": s.get("form_type", "N/A"),
                "filed_date": s.get("file_date", "N/A"),
                "period": s.get("period_of_report", "N/A"),
                "file_num": s.get("file_num", ""),
                "url": _build_filing_url(h.get("_id", "")),
            }
        )
    return results


def get_company_cik(ticker: str):
    """Resolve a ticker symbol to a CIK number."""
    data = _get(f"{DATA_BASE}/submissions/CIK{ticker.upper()}.json")
    if data:
        return data.get("cik")
    # Try the ticker mapping endpoint
    mapping = _get("https://www.sec.gov/files/company_tickers.json")
    if mapping:
        for entry in mapping.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"]).zfill(10)
    return None


def get_company_filings(ticker: str, form_types=None, limit=25):
    """Get recent filings for a company from EDGAR submissions API."""
    if form_types is None:
        form_types = ["10-K", "10-Q", "8-K", "6-K"]
    try:
        mapping = _get("https://www.sec.gov/files/company_tickers.json")
        cik_raw = None
        entity_name = ticker
        if mapping:
            for entry in mapping.values():
                if entry.get("ticker", "").upper() == ticker.upper():
                    cik_raw = str(entry["cik_str"]).zfill(10)
                    entity_name = entry.get("title", ticker)
                    break
        if not cik_raw:
            return []

        data = _get(f"{DATA_BASE}/submissions/CIK{cik_raw}.json")
        if not data:
            return []

        filings = data.get("filings", {}).get("recent", {})
        if not filings:
            return []

        results = []
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        desc = filings.get("primaryDocument", [])
        accnums = filings.get("accessionNumber", [])
        docs = filings.get("primaryDocDescription", [])

        for i, form in enumerate(forms):
            if form in form_types:
                accn = accnums[i].replace("-", "") if i < len(accnums) else ""
                doc = desc[i] if i < len(desc) else ""
                url = (
                    (f"https://www.sec.gov/Archives/edgar/data/{int(cik_raw)}/{accn}/{doc}")
                    if accn and doc
                    else ""
                )
                results.append(
                    {
                        "company": entity_name,
                        "ticker": ticker.upper(),
                        "form_type": form,
                        "filed_date": dates[i] if i < len(dates) else "",
                        "description": docs[i] if i < len(docs) else "",
                        "url": url
                        or f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_raw}&type={form}",
                    }
                )
                if len(results) >= limit:
                    break
        return results
    except Exception as e:
        logger.error(f"Error fetching filings for {ticker}: {e}")
        return []


def get_insider_transactions(ticker: str, limit=30):
    """
    Fetch recent Form 4 (insider trading) filings for a company.
    Returns list of insider transaction dicts.
    """
    try:
        mapping = _get("https://www.sec.gov/files/company_tickers.json")
        cik_raw = None
        if mapping:
            for entry in mapping.values():
                if entry.get("ticker", "").upper() == ticker.upper():
                    cik_raw = str(entry["cik_str"]).zfill(10)
                    break
        if not cik_raw:
            return []

        data = _get(f"{DATA_BASE}/submissions/CIK{cik_raw}.json")
        if not data:
            return []

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accnums = filings.get("accessionNumber", [])

        results = []
        for i, form in enumerate(forms):
            if form == "4":
                accn = accnums[i] if i < len(accnums) else ""
                date = dates[i] if i < len(dates) else ""
                url = (
                    (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{int(cik_raw)}/{accn.replace('-', '')}/"
                    )
                    if accn
                    else ""
                )
                results.append(
                    {
                        "ticker": ticker.upper(),
                        "form_type": "4",
                        "filed_date": date,
                        "accession": accn,
                        "edgar_url": url
                        or f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_raw}&type=4",
                    }
                )
                if len(results) >= limit:
                    break
        return results
    except Exception as e:
        logger.error(f"Error fetching insider transactions for {ticker}: {e}")
        return []


def _build_filing_url(file_id: str) -> str:
    """Convert EDGAR file_id to a viewer URL."""
    if not file_id:
        return ""
    return f"https://efts.sec.gov/LATEST/search-index?q={file_id}"
