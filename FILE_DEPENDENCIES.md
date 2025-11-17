# 项目文件依赖关系分析

## 概览

本文档详细说明了 **GE5226 WHERE-TO-DINE** 项目中所有文件之间的依赖关系，包括：
- 代码模块依赖（import关系）
- 数据流依赖（输入/输出文件）
- 执行顺序依赖

---

## 一、系统架构依赖图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                               │
│  ┌──────────────┐                 ┌─────────────────────┐  │
│  │  app.py      │ ◄───使用────────│ templates/          │  │
│  │ (Flask Web)  │                 │   index.html        │  │
│  └──────┬───────┘                 └─────────────────────┘  │
│         │ 读取                                              │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据产出层                                 │
│         data/processed/final_hotspots.geojson                │
└─────────────────────────────────────────────────────────────┘
          ▲
          │ 生成
┌─────────┴───────────────────────────────────────────────────┐
│                  数据处理流程层                               │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │        run_pipeline.py (流程控制器)                  │    │
│  │              按顺序调用↓                              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                               │
│  [Phase 1]  02_process_taxi_data.py                         │
│               ↓ 输出: taxi_dropoffs_weighted.parquet        │
│                                                               │
│  [Phase 2]  02_merge_restaurants.py                         │
│               ↓ 输出: restaurants_merged.geojson            │
│                                                               │
│  [Phase 3]  06_cluster_restaurants.py                       │
│               ↓ 输入: restaurants_merged.geojson            │
│               ↓ 输出: dining_zones.geojson                  │
│               ↓       restaurants_clustered.geojson          │
│                                                               │
│  [Phase 4]  07_cluster_taxi_dropoffs.py                     │
│               ↓ 输入: taxi_dropoffs_weighted.parquet        │
│               ↓ 输出: taxi_hotspots.geojson                 │
│                                                               │
│  [Phase 5]  08_spatial_intersection.py                      │
│               ↓ 输入: dining_zones.geojson                  │
│               ↓       taxi_hotspots.geojson                  │
│               ↓ 输出: final_hotspots.geojson                │
│                                                               │
└───────────────────────────────────────────────────────────────┘
          │ 所有模块依赖
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    工具模块层                                 │
│  ┌─────────────────────┐      ┌────────────────────────┐   │
│  │ src/utils/          │      │ src/analysis/          │   │
│  │  config_loader.py   │      │  clustering.py         │   │
│  │ (配置加载)           │      │  isochrone.py          │   │
│  └─────────────────────┘      └────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          ▲
          │ 读取
┌─────────┴───────────────────────────────────────────────────┐
│                    配置层                                     │
│              config/config.yaml                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、详细文件依赖关系

### 2.1 入口文件依赖

#### **app.py** (Web应用)

**直接依赖:**
```python
from flask import Flask, render_template, request, jsonify
import geopandas, pandas, numpy, shapely, json
```

**文件依赖:**
- **读取**: `data/processed/final_hotspots.geojson`
- **使用**: `templates/index.html`

**被依赖情况:** 无（顶层应用）

---

#### **run_pipeline.py** (流程控制器)

**直接依赖:**
```python
import subprocess, sys, logging, pathlib, time, datetime
```

**调用顺序:**
1. `src/data_processing/02_process_taxi_data.py`
2. `src/data_processing/02_merge_restaurants.py`
3. `src/data_processing/06_cluster_restaurants.py`
4. `src/data_processing/07_cluster_taxi_dropoffs.py`
5. `src/data_processing/08_spatial_intersection.py`

**检查文件:**
- `config/config.yaml`
- `data/external/boundaries/nybb.shp`
- `data/raw/taxi/` (目录)
- `data/raw/restaurants/` (目录)

**被依赖情况:** 无（顶层控制器）

---

### 2.2 工具模块依赖

#### **src/utils/config_loader.py**

**直接依赖:**
```python
import yaml, pathlib
```

**文件依赖:**
- **读取**: `config/config.yaml`

**被依赖者:**
- `02_process_taxi_data.py`
- `02_merge_restaurants.py`
- `06_cluster_restaurants.py`
- `07_cluster_taxi_dropoffs.py`
- `08_spatial_intersection.py`
- `clustering.py`

