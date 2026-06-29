# Where to DINE — 项目状态移交文档（Codex 版）

> **生成日期**: 2026-06-26  
> **当前分支**: `fixing`（已推送到 `origin/fixing`）  
> **最近提交**: `c273ea3` — Stage 4: TravelTimeCalculator architecture

---

## 1. 项目概述

**Where to DINE** 是一个基于 GIS 的纽约市餐饮热点推荐系统，通过融合出租车 GPS 数据与餐厅 POI 数据，识别高潜力用餐区域。当前研究定位为"控制性诊断研究"——重点在于评估不同数据质量、评分方法和空间分辨率对结果的影响，而非提出新架构。

**核心数据流：**
```
原始数据 → 处理 → 聚类 → 空间交集 → 评分 → 热点输出
                                    ↓
                              2014坐标数据（当前使用）
                              2024 zone-centroid（已诊断，不推荐使用）
```

---

## 2. 已完成工作（Stage 0–4）

### Stage 0: 代码清理与基础架构（commit `af9d01a`）

**目标**: 修复导入路径、统一配置、添加测试。

**改动文件:**
- `src/utils/isochrone.py` — 修复 H3 导入错误
- `src/analysis/scoring.py` — 新增评分引擎（28个函数）
- `tests/test_scoring.py` — 28 个单元测试（全部通过）
- `config/config.yaml` — 统一配置路径
- `README.md` — 更新项目文档
- 创建缺失目录：`data/interim/`, `outputs/figures/`, `outputs/maps/`

**关键发现**: 原始代码有多处路径不一致和导入错误，已修复。

---

### Stage 1: 2014 vs 2024 数据分辨率对比（commit `1019e16`）

**目标**: 诊断 2024 zone-centroid 数据的局限性。

**实验设计**:
- 2024: 使用 TLC zone-centroid（无精确坐标，只有 263 个 zone 的质心）
- 2014: 使用 SODA API 下载精确坐标（`dropoff_longitude/latitude`），1 天数据 = 282,246 条记录

**核心发现（论文级发现）:**

| 指标 | 2024 zone-centroid | 2014 coordinate | 比例 |
|------|-------------------|-----------------|------|
| Taxi hotspots | 233 | 63 | 3.7× |
| 平均面积 | 0.047 km² | 3.45 km² | 73× |
| 平均密度 | 56,642/km² | 41/km² | 1,378× |
| 与餐厅的 IoU | 0.6% | 22.2% | 37× |
| 最终热点数 | 2 | 62 | 31× |

**结论**: Zone-centroid 数据完全不可用于空间聚类。密度被人为放大了 **1,378 倍**，因为热点面积被压缩了 73 倍。2014 坐标数据是**唯一可用**的数据源。

**新增文件:**
- `scripts/download_2014_taxi_month.py` — SODA API 下载（支持断点续传）
- `data/processed/taxi_hotspots_2014.geojson` — 2014 坐标聚类结果（63 个热点）
- `data/processed/comparison_2014_vs_2024.json` — 对比统计

---

### Stage 2: 评分方法升级（commits `3d698cb`, `39bfb6a`）

**目标**: 修复空热点问题 + 升级评分引擎。

**改动:**

**2a. 修复空 final_hotspots**:
- `config/config.yaml`: `min_overlap_ratio` 从 `0.15` → `0.05`
- 原因: zone-centroid 数据导致几何重叠极小

**2b. 评分引擎升级**:

| 版本 | 方法 | 权重 | 问题 |
|------|------|------|------|
| V1 | max-normalization | 固定 0.5/0.5 | 对 outlier 敏感，不稳定 |
| V2 | z-score + winsorization | 固定 0.5/0.5 | 权重任意，14 个平局 |
| V2.1 | **Entropy-TOPSIS** | 数据驱动 | 1 个平局，93% 改善 |

