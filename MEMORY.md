# Hejinshun Data Platform - Project Memory

## Project Overview

和金顺数据平台 - 电商数据采集、生成与可视化一体化平台

## Current Status (2026-05-26)

### Completed Features
- [x] 核心框架搭建（crawler、storage、web、data-factory 四大模块）
- [x] 京东/什么值得买爬虫实现（DrissionPage）
- [x] Excel数据存储与清洗
- [x] 数据大屏可视化（ECharts 5.5）
- [x] 中国地图热力图（省份 + 城市级散点，缩放拖拽，悬停详情）
- [x] 可视化洞察仪表盘（4 组件实时指标 + 动画进度条）
- [x] Apple 风格 UI 设计系统（毛玻璃拟态、视差滚动、滚动揭示、噪点纹理）
- [x] 侧边栏导航（三大模式切换）
- [x] ECharts代码生成器（拖拽上传 → 配置代码）
- [x] **数据制造工厂** - 结论驱动数据生成
- [x] 用户画像字段（年龄、性别、地区）
- [x] PyInstaller 打包发布

## Architecture

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
           └──────────────────┘
```

## Key Decisions

| Decision | Description | Date |
|----------|-------------|------|
| D1 | Excel replaces SQLite - simpler, portable, inspectable | D1 |
| D2 | Scrape data auto-saves via storage module | D1 |
| D3 | Data Factory as independent sub-project with export to main data | D4 |
| D4 | User demographics fields added (age, gender, region) | D4 |
| D5 | Conclusion-driven data generation engine | D4 |
| D6 | Apple design system (glass morphism, parallax, scroll reveal) | D5 |
| D7 | China interactive map + visual insight dashboard | D6 |

## Services

| Service | Port | Command |
|---------|------|---------|
| 数据大屏 | 5001 | `python main.py` |
| 数据工厂 | 5007 | `python main.py --factory` |
| 代码生成器 | 5003 | `python main.py --generator` |

## Recent Work

### 2026-05-26 (D6)
- 中国地图交互热力图 (ECharts + DataV GeoJSON, 省份热力 + 城市涟漪散点)
- 可视化洞察仪表盘 (4 组件: 商品总量/价格中位数/覆盖地区/性别比例)
- 超大侧边栏导航 (230px, 3 模式切换)
- 滚动动画双向触发 (IntersectionObserver 进入+离开)
- 饼图悬浮提示突出占比显示
- 价格柱状图均匀整数区间算法 (niceSteps)
- 7 光球视差背景 + SVG 噪点纹理覆盖
- 毛玻璃效果强化 (backdrop-filter saturate blur)
- UI 细节打磨 (圆角/阴影/缓动/字重)

### 2026-05-25 (D5)
- Apple MacBook Neo 风格前端全面重设计
- 毛玻璃导航栏 + 滚动揭示动画 + 视差背景光球
- 数据大屏指标卡片放大 + 悬浮发光效果

### 2026-05-24 (D4)
- 添加数据制造工厂模块
- 实现结论驱动数据生成引擎
- 添加用户画像字段支持
- 更新数据大屏显示用户统计

---

*Last updated: 2026-05-26*
