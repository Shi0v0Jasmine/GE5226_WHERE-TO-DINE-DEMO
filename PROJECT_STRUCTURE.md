# GE5226 WHERE-TO-DINE-DEMO 项目结构图

## 项目概述
一个基于真实数据的纽约市(NYC)餐厅推荐系统，使用出租车下车数据作为"用脚投票"的人气指标，结合空间分析和聚类算法来识别和推荐dining hotspots。

---

## 目录结构树

```
GE5226_WHERE-TO-DINE-DEMO/
│
├── 📄 核心文件
│   ├── app.py                      # Flask Web应用主入口
│   ├── run_pipeline.py             # 数据处理流程主控脚本
│   ├── requirements.txt            # Python依赖包列表
│   ├── .gitattributes             # Git LFS配置(大文件管理)
│   ├── README_DEMO.md             # Web演示说明文档
│   └── WEB_DEMO_GUIDE.md          # Web演示使用指南
│
├── 📁 src/                        # 源代码目录
│   ├── __init__.py
│   │
│   ├── data_processing/           # 数据处理模块
│   │   ├── __init__.py
│   │   ├── 02_process_taxi_data.py       # 出租车数据处理
│   │   ├── 02_merge_restaurants.py       # 餐厅数据合并
│   │   ├── 06_cluster_restaurants.py     # 餐厅聚类分析
│   │   ├── 07_cluster_taxi_dropoffs.py   # 出租车下车点聚类
│   │   └── 08_spatial_intersection.py    # 空间交叉分析
│   │
│   ├── analysis/                  # 分析算法模块
│   │   ├── __init__.py
│   │   ├── clustering.py          # 聚类算法(HDBSCAN)
│   │   └── isochrone.py          # 等时圈分析(可达性)
│   │
│   ├── visualization/             # 可视化模块
│   │   ├── __init__.py
│   │   └── 01_visualize_results.py  # 结果可视化
│   │
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       └── config_loader.py       # 配置文件加载器
│
├── 📁 data/                       # 数据目录
│   │
│   ├── raw/                       # 原始数据
│   │   ├── taxi/                  # 出租车数据(2024年1-12月)
│   │   │   ├── yellow_tripdata_2024-01.parquet
│   │   │   ├── yellow_tripdata_2024-02.parquet
│   │   │   ├── ...
│   │   │   └── yellow_tripdata_2024-12.parquet
│   │   │
│   │   ├── restaurants/           # 餐厅数据
│   │   │   ├── restaurants_nyc_osm.geojson
│   │   │   ├── restaurants_nyc_osm.csv
│   │   │   └── restaurants_nyc_googlemaps.csv
│   │   │
│   │   ├── gtfs/                  # GTFS公交数据
│   │   │   ├── gtfs_subway.zip    # 地铁
│   │   │   ├── gtfs_b.zip         # 布鲁克林公交
│   │   │   ├── gtfs_bx.zip        # 布朗克斯公交
│   │   │   ├── gtfs_m.zip         # 曼哈顿公交
│   │   │   ├── gtfs_q.zip         # 皇后区公交
│   │   │   ├── gtfs_si.zip        # 斯塔滕岛公交
│   │   │   ├── gtfs_busco.zip     # 其他公交
│   │   │   └── README.txt
│   │   │
│   │   └── osm/                   # OpenStreetMap数据
│   │       └── new-york-251104.osm.pbf
│   │
│   ├── interim/                   # 中间处理数据
│   │   ├── taxi_dropoffs_weighted.parquet
│   │   ├── taxi_dropoffs_weighted_sample.geojson
│   │   ├── taxi_processing_summary.json
│   │   ├── restaurants_merged.csv
│   │   └── restaurants_merged.geojson
│   │
│   ├── processed/                 # 处理后的最终数据
│   │   ├── final_hotspots.geojson           # 最终推荐热点
│   │   ├── dining_zones.geojson             # 用餐区域
│   │   ├── restaurants_clustered.geojson    # 聚类后的餐厅
│   │   ├── taxi_dropoffs_clustered.parquet  # 聚类后的出租车数据
│   │   ├── taxi_hotspots.geojson           # 出租车热点
│   │   ├── taxi_clustering_metrics.json     # 出租车聚类指标
│   │   ├── clustering_metrics.json          # 聚类评估指标
│   │   └── intersection_analysis.json       # 空间交叉分析结果
│   │
│   └── external/                  # 外部参考数据
│       └── boundaries/            # 边界数据
│           ├── nybb.shp           # NYC行政区边界
│           ├── nybb.dbf
│           ├── nybb.prj
│           ├── nybb.shx
│           ├── nybb.shp.xml
│           ├── taxi_zones.shp     # 出租车区域边界
│           ├── taxi_zones.dbf
│           ├── taxi_zones.prj
│           ├── taxi_zones.shx
│           ├── taxi_zones.sbn
│           ├── taxi_zones.sbx
│           └── taxi_zones.shp.xml
│
├── 📁 outputs/                    # 输出结果目录
│   ├── figures/                   # 图表
│   ├── maps/                      # 地图
│   ├── reports/                   # 报告
│   └── tables/                    # 数据表
│
├── 📁 templates/                  # Web模板
│   └── index.html                 # Web应用主页面
│
├── 📁 config/                     # 配置文件目录
│
├── 📁 cache/                      # 缓存文件(JSON格式)
│   └── [多个缓存文件.json]
│
└── 📁 docs/                       # 文档目录
    ├── ACADEMIC_EVALUATION.md           # 学术评估文档
    ├── DATA_PROCESSING_PIPELINE.md      # 数据处理流程说明
    ├── DIRECTORY_STRUCTURE.md           # 目录结构说明
    ├── FINAL_REPORT_TEMPLATE.md         # 最终报告模板
    ├── PIPELINE_OVERVIEW.md             # 流程概览
    ├── PRESENTATION_GUIDE.md            # 演示指南
    ├── PRESENTATION_SPEECH.md           # 演示讲稿
    ├── SYSTEM_ARCHITECTURE.md           # 系统架构文档
    ├── TASK_CHECKLIST.md               # 任务清单
    │
    └── methodology/                     # 方法论文档
        ├── isochrone_thresholds.md      # 等时圈阈值设定
        ├── recommendation_scoring.md     # 推荐评分算法
        ├── spatial_intersection_criteria.md  # 空间交叉准则
        └── temporal_weighting.md        # 时间权重计算
```