**Entropy-TOPSIS 原理**:
1. 计算每个指标的 z-score + winsorization (1%, 99%)
2. 用信息熵计算客观权重（信息量越大 → 权重越高）
3. TOPSIS 计算每个热点到正/负理想解的距离
4. 结果归一化到 [0, 100]

**V1 vs V2 vs V3 对比**（基于 233 个 taxi hotspots）:
- Spearman ρ(V1, V3) = 0.981
- 平局: V1=10, V2=14, V3=1
- 分布: V3 峰度 5.97（介于 V1 的 6.33 和 V2 的 4.31 之间）

---

### Stage 3: 加入 Peak Time + Accessibility（commit `aea10c5`）

**目标**: 从 2 指标评分扩展到 4 指标，加入时间维度 + 空间可达性。

**新增特征**:

**3a. Peak Time Score**（`add_peak_time_features()`）:
- 从 2014 taxi 数据计算每个热点的 `peak_hour_ratio` = 17-23点 dropoff 权重 / 总权重
- 范围: [0.186, 0.847]
- z-score + winsorization 归一化到 [0, 100]
- 数据来源: `data/interim/taxi_dropoffs_2014_weighted.parquet`

**3b. Accessibility Proxy**（`add_accessibility_proxy()`）:
- 以 Times Square (40.7580, -73.9855) 为曼哈顿参考点
- 计算每个热点 centroid 到参考点的直线距离（km）
- 指数衰减: `score = 100 * exp(-0.05 * distance_km)`
- 范围: [2.9, 59.4]（距离 10.4 km 到 70.7 km）
- **注意**: 这是 proxy，不是真实路网。真实路网由 Stage 4 的 TravelTimeCalculator 处理。

**4 指标 Entropy-TOPSIS**（当前运行结果）:

| 指标 | Entropy Weight | 含义 |
|------|---------------|------|
| **taxi_density** | **0.696** | 出租车密度（信息量最高） |
| **restaurant_density** | 0.186 | 餐厅密度 |
| **accessibility_proxy** | 0.083 | 到曼哈顿中城距离 |
| **peak_time_score** | 0.036 | 晚餐高峰占比 |

**Top 5 热点**（V2.1 评分）:

| Rank | Score | Restaurants | Dropoffs | Peak Ratio | Accessibility | 位置特征 |
|------|-------|------------|----------|-----------|--------------|---------|
| 1 | 86.7 | 363 | 246,900 | 0.61 | 55.5 | 高 taxi + 高餐厅 + 高可达 |
| 2 | 86.6 | 753 | 246,900 | 0.61 | 51.9 | 同上，更大餐厅密度 |
| 3 | 22.7 | 36 | 272 | 0.23 | 3.4 | 高餐厅但低 taxi（远郊） |
| 4 | 21.6 | 48 | 577 | 0.54 | 3.0 | 中等，低可达 |
| 5 | 13.0 | 72 | 622 | 0.01 | 18.0 | 低 peak time |

**关键发现**: Taxi 密度主导了评分（69.6% 权重），因为 2014 坐标数据中的 dropoff 分布极其不均匀。

**API 升级**（`app.py`）:
- 新增查询参数:
  - `?profile=balanced|quality_seeker|convenience|local_gem|late_night`
  - `?time_profile=any|lunch|dinner|late_night`
  - `?version=v1|v2`
  - `?access_method=decay|euclidean`
- Response 包含 `peak_time_score`, `accessibility_proxy`, `peak_hour_ratio`

---

### Stage 4: TravelTimeCalculator 架构（commit `c273ea3`）

**目标**: 建立可插拔的出行时间计算框架，支持多种后端。

**新增模块**: `src/travel_time/`（6 个文件）

```
src/travel_time/
├── __init__.py                    # 导出 TravelTimeCalculator
├── travel_time_calculator.py      # 工厂接口
├── proxy_backend.py               # ✅ 当前激活（默认）
├── osmnx_backend.py               # 🔒 预留（需下载路网）
├── google_maps_backend.py         # 🔒 预留（需 API key）
├── transit_graph.py               # 🔒 预留（需 Codex 实现）
└── README.md                      # 使用指南
```