**核心功能:**
- `load_config()` - 加载YAML配置
- `get_data_path()` - 获取数据路径
- `get_config_value()` - 获取配置值

---

#### **src/analysis/clustering.py**

**直接依赖:**
```python
import numpy, pandas, geopandas, hdbscan
from sklearn.metrics import silhouette_score, davies_bouldin_score
from src.utils.config_loader import load_config
```

**被依赖情况:**
- 理论上可被导入，但实际各处理脚本都是**内嵌实现**而非导入此模块
- 提供参考实现和测试代码

---

#### **src/analysis/isochrone.py**

**直接依赖:**
```python
import networkx, osmnx, geopandas, shapely
```

**文件依赖:**
- **读取**: `data/processed/networks/network_walk.gpickle` (可选)

**被依赖情况:** 独立功能模块，未被其他脚本调用

**状态:** 可选功能（用于可达性分析）

---

### 2.3 数据处理流程依赖

#### **Phase 1: 02_process_taxi_data.py**

**代码依赖:**
```python
import pandas, geopandas, numpy, shapely
from pathlib import Path
from pandarallel import pandarallel
from src.utils.config_loader import load_config, get_config_value
```

**输入文件:**
- `data/raw/taxi/*.parquet` (12个月份)
- `data/external/boundaries/nybb.shp` (NYC边界)
- `data/external/boundaries/taxi_zones.shp` (出租车区域)
- `config/config.yaml`

**输出文件:**
- `data/interim/taxi_dropoffs_weighted.parquet` ✅ **主要输出**
- `data/interim/taxi_dropoffs_weighted_sample.geojson`
- `data/interim/taxi_processing_summary.json`

**关键处理:**
1. 批处理加载12个月Parquet文件
2. LocationID → 经纬度转换（使用taxi_zones.shp）
3. 过滤到用餐时间段（breakfast, lunch, dinner, late-night）
4. 应用时间权重（周末晚餐1.5x，工作日晚餐1.0x等）
5. 过滤到NYC边界内

**被依赖者:** `07_cluster_taxi_dropoffs.py`

---

#### **Phase 2: 02_merge_restaurants.py**

**代码依赖:**
```python
import pandas, geopandas, shapely
from scipy.spatial import cKDTree
from fuzzywuzzy import fuzz
```

**输入文件:**
- `data/raw/restaurants/restaurants_nyc_googlemaps.csv`
- `data/raw/restaurants/restaurants_nyc_osm.csv`

**输出文件:**
- `data/interim/restaurants_merged.geojson` ✅ **主要输出**
- `data/interim/restaurants_merged.csv`

**关键处理:**
1. 加载Google Maps和OSM餐厅数据
2. 标准化字段（name, lat, lon, rating等）
3. 去重（空间距离<50m + 名称相似度>80%）
4. 使用KDTree优化空间搜索

**被依赖者:** `06_cluster_restaurants.py`

---

#### **Phase 3: 06_cluster_restaurants.py**

**代码依赖:**
```python
import pandas, geopandas, numpy
from pathlib import Path
from shapely.geometry import MultiPoint
from hdbscan import HDBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
from src.utils.config_loader import load_config, get_config_value
```

**输入文件:**
- `data/interim/restaurants_merged.geojson` ← Phase 2
- `config/config.yaml`

**输出文件:**
- `data/processed/dining_zones.geojson` ✅ **主要输出**
- `data/processed/restaurants_clustered.geojson`
- `data/processed/clustering_metrics.json`

**关键处理:**
1. 投影到EPSG:2263（米制坐标）
2. HDBSCAN聚类（min_cluster_size=30, epsilon=200m）
3. 生成凸包 + 缓冲区(100m) → dining zones
4. 计算验证指标（Silhouette, Davies-Bouldin）

**被依赖者:** `08_spatial_intersection.py`

---

#### **Phase 4: 07_cluster_taxi_dropoffs.py**

**代码依赖:**
```python
import pandas, geopandas, numpy
from shapely.geometry import MultiPoint
from hdbscan import HDBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
from src.utils.config_loader import load_config, get_config_value
```

**输入文件:**
- `data/interim/taxi_dropoffs_weighted.parquet` ← Phase 1
- `config/config.yaml`

