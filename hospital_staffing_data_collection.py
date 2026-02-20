"""
NY Hospital Staffing Plans - RN Day Shift Only
===============================================
Scrapes normalized PDFs and extracts only RN Day Shift staffing data.

Install:
  pip install pdfplumber requests beautifulsoup4 pandas

Run:
  python parse_rn_day_shift.py
"""

import requests
import pdfplumber
import pandas as pd
import io
import time
from bs4 import BeautifulSoup

BASE_URL = "https://www.health.ny.gov"
PAGE_URL = f"{BASE_URL}/facilities/hospital/staffing_plans/"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}


def get_facilities():
    print("Fetching facility list...")
    resp = requests.get(PAGE_URL, timeout=30, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    facilities = []
    for row in soup.select("table tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        norm_link = cols[3].find("a")
        if norm_link:
            facilities.append({
                "pfi":    cols[0].text.strip(),
                "name":   cols[1].text.strip(),
                "county": cols[2].text.strip(),
                "url":    BASE_URL + norm_link["href"],
            })

    print(f"Found {len(facilities)} facilities")
    return facilities


def parse_rn_day_shift(pdf_bytes):
    """Extract hospital info and all RN Day Shift rows from a PDF."""
    hospital_info = {}
    rn_day_rows = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            first_line = text.split("\n")[0].strip().upper()

            # Page 1: hospital info
            if "HOSPITAL INFORMATION" in first_line:
                tables = page.extract_tables()
                if tables:
                    for row in tables[0][1:]:
                        if row and len(row) >= 2 and row[0]:
                            key = row[0].strip().lower().replace(" ", "_")
                            hospital_info[key] = (row[1] or "").strip()

            # RN Day Shift page
            elif "RN DAY SHIFT" in first_line:
                tables = page.extract_tables()
                if not tables:
                    continue
                # Skip row 0 (section title) and row 1 (column headers), data starts at row 2
                for row in tables[0][2:]:
                    if not row or not row[0] or not str(row[0]).strip():
                        continue
                    rn_day_rows.append({
                        "unit_name":       str(row[0]).strip(),
                        "unit_description": str(row[1]).strip() if row[1] else "",
                        "rn_count":        str(row[2]).strip() if row[2] else "",
                        "rn_hours_per_pt": str(row[3]).strip() if row[3] else "",
                        "avg_patients":    str(row[4]).strip() if row[4] else "",
                        "rn_pts_per_nurse": str(row[5]).strip() if row[5] else "",
                    })

    return hospital_info, rn_day_rows


def main():
    #  # ── Test on a single PDF ──────────────────────────────────────────────────
    # test_url = "https://www.health.ny.gov/facilities/hospital/staffing_plans/docs/0001.pdf"
    # print(f"Testing on: {test_url}")

    # headers = HEADERS
    # resp = requests.get(test_url, timeout=60, headers=headers)
    # resp.raise_for_status()
    # hospital_info, rn_day_rows = parse_rn_day_shift(resp.content)

    # rows = []
    # for unit in rn_day_rows:
    #     rows.append({
    #         "pfi":           hospital_info.get("reporting_organization_id", ""),
    #         "hospital_name": hospital_info.get("reporting_organization", ""),
    #         "county":        hospital_info.get("county", ""),
    #         "region":        hospital_info.get("region", ""),
    #         **unit,
    #     })

    # df = pd.DataFrame(rows)
    # print(df.to_string())
    # df.to_csv("rn_day_shift_test.csv", index=False)
    # print(f"\nSaved {len(rows)} rows to rn_day_shift_test.csv")

    facilities = get_facilities()
    all_rows = []
    errors = []

    for i, f in enumerate(facilities):
        print(f"[{i+1}/{len(facilities)}] {f['pfi']} - {f['name']}")
        try:
            headers = HEADERS
            resp = requests.get(f["url"], timeout=60, headers=headers)
            resp.raise_for_status()
            hospital_info, rn_day_rows = parse_rn_day_shift(resp.content)

            for unit in rn_day_rows:
                all_rows.append({
                    "pfi":           f["pfi"],
                    "hospital_name": f["name"],
                    "county":        f["county"],
                    "region":        hospital_info.get("region", ""),
                    **unit,
                })

        except Exception as e:
            print(f"  ERROR: {e}")
            errors.append({"pfi": f["pfi"], "name": f["name"], "error": str(e)})

        time.sleep(0.75)

    df = pd.DataFrame(all_rows)
    df.to_csv("rn_day_shift.csv", index=False)
    print(f"\nDone! {len(all_rows)} rows saved to rn_day_shift.csv")

    if errors:
        pd.DataFrame(errors).to_csv("rn_day_shift_errors.csv", index=False)
        print(f"{len(errors)} errors saved to rn_day_shift_errors.csv")


if __name__ == "__main__":
    main()