"""
Shared configuration and data contract.
All modules import from this file to stay synchronized.
"""
import os

# -- Paths --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
CLEANED_DIR = os.path.join(DATA_DIR, "cleaned")
CHROME_PROFILE_DIR = os.path.join(DATA_DIR, "chrome_profile")

# -- Scraping defaults --
DEFAULT_SCRAPE_COUNT = 50
INIT_WAIT_SECONDS = 1.0
SCROLL_WAIT_SECONDS = 0.5
PAGE_WAIT_SECONDS = 1.0
LOGIN_TIMEOUT_SECONDS = 120

# -- Data contract: field definitions --
# (dict_key, excel_header, python_type, default_value)
PRODUCT_FIELDS = [
    ("name",           "Product Name",    str,                   ""),
    ("price",          "Price",           float,                 0.0),
    ("original_price", "Original Price",  (float, type(None)),   None),
    ("platform",       "Platform",        str,                   ""),
    ("rating",         "Rating",          (float, type(None)),   None),
    ("comment_count",  "Comment Count",   int,                   0),
    ("category",       "Category",        str,                   ""),
    # 用户画像字段
    ("user_age",       "User Age",        (int, type(None)),     None),
    ("user_gender",    "User Gender",     str,                   ""),
    ("user_region",    "User Region",     str,                   ""),
    # 链接字段
    ("image_url",      "Image URL",       str,                   ""),
    ("product_url",    "Product URL",     str,                   ""),
    ("scraped_at",     "Scraped At",      str,                   ""),
]


def get_excel_headers():
    return [f[1] for f in PRODUCT_FIELDS]


def get_field_keys():
    return [f[0] for f in PRODUCT_FIELDS]


def get_defaults():
    return {f[0]: f[3] for f in PRODUCT_FIELDS}
