# Hejinshun Data Platform - Project Memory

## Project Overview

和金顺数据平台 - 电商数据采集、生成与可视化一体化平台

## Current Status (2026-05-25)

### Completed Features
- [x] 核心框架搭建（crawler、storage、web 三大模块）
- [x] 京东/什么值得买爬虫实现（DrissionPage）
- [x] Excel数据存储与清洗
- [x] 数据大屏可视化（ECharts）
- [x] ECharts代码生成器
- [x] **数据制造工厂** - 结论驱动数据生成
- [x] 用户画像字段（年龄、性别、地区）
- [x] 数据工厂与主程序联动

### Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   crawler   │ ──► │   storage   │ ──► │     web     │
│   爬虫模块   │     │   存储模块   │     │   前端模块   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                       │
      └──────────► data-factory ◄─────────────┘
                   数据制造工厂
```

## Key Decisions

| Decision | Description | Date |
|----------|-------------|------|
| D1 | Excel replaces SQLite - simpler, portable, inspectable | D1 |
| D2 | Scrape data auto-saves via storage module | D1 |
| D3 | Data Factory as independent sub-project with export to main data | D4 |
| D4 | User demographics fields added (age, gender, region) | D4 |
| D5 | Conclusion-driven data generation engine | D4 |

## Modules

### 1. crawler/ - 爬虫模块
- `jd_crawler.py`: 京东商品采集
- `smzdm_crawler.py`: 什么值得买采集
- Returns: `list[dict]` 格式数据

### 2. storage/ - 存储模块
- `excel_handler.py`: Excel 读写
- `data_cleaner.py`: 数据清洗与合并
- Main data file: `data/cleaned/products.xlsx`

### 3. web/ - 前端模块
- `dashboard.py`: 数据大屏 (port 5001)
- `generator.py`: ECharts代码生成器 (port 5003)

### 4. data-factory/ - 数据制造工厂
- `web_app.py`: Web应用 (port 5007)
- `conclusion_engine.py`: 结论驱动引擎
- `generators/`: 数据生成器
- `output/`: 输出模块 (Excel/JSON/CSV)

## Data Fields

```python
PRODUCT_FIELDS = [
    # 商品信息
    ("name", "price", "original_price", "platform", "rating", "comment_count", "category"),
    # 用户画像
    ("user_age", "user_gender", "user_region"),
    # 链接
    ("image_url", "product_url", "scraped_at")
]
```

## Services

| Service | Port | Command |
|---------|------|---------|
| 数据大屏 | 5001 | `python main.py` |
| 数据工厂 | 5007 | `python main.py --factory` |
| 代码生成器 | 5003 | `python main.py --generator` |

## Recent Work

### 2026-05-25 (D4)
- 添加数据制造工厂模块
- 实现结论驱动数据生成引擎
- 添加用户画像字段支持
- 更新数据大屏显示用户统计
- 完善数据工厂导出功能

---

*Last updated: 2026-05-25*
