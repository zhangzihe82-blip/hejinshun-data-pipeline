# Hejinshun Data Platform -- Project Rules

## 自动技能调用规则

根据用户需求自动调用对应技能，无需用户明确指定：

### 触发规则

| 用户需求 | 自动调用技能 | 说明 |
|----------|-------------|------|
| "帮我规划/设计/构思" | `/autopilot` 或 `Plan` | 需求分析与架构设计 |
| "实现新功能/开发" | `/autopilot` 或 `executor` | 自动完成开发流程 |
| "代码审查/检查质量" | `code-reviewer` | 代码质量审查 |
| "找出bug/调试问题" | `debugger` | 问题定位与修复 |
| "搜索代码/查找文件" | `Explore` 或 `explore` | 代码库搜索 |
| "安全检查/漏洞扫描" | `security-reviewer` | 安全性审查 |
| "写测试/测试覆盖率" | `test-engineer` | 测试策略与实现 |
| "生成文档/写README" | `writer` | 技术文档编写 |
| "UI设计/界面开发" | `designer` | UI/UX设计与开发 |
| "复杂多步骤任务" | `/autopilot` | 完整自动化流程 |

### 自动判断原则

1. **模糊需求 → 规划先行**: 先用 `Plan` 或 `planner` 分析，再执行
2. **实现任务 → autopilot**: 完整需求直接启动自动化流程
3. **调试问题 → debugger**: 错误排查使用专用调试代理
4. **搜索查找 → Explore**: 快速定位代码位置
5. **代码质量 → code-reviewer**: 审查已完成的代码

### 执行模式

```
用户输入
    │
    ▼
┌─────────────────┐
│  需求理解与分类  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
 规划类     实现类
    │         │
    ▼         ▼
Plan     autopilot
planner   executor
    │         │
    └────┬────┘
         │
         ▼
    ┌─────────────────┐
    │   验证与测试     │
    │  verifier       │
    └─────────────────┘
```

---

## 项目架构

```
┌──────────────────────────────────────────────────────────────┐
│                     和金顺数据平台 v2.0                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │ crawler  │───▶│ storage  │───▶│        web           │   │
│  │ 爬虫模块  │    │ 存储模块  │    │    前端可视化模块     │   │
│  └──────────┘    └──────────┘    ├──────────────────────┤   │
│       │               │         │ dashboard  :5001     │   │
│       │               │         │ generator  :5003     │   │
│       │               │         └──────────┬───────────┘   │
│       │               │                    │                │
│       └───────────────┴────────────────────┘                │
│                        │                                    │
│                        ▼                                    │
│              ┌──────────────────┐                           │
│              │  data-factory    │                           │
│              │  数据制造工厂      │                           │
│              │  web_app  :5007  │                           │
│              └────────┬─────────┘                           │
│                       │                                     │
│                       ▼                                     │
│              ┌──────────────────┐                           │
│              │ data/cleaned/    │                           │
│              │ products.xlsx    │                           │
│              └──────────────────┘                           │
└──────────────────────────────────────────────────────────────┘
```

**四大模块相对独立，在 main.py 中统一调用。launcher.py 为 PyInstaller 打包入口。**

---

## 模块边界

### crawler/ (爬虫模块)
- **职责**: 多平台电商数据采集，返回 `list[dict]`
- **规则**: NEVER 写文件，只返回数据
- **子模块**:
  - `jd_crawler.py`: 京东爬虫 (DrissionPage)
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
  - `generator.py`: ECharts 代码生成器 (port 5003)

### data-factory/ (数据制造工厂)
- **职责**: 结论驱动数据生成
- **规则**: 独立子项目，可导出到主数据
- **子模块**:
  - `web_app.py`: Web应用 (port 5007)
  - `conclusion_engine.py`: 结论驱动引擎
  - `generators/`: 数据生成器
  - `output/`: 输出模块 (Excel/JSON/CSV)
  - `rules/`: 约束规则模块
  - `validators/`: 统计验证模块

---

## 数据流向

```
crawler.scrape() → storage.clean_records() → storage.save_cleaned()
                                                       ↓
web.dashboard ← storage.read_cleaned() ←──────────────┘
                                                       ↑
data-factory.generate() → export → ───────────────────┘
```

---

## 数据存储

- **No database.** Excel files only (openpyxl).
- `data/raw/` = 原始数据备份
- `data/cleaned/products.xlsx` = 主数据文件

## 数据字段

```python
PRODUCT_FIELDS = [
    # 商品信息
    ("name", "price", "original_price", "platform", "rating", "comment_count", "category"),
    # 用户画像
    ("user_age", "user_gender", "user_region"),
    # 链接与时间
    ("image_url", "product_url", "scraped_at", "created_at")
]
```

---

## 配置约定

- `config.py` 是数据字段的唯一定义来源
- `PRODUCT_FIELDS` 定义所有字段 (key, header, type, default)
- 新增字段只需修改 `config.py`

## 服务端口

| 服务 | 端口 | 启动命令 |
|------|------|---------|
| 数据大屏 | 5001 | `python main.py` |
| 数据工厂 | 5007 | `python main.py --factory` |
| 代码生成器 | 5003 | `python main.py --generator` |

## 打包发布

```bash
pyinstaller hejinshun.spec --noconfirm   # 输出 dist/和金顺数据平台.exe
```

---

## 前端设计系统 (Apple-Inspired)

### 设计令牌 (CSS Variables)
- 色彩: `--bg: #f5f5f7`, `--text: #1d1d1f`, `--blue: #0071e3`, `--purple: #af52de`
- 玻璃态: `backdrop-filter: saturate(180%) blur(20px)` on `rgba(255,255,255,.72)`
- 动画: Apple ease-out `cubic-bezier(0.22, 1, 0.36, 1)`, spring `cubic-bezier(0.34, 1.56, 0.64, 1)`
- 圆角: 12px / 18px / 24px / 32px 梯度

### 仪表盘功能模块
1. **侧边栏导航**: 230px 宽, 3个模式切换 (数据看板/数据接入/自定义分析)
2. **关键指标卡片**: 5 项核心指标, 玻璃态悬浮, 发光 hover 效果
3. **中国地图热力图**: ECharts + GeoJSON (DataV CDN), 省份热力 + 城市散点涟漪
4. **可视化洞察仪表盘**: 4 组件 (商品总量/价格中位数/覆盖地区/性别比例), 带动画进度条
5. **图表面板**: 平台占比 (玫瑰图), 价格分布 (柱状图), 均价/年龄/性别/地区等 7 个图表
6. **视差背景**: 7 个彩色光球以不同速度随滚动漂移, SVG 噪点纹理覆盖
7. **滚动驱动动画**: IntersectionObserver 双向触发 (进入+离开), 缩放/位移/淡入

### 数据工厂 & 代码生成器
- 统一的 Apple 设计语言 (导航栏, 玻璃态卡片, 滚动揭示)
- 结构化 + 自然语言双模式输入
- ECharts JSON 配置即时渲染

---

## 开发指南

1. **新增爬虫平台**: 在 `crawler/` 下添加新文件
2. **新增前端功能**: 在 `web/` 下添加新文件
3. **修改数据字段**: 只改 `config.py` 中的 `PRODUCT_FIELDS`
4. **新增数据生成规则**: 在 `data-factory/conclusion_engine.py` 中扩展

## 命名约定

- 所有文件名、路径使用英文
- 模块导入使用绝对导入

---

*最后更新: 2026-05-26*
