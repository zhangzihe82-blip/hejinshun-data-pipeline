# Hejinshun Data Pipeline -- Project Rules

## 项目架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   crawler   │ ──► │   storage   │ ──► │     web     │
│   爬虫模块   │     │   存储模块   │     │   前端模块   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**三大模块相对独立，在 main.py 中统一调用**

## 模块边界

### crawler/ (爬虫模块)
- **职责**: 多平台电商数据采集，返回 `list[dict]`
- **规则**: NEVER 写文件，只返回数据
- **子模块**:
  - `jd_crawler.py`: 京东爬虫
  - `smzdm_crawler.py`: 什么值得买爬虫

### storage/ (存储模块)
- **职责**: Excel 数据读写与清洗
- **规则**: 唯一操作 Excel 的模块
- **子模块**:
  - `excel_handler.py`: Excel 文件读写
  - `data_cleaner.py`: 数据清洗与合并

### web/ (前端模块)
- **职责**: Web 界面展示
- **规则**: 不直接爬取数据，通过 storage 读取
- **子模块**:
  - `dashboard.py`: 数据仪表盘 (port 5001)
  - `generator.py`: ECharts 代码生成器 (port 5002)

## 数据流向

```
crawler.scrape() → storage.clean_records() → storage.save_cleaned()
                                                       ↓
web.dashboard ← storage.read_cleaned() ←──────────────┘
```

## 数据存储

- **No database.** Excel files only (openpyxl).
- `data/raw/` = 原始数据备份（每次爬取一个文件）
- `data/cleaned/products.xlsx` = 主数据文件

## 配置约定

- `config.py` 是数据字段的唯一定义来源
- `PRODUCT_FIELDS` 定义所有字段 (key, header, type, default)
- 新增字段只需修改 `config.py`

## 开发指南

1. **新增爬虫平台**: 在 `crawler/` 下添加新文件，导出 `scrape_xxx()` 函数
2. **新增前端功能**: 在 `web/` 下添加新文件
3. **修改数据字段**: 只改 `config.py` 中的 `PRODUCT_FIELDS`
4. **调试单个模块**: 直接运行该模块文件（每个子模块可独立测试）

## 命名约定

- 所有文件名、路径使用英文
- 模块导入使用绝对导入