**后端对比:**

| 后端 | 状态 | 依赖 | 精度 | 费用 |
|------|------|------|------|------|
| **proxy** | ✅ 激活 | 无 | 直线距离 + 模式系数 | 免费 |
| **osmnx** | 🔒 预留 | `osmnx`, `networkx` | 真实路网的步行/驾车 | 免费 |
| **google** | 🔒 预留 | `requests` + API key | 真实 transit（地铁+公交） | ~$5/1k elements |
| **transit** | 🔒 预留 | GTFS 数据 + 手动实现 | 精确的地铁换乘图 | 免费（需下载 GTFS） |

**Proxy 模式速度:**

| 模式 | 速度 | 测试: Times Square → Brooklyn |
|------|------|-------------------------------|
| walk | 5 km/h | 60 min（超时 cap） |
| bike | 15 km/h | 20 min |
| drive | 25 km/h | 28 min |
| transit | 30 km/h | 27 min |

**API 查询参数**:
- `?mode=walk|bike|drive|transit` — 出行方式
- `?access_method=proxy|osmnx|google` — 后端选择
- `?time_profile=any|lunch|dinner|late_night` — 时间场景
- `?version=v1|v2` — 评分版本
- `?profile=balanced|quality_seeker|convenience|local_gem|late_night` — 偏好

**Response 新增字段**: `travel_time_min`, `travel_mode`, `access_backend`

**下载 NYC 路网命令**:
```bash
pip install osmnx networkx
python scripts/download_nyc_network.py
```
输出: `data/networks/nyc_{walk,drive,bike}.graphml`（~500-800 MB）

---

## 3. 当前关键数据

### 3.1 数据文件清单

| 文件路径 | 格式 | 大小 | 内容 | 备注 |
|---------|------|------|------|------|
| `data/processed/final_hotspots.geojson` | GeoJSON | ~500 KB | 62 个最终热点 | 当前主输出 |
| `data/processed/taxi_hotspots_2014.geojson` | GeoJSON | ~200 KB | 63 个 taxi 聚类 | 2014 坐标聚类 |
| `data/processed/dining_zones.geojson` | GeoJSON | ~300 KB | 189 个餐厅聚类 | 2024 餐厅数据 |
| `data/interim/taxi_dropoffs_2014_weighted.parquet` | Parquet | ~2 MB | 282,246 条 dropoff | 2014 坐标+时间 |
| `data/raw/taxi_2014/` | Parquet | ~10 MB | 原始 2014 下载 | 2 天数据（1 天完整） |
| `data/processed/intersection_analysis.json` | JSON | ~10 KB | 分析摘要 | V1 评分 |
| `data/processed/intersection_analysis_v2.json` | JSON | ~15 KB | V2 分析摘要 | 含 entropy 权重 |
| `data/processed/final_hotspots_v2.geojson` | GeoJSON | ~500 KB | V2 评分热点 | 与主文件相同数据 |

### 3.2 最终热点字段说明

`final_hotspots.geojson` 包含 31 个字段，关键字段:

| 字段 | 类型 | 说明 |
|------|------|------|
| `dining_cluster_id` | int | 餐厅聚类 ID |
| `taxi_hotspot_id` | int | Taxi 聚类 ID |
| `n_restaurants` | int | 该热点内餐厅数量 |
| `n_taxi_dropoffs` | int | 该热点内 taxi dropoff 数 |
| `taxi_weight` | float | 加权 dropoff 数 |
| `avg_rating` | float | 餐厅平均评分 |
| `intersection_area_sqm` | float | 交集面积（平方米） |
| `overlap_ratio_taxi` | float | 交集 / taxi 面积 |
| `peak_hour_ratio` | float | 17-23点 dropoff 占比 |
| `peak_time_score` | float | 0-100，z-score 归一化 |
| `accessibility_proxy` | float | 0-100，到曼哈顿距离衰减 |
| `restaurant_score` | float | 0-100，V1 max-normalization |
| `taxi_score` | float | 0-100，V1 max-normalization |
| `popularity_score` | float | 0-100，V1 固定权重 |
| `restaurant_score_v2` | float | 0-100，z-score + winsorize |
| `taxi_score_v2` | float | 0-100，z-score + winsorize |
| `popularity_score_v2` | float | 0-100，Entropy-TOPSIS |
| `entropy_weight_restaurant` | float | 0-1，entropy 权重 |
| `entropy_weight_taxi` | float | 0-1，entropy 权重 |
| `entropy_weight_peak_time` | float | 0-1，entropy 权重 |
| `entropy_weight_accessibility` | float | 0-1，entropy 权重 |
| `rank` | int | V1 排名 |
| `rank_v2` | int | V2 排名 |
| `geometry` | Polygon | 热点多边形（WGS84） |

