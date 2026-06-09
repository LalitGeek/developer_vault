# Google Maps Bulk Scraper (GUI)

A powerful, user-friendly GUI-based tool to scrape business information from Google Maps. This tool extracts names, addresses, phone numbers, and websites, and allows you to export the data directly to a CSV file.

## Features

- **Search Query:** Search for any business type or location (e.g., "Hospitals in Mumbai", "Cafes in London").
- **Max Results:** Set a limit on the number of results to fetch.
- **Headless Mode:** Run the scraper in the background without opening a browser window.
- **Real-time Updates:** View results in a table as they are being scraped.
- **CSV Export:** Save your collected data easily for further analysis.
- **Automatic Driver Management:** Uses `webdriver-manager` to automatically handle Chrome driver installation and updates.

## Prerequisites

- **Python 3.x** installed on your system.
- **Google Chrome** browser installed.

## Installation

1. **Clone the repository** (or download the script):
   ```bash
   git clone https://github.com/your-username/gmaps-scraper.git
   cd gmaps-scraper
   ```

2. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: On Linux, you might also need to install the tkinter package if not already present:*
   ```bash
   sudo apt-get install python3-tk
   ```

## Usage

1. **Run the script**:
   ```bash
   python gmaps_scraper_gui.py
   ```

2. **Configure your search**:
   - Enter your **Search Query** in the input field.
   - Specify the **Max Results** you want to collect.
   - (Optional) Toggle **Headless Mode** if you don't want to see the browser window.

3. **Start Scraping**:
   - Click the **Start Scraping** button.
   - The status bar will show the current progress, and the table will populate with results.

4. **Export Data**:
   - Once the scraping is complete (or stopped), click **Export to CSV** to save the results.

## Troubleshooting

- **No Search Box Found:** If the script fails to find the search box, it will save an `error_screenshot.png`. Check this image to see what Google Maps was displaying (e.g., a captcha or a new layout).
- **Log Files:** Check `scraper_error.log` if the application encounters a fatal error.
- **Chrome Version:** Ensure your Google Chrome is up to date.

## Disclaimer

This tool is for educational purposes only. Scraping Google Maps may violate their Terms of Service. Use responsibly and at your own risk.

## Author

**LalitGeek**
