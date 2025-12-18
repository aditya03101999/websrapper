import requests
import pandas as pd
import re
import time
import logging
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ----------------------------------
# Logger Configuration
# ----------------------------------
LOG_FILE = "scraper.log"

logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


class IBBIScraper:
    BASE_URL = "https://ibbi.gov.in"

    def __init__(self):
        self.progress_callback = None
        logger.info("IBBI Scraper initialized")

        # Setup session with retries
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        logger.info("HTTP session with retry configured")

    # ----------------------------------
    # Progress callback
    # ----------------------------------
    def set_progress_callback(self, callback):
        self.progress_callback = callback
        logger.info("Progress callback registered")

    # ----------------------------------
    # Extract Form G URL + File Type
    # ----------------------------------
    def extract_formg_link(self, td):
        try:
            a_tag = td.find("a")
            if not a_tag:
                logger.warning("Form G link not found")
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
                file_type = "PDF" if ext == "pdf" else "IMAGE"
                return url, file_type

        except Exception as e:
            logger.error(f"Form G extraction failed: {e}")

        return "", "UNKNOWN"

    # ----------------------------------
    # Scrape single page
    # ----------------------------------
    def scrape_page(self, page):
        logger.info(f"Scraping page {page}")

        try:
            url = f"{self.BASE_URL}/resolution-plans?page={page}"
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")

            if not table:
                logger.warning(f"No table found on page {page}")
                return []

            rows = table.find_all("tr")[1:]
            if not rows:
                logger.warning(f"No rows found on page {page}")
                return []

            records = []

            for index, row in enumerate(rows, start=1):
                try:
                    tds = row.find_all("td")
                    if len(tds) < 6:
                        logger.warning(
                            f"Skipping row {index} on page {page} due to insufficient columns"
                        )
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
                    logger.error(
                        f"Row parsing failed on page {page}, row {index}: {row_error}"
                    )

            logger.info(f"Page {page} scraped successfully with {len(records)} records")
            return records

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Network error on page {page}: {req_err}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error on page {page}: {e}")
            return []

    # ----------------------------------
    # Scrape all pages
    # ----------------------------------
    def scrape_all_pages(self, max_pages=400):
        logger.info("Scraping started")
        all_data = []

        for page in range(1, max_pages + 1):
            logger.info(f"Processing page {page}")

            data = self.scrape_page(page)

            # Retry once if page is empty
            if not data:
                logger.warning(f"Empty data on page {page}, retrying once")
                data = self.scrape_page(page)

                if not data:
                    logger.info(f"Stopping scraper at page {page}")
                    break

            all_data.extend(data)

            if self.progress_callback:
                self.progress_callback(page, max_pages)

            time.sleep(1)

        logger.info(f"Scraping completed. Total records: {len(all_data)}")
        return all_data

    # ----------------------------------
    # Save to Excel
    # ----------------------------------
    def save_to_excel(self, data, file_path):
        try:
            if not data:
                logger.error("No data available to save")
                return None

            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False)
            logger.info(f"Excel file saved successfully: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save Excel file: {e}")
            return None