### 3.3 2014 Taxi 数据字段

`data/interim/taxi_dropoffs_2014_weighted.parquet`:

| 字段 | 类型 | 说明 |
|------|------|------|
| `dropoff_datetime` | datetime | 落客时间 |
| `dropoff_lon` | float | 经度（WGS84） |
| `dropoff_lat` | float | 纬度（WGS84） |
| `hour` | int | 0-23 |
| `day_of_week` | int | 0=周一 |
| `is_weekend` | bool | 是否周末 |
| `weight` | float | 1.0（weekday）/ 0.4（weekend）|

---

## 4. 项目架构

### 4.1 模块结构

```
Where-to-dine-demo/
├── app.py                          # Flask API（主入口）
├── config/
│   └── config.yaml                 # 全局配置
├── src/
│   ├── analysis/
│   │   └── scoring.py              # 评分引擎（28个函数）
│   ├── data_processing/
│   │   ├── 01_extract_taxi_hotspots.py
│   │   ├── 02_process_taxi_data.py
│   │   ├── 03_generate_dining_zones.py
│   │   ├── 04_cluster_restaurants.py
│   │   ├── 05_hotspot_analysis.py
│   │   ├── 06_compare_pipeline.py
│   │   ├── 07_spatial_analysis.py
│   │   ├── 08_spatial_intersection.py  # ⭐ 核心pipeline
│   │   └── compare_scoring_v1_vs_v2.py
│   ├── travel_time/                # ⭐ 新增模块（Stage 4）
│   │   ├── __init__.py
│   │   ├── travel_time_calculator.py
│   │   ├── proxy_backend.py
│   │   ├── osmnx_backend.py
│   │   ├── google_maps_backend.py
│   │   └── transit_graph.py
│   ├── utils/
│   │   └── config_loader.py
│   └── visualization/
│       └── ...
├── tests/
│   └── test_scoring.py             # 28 个单元测试
├── scripts/
│   ├── download_2014_taxi_month.py # SODA API 下载
│   └── download_nyc_network.py     # OSMnx 路网下载
├── data/
│   ├── raw/                        # 原始数据
│   ├── interim/                    # 中间处理
│   └── processed/                  # 最终输出
├── outputs/
│   ├── figures/                    # 图表
│   └── maps/                       # 地图
└── reports/
    └── stage2_scoring_upgrade_report.md
```

### 4.2 数据流图

