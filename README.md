# 和金顺数据平台

电商数据采集、生成与可视化一体化平台。

## 项目架构

```
┌──────────┐    ┌──────────┐    ┌─────────────────┐
│ crawler  │───▶│ storage  │───▶│       web       │
│ 爬虫模块  │    │ 存储模块  │    │  前端可视化模块   │
└──────────┘    └──────────┘    ├─────────────────┤
     │              │           │ dashboard :5001 │
     │              │           │ generator :5003 │
     │              │           └────────┬────────┘
     └──────────────┴───────────────────┘
                     │
                     ▼
           ┌──────────────────┐
           │  data-factory    │
           │  数据制造工厂      │
           │  web_app  :5007  │
           └────────┬─────────┘
                    ▼
           ┌──────────────────┐
           │ data/cleaned/    │
           │ products.xlsx    │
           └──────────────────┘
```

### 四大模块

| 模块 | 目录 | 功能 |
|------|------|------|
| 爬虫 | `crawler/` | 京东、什么值得买多平台数据采集 |
| 存储 | `storage/` | Excel 读写、数据清洗与去重合并 |
| 前端 | `web/` | 数据大屏仪表盘、ECharts 代码生成器 |
| 数据工厂 | `data-factory/` | 结论驱动数据生成、一键导出到主数据 |

## 功能特性

### 数据大屏 (Port 5001)
- **侧边栏导航**: 三大模式切换 (数据看板 / 数据接入 / 自定义分析)
- **中国地图热力图**: 省份级销售分布 + 城市级散点涟漪动效, 支持缩放拖拽, 悬停查看详细指标
- **可视化洞察仪表盘**: 商品总量、价格中位数、覆盖地区、性别比例 — 带动画进度条
- **关键指标卡片**: 5 项核心 KPI, 毛玻璃悬浮发光效果
- **7 种图表**: 平台占比玫瑰图、价格分布柱状图、平台均价、价格区间、年龄分布、性别比例、地区分布
- **Apple 风格 UI**: 毛玻璃拟态、视差滚动背景 (7 光球 + 噪点纹理)、滚动揭示动画、弹性缓动
- **实时采集**: 支持关键词搜索采集 + URL 直采, 终端日志实时反馈

### 数据制造工厂 (Port 5007)
- **结构化输入**: 品类、价格区间、年龄、性别比例参数配置
- **自然语言输入**: "手机品类价格呈上涨趋势" → 自动生成符合结论的数据
- **用户画像生成**: 年龄分布、性别比例、地区分布
- **一键导出**: 自动合并到主数据文件

### 代码生成器 (Port 5003)
- Excel 拖拽上传 → ECharts 配置代码自动生成
- 支持饼图、柱状图、折线图、散点图、漏斗图、雷达图、词云、矩形树图
- Apple 风格暗色代码编辑器

## 快速开始

```bash
pip install -r requirements.txt

# 启动数据大屏 (port 5001)
python main.py

# 启动数据工厂 (port 5007)
python main.py --factory

# 启动代码生成器 (port 5003)
python main.py --generator
```

## 项目结构

```
和金顺新计划/
├── main.py                     # 主入口 (CLI 参数调度)
├── launcher.py                 # PyInstaller 打包启动器
├── config.py                   # 全局配置 (数据字段定义)
├── hejinshun.spec              # PyInstaller 打包配置
├── requirements.txt
│
├── crawler/                    # 爬虫模块
│   ├── jd_crawler.py          # 京东爬虫 (DrissionPage)
│   └── smzdm_crawler.py       # 什么值得买爬虫
│
├── storage/                    # 存储模块
│   ├── excel_handler.py       # Excel 读写
│   └── data_cleaner.py        # 数据清洗与合并
│
├── web/                        # 前端模块
│   ├── dashboard.py           # 数据大屏 API (5001)
│   └── generator.py           # ECharts 代码生成器 (5003)
│
├── data-factory/               # 数据制造工厂
│   ├── web_app.py             # Web 应用 (5007)
│   ├── conclusion_engine.py   # 结论驱动引擎
│   ├── generators/            # 数据生成器
│   ├── output/                # 输出 (Excel/JSON/CSV)
│   ├── rules/                 # 约束规则
│   └── validators/            # 统计验证
│
├── templates/                  # 前端模板
│   ├── index.html             # 数据大屏界面
│   └── generator.html         # 代码生成器界面
│
└── dist/                       # 打包输出
    └── 和金顺数据平台.exe
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
| user_age | int | 用户年龄 |
| user_gender | string | 用户性别 |
| user_region | string | 用户地区 |
| image_url | string | 图片链接 |
| product_url | string | 商品链接 |
| scraped_at | string | 采集时间 |

## API 接口

### 数据大屏 (5001)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 仪表盘页面 |
| GET | `/api/products` | 商品列表 (支持排序) |
| GET | `/api/stats` | 统计数据 |
| GET | `/api/status` | 采集状态 |
| POST | `/api/scrape` | 启动采集 |
| POST | `/api/scrape/search` | 关键词搜索采集 |
| POST | `/api/stop` | 中止采集 |
| POST | `/api/reset` | 重置状态 |
| DELETE | `/api/clear` | 清空数据 |

### 数据工厂 (5007)

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/` | 数据工厂页面 |
| POST | `/api/generate-structured` | 结构化生成 |
| POST | `/api/generate-from-conclusion` | 结论驱动生成 |
| POST | `/api/export` | 导出到主数据 |
| GET | `/api/download` | 下载生成文件 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 + Flask |
| 前端 | HTML5 + CSS3 + Vanilla JS |
| 图表 | ECharts 5.5 + ECharts WordCloud |
| 地图 | DataV GeoJSON + ECharts Map |
| 爬虫 | DrissionPage |
| 存储 | Excel (openpyxl) |
| 打包 | PyInstaller |

## 开发规范

1. **模块边界**: 各模块职责明确，不跨模块直接操作
2. **数据流**: crawler → storage → web，单向流动
3. **配置统一**: 所有字段定义在 `config.py`
4. **无数据库**: 纯 Excel 存储，简单可移植
5. **前端零框架**: 原生 HTML/CSS/JS，无构建工具依赖

---

*最后更新: 2026-05-26*
