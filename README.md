# 和金顺数据平台

电商数据采集、生成与可视化一体化平台。

## 项目大纲

本项目分为 **4 个核心模块**，模块之间相对独立，通过 `main.py` 统一调度：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   crawler   │ ──► │   storage   │ ──► │     web     │
│   爬虫模块   │     │   存储模块   │     │   前端模块   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
  京东/什么值得买      Excel读写/清洗       数据大屏/代码生成器
      │                                       │
      └──────────► data-factory ◄─────────────┘
                   数据制造工厂
```

### 模块说明

| 模块 | 目录 | 功能 | 子模块 |
|------|------|------|--------|
| 爬虫 | `crawler/` | 多平台数据采集 | jd_crawler, smzdm_crawler |
| 存储 | `storage/` | Excel数据管理 | excel_handler, data_cleaner |
| 前端 | `web/` | Web界面展示 | dashboard, generator |
| **数据工厂** | `data-factory/` | 结论驱动数据生成 | conclusion_engine, generators |

## 功能特性

### 数据采集
- 京东商品数据爬取
- 什么值得买数据爬取
- 自动登录与反爬处理
- 数据清洗与去重

### 数据制造工厂
- **结构化输入**: 品类、价格区间、年龄、性别比例
- **自然语言输入**: "手机品类价格呈上涨趋势"
- **用户画像生成**: 年龄分布、性别比例、地区分布
- **一键导出**: 自动合并到主数据文件

### 数据可视化
- 平台商品占比
- 价格分布与趋势
- 用户画像统计（年龄、性别、地区）
- 实时数据更新

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
# 启动数据大屏 (port 5001)
python main.py

# 启动数据工厂 (port 5007)
python main.py --factory

# 启动代码生成器 (port 5003)
python main.py --generator

# 指定端口
python main.py -p 8080

# 不自动打开浏览器
python main.py --no-browser
```

## 目录结构

```
和金顺新计划/
├── main.py                    # 主入口文件
├── config.py                  # 全局配置（数据字段定义）
├── README.md                  # 项目说明
├── MEMORY.md                  # 项目记忆
├── FRAMEWORK.md               # 项目框架文档
│
├── crawler/                   # 爬虫模块
│   ├── __init__.py
│   ├── jd_crawler.py         # 京东爬虫
│   └── smzdm_crawler.py      # 什么值得买爬虫
│
├── storage/                   # 存储模块
│   ├── __init__.py
│   ├── excel_handler.py      # Excel读写
│   └── data_cleaner.py       # 数据清洗
│
├── web/                       # 前端模块
│   ├── __init__.py
│   ├── dashboard.py          # 数据大屏 (port 5001)
│   └── generator.py          # ECharts代码生成器 (port 5003)
│
├── data-factory/              # 数据制造工厂
│   ├── web_app.py            # Web应用
│   ├── conclusion_engine.py  # 结论驱动引擎
│   ├── generators/           # 数据生成器
│   ├── output/               # 输出模块
│   └── templates/            # HTML模板
│
├── data/                      # 数据目录
│   ├── raw/                  # 原始数据备份
│   └── cleaned/              # 清洗后数据
│       └── products.xlsx     # 主数据文件
│
├── templates/                 # 数据大屏模板
│   └── index.html
│
└── requirements.txt           # 依赖列表
```

## 数据字段

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 商品名称 |
| price | float | 价格 |
| original_price | float | 原价 |
| platform | string | 平台 |
| rating | float | 评分 |
| comment_count | int | 评论数 |
| category | string | 品类 |
| **user_age** | int | 用户年龄 |
| **user_gender** | string | 用户性别 |
| **user_region** | string | 用户地区 |
| image_url | string | 图片链接 |
| product_url | string | 商品链接 |
| scraped_at | string | 采集时间 |

## API 接口

### 数据大屏 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 数据大屏页面 |
| GET | `/api/products` | 获取商品列表 |
| GET | `/api/stats` | 获取统计数据 |
| POST | `/api/scrape` | 启动数据采集 |
| DELETE | `/api/clear` | 清空数据 |

### 数据工厂 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 数据工厂页面 |
| POST | `/api/generate-structured` | 结构化生成数据 |
| POST | `/api/generate-from-conclusion` | 结论驱动生成 |
| POST | `/api/export` | 导出到主数据 |
| GET | `/api/download` | 下载生成文件 |

## 使用指南

### 数据采集流程

1. 启动数据大屏: `python main.py`
2. 切换到"数据接入"标签
3. 输入数据源URL（可选）和采集数量
4. 点击"开始采集"
5. 等待采集完成后查看数据

### 数据生成流程

1. 启动数据工厂: `python main.py --factory`
2. 选择"结构化输入"或"自然语言"模式
3. 配置参数（品类、价格、年龄、性别等）
4. 点击"生成数据"
5. 点击"导出到和金顺平台"
6. 刷新数据大屏查看新数据

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.x + Flask |
| 前端 | HTML + CSS + JavaScript |
| 图表 | ECharts 5.x |
| 爬虫 | DrissionPage |
| 存储 | Excel (openpyxl) |
| 数据生成 | NumPy |

## 开发规范

1. **模块边界**: 各模块职责明确，不跨模块直接操作
2. **数据流**: crawler → storage → web，单向流动
3. **配置统一**: 所有字段定义在 `config.py`
4. **命名规范**: 文件名英文，函数名snake_case
5. **模块独立**: 每个子模块可独立运行测试

## 相关文档

- [FRAMEWORK.md](FRAMEWORK.md) - 详细项目框架
- [MEMORY.md](MEMORY.md) - 项目记忆与决策记录
- [CLAUDE.md](CLAUDE.md) - 开发规则与指南

---

*最后更新: 2026-05-25*
