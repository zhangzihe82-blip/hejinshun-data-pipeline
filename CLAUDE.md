# Hejinshun Data Pipeline -- Project Rules

## Architecture
- scraper.py -> storage.py -> main.py (dashboard)
- scraper.py -> storage.py -> generator_app.py (code generator)
- Data flows one direction: scrape -> clean -> Excel -> display
- config.py is the single source of truth for field definitions

## Data Storage
- **No database.** Excel files only (openpyxl).
- storage.py is the ONLY module that reads/writes Excel files.
- data/raw/ = timestamped raw backups per scrape run
- data/cleaned/products.xlsx = canonical data file (dashboard reads this)

## Module Boundaries
- scraper.py: NEVER writes files, only returns list[dict]
- storage.py: ONLY module touching Excel
- main.py: imports storage + scraper, serves dashboard
- generator_app.py: standalone Flask app, reads Excel for code generation

## Naming
- All file names and paths in English
- Product data fields defined once in config.py PRODUCT_FIELDS
