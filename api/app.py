from flask import Flask, send_file, jsonify, send_from_directory
from scraper.functions import IBBIScraper
from datetime import datetime
import os

app = Flask(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../output')
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

os.makedirs(OUTPUT_DIR, exist_ok=True)


# Serve frontend
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

# Serve favicon
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        FRONTEND_DIR,
        "favicon.png",
        mimetype="image/png"
    )


# Scraper endpoint
@app.route("/start-scraping", methods=["GET"])
def start_scraping():
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"ibbi_resolution_plans_{timestamp}.xlsx"
        file_path = os.path.join(OUTPUT_DIR, file_name)

        scraper = IBBIScraper()
        data = scraper.scrape_all_pages()

        if not data:
            return jsonify({"error": "No data scraped"}), 500

        saved_file = scraper.save_to_excel(data, file_path)
        if not saved_file:
            return jsonify({"error": "Failed to save Excel file"}), 500

        return send_file(
            saved_file,
            as_attachment=True,
            download_name=file_name
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