**输出文件:**
- `data/processed/taxi_hotspots.geojson` ✅ **主要输出**
- `data/processed/taxi_dropoffs_clustered.parquet`
- `data/processed/taxi_clustering_metrics.json`

**关键处理:**
1. 加载带权重的出租车数据
2. 可选H3聚合（减少数据量）
3. 根据权重复制点（weight=1.5 → 复制2次）
4. HDBSCAN聚类（min_cluster_size=50, epsilon=250m）
5. 生成凸包 + 缓冲区(150m) → taxi hotspots

**被依赖者:** `08_spatial_intersection.py`

---

#### **Phase 5: 08_spatial_intersection.py**

**代码依赖:**
```python
import geopandas, pandas, numpy
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from src.utils.config_loader import load_config, get_config_value
```

**输入文件:**
- `data/processed/dining_zones.geojson` ← Phase 3
- `data/processed/taxi_hotspots.geojson` ← Phase 4
- `config/config.yaml`

**输出文件:**
- `data/processed/final_hotspots.geojson` ✅ **最终输出**
- `data/processed/intersection_analysis.json`

**关键处理:**
1. 空间求交：dining_zones ∩ taxi_hotspots
2. 过滤条件：
   - 最小面积 ≥ 10,000 m²
   - 最小重叠率 ≥ 15%
3. 计算复合得分：
   - restaurant_score (餐厅密度归一化)
   - taxi_score (出租车密度归一化)
   - popularity_score = 0.5×restaurant + 0.5×taxi
4. 排名并输出top N

**被依赖者:** `app.py`, `01_visualize_results.py`

---

### 2.4 可视化模块依赖

#### **src/visualization/01_visualize_results.py**

**代码依赖:**
```python
import geopandas, pandas, folium
from folium import plugins
```

**输入文件:**
- `data/processed/restaurants_clustered.geojson`
- `data/processed/dining_zones.geojson`
- `data/processed/taxi_hotspots.geojson`
- `data/processed/final_hotspots.geojson`

**输出文件:**
- `maps/01_restaurants_clusters.html`
- `maps/02_taxi_hotspots.html`
- `maps/03_final_hotspots.html`

**被依赖情况:** 独立执行，不被其他模块依赖

---

## 三、数据流依赖图

### 3.1 完整数据流

```
原始数据源
├─ data/raw/taxi/*.parquet (12个月)
├─ data/raw/restaurants/restaurants_nyc_googlemaps.csv
├─ data/raw/restaurants/restaurants_nyc_osm.csv
├─ data/external/boundaries/nybb.shp
└─ data/external/boundaries/taxi_zones.shp
        │
        ▼
┌────────────────────────────────────────────────┐
│  Phase 1: 02_process_taxi_data.py             │
│  └─→ data/interim/taxi_dropoffs_weighted.parquet
└────────────────────────────────────────────────┘
        │
        │                   ┌────────────────────────────────────┐
        │                   │ Phase 2: 02_merge_restaurants.py    │
        │                   │ └─→ data/interim/restaurants_merged.geojson
        │                   └────────────────────────────────────┘
        │                                   │
        ▼                                   ▼
┌─────────────────────────────┐   ┌──────────────────────────────┐
│ Phase 4:                    │   │ Phase 3:                     │
│ 07_cluster_taxi_dropoffs.py │   │ 06_cluster_restaurants.py    │
│ └─→ taxi_hotspots.geojson   │   │ └─→ dining_zones.geojson     │
└─────────────────────────────┘   └──────────────────────────────┘
        │                                   │
        └───────────┬───────────────────────┘
                    ▼
        ┌───────────────────────────────────────┐
        │ Phase 5:                              │
        │ 08_spatial_intersection.py            │
        │ └─→ data/processed/                   │
        │     final_hotspots.geojson            │
        └───────────────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
┌───────────────────┐   ┌────────────────────────┐
│ app.py            │   │ 01_visualize_results.py│
│ (Web应用)          │   │ (可视化)                │
│ → 127.0.0.1:5000  │   │ → maps/*.html          │
└───────────────────┘   └────────────────────────┘
```

---

### 3.2 关键数据文件依赖矩阵

