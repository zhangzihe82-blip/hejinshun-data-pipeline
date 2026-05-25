# 和金顺数据平台 - 项目框架

## 项目架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              和金顺数据平台                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │   crawler   │────►│   storage   │────►│     web     │                  │
│   │   爬虫模块   │     │   存储模块   │     │   前端模块   │                  │
│   └─────────────┘     └─────────────┘     └─────────────┘                  │
│         │                   │                   │                          │
│         │                   ▼                   │                          │
│         │         ┌─────────────────┐           │                          │
│         └────────►│  data-factory   │◄──────────┘                          │
│                   │   数据制造工厂   │                                      │
│                   └─────────────────┘                                      │
│                           │                                                │
│                           ▼                                                │
│                   ┌─────────────────┐                                      │
│                   │  data/cleaned/  │                                      │
│                   │  products.xlsx  │                                      │
│                   └─────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 一、目录结构

```
和金顺新计划/
├── main.py                    # 主入口文件
├── config.py                  # 全局配置（数据字段定义）
├── CLAUDE.md                  # 项目规则文档
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
├── data-factory/              # 数据制造工厂（独立子项目）
│   ├── web_app.py            # Web应用入口
│   ├── conclusion_engine.py  # 结论驱动引擎
│   ├── main.py               # 独立运行入口
│   ├── config.py             # 工厂配置
│   │
│   ├── generators/           # 数据生成器
│   │   ├── __init__.py
│   │   └── base.py           # 基础生成器
│   │
│   ├── output/               # 输出模块
│   │   ├── __init__.py
│   │   ├── excel.py          # Excel输出
│   │   ├── json_out.py       # JSON输出
│   │   └── csv_out.py        # CSV输出
│   │
│   ├── rules/                # 规则模块
│   │   └── constraints.py    # 约束规则
│   │
│   ├── validators/           # 验证模块
│   │   └── statistical.py    # 统计验证
│   │
│   ├── templates/            # HTML模板
│   │   └── factory.html      # 数据工厂界面
│   │
│   └── output/               # 生成的数据文件
│
├── data/                      # 数据目录
│   ├── raw/                  # 原始数据备份
│   ├── cleaned/              # 清洗后数据
│   │   └── products.xlsx     # 主数据文件
│   └── chrome_profile/       # Chrome配置
│
├── templates/                 # 数据大屏模板
│   └── index.html            # 大屏界面
│
└── dist/                      # 打包输出目录
```

---

## 二、模块详解

### 1. 主入口 (main.py)

```
命令行参数:
  无参数          启动数据大屏 (port 5001)
  --factory       启动数据制造工厂 (port 5002)
  --generator     启动代码生成器 (port 5003)
  -p <port>       指定端口
  --no-browser    不自动打开浏览器
```

### 2. 爬虫模块 (crawler/)

```
职责: 多平台电商数据采集
输出: list[dict] 格式数据
规则: 不写文件，只返回数据

┌─────────────────────────────────────────────┐
│                 crawler 模块                 │
├─────────────────────────────────────────────┤
│  jd_crawler.py                              │
│  ├── scrape_jd() → list[dict]              │
│  └── 使用 DrissionPage 自动化采集            │
│                                             │
│  smzdm_crawler.py                           │
│  ├── scrape_smzdm() → list[dict]           │
│  └── 什么值得买数据采集                       │
└─────────────────────────────────────────────┘
```

### 3. 存储模块 (storage/)

```
职责: Excel数据读写与清洗
规则: 唯一操作Excel的模块

┌─────────────────────────────────────────────┐
│                 storage 模块                 │
├─────────────────────────────────────────────┤
│  excel_handler.py                           │
│  ├── save_raw(records)      → 保存原始数据   │
│  ├── save_cleaned(records)  → 保存清洗数据   │
│  ├── read_cleaned()         → 读取数据      │
│  └── clear_products()       → 清空数据      │
│                                             │
│  data_cleaner.py                            │
│  ├── clean_records(records) → 清洗数据      │
│  └── merge_data(existing, new) → 合并数据   │
└─────────────────────────────────────────────┘
```

### 4. 前端模块 (web/)

```
职责: Web界面展示
规则: 不直接爬取数据，通过storage读取

┌─────────────────────────────────────────────┐
│                   web 模块                   │
├─────────────────────────────────────────────┤
│  dashboard.py (port 5001)                   │
│  ├── GET /              → 数据大屏页面       │
│  ├── GET /api/products  → 商品列表API       │
│  ├── GET /api/stats     → 统计数据API       │
│  ├── POST /api/scrape   → 启动采集          │
│  └── DELETE /api/clear  → 清空数据          │
│                                             │
│  generator.py (port 5003)                   │
│  └── ECharts代码生成器                       │
└─────────────────────────────────────────────┘
```

### 5. 数据制造工厂 (data-factory/)

