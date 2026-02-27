"""
NY Hospital Staffing Plans - RN Day, Evening & Night Shifts
============================================================
Scrapes normalized PDFs and extracts RN staffing data for all three shifts,
with one row per clinical unit containing all shifts side by side.

Only keeps units: Critical Care, Medical/Surgical, Emergency Department

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

KEEP_UNITS = {"intensive care", "critical care", "medical/surgical", "emergency department"}

SHIFT_KEYWORDS = {
    "day":     "DAY UNLICENSED SHIFT",
    "evening": "EVENING UNLICENSED SHIFT",
    "night":   "NIGHT UNLICENSED SHIFT",
}


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


def parse_rn_shifts(pdf_bytes):
    """
    Returns:
      hospital_info: dict
      units: dict keyed by unit_name ->
               { "unit_description": ...,
                 "day_rn_count": ..., "day_rn_hours_per_pt": ..., etc.
                 "evening_rn_count": ..., etc.
                 "night_rn_count": ..., etc. }
    """
    hospital_info = {}
    units = {}

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            first_line = text.split("\n")[0].strip().upper()

            # Hospital info (page 1)
            if "HOSPITAL INFORMATION" in first_line:
                tables = page.extract_tables()
                if tables:
                    for row in tables[0][1:]:
                        if row and len(row) >= 2 and row[0]:
                            key = row[0].strip().lower().replace(" ", "_")
                            hospital_info[key] = (row[1] or "").strip()
                continue

            # Detect which shift this page is
            shift = None
            for shift_name, keyword in SHIFT_KEYWORDS.items():
                if keyword in first_line:
                    shift = shift_name
                    break
            if shift is None:
                continue

            tables = page.extract_tables()
            if not tables:
                continue

            prefix = f"{shift}_"

            for row in tables[0][2:]:  # skip title row and header row
                if not row or not row[0] or not str(row[0]).strip():
                    continue
                unit_name = str(row[0]).strip()

                # Filter to only the units we care about
                if unit_name.lower() not in KEEP_UNITS:
                    continue

                if unit_name not in units:
                    units[unit_name] = {
                        "unit_name":        unit_name,
                        "unit_description": str(row[1]).strip() if row[1] else "",
                    }

                u = units[unit_name]
                u[f"{prefix}unlicensed_count"]        = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                u[f"{prefix}unlicensed_hours_per_pt"] = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                u[f"{prefix}avg_patients"]     = str(row[4]).strip() if len(row) > 4 and row[4] else ""
                u[f"{prefix}unlicensed_pts_per_nurse"] = str(row[5]).strip() if len(row) > 5 and row[5] else ""

    return hospital_info, units


def main():
    #  # ── Test on a single PDF ──────────────────────────────────────────────────
    # test_url = "https://www.health.ny.gov/facilities/hospital/staffing_plans/docs/0001.pdf"
    # print(f"Testing on: {test_url}")

    # resp = requests.get(test_url, timeout=60, headers=HEADERS)
    # resp.raise_for_status()
    # hospital_info, units = parse_rn_shifts(resp.content)

    # rows = []
    # for unit in units.values():
    #     rows.append({
    #         "pfi":           hospital_info.get("reporting_organization_id", ""),
    #         "hospital_name": hospital_info.get("reporting_organization", ""),
    #         "county":        hospital_info.get("county", ""),
    #         "region":        hospital_info.get("region", ""),
    #         **unit,
    #     })

    # print("\nAll unit names found in this PDF:")
    # with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
    #     for page in pdf.pages:
    #         text = page.extract_text() or ""
    #         first_line = text.split("\n")[0].strip().upper()
    #         if "RN DAY SHIFT" in first_line:
    #             tables = page.extract_tables()
    #             if tables:
    #                 for row in tables[0][2:]:
    #                     if row and row[0] and str(row[0]).strip():
    #                         print(f"  '{row[0].strip()}'")

    # df = pd.DataFrame(rows)
    # print(df.to_string())
    # df.to_csv("rn_shifts_test.csv", index=False)
    # print(f"\nSaved {len(rows)} rows to rn_shifts_test.csv")
    facilities = get_facilities()
    all_rows = []
    errors = []

    for i, f in enumerate(facilities):
        print(f"[{i+1}/{len(facilities)}] {f['pfi']} - {f['name']}")
        try:
            resp = requests.get(f["url"], timeout=60, headers=HEADERS)
            resp.raise_for_status()
            hospital_info, units = parse_rn_shifts(resp.content)

            for unit in units.values():
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
    df.to_csv("unlicensed_shifts_all.csv", index=False)
    print(f"\nDone! {len(all_rows)} rows saved to unlicensed_shifts_all.csv")

    if errors:
        pd.DataFrame(errors).to_csv("unlicensed_shifts_errors.csv", index=False)
        print(f"{len(errors)} errors saved to unlicensed_shifts_errors.csv")


if __name__ == "__main__":
    main()