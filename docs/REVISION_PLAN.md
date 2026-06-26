# Where to DINE — 重构与完善计划

> **目标**：将本项目从「课程作业demo」升级为「可写入简历的portfolio-grade作品」，以"高德扫街榜"为产品灵感，构建一个 uncertainty-aware 的 NYC 餐饮区域发现系统。
>
> **核心故事**：诊断公开出租车数据的空间分辨率限制 → 引入2014坐标级数据做对比实验 → 重构评分算法与可达性分析 → 产出可交互的WebGIS demo。

---

## 1. 现状诊断（清理前必须先看清问题）

### 1.1 数据层面

| 问题 | 详情 | 影响 |
|------|------|------|
| **数据不同步** | `intersection_analysis.json` 报告 `n_hotspots=0`，但 `final_hotspots.geojson` 有 ~14 个 features | processed 输出由不同运行或手动编辑产生，pipeline不可复现 |
| ** spatial resolution 天花板** | 2024 Yellow Taxi 只有 `DOLocationID`，无真实坐标；当前映射到 zone centroid | 同一个 zone 的所有 drop-off 坍缩为一个点，clustering 和 ranking 的精度被人为高估 |
| ** restaurant 数据未验证** | Google Maps + OSM 合并后有 `restaurants_merged.geojson`，但去重逻辑未公开验证 | 可能存在同一餐厅的重复记录 |
| **缺失 ground truth 标注** | `validation.known_districts` 在 config 里只有5个粗略坐标点 | 无法做系统的定量验证 |

### 1.2 算法与代码层面

| 问题 | 位置 | 详情 |
|------|------|------|
| **Max normalization 不稳定** | `08_spatial_intersection.py` 第266-278行 | `restaurant_score = 100 * density / max(density)`，一个 outlier 就能压扁所有其他分数 |
| **Accessibility 依赖当前结果集** | `app.py` 第161-165行 | `accessibility_score = 100 * (1 - distance_km / max_dist)`，同一个 hotspot 在不同查询中得分不同 |
| **Ranking 同分严重** | `08_spatial_intersection.py` 第287行 | 使用 `method='dense'`，大量热点同分，缺乏有效 tie-breaker |
| **HDBSCAN 不处理 weight** | `clustering.py` 第235-243行 | 注释承认标准 HDBSCAN 不支持 sample weights，temporal weight 实际上未真正融入聚类 |
| **isochrone 模块与 demo 脱节** | `isochrone.py` vs `app.py` | isochrone 用 OSMnx/NetworkX 做网络 travel time，但 Flask app 只用欧氏距离，两者未连接 |
| **isochrone.py bug** | `isochrone.py` 第227行 | `calculate_multiple_isochrones` 使用 `pd.concat`，但模块顶部没有 `import pandas as pd` |
| **路径不匹配** | `isochrone.py` 默认路径 vs `config.yaml` | 默认 `network_walk.gpickle` 与 `config.yaml` 中 `network_walk` 路径不一致 |
| **评分公式全写在 app.py 里** | `app.py` 第159-170行 | 没有独立的 `scoring.py` 模块，无法做单元测试和参数扫描 |

### 1.3 文档与结构层面

| 问题 | 详情 |
|------|------|
| **README 与仓库实际不符** | README 列了 `notebooks/`, `tests/`, `scripts/` 目录及 6 个 notebook，但仓库中全不存在 |
| **README 克隆地址错误** | 仍指向 `Where-to-dine-final-version`，但实际仓库是 `GE5226_WHERE-TO-DINE-DEMO` |
| **文档过度冗余** | 已有 `ACADEMIC_EVALUATION.md`, `NYC_2014_COORDINATE_TAXI_COMPARISON_PLAN.md`, `PROJECT_REFRAME_NOTES.md`, `TASK_CHECKLIST.md` 等大量文档，但核心代码实现不完整 |
| **缺少数据字典** | `data/processed/` 和 `data/interim/` 中的文件没有字段说明文档 |

---

## 2. 清理清单（Clean-up Checklist）

### 2.1 立即修复（不改变数据逻辑，只修 bug）

