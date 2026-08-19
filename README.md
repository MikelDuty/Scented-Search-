# ScentCompare Israel 🇮🇱

A mobile-friendly perfume price comparison MVP. It runs as a web app, so you can use it from an iPhone Safari browser.

## Fastest way from iPhone: Streamlit Community Cloud
1. Create a GitHub repository named `scentcompare`.
2. Upload `app.py` and `requirements.txt`.
3. Go to Streamlit Community Cloud and deploy `app.py`.
4. Open the generated HTTPS URL on your iPhone and optionally add it to the Home Screen.

## Local / Replit / Docker
```bash
pip install -r requirements.txt
streamlit run app.py
```

Docker:
```bash
docker build -t scentcompare .
docker run -p 8501:8501 scentcompare
```

## Current live adapters
- Ivory
- CallPerfume

The app also seeds Rasasi Hawas Ice 100ml with verified example offers so the UI works immediately. Live discovery uses search-engine result pages and then parses store pages; this is intentionally an MVP. For production, replace discovery with dedicated store adapters/APIs and add a scheduled cloud database, barcode/SKU matching, shipping rules, monitoring, and anti-bot-compliant crawling.