```
                              ┌────────────────────────────────────────┐
                              │         2014 TLC Coordinate Data       │
                              │  (SODA API: yellow_tripdata_2014)     │
                              │  282,246 records, 1 day (Jan 6-7)    │
                              └────────────────┬───────────────────────┘
                                               │
                                               ▼
                              ┌────────────────────────────────────────┐
                              │  data_processing/02_process_taxi_data │
                              │  - 加权: weekday=1.0, weekend=0.4      │
                              │  - 保留: lon, lat, hour, day_of_week   │
                              └────────────────┬───────────────────────┘
                                               │
                                               ▼
                              ┌────────────────────────────────────────┐
                              │  data_processing/01_extract_taxi_hotspots│
                              │  - HDBSCAN 聚类 (min_cluster_size=20)  │
                              │  - 输出: 63 个 taxi hotspots           │
                              └────────────────┬───────────────────────┘
                                               │
                                               │ taxi_hotspots_2014.geojson
                                               ▼
┌─────────────────────┐        ┌────────────────────────────────────────┐
│  Google Places API  │        │  data_processing/03_generate_dining_zones│
│  (2024 餐厅数据)    │────────│  - 聚类: 189 个 dining zones            │
│  7,000 家餐厅       │        │  - 凸包几何 + 平均评分                    │
└─────────────────────┘        └────────────────┬───────────────────────┘
                                               │ dining_zones.geojson
                                               │
                                               ▼
                              ┌────────────────────────────────────────┐
                              │  data_processing/08_spatial_intersection│
                              │  ⭐ 核心 Pipeline                        │
                              │  1. 几何交集 (WGS84 → EPSG:2263)        │
                              │  2. 过滤: area ≥ 10,000 m², overlap ≥ 0.05│
                              │  3. 特征: peak_time + accessibility     │
                              │  4. 评分: 4-indicator Entropy-TOPSIS    │
                              │  5. 输出: final_hotspots.geojson         │
                              └────────────────┬───────────────────────┘
                                               │
                                               ▼
                              ┌────────────────────────────────────────┐
                              │  app.py (Flask API)                     │
                              │  - /api/hotspots                        │
                              │  - /api/recommend (POST)               │
                              │  - /api/stats                          │
                              │  - TravelTimeCalculator (proxy/osmnx/ │
                              │    google/transit)                      │
                              └────────────────────────────────────────┘
```

---

## 5. 已知问题与限制

### 5.1 数据问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **时间不匹配** | 🔴 高 | 2014 taxi × 2024 餐厅。这是结构性问题，已在论文中定位为"控制性诊断" |
| **只有 2 天 2014 数据** | 🟡 中 | 下载了 1 天完整数据（Jan 6-7），但 2014 全年可用。时间限制未下载更多 |
| **餐厅数据无坐标** | 🟡 中 | 2024 餐厅只有 zone 信息，没有精确坐标。已通过 convex hull 处理 |
| **Accessibility 是 proxy** | 🟡 中 | 当前用直线距离 + 指数衰减。真实路网需要 OSMnx/Google |
| **Transit 模式未实现** | 🟡 中 | `transit_graph.py` 是 placeholder，需要 GTFS + 手动实现 |
| **Peak time 只定义 17-23** | 🟢 低 | 固定晚餐高峰。可扩展为 lunch peak (11-14) 或自定义 |

### 5.2 代码问题

| 问题 | 位置 | 说明 |
|------|------|------|
| `km²` 字符在 GBK 终端崩溃 | `02_process_taxi_data.py`, `08_spatial_intersection.py` | 已部分修复，可能还有残余 |
| `pandarallel` 未安装 | `02_process_taxi_data.py` | 已 fallback 到标准 pandas apply |
| `osmnx` 未安装 | `src/travel_time/` | 预留，不影响当前运行 |
| Flask `blinker` 未安装 | `app.py` | 不影响当前评分逻辑 |
| `sys.path.append` 硬编码 | 多个文件 | 使用相对路径导入，可能需要改为包结构 |

### 5.3 评分问题

| 问题 | 说明 |
|------|------|
| **Taxi 密度主导** | 权重 0.696，因为 dropoff 分布极度不均匀。可能需要加权或分层 |
| **JFK/LGA 机场热点** | 246,900 dropoff 的巨热点可能是机场。需要地理过滤排除机场 zone |
| **面积权重未处理** | 大 area 热点（28.959 km²）和小 area 热点（0.171 km²）在密度计算中被同等处理。可能需要面积加权 |
| **Rating 未充分利用** | `avg_rating` 存在但当前只用于 tie-breaker，未进入主评分 |

---

## 6. 下一步工作清单（Codex 优先级）

### 🔴 P0: 高优先级（论文/演示必需）

