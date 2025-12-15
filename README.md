# IBBI Resolution Plan Scraper

A Python-based web scraper to extract Resolution Plan data from the IBBI website.

## Features
- Scrapes all paginated resolution plan data
- Extracts Form-G PDF URLs
- Exposes a Flask API to trigger scraping
- Frontend with a Start button
- Exports data to Excel with timestamped filenames

## Tech Stack
- Python
- Flask
- BeautifulSoup
- Pandas

## Setup Instructions

```bash
git clone <repo-url>
cd web_scraper
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