```
职责: 结论驱动数据生成
特点: 独立子项目，可与主程序联动

┌─────────────────────────────────────────────┐
│              data-factory 模块               │
├─────────────────────────────────────────────┤
│  web_app.py (port 5002/5007)                │
│  ├── GET /              → 数据工厂页面       │
│  ├── GET /api/defaults  → 获取默认配置       │
│  ├── POST /api/generate-structured          │
│  │   → 结构化参数生成                        │
│  ├── POST /api/generate-from-conclusion     │
│  │   → 自然语言生成                          │
│  ├── POST /api/export   → 导出到主程序       │
│  └── GET /api/download  → 下载文件          │
│                                             │
│  conclusion_engine.py                       │
│  ├── ConclusionParser     → 解析结论语句     │
│  ├── DataRuleGenerator    → 生成数据规则     │
│  └── ConclusionDrivenGenerator              │
│       → 结论驱动生成器                       │
│                                             │
│  generators/base.py                         │
│  └── DataGenerator → 数据生成器             │
│                                             │
│  output/                                    │
│  ├── ExcelWriter → Excel输出                │
│  ├── JSONWriter  → JSON输出                 │
│  └── CSVWriter   → CSV输出                  │
└─────────────────────────────────────────────┘
```

---

## 三、数据流向

```
                    数据流向图
                    
┌──────────┐      ┌──────────┐      ┌──────────┐
│  用户输入  │─────►│  爬虫采集  │─────►│  数据清洗  │
│  URL/数量 │      │  crawler  │      │  storage │
└──────────┘      └──────────┘      └──────────┘
                                            │
                                            ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│  数据大屏  │◄────│  主数据   │◄────│  数据存储  │
│  dashboard│      │products  │      │  Excel   │
└──────────┘      └──────────┘      └──────────┘
      ▲                                    ▲
      │                                    │
┌──────────┐      ┌──────────┐      ┌──────────┐
│  统计图表  │◄────│  数据生成  │◄────│  结论输入  │
│  用户画像  │      │  factory │      │  参数配置  │
└──────────┘      └──────────┘      └──────────┘
```

---

## 四、数据字段定义 (config.py)

```python
PRODUCT_FIELDS = [
    # 商品基础信息
    ("name",           "Product Name",    str,   ""),        # 商品名称
    ("price",          "Price",           float, 0.0),       # 价格
    ("original_price", "Original Price",  float, None),      # 原价
    ("platform",       "Platform",        str,   ""),        # 平台
    ("rating",         "Rating",          float, None),      # 评分
    ("comment_count",  "Comment Count",   int,   0),         # 评论数
    ("category",       "Category",        str,   ""),        # 品类
    
    # 用户画像字段（新增）
    ("user_age",       "User Age",        int,   None),      # 用户年龄
    ("user_gender",    "User Gender",     str,   ""),        # 用户性别
    ("user_region",    "User Region",     str,   ""),        # 用户地区
    
    # 链接信息
    ("image_url",      "Image URL",       str,   ""),        # 图片链接
    ("product_url",    "Product URL",     str,   ""),        # 商品链接
    ("scraped_at",     "Scraped At",      str,   ""),        # 采集时间
]
```

---

## 五、API 接口

### 数据大屏 API (port 5001)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 数据大屏页面 |
| GET | `/api/products` | 获取商品列表 |
| GET | `/api/stats` | 获取统计数据 |
| POST | `/api/scrape` | 启动数据采集 |
| POST | `/api/stop` | 停止采集 |
| DELETE | `/api/clear` | 清空数据 |

### 数据工厂 API (port 5007)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 数据工厂页面 |
| GET | `/api/defaults` | 获取默认配置 |
| POST | `/api/generate-structured` | 结构化生成数据 |
| POST | `/api/generate-from-conclusion` | 结论驱动生成 |
| POST | `/api/export` | 导出到主数据 |
| GET | `/api/download` | 下载生成文件 |
| GET | `/api/status` | 获取生成状态 |

---

## 六、使用指南

### 启动服务

```bash
# 启动数据大屏
python main.py

# 启动数据工厂
python main.py --factory

# 启动代码生成器
python main.py --generator

# 指定端口
python main.py -p 8080
```

### 数据采集流程

```
1. 打开数据大屏 (http://127.0.0.1:5001)
2. 切换到"数据接入"标签
3. 输入数据源URL（可选）和采集数量
4. 点击"开始采集"
5. 等待采集完成
6. 切换到"数据看板"查看结果
```

### 数据生成流程

```
1. 打开数据工厂 (http://127.0.0.1:5007)
2. 选择"结构化输入"或"自然语言"模式
3. 配置参数:
   - 品类、价格区间
   - 年龄范围、性别比例
   - 价格趋势、评分水平
4. 点击"生成数据"
5. 点击"导出到和金顺平台"
6. 刷新数据大屏查看新数据
```

---

## 七、技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.x + Flask |
| 前端 | HTML + CSS + JavaScript + ECharts |
| 爬虫 | DrissionPage |
| 存储 | Excel (openpyxl) |
| 数据生成 | NumPy (统计分布) |

---

## 八、模块依赖关系

```
                    ┌──────────┐
                    │  config  │
                    │  全局配置  │
                    └────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  crawler │   │  storage │   │   web    │
    │  爬虫模块  │   │  存储模块  │   │  前端模块 │
    └────┬─────┘   └────┬─────┘   └────┬─────┘
         │              │              │
         │              │              │
         └──────────────┴──────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ data-factory │
                 │  数据制造工厂  │
                 └──────────────┘
```

---

## 九、开发规范

1. **模块边界**: 各模块职责明确，不跨模块直接操作
2. **数据流**: crawler → storage → web，单向流动
3. **配置统一**: 所有字段定义在 `config.py`
4. **命名规范**: 文件名英文，函数名snake_case
5. **模块独立**: 每个子模块可独立运行测试

---

*最后更新: 2026-05-25*
