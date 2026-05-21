# Hejinshun Data Pipeline -- Project State

## Current Status
- [x] Project framework created
- [x] storage.py fully implemented (Excel read/write/clean/merge)
- [x] main.py rewritten to use Excel instead of SQLite
- [x] scraper.py copied from old project (working JD + SMZDM)
- [x] generator_app.py copied from old project
- [x] templates copied (index.html + generator.html)
- [ ] End-to-end test with real scraping

## Key Decisions
- D1: Excel replaces SQLite -- simpler, portable, inspectable
- D2: Scrape data auto-saves to Excel via storage.py in main.py _task()
- D3: read_cleaned() adds 'created_at' alias for 'scraped_at' (dashboard compatibility)
