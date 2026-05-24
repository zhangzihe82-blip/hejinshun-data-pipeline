# 和金顺数据平台

电商数据采集与可视化平台，支持多平台爬取、Excel存储、Web展示。

## 项目大纲

本项目分为 **3 个核心模块**，模块之间相对独立，通过 `main.py` 统一调度：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   crawler   │ ──► │   storage   │ ──► │     web     │
│   爬虫模块   │     │   存储模块   │     │   前端模块   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
  京东/什么值得买      Excel读写/清洗       仪表盘/代码生成器
```

### 模块说明

| 模块 | 目录 | 功能 | 子模块 |
|------|------|------|--------|
| 爬虫 | `crawler/` | 多平台数据采集 | jd_crawler, smzdm_crawler |
| 存储 | `storage/` | Excel数据管理 | excel_handler, data_cleaner |
| 前端 | `web/` | Web界面展示 | dashboard, generator |

### 数据流向

1. **爬虫模块** 采集数据，返回 `list[dict]`
2. **存储模块** 清洗数据，写入 Excel
3. **前端模块** 读取 Excel，展示可视化界面

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动仪表盘
python main.py

# 启动代码生成器
python main.py --generator
```

## 目录结构

```
和金顺新计划/
├── main.py              # 主入口
├── config.py            # 全局配置
├── README.md            # 项目大纲（本文件）
│
├── crawler/             # 爬虫模块
│   ├── __init__.py
│   ├── jd_crawler.py    # 京东爬虫
│   └── smzdm_crawler.py # 什么值得买爬虫
│
├── storage/             # 存储模块
│   ├── __init__.py
│   ├── excel_handler.py # Excel读写
│   └── data_cleaner.py  # 数据清洗
│
├── web/                 # 前端模块
│   ├── __init__.py
│   ├── dashboard.py     # 仪表盘应用
│   └── generator.py     # 代码生成器
│
├── templates/           # HTML模板
├── data/                # 数据目录
│   ├── raw/             # 原始数据
│   └── cleaned/         # 清洗后数据
└── requirements.txt     # 依赖列表
```

## 开发指南

- 每个模块独立维护，互不直接调用内部函数
- `config.py` 是数据字段的唯一定义来源
- 新增爬虫平台：在 `crawler/` 下添加新文件
- 新增前端功能：在 `web/` 下添加新文件