- [ ] **修复 `isochrone.py` 的 import bug**：在顶部添加 `import pandas as pd`
- [ ] **统一 network 路径**：将 `isochrone.py` 中的默认路径改为与 `config.yaml` 一致，或统一从 config 读取
- [ ] **标记 processed 数据状态**：在 `data/processed/` 下添加 `README.md`，说明哪些文件是 demo fixture（非自动生成的），并解释 `intersection_analysis.json` 与 `final_hotspots.geojson` 不一致的原因
- [ ] **创建缺失目录骨架**：新建 `notebooks/`, `tests/`, `scripts/` 目录（可放 `.gitkeep`），使目录结构与 README 一致
- [ ] **更新 README 克隆地址**：将 `https://github.com/Shi0v0Jasmine/Where-to-dine-final-version.git` 改为正确的仓库地址
- [ ] **在 README 中添加数据质量/方法局限性的诚实声明**：明确说明 2024 taxi 数据只有 zone-centroid，这是一个已知限制

### 2.2 移除或归档（不直接删除，先标记）

- [ ] **归档 `README_DEMO.md`**（如果存在且内容已合并到 README）
- [ ] **清理 `docs/` 中过期模板**：`PRESENTATION_SPEECH.md` 和 `PRESENTATION_GUIDE.md` 中如果有占位符（如 `[Your Name]`, `[Name]`），应标记为 TODO 或删除
- [ ] **检查 `data/raw/` 中是否有大文件未走 LFS**：如果 raw taxi parquet 被直接提交到 git 而未走 Git LFS，需要整理

---

## 3. 重构阶段（Reframe Roadmap）

> 以 **NYC 2014 Yellow Taxi 坐标数据** 为核心实验数据，保留 NYC 城市背景和现有餐厅数据框架，但全面升级方法论。

### Stage 0: 基础稳固（1-2 天）

**目标**：清理 bug、统一路径、建立可复现的 pipeline。

- [ ] 完成上述所有清理清单项
- [ ] 将 `app.py` 中的评分公式提取到新的 `src/analysis/scoring.py`
- [ ] 为 `scoring.py` 写单元测试（baseline 测试：完美可达、边界可达、不可达）
- [ ] 确保 `run_pipeline.py` 能从头到尾运行一遍（先验证现有数据，再逐步引入新数据）
- [ ] 提交一个清理 commit：`chore: fix isochrone import, unify paths, add data README`

### Stage 1: 2014 坐标数据引入与对比实验（3-5 天）

**目标**：用真实坐标数据跑通同一个 pipeline，证明 zone-centroid vs coordinate 的差异。