| 输出文件 | 被哪些脚本使用 | 依赖哪些输入文件 |
|---------|---------------|----------------|
| `taxi_dropoffs_weighted.parquet` | 07_cluster_taxi_dropoffs.py | raw/taxi/*.parquet, boundaries/nybb.shp, taxi_zones.shp |
| `restaurants_merged.geojson` | 06_cluster_restaurants.py | raw/restaurants/*.csv |
| `dining_zones.geojson` | 08_spatial_intersection.py, 01_visualize_results.py | restaurants_merged.geojson |
| `taxi_hotspots.geojson` | 08_spatial_intersection.py, 01_visualize_results.py | taxi_dropoffs_weighted.parquet |
| `final_hotspots.geojson` | app.py, 01_visualize_results.py | dining_zones.geojson, taxi_hotspots.geojson |

---

## 四、配置文件依赖

### **config/config.yaml**

被以下所有处理脚本读取：
- `02_process_taxi_data.py` - 时间权重、CRS配置
- `06_cluster_restaurants.py` - HDBSCAN参数、缓冲距离
- `07_cluster_taxi_dropoffs.py` - HDBSCAN参数、H3配置
- `08_spatial_intersection.py` - 过滤阈值

**关键配置项:**
```yaml
clustering:
  restaurants:
    min_cluster_size: 30
    min_samples: 10
    cluster_selection_epsilon: 200  # meters

  taxi:
    min_cluster_size: 50
    min_samples: 15
    cluster_selection_epsilon: 250  # meters

temporal:
  weights:
    weekend_dinner: 1.5
    weekday_dinner: 1.0
    weekday_lunch: 0.8
    breakfast: 0.5

intersection:
  min_area_sqm: 10000
  min_overlap_ratio: 0.15
```

---

## 五、第三方库依赖

### 5.1 核心数据处理
```
pandas>=2.0.0          # 数据框架
numpy>=1.24.0          # 数值计算
geopandas>=0.14.0      # 地理空间数据
shapely>=2.0.0         # 几何操作
pyproj>=3.6.0          # 投影转换
```

### 5.2 机器学习
```
hdbscan>=0.8.33        # 密度聚类
scikit-learn>=1.3.0    # 验证指标
scipy>=1.10.0          # KDTree空间索引
```

### 5.3 数据加载
```
pyarrow>=12.0.0        # Parquet文件支持
fiona>=1.9.0           # Shapefile支持
```

### 5.4 Web与可视化
```
flask>=2.3.0           # Web框架
folium>=0.14.0         # 交互式地图
```

### 5.5 优化库（可选）
```
pandarallel>=1.6.0     # 并行pandas操作
h3>=3.7.6              # 六边形空间索引
rtree>=1.0.1           # R-tree空间索引
```

---

## 六、执行顺序约束

### 6.1 必须顺序执行

```
1. 02_process_taxi_data.py        ← 必须最先执行
   │
2. 02_merge_restaurants.py        ← 可与步骤1并行
   │
   ├─→ 3. 06_cluster_restaurants.py
   │
   └─→ 4. 07_cluster_taxi_dropoffs.py  ← 步骤3、4可并行
   │
5. 08_spatial_intersection.py     ← 必须在步骤3、4完成后
```

### 6.2 可选执行

- `01_visualize_results.py` - 任何时候（需要processed数据）
- `app.py` - 任何时候（需要final_hotspots.geojson）

---

## 七、缓存机制

### **cache/** 目录

包含若干 `.json` 缓存文件（哈希命名），用于：
- API请求缓存（可能来自Google Maps API）
- 中间计算结果缓存

**依赖情况:** 无直接代码依赖，系统透明管理

---

## 八、依赖关系总结

### 8.1 强依赖（必需）

```
run_pipeline.py
  ↓
  ├─ config/config.yaml
  ├─ src/utils/config_loader.py
  ├─ data/raw/* (所有原始数据)
  └─ data/external/boundaries/*.shp

app.py
  ↓
  └─ data/processed/final_hotspots.geojson
```

### 8.2 弱依赖（可选）

```
src/analysis/isochrone.py
  ↓ (可选)
  └─ data/processed/networks/*.gpickle

01_visualize_results.py
  ↓ (可选)
  └─ data/processed/*.geojson
```

### 8.3 无依赖（独立）

- `templates/index.html` - 纯HTML模板
- `docs/*.md` - 文档文件
- `outputs/*` - 输出目录

---

## 九、依赖破坏风险分析

### 高风险依赖

| 如果删除/损坏... | 影响范围 |
|----------------|---------|
| `config/config.yaml` | 🔴 **所有处理脚本失败** |
| `src/utils/config_loader.py` | 🔴 **所有处理脚本失败** |
| `data/interim/taxi_dropoffs_weighted.parquet` | 🔴 Phase 4-5失败 |
| `data/interim/restaurants_merged.geojson` | 🔴 Phase 3失败 → Phase 5失败 |
| `data/processed/final_hotspots.geojson` | 🔴 Web应用无法启动 |

### 中风险依赖

| 如果删除/损坏... | 影响范围 |
|----------------|---------|
| `data/external/boundaries/taxi_zones.shp` | 🟡 Phase 1失败（LocationID转换） |
| `data/processed/dining_zones.geojson` | 🟡 Phase 5失败 |
| `data/processed/taxi_hotspots.geojson` | 🟡 Phase 5失败 |

### 低风险依赖

| 如果删除/损坏... | 影响范围 |
|----------------|---------|
| `01_visualize_results.py` | ⚪ 仅可视化失败 |
| `src/analysis/isochrone.py` | ⚪ 无影响（未使用） |
| `cache/*.json` | ⚪ 仅性能下降，需重新计算 |

---

## 十、依赖优化建议

### 10.1 模块化改进

**当前问题:** 聚类代码在各脚本中重复实现

**建议:** 统一使用 `src/analysis/clustering.py`
```python
# 替代当前内嵌的HDBSCAN代码
from src.analysis.clustering import cluster_restaurants, cluster_taxi_dropoffs
```

### 10.2 配置管理

**当前:** 硬编码文件路径

**建议:** 全部路径通过配置管理
```python
# 替代 "data/interim/taxi_dropoffs_weighted.parquet"
from src.utils.config_loader import get_data_path
input_path = get_data_path("interim.taxi_filtered")
```

### 10.3 依赖注入

**当前:** run_pipeline.py直接调用subprocess

**建议:** 使用函数导入
```python
# 替代 subprocess.run([sys.executable, script_path])
from src.data_processing.process_taxi import main as process_taxi
process_taxi()
```

---

## 十一、依赖关系快速查询

### 问："如果我修改了餐厅数据，需要重新运行哪些脚本？"

**答:**
```
1. 02_merge_restaurants.py           (重新合并)
2. 06_cluster_restaurants.py         (重新聚类)
3. 08_spatial_intersection.py        (重新求交)
```

### 问："如果我只想更新Web应用显示效果，需要重新处理数据吗？"

**答:** 不需要，只需修改：
- `app.py` (后端逻辑)
- `templates/index.html` (前端展示)

### 问："如果我修改了聚类参数，会影响哪些输出？"

**答:**
- 修改 `clustering.restaurants.*` → 影响 `dining_zones.geojson` → 影响 `final_hotspots.geojson`
- 修改 `clustering.taxi.*` → 影响 `taxi_hotspots.geojson` → 影响 `final_hotspots.geojson`

---

## 十二、依赖检查清单

### 启动前检查
```bash
# 1. 配置文件
✓ config/config.yaml

# 2. 原始数据
✓ data/raw/taxi/*.parquet (12个文件)
✓ data/raw/restaurants/restaurants_nyc_googlemaps.csv
✓ data/raw/restaurants/restaurants_nyc_osm.csv

# 3. 边界数据
✓ data/external/boundaries/nybb.shp
✓ data/external/boundaries/taxi_zones.shp

# 4. Python环境
✓ requirements.txt 中所有库已安装
```

### 运行后检查
```bash
# Phase 1输出
✓ data/interim/taxi_dropoffs_weighted.parquet

# Phase 2输出
✓ data/interim/restaurants_merged.geojson

# Phase 3输出
✓ data/processed/dining_zones.geojson
✓ data/processed/restaurants_clustered.geojson

# Phase 4输出
✓ data/processed/taxi_hotspots.geojson

# Phase 5输出（最终）
✓ data/processed/final_hotspots.geojson
```

---

**文档版本:** v1.0
**最后更新:** 2025-11-17
**维护者:** WHERE-TO-DINE Project Team