---

## 核心模块说明

### 1. Web应用层 (app.py)
- **技术栈**: Flask + Leaflet.js
- **功能**:
  - 交互式地图展示dining hotspots
  - 点击地图获取附近推荐
  - 基于距离和人气的智能排序
  - 实时显示top 10推荐结果

### 2. 数据处理流程 (run_pipeline.py + src/data_processing/)
数据处理按编号顺序执行:

1. **02_merge_restaurants.py** - 合并OSM和Google Maps餐厅数据
2. **02_process_taxi_data.py** - 处理2024年全年出租车下车数据
3. **06_cluster_restaurants.py** - 使用HDBSCAN对餐厅进行空间聚类
4. **07_cluster_taxi_dropoffs.py** - 对出租车下车点进行聚类分析
5. **08_spatial_intersection.py** - 空间交叉分析，识别真正的dining hotspots

### 3. 分析算法 (src/analysis/)
- **clustering.py**: HDBSCAN聚类算法实现
- **isochrone.py**: 基于OSM路网的等时圈可达性分析

### 4. 可视化 (src/visualization/)
- **01_visualize_results.py**: 生成各类地图和图表

---

## 数据流程图

```
原始数据 (raw/)
    │
    ├─> Taxi数据 (12个月Parquet) ──┐
    ├─> 餐厅数据 (OSM + Google) ───┤
    ├─> GTFS公交数据 ──────────────┤
    └─> OSM路网数据 ───────────────┤
                                   │
                                   ↓
                          中间处理 (interim/)
                                   │
                ┌──────────────────┴──────────────────┐
                ↓                                     ↓
         餐厅数据合并                            出租车数据处理
         restaurants_merged                    taxi_dropoffs_weighted
                │                                     │
                ↓                                     ↓
            餐厅聚类                              出租车聚类
         (HDBSCAN)                               (HDBSCAN)
                │                                     │
                └──────────────┬──────────────────────┘
                               ↓
                        空间交叉分析
                    (Spatial Intersection)
                               │
                               ↓
                      最终结果 (processed/)
                               │
                    ┌──────────┴──────────┐
                    ↓                     ↓
              final_hotspots        clustering_metrics
                    │                     │
                    └──────────┬──────────┘
                               ↓
                         Web应用展示
                          (app.py)
```

---

## 技术栈总结

### 后端技术
- **Python 3.9+**: 主要开发语言
- **Flask**: Web框架
- **GeoPandas**: 地理空间数据处理
- **HDBSCAN**: 密度聚类算法
- **OSMnx**: OpenStreetMap路网分析
- **Pandas/NumPy**: 数据处理

### 前端技术
- **Leaflet.js**: 交互式地图
- **HTML/CSS/JavaScript**: 基础Web技术

### 数据格式
- **Parquet**: 高效的列式存储(出租车数据)
- **GeoJSON**: 地理空间数据交换格式
- **Shapefile**: GIS标准格式(边界数据)
- **CSV**: 通用数据格式

### 依赖管理
- **Git LFS**: 大文件版本控制(.parquet, .pbf文件)

---

## 关键算法

### 1. HDBSCAN聚类
- 基于密度的层次聚类
- 自动发现不同密度的聚类
- 能识别噪声点

### 2. 空间交叉分析
- 餐厅聚类 ∩ 出租车热点
- 识别高人气dining区域

### 3. 推荐评分
- 结合距离和人气
- 考虑时间权重
- 多维度评估

---

## 项目特色

1. **真实数据驱动**: 使用2024年全年NYC出租车数据(约1.4亿条记录)
2. **多源数据融合**: 整合OSM、Google Maps、GTFS等多个数据源
3. **学术严谨性**: 完整的方法论文档和评估指标
4. **实用性**: 提供交互式Web演示应用
5. **可扩展性**: 模块化设计，易于扩展和维护

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行数据处理流程
python run_pipeline.py

# 3. 启动Web应用
python app.py

# 4. 访问 http://localhost:5000
```

---

## 文档导航

- **开发文档**: `/docs/SYSTEM_ARCHITECTURE.md`
- **数据流程**: `/docs/DATA_PROCESSING_PIPELINE.md`
- **方法论**: `/docs/methodology/`
- **演示指南**: `/WEB_DEMO_GUIDE.md`
- **学术评估**: `/docs/ACADEMIC_EVALUATION.md`

---

**项目类型**: GE5226课程项目 - 地理信息系统与空间分析
**主题**: NYC餐厅推荐系统 (Where to DINE)
**数据规模**: ~1.4亿条出租车记录 + 数万个餐厅POI
**技术难度**: 高级 (大数据处理 + 空间分析 + Web开发)
