"""
数据清洗子模块
负责数据验证、清洗、合并
"""
import logging
from datetime import datetime, timezone

from config import PRODUCT_FIELDS, get_field_keys, get_defaults

logger = logging.getLogger(__name__)


def clean_record(record):
    """清洗单条记录"""
    cleaned = get_defaults()
    for key in get_field_keys():
        if key in record and record[key] is not None:
            cleaned[key] = record[key]
    for key, _, py_type, _ in PRODUCT_FIELDS:
        if py_type is str and cleaned[key] is not None:
            cleaned[key] = str(cleaned[key]).strip()
    try:
        cleaned["price"] = float(cleaned["price"]) if cleaned["price"] not in (None, "") else 0.0
    except (ValueError, TypeError):
        cleaned["price"] = 0.0
    try:
        cleaned["comment_count"] = int(float(str(cleaned["comment_count"]).replace(",", "")))
    except (ValueError, TypeError):
        cleaned["comment_count"] = 0
    try:
        cleaned["original_price"] = float(cleaned["original_price"]) if cleaned["original_price"] not in (None, "") else None
    except (ValueError, TypeError):
        cleaned["original_price"] = None
    try:
        cleaned["rating"] = float(cleaned["rating"]) if cleaned["rating"] not in (None, "") else None
    except (ValueError, TypeError):
        cleaned["rating"] = None
    cleaned["scraped_at"] = datetime.now(timezone.utc).isoformat()
    if not cleaned.get("name"):
        return None
    return cleaned


def clean_records(records):
    """清洗多条记录"""
    return [c for r in records if (c := clean_record(r)) is not None]


def merge_data(existing, new_records, dedup_key="product_url"):
    """合并数据，按指定字段去重"""
    lookup = {}
    for rec in existing:
        key_val = rec.get(dedup_key, "")
        if key_val:
            lookup[key_val] = rec
    for rec in new_records:
        key_val = rec.get(dedup_key, "")
        if key_val and key_val in lookup:
            lookup[key_val] = rec
        else:
            lookup[key_val or id(rec)] = rec
    return list(lookup.values())


def get_stats(records):
    """获取数据统计"""
    if not records:
        return {"total": 0, "price_range": {"min": None, "max": None, "avg": None},
                "platform_stats": [], "rating_dist": []}
    prices = [r["price"] for r in records if r.get("price") and r["price"] > 0]
    platforms = {}
    for r in records:
        p = r.get("platform") or "未知"
        platforms.setdefault(p, {"sum": 0, "cnt": 0})
        if r.get("price") and r["price"] > 0:
            platforms[p]["sum"] += r["price"]
            platforms[p]["cnt"] += 1
        else:
            platforms[p]["cnt"] += 1
    platform_stats = [
        {"platform": k, "count": v["cnt"], "avg_price": round(v["sum"] / v["cnt"], 2) if v["cnt"] else 0}
        for k, v in platforms.items()
    ]
    platform_stats.sort(key=lambda x: x["count"], reverse=True)
    return {
        "total": len(records),
        "price_range": {
            "min": round(min(prices), 2) if prices else None,
            "max": round(max(prices), 2) if prices else None,
            "avg": round(sum(prices) / len(prices), 2) if prices else None,
        },
        "platform_stats": platform_stats,
        "rating_dist": [],
    }
