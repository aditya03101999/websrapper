import requests
import pandas as pd
import re
import time
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class IBBIScraper:
    BASE_URL = "https://ibbi.gov.in"

    def __init__(self):
        self.progress_callback = None

        # Setup session with retries
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    # -------------------------------
    # Progress callback
    # -------------------------------
    def set_progress_callback(self, callback):
        """
        Accepts a callback function: callback(current_page, total_pages)
        """
        self.progress_callback = callback

    # -------------------------------
    # Extract Form G URL + File Type
    # -------------------------------
    def extract_formg_link(self, td):
        try:
            a_tag = td.find("a")
            if not a_tag:
                return "", "UNKNOWN"

            onclick = a_tag.get("onclick", "")
            match = re.search(
                r"\('([^']+\.(pdf|jpg|jpeg|png))'\)",
                onclick,
                re.IGNORECASE
            )
            if match:
                url = match.group(1).strip()
                ext = match.group(2).lower()
                return url, "PDF" if ext == "pdf" else "IMAGE"
        except Exception as e:
            print(f"[ERROR] Form-G link extraction failed: {e}")
        return "", "UNKNOWN"

    # -------------------------------
    # Scrape single page
    # -------------------------------
    def scrape_page(self, page):
        try:
            url = f"{self.BASE_URL}/resolution-plans?page={page}"
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if not table:
                return []

            rows = table.find_all("tr")[1:]
            if not rows:
                return []

            records = []
            for row in rows:
                try:
                    tds = row.find_all("td")
                    if len(tds) < 6:
                        print(f"[WARN] Skipping row on page {page}, not enough columns")
                        continue

                    formg_url, file_type = self.extract_formg_link(tds[5])
                    remarks = tds[6].get_text(strip=True) if len(tds) > 6 else ""

                    records.append({
                        "Corporate Debtor": tds[0].get_text(strip=True),
                        "Resolution Professional": tds[1].get_text(strip=True),
                        "Last Date of EOI": tds[2].get_text(strip=True),
                        "Date of Issue to PRA": tds[3].get_text(strip=True),
                        "Last Date of Objections": tds[4].get_text(strip=True),
                        "Form G URL": formg_url,
                        "Form G File Type": file_type,
                        "Remarks": remarks
                    })

                except Exception as row_error:
                    print(f"[ERROR] Failed parsing row on page {page}: {row_error}")

            return records

        except requests.exceptions.RequestException as req_err:
            print(f"[ERROR] Network issue on page {page}: {req_err}")
            return []
        except Exception as e:
            print(f"[ERROR] Unexpected error on page {page}: {e}")
            return []

    # -------------------------------
    # Scrape all pages
    # -------------------------------
    def scrape_all_pages(self, max_pages=400):
        all_data = []
        for page in range(1, max_pages + 1):
            print(f"Scraping page {page}...")
            try:
                data = self.scrape_page(page)

                # Retry once if empty
                if not data:
                    print(f"[WARN] Page {page} empty. Retrying once...")
                    data = self.scrape_page(page)
                    if not data:
                        print(f"No more data found. Stopping at page {page}.")
                        break

                all_data.extend(data)

                if self.progress_callback:
                    self.progress_callback(page, max_pages)

                time.sleep(1)

            except Exception as e:
                print(f"[ERROR] Exception on page {page}: {e}")

        return all_data

    # -------------------------------
    # Save to Excel
    # -------------------------------
    def save_to_excel(self, data, file_path):
        try:
            if not data:
                print("[ERROR] No data available to save.")
                return None
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False)
            return file_path
        except Exception as e:
            print(f"[ERROR] Failed to save Excel file: {e}")
            return None