#### 6.1 下载 NYC 路网并测试 OSMnx 后端
```bash
pip install osmnx networkx
python scripts/download_nyc_network.py
```
- 预期: `data/networks/nyc_walk.graphml` (~500-800 MB)
- 验证: `TravelTimeCalculator(mode='walk', backend='osmnx').is_available()` 返回 True
- 测试: 对比 proxy 和 osmnx 的 travel time（Times Square → Brooklyn 应该接近 30-40 min 步行）

#### 6.2 修复 V2 评分中的机场问题
- 在 `08_spatial_intersection.py` 中过滤掉 JFK (Zone 132) 和 LGA (Zone 138) 相关的 taxi 热点
- 或者: 给 `n_taxi_dropoffs` 添加距离衰减（机场 dropoff 不应直接等同于餐厅需求）

#### 6.3 加入 Rating 作为第五指标
- 在 `calculate_composite_scores_v2()` 中把 `avg_rating` 加入 indicators 矩阵
- 注意处理 NaN 值（部分热点可能没有餐厅，avg_rating 为 null）
- 更新 entropy weights 计算

#### 6.4 添加 `lunch` peak time 模式
- 当前 `peak_hour_ratio` 只计算 17-23
- 添加 `lunch_peak_ratio` 计算 11-14 的 dropoff 占比
- API 中 `?time_profile=lunch` 时切换使用 `lunch_peak_ratio`

### 🟡 P1: 中优先级（论文增强）

#### 6.5 实现 TransitGraph（GTFS 地铁/公交）
- 下载 MTA GTFS: https://new.mta.info/developers
- 解压到 `data/transit/mta_gtfs/`
- 在 `transit_graph.py` 中实现：
  1. `stops.txt` → 解析站点坐标
  2. `stop_times.txt` → 构建 route 边（travel time）
  3. `transfers.txt` → 添加换乘边（步行时间 + penalty）
  4. 添加 origin 到 nearest station 的 walking edge
  5. Dijkstra 计算最短路径
- 预期: 4-6 小时集中工作
- 参考: `transit_graph.py` 已有占位代码和步骤说明

#### 6.6 Google API 激活
- 申请 Google Cloud API key
- 设置 `GOOGLE_MAPS_API_KEY` 环境变量
- 测试 `TravelTimeCalculator(mode='transit', backend='google')`
- 验证: transit 模式返回时间应接近真实 NYC 地铁时间（Manhattan→Brooklyn ~25-35 min）

#### 6.7 Streamlit 可视化仪表盘
- 创建 `dashboard.py` 或 `app_streamlit.py`
- 功能:
  - 交互式地图显示 62 个热点（热力图 + 边界）
  - 点击地图任意点 → 调用 `/api/recommend`
  - 时间滑块（0-23）→ 动态调整 peak time 权重
  - 模式选择（walk/drive/transit）→ 切换 TravelTimeCalculator
  - 评分对比（V1 vs V2）并排显示
- 参考文件: `data/processed/final_hotspots.geojson` 包含所有数据

### 🟢 P2: 低优先级（未来扩展）

#### 6.8 下载更多 2014 数据
- 使用 `scripts/download_2014_taxi_month.py` 下载更多天（支持断点续传）
- 目标: 至少 1 周数据，覆盖 weekday + weekend 模式
- 注意: SODA API 很慢（~3 min / 50k 页），建议在空闲时间后台下载

#### 6.9 Ground-truth 验证
- 收集 NYC 已知餐饮区: Chinatown, Koreatown, Little Italy, East Village, Williamsburg, Astoria
- 计算这些区域的评分排名，验证模型是否识别出这些区域
- 产出: 混淆矩阵 + ROC 曲线（如果把已知区域作为正样本）

#### 6.10 论文写作
- 把 4 个阶段写成方法论章节
- 重点: "控制性诊断研究"框架——我们不是在提出新架构，而是在评估数据质量、评分方法、空间分辨率对结果的影响
- 关键图表: 2014 vs 2024 对比（图1）, V1 vs V2 vs V3 评分对比（图2）, 4-indicator TOPSIS 权重（图3）