- [ ] **下载 2014 数据样本**：从 [NYC Open Data](https://data.cityofnewyork.us/Transportation/2014-Yellow-Taxi-Trip-Data/gkne-dk5s) 下载 1-2 个月（如 2014-01 或 2014-06），用 SODA API 或 CSV 下载，不必下全年
- [ ] **数据清洗**：过滤无效坐标（`dropoff_longitude/latitude` 为 0 或空值），过滤非 NYC 范围，过滤餐饮时段（11:00-14:00, 17:00-23:00）
- [ ] **复用现有 temporal weighting**：将 2014 坐标数据按 `dropoff_datetime` 打上同样的 temporal weight
- [ ] **运行对比 pipeline**：
  - Pipeline A（Baseline）：2024 zone-centroid（现有数据）
  - Pipeline B（Experiment）：2014 坐标级 drop-off 点
- [ ] **生成对比指标**：
  - Hotspot 数量、平均面积、紧致度
  - 与已知餐饮区的重叠率（Jaccard / IoU）
  - 2014 与 2024 输出之间的热点重叠率
  - 排名稳定性（Spearman 秩相关）
- [ ] **输出**：`notebooks/nyc_2014_vs_2024_comparison.ipynb` 或 `src/experiments/compare_2014_vs_2024.py`

**简历话术**：
> "Diagnosed spatial-resolution limits in public TLC zone-level data and validated the improvement with 2014 coordinate-level taxi data through a side-by-side A/B pipeline experiment."

### Stage 2: 评分算法重构（3-5 天）

**目标**：从 max-normalization + 固定加权，升级为 robust normalization + 多维度评分。

基于已有文献综述（`docs/literature/2026-06-scoring-accessibility-clustering-review.md`），新评分体系：

```
demand_score     = log1p(taxi_dropoffs) → z-score → winsorize(1%, 99%)
poi_score        = f(restaurant_density, rating_confidence, cuisine_diversity)
access_score     = exp(-lambda * travel_time_min)  # 固定衰减，不依赖当前结果集
confidence_score = data_quality_proxy(coordinate_precision, sample_size, temporal_coverage)

final_score = entropy_weighted_TOPSIS(demand_score, poi_score, access_score, confidence_score)
```

- [ ] **实现 `src/analysis/scoring.py`**：
  - `normalize_zscore_winsorize()`
  - `normalize_percentile()`
  - `compute_access_score_decay(travel_time, max_time=30, lambda=0.3)`
  - `compute_entropy_weights()`
  - `compute_topsis_rank()`
  - `compute_composite_score()`（保留旧版 baseline score 用于对比）
- [ ] **添加 tie-breaker**：travel_time → rating_confidence → review_count → restaurant_diversity
- [ ] **保留可配置的用户偏好模式**（受扫街榜启发）：
  - `quality_seeker`: 高 demand_score 权重
  - `convenience`: 高 access_score 权重
  - `local_gem`: 高 poi_score 中的小餐厅/高评分置信度
  - `late_night`: 高 temporal weight 在 22:00-02:00
- [ ] **对比实验**：输出旧版 vs 新版评分的排名差异，计算 Spearman ρ 和 Kendall τ
- [ ] **输出**：`notebooks/scoring_redesign_comparison.ipynb`

**简历话术**：
> "Redesigned the scoring algorithm from unstable max-normalization to a robust entropy-weighted TOPSIS framework with z-score winsorization, stable travel-time decay, and deterministic tie-breakers."

### Stage 3: 可达性升级（2-4 天）

**目标**：从欧氏距离升级为网络 travel time，接入 Flask demo。

**短期（必须做）**：
- [ ] **用 OSMnx 构建 NYC 步行网络**，预计算 travel time matrix（从用户候选点集到各 hotspot centroid）
- [ ] **将 OSMnx travel time 接入 Flask API**：在 `api/recommend` 中替换欧氏距离为 network shortest-path time
- [ ] **添加固定 accessibility decay**：`access_score = exp(-lambda * travel_time)`，其中 lambda 基于 15 分钟/30 分钟步行阈值校准
- [ ] **保留欧氏距离 fallback**：当网络数据缺失时优雅降级

**中期（可选，强烈建议）**：
- [ ] **评估 r5py**：用 OSM + GTFS 计算多模式（walk + transit）travel time matrix
- [ ] **如果 r5py 在 NYC 规模可行**，添加 transit 模式到 demo UI
- [ ] **输出**：`notebooks/accessibility_osmnx_vs_r5py.ipynb`

**简历话术**：
> "Upgraded accessibility measurement from Euclidean distance to OSMnx network-based travel time, with a planned r5py multimodal integration for walk + transit routing."

### Stage 4: H3 网格多源融合（3-4 天）

**目标**：统一空间单元，将 taxi、bike、POI 融合到同一分析框架。

- [ ] **将 taxi、bike、POI 投影到 H3 grid**（resolution 8-9，约 70-250m）
- [ ] **每格计算特征**：
  - `taxi_demand` = 加权 drop-off 数（log1p）
  - `bike_demand` = Citi Bike 终点到达数（log1p）
  - `poi_density` = 餐厅数 / 格面积
  - `rating_confidence` = Wilson score 或 review count proxy
  - `cuisine_diversity` = Shannon entropy of cuisine types
- [ ] **计算 mobility consensus**：`min(percentile(taxi), percentile(bike))` —— 两源都高才更可信
- [ ] **用 H3 热图替代/补充 HDBSCAN polygon**：
  - 在 H3 上跑 Getis-Ord Gi* 做统计显著性 hotspot 检测
  - 与 HDBSCAN cluster 结果做对比
- [ ] **输出**：`notebooks/h3_multisource_fusion.ipynb`

**简历话术**：
> "Designed a unified H3-hexagonal analysis grid to fuse taxi, bike-share, and POI signals, with a mobility-consensus score that cross-validates demand sources."

### Stage 5: Demo 与 UI 升级（2-3 天）

**目标**：从功能 demo 升级为有产品感的交互界面。

受**高德扫街榜**启发，产品核心概念：
- **真实行为 > 主观评分**：taxi drop-off 是 "用脚投票"
- **动态榜单**：支持时间维度切换（午餐榜、晚餐榜、周末榜、深夜榜）
- **分类发现**：不只给排名，给类别（如 "repeat-visit zones", "special-trip zones", "local gems", "late-night clusters"）
- **空间智能**：isochrone overlay 显示用户当前可达范围

- [ ] **重构前端**：从纯 Flask 模板升级为 **Streamlit + PyDeck/Folium**（开发更快，map 交互更现代）
  - 或者保留 Flask 后端，但用更好的前端框架（如 React + MapLibre）
  - **推荐 Streamlit**：简历上写 "Streamlit + PyDeck interactive dashboard" 很直观
- [ ] **添加 UI 控件**：
  - 时间窗口选择（午餐/晚餐/周末/深夜）
  - 用户偏好模式（quality_seeker / convenience / local_gem / late_night）
  - 旅行模式（walk / transit）
  - 置信度/不确定性可视化（如半透明 overlay 表示数据质量）
- [ ] **添加不确定性可视化**：
  - 在 map 上标注 hotspot 的 "confidence level"（基于 coordinate precision 和 sample size）
  - 对 2014 坐标级热点用实线边界，对 2024 zone-centroid 热点用虚线边界（诚实区分）
- [ ] **输出**：`streamlit_app.py` 或升级后的 `app.py` + `templates/`

**简历话术**：
> "Built an interactive Streamlit dashboard with time-aware filters, user-preference profiles, and uncertainty visualization, inspired by real-world product design (e.g., Amap Street Rank)."

### Stage 6: 验证与收尾（2-3 天）

- [ ] **Ground truth 验证**：
  - 对比已知 NYC 餐饮区（Chinatown, Koreatown, Little Italy, Williamsburg, East Village, Flushing 等）
  - 计算 precision/recall / IoU
- [ ] **参数敏感性分析**：
  - HDBSCAN `min_cluster_size` = 10, 20, 50
  - TOPSIS weight 方案变化
  - 不同 travel-time decay lambda
- [ ] **输出验证报告**：`docs/VALIDATION_REPORT.md`
- [ ] **写最终 README**：
  - 清晰的项目故事（zone-centroid limitation → coordinate data → robust scoring）
  - 技术栈（Python, GeoPandas, HDBSCAN, OSMnx, Streamlit, TOPSIS）
  - 数据说明（2014 vs 2024 对比）
  - 局限性与未来工作
- [ ] **提交最终版本**：`git tag v2.0.0`

---

## 4. 高德扫街榜灵感映射（产品化思维）

| 扫街榜特点 | 本项目对应实现 | 技术/方法 |
|-----------|--------------|----------|
| **真实行为数据**（导航、到店、收藏） | Taxi drop-off = revealed preference；Citi Bike = active mobility | 加权 drop-off 计数、停留时间推断 |
| **信用加权去刷评** | 用出租车数据替代/补充主观评分；用 Wilson score 处理 rating 置信度 | Bayesian rating average、review count 作为权重 |
| **动态榜单**（时令、品类） | 时间窗口切换（午餐/晚餐/周末/深夜）、H3 时序热图 | Temporal filtering、时序对比 |
| **分类发现**（不只是排名） | 给 hotspot 打标签：repeat-visit zone、special-trip zone、local gem、late-night cluster | 基于 mobility pattern 的聚类特征 + 规则标注 |
| **空间智能**（位置+可达性） | isochrone overlay、network travel time、实时推荐 | OSMnx shortest-path、r5py 多模式 routing |
| **AR/实景探店**（未来可扩展） | 可展示 hotspot 内的代表餐厅图片、街景（未来可用 Google Street View API） | 未来 work |

---

## 5. 简历包装策略（Resume Storyline）

### 5.1 项目定位（Project Framing）

> **Where to DINE: Urban Dining Intelligence from Mobility Data**
> 
> An uncertainty-aware geospatial analytics pipeline that discovers and ranks NYC dining districts by fusing restaurant POIs, taxi GPS drop-offs, and bike-share demand, with robust normalization and network-based accessibility.

### 5.2 简历 bullet points（英文，可直接使用）

- **Built an end-to-end geospatial analytics pipeline** processing 20K+ restaurant POIs and millions of taxi drop-offs to identify urban dining hotspots using HDBSCAN, H3 hexagonal grids, and spatial intersection analysis.
- **Diagnosed a critical spatial-resolution limitation** in public TLC zone-centroid data and validated the improvement with 2014 coordinate-level taxi data through a reproducible A/B pipeline experiment.
- **Redesigned the scoring algorithm** from unstable max-normalization to a robust entropy-weighted TOPSIS framework with z-score winsorization, stable travel-time decay, and deterministic tie-breakers.
- **Upgraded accessibility analysis** from Euclidean distance to OSMnx network-based travel time, with planned r5py multimodal integration for walk + transit routing.
- **Delivered an interactive Streamlit dashboard** featuring time-aware filters, user-preference profiles, and uncertainty visualization, inspired by product design principles from real-world local-life platforms.
- **Conducted systematic validation** against known NYC dining districts, with parameter sensitivity analysis and ground-truth IoU reporting.

### 5.3 技术栈关键词（ATS-friendly）

Python, GeoPandas, HDBSCAN, OSMnx, NetworkX, Streamlit, Folium, PyDeck, TOPSIS, Entropy Weight Method, Z-score normalization, Winsorization, 2SFCA, R5/r5py, H3, Getis-Ord Gi*, Spatial Autocorrelation, NYC Open Data, SODA API, Git, Git LFS, Docker (optional)

### 5.4 GitHub 展示优化

- [ ] **README 第一屏要有 GIF/截图**：展示 Streamlit 界面，包含 isochrone overlay 和 ranked hotspots
- [ ] **添加 `docs/ARCHITECTURE.md`**：用一张图说明 pipeline（数据流 → 聚类 → 评分 → 推荐）
- [ ] **添加 `docs/CHANGELOG.md`**：从 v1.0 (course demo) 到 v2.0 (portfolio version) 的演进
- [ ] **Release 一个 v2.0.0**：包含对比实验结果截图和 demo 视频链接

---

## 6. 时间估算

| 阶段 | 预估时间 | 优先级 |
|------|---------|--------|
| Stage 0: 清理与稳固 | 1-2 天 | 🔴 P0 — 必须先做 |
| Stage 1: 2014 坐标对比 | 3-5 天 | 🔴 P0 — 核心故事 |
| Stage 2: 评分重构 | 3-5 天 | 🔴 P0 — 核心贡献 |
| Stage 3: 可达性升级 | 2-4 天 | 🟡 P1 — 强烈建议 |
| Stage 4: H3 多源融合 | 3-4 天 | 🟡 P1 — 加分项 |
| Stage 5: Demo UI | 2-3 天 | 🟡 P1 — 展示力 |
| Stage 6: 验证与收尾 | 2-3 天 | 🟡 P1 — 完成闭环 |
| **总计** | **16-26 天** | 约 3-4 周专注工作 |

---

## 7. 参考文件索引（已有资产）

| 文件 | 用途 | 状态 |
|------|------|------|
| `docs/NYC_2014_COORDINATE_TAXI_COMPARISON_PLAN.md` | 对比实验完整设计 | ✅ 可直接执行 |
| `docs/PROJECT_REFRAME_NOTES.md` | 问题诊断与产品定位 | ✅ 核心参考 |
| `docs/literature/2026-06-scoring-accessibility-clustering-review.md` | 25篇文献综述，含算法选型表 | ✅ 核心参考，不需要重做文献搜索 |
| `docs/ACADEMIC_EVALUATION.md` | 教授评审反馈，列出了所有必须修复的问题 | ✅ 对照清单 |
| `docs/methodology/recommendation_scoring.md` | 现有评分公式文档（已过时，需重写） | ⚠️ 需更新 |
| `docs/TASK_CHECKLIST.md` | 10周完整计划（太细，参考即可） | ⚠️ 参考 |

---

## 8. 下一步行动（Next Actions）

1. ✅ **确认本 plan**（当前对话）
2. 🔜 **执行 Stage 0 清理**：修复 isochrone import bug、统一路径、标记数据状态、创建缺失目录
3. 🔜 **写 `src/analysis/scoring.py` 骨架**：定义新评分接口，保留旧版用于对比
4. 🔜 **下载 2014  taxi 样本**：从 NYC Open Data 拉 1 个月数据验证 pipeline
5. 🔜 **并行**：评估 Streamlit 是否比升级 Flask 更适合快速出 demo

---

**Plan Version**: 1.0  
**Date**: 2026-06-25  
**Author**: Orchestrator (Kimi) + Jasmine  
**Status**: Ready for execution