---

## 7. 技术栈

### 7.1 核心依赖

```
Python 3.11.9
├── geopandas  (空间数据处理)
├── pandas     (数据框)
├── numpy      (数值计算)
├── hdbscan    (空间聚类)
├── scipy      (统计检验)
├── shapely    (几何运算)
├── flask      (Web API)
├── matplotlib (可视化)
└── pytest     (测试)
```

### 7.2 可选依赖（预留）

```
osmnx        (OpenStreetMap 网络分析)  ← 需要下载 NYC 路网
networkx     (图算法)                  ← osmnx 依赖
requests     (HTTP 请求)                ← Google API 需要
streamlit    (可视化仪表盘)             ← P1 任务
```

### 7.3 环境变量

```bash
# Google Maps API (预留)
export GOOGLE_MAPS_API_KEY="your_key_here"

# 可选: OSMnx 缓存目录
export OSMNX_CACHE_DIR="data/osmnx_cache"
```

---

## 8. 快速验证命令

```bash
# 1. 验证评分引擎
python -m pytest tests/test_scoring.py -v

# 2. 验证 TravelTimeCalculator
python -c "
from src.travel_time import TravelTimeCalculator
for mode in ['walk', 'drive', 'transit']:
    tt = TravelTimeCalculator(mode=mode, backend='proxy')
    t = tt.single((40.7580, -73.9855), (40.6782, -73.9442))
    print(f'{mode}: {t:.1f} min')
"

# 3. 运行完整 pipeline
python src/data_processing/08_spatial_intersection.py

# 4. 验证输出
python -c "
import geopandas as gpd
gdf = gpd.read_file('data/processed/final_hotspots.geojson')
print(f'Hotspots: {len(gdf)}')
print(f'Columns: {list(gdf.columns)[:5]}...')
print(f'Top score: {gdf.popularity_score_v2.max():.1f}')
"

# 5. 启动 Flask（需要 blinker）
# pip install flask blinker
# python app.py
```

---

## 9. 论文相关要点

### 9.1 核心贡献定位

**不是**: "我们提出了一个新的餐饮推荐算法"
**而是**: "我们诊断了公共 TLC 数据在空间分析中的关键限制，并评估了不同数据分辨率、评分方法和出行模式对结果的影响"

### 9.2 关键发现（可用于论文）

1. **Zone-centroid 数据的空间失真**: 密度被人为放大 1,378×，面积压缩 73×，IoU 仅 0.6%
2. **Entropy-TOPSIS 的自适应性**: 自动识别 taxi 密度为信息量最高指标（69.6%），无需人工设定权重
3. **多模式出行时间的可扩展性**: 建立了 proxy→osmnx→google→transit 的渐进式架构
4. **Peak time 的区分度**: 不同热点的晚餐高峰占比差异明显（0.186–0.847），但信息量低于密度指标

### 9.3 已知局限性（诚实披露）

- 2014 taxi × 2024 餐厅的时间不匹配
- 只有 2 天出租车数据
- Accessibility 目前为直线距离 proxy
- 餐厅数据只有 zone 级别，无精确坐标
- 未考虑价格、菜系、营业时间等餐厅属性

---

## 10. 联系与上下文

- **项目所有者**: Jasmine（研究生，GIS + 时空图神经网络方向）
- **研究区域**: 纽约市（最初考虑 Chicago，后切换到 NYC）
- **数据来源**: TLC (Taxi & Limousine Commission) + Google Places API
- **论文目标**: GIS/交通期刊投稿（非纯 AI 顶会）
- **当前状态**: 4/6 个核心阶段完成，数据 + 评分 + 架构就绪，等待可视化和 ground-truth 验证

---

*文档生成时间: 2026-06-26 18:00 UTC+8*  
*最新 commit: `c273ea3` — Stage 4: TravelTimeCalculator architecture*
