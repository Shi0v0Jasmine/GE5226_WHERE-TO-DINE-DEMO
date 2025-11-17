# 项目依赖关系可视化图表

本文档使用 Mermaid 图表展示项目的各种依赖关系。

> **查看提示:** 在支持Mermaid的Markdown查看器中打开（如GitHub、GitLab、VS Code + Mermaid插件）

---

## 1. 整体系统架构图

```mermaid
graph TB
    subgraph "用户交互层"
        APP[app.py<br/>Flask Web应用]
        TEMPLATE[templates/index.html]
        USER((用户浏览器))
    end

    subgraph "最终输出"
        FINAL[final_hotspots.geojson<br/>🎯最终推荐结果]
    end

    subgraph "数据处理流程"
        PIPELINE[run_pipeline.py<br/>流程控制器]
        P1[Phase 1<br/>02_process_taxi_data.py]
        P2[Phase 2<br/>02_merge_restaurants.py]
        P3[Phase 3<br/>06_cluster_restaurants.py]
        P4[Phase 4<br/>07_cluster_taxi_dropoffs.py]
        P5[Phase 5<br/>08_spatial_intersection.py]
    end

    subgraph "工具模块"
        CONFIG[src/utils/<br/>config_loader.py]
        CLUSTER[src/analysis/<br/>clustering.py]
        ISO[src/analysis/<br/>isochrone.py]
    end

    subgraph "配置与数据"
        YAML[config/config.yaml]
        RAW[data/raw/*<br/>原始数据]
    end

    USER -->|访问| APP
    APP -->|使用| TEMPLATE
    APP -->|读取| FINAL

    PIPELINE -->|调用| P1
    PIPELINE -->|调用| P2
    PIPELINE -->|调用| P3
    PIPELINE -->|调用| P4
    PIPELINE -->|调用| P5

    P1 -->|输出| TAXI_W[taxi_dropoffs_weighted.parquet]
    P2 -->|输出| REST_M[restaurants_merged.geojson]
    P3 -->|输出| DZONE[dining_zones.geojson]
    P4 -->|输出| THOT[taxi_hotspots.geojson]
    P5 -->|输出| FINAL

    TAXI_W -->|输入| P4
    REST_M -->|输入| P3
    DZONE -->|输入| P5
    THOT -->|输入| P5

    CONFIG -->|被引用| P1
    CONFIG -->|被引用| P2
    CONFIG -->|被引用| P3
    CONFIG -->|被引用| P4
    CONFIG -->|被引用| P5

    YAML -->|读取| CONFIG
    RAW -->|读取| P1
    RAW -->|读取| P2

    style FINAL fill:#ff6b6b,stroke:#c92a2a,stroke-width:4px
    style APP fill:#4dabf7,stroke:#1971c2,stroke-width:3px
    style PIPELINE fill:#51cf66,stroke:#2f9e44,stroke-width:3px
```

---

## 2. 数据处理流程详细图

```mermaid
flowchart TD
    START([开始: run_pipeline.py])

    subgraph "原始数据源"
        TAXI_RAW[12个月 Taxi Parquet<br/>约1.4亿条记录]
        REST_GM[Google Maps<br/>餐厅数据]
        REST_OSM[OpenStreetMap<br/>餐厅数据]
        BOUND[NYC边界数据<br/>nybb.shp]
        ZONES[Taxi Zones<br/>taxi_zones.shp]
    end

    subgraph "Phase 1: 出租车数据处理"
        P1[02_process_taxi_data.py]
        P1_1[批处理加载12个文件]
        P1_2[LocationID → 经纬度]
        P1_3[过滤到用餐时间]
        P1_4[应用时间权重]
        P1_5[NYC边界过滤]
    end

    subgraph "Phase 2: 餐厅数据合并"
        P2[02_merge_restaurants.py]
        P2_1[标准化字段]
        P2_2[空间去重<br/>KDTree + 模糊匹配]
        P2_3[合并数据集]
    end

    subgraph "Phase 3: 餐厅聚类"
        P3[06_cluster_restaurants.py]
        P3_1[坐标投影<br/>WGS84 → EPSG:2263]
        P3_2[HDBSCAN聚类<br/>min_size=30, ε=200m]
        P3_3[生成dining zones<br/>凸包+缓冲100m]
        P3_4[计算验证指标]
    end

    subgraph "Phase 4: 出租车聚类"
        P4[07_cluster_taxi_dropoffs.py]
        P4_1[权重复制点<br/>weight=1.5→2份]
        P4_2[HDBSCAN聚类<br/>min_size=50, ε=250m]
        P4_3[生成hotspots<br/>凸包+缓冲150m]
    end

    subgraph "Phase 5: 空间求交"
        P5[08_spatial_intersection.py]
        P5_1[空间求交<br/>D ∩ T]
        P5_2[面积过滤<br/>≥10,000m²]
        P5_3[重叠率过滤<br/>≥15%]
        P5_4[计算复合得分<br/>0.5×R + 0.5×T]
        P5_5[排名输出]
    end

    START --> P1 & P2

    TAXI_RAW --> P1_1
    ZONES --> P1_2
    P1_1 --> P1_2 --> P1_3 --> P1_4 --> P1_5
    BOUND --> P1_5
    P1_5 --> TAXI_W[taxi_dropoffs_weighted.parquet]

    REST_GM --> P2_1
    REST_OSM --> P2_1
    P2_1 --> P2_2 --> P2_3
    P2_3 --> REST_M[restaurants_merged.geojson]

    REST_M --> P3_1 --> P3_2 --> P3_3 --> P3_4
    P3_4 --> DZONE[dining_zones.geojson]

    TAXI_W --> P4_1 --> P4_2 --> P4_3
    P4_3 --> THOT[taxi_hotspots.geojson]

    DZONE --> P5_1
    THOT --> P5_1
    P5_1 --> P5_2 --> P5_3 --> P5_4 --> P5_5
    P5_5 --> FINAL[final_hotspots.geojson]

    FINAL --> END([完成])

    style START fill:#51cf66
    style END fill:#ff6b6b
    style FINAL fill:#ffd43b,stroke:#f59f00,stroke-width:3px
    style TAXI_W fill:#a9e34b
    style REST_M fill:#a9e34b
    style DZONE fill:#74c0fc
    style THOT fill:#74c0fc
```

---

## 3. 代码模块依赖关系图

```mermaid
graph LR
    subgraph "入口文件"
        APP[app.py]
        PIPE[run_pipeline.py]
    end

    subgraph "数据处理脚本"
        P1[02_process_taxi_data.py]
        P2[02_merge_restaurants.py]
        P3[06_cluster_restaurants.py]
        P4[07_cluster_taxi_dropoffs.py]
        P5[08_spatial_intersection.py]
    end

    subgraph "分析模块"
        CLU[clustering.py]
        ISO[isochrone.py]
    end

    subgraph "工具模块"
        CONF[config_loader.py]
    end

    subgraph "可视化"
        VIS[01_visualize_results.py]
    end

    subgraph "配置"
        YAML[config.yaml]
    end

    PIPE -.subprocess调用.-> P1
    PIPE -.subprocess调用.-> P2
    PIPE -.subprocess调用.-> P3
    PIPE -.subprocess调用.-> P4
    PIPE -.subprocess调用.-> P5

    P1 -->|import| CONF
    P2 -->|import| CONF
    P3 -->|import| CONF
    P4 -->|import| CONF
    P5 -->|import| CONF

    CONF -->|读取| YAML

    CLU -.理论可引用.-> P3
    CLU -.理论可引用.-> P4

    ISO -.独立功能.-> VIS

    APP -->|pandas/geopandas| P5
    VIS -->|folium| P3
    VIS -->|folium| P4
    VIS -->|folium| P5

    style APP fill:#4dabf7
    style PIPE fill:#51cf66
    style CONF fill:#ffd43b
    style YAML fill:#ff8787
```

---

## 4. 文件输入输出依赖图

```mermaid
flowchart LR
    subgraph "Raw Data"
        R1[taxi/*.parquet]
        R2[restaurants_googlemaps.csv]
        R3[restaurants_osm.csv]
        R4[boundaries/nybb.shp]
        R5[boundaries/taxi_zones.shp]
    end

    subgraph "Interim"
        I1[taxi_dropoffs_weighted.parquet]
        I2[restaurants_merged.geojson]
    end

    subgraph "Processed"
        O1[dining_zones.geojson]
        O2[restaurants_clustered.geojson]
        O3[taxi_hotspots.geojson]
        O4[taxi_dropoffs_clustered.parquet]
        O5[final_hotspots.geojson]
    end

    subgraph "Outputs"
        V1[maps/*.html]
        V2[Web @ :5000]
    end

    R1 --> |P1| I1
    R4 --> |P1| I1
    R5 --> |P1| I1

    R2 --> |P2| I2
    R3 --> |P2| I2

    I2 --> |P3| O1
    I2 --> |P3| O2

    I1 --> |P4| O3
    I1 --> |P4| O4

    O1 --> |P5| O5
    O3 --> |P5| O5

    O1 --> |viz| V1
    O2 --> |viz| V1
    O3 --> |viz| V1
    O5 --> |viz| V1

    O5 --> |app| V2

    style I1 fill:#a9e34b
    style I2 fill:#a9e34b
    style O5 fill:#ffd43b,stroke:#f59f00,stroke-width:3px
    style V2 fill:#4dabf7
```

---

## 5. 执行顺序时序图

```mermaid
sequenceDiagram
    participant User
    participant Pipeline as run_pipeline.py
    participant P1 as Phase 1
    participant P2 as Phase 2
    participant P3 as Phase 3
    participant P4 as Phase 4
    participant P5 as Phase 5
    participant Data as data/processed/

    User->>Pipeline: python run_pipeline.py
    activate Pipeline

    Pipeline->>P1: 执行 02_process_taxi_data.py
    activate P1
    P1->>Data: 输出 taxi_dropoffs_weighted.parquet
    P1-->>Pipeline: ✅ 完成
    deactivate P1

    Pipeline->>P2: 执行 02_merge_restaurants.py
    activate P2
    P2->>Data: 输出 restaurants_merged.geojson
    P2-->>Pipeline: ✅ 完成
    deactivate P2

    Note over Pipeline: Phase 1, 2 必须完成后才能继续

    Pipeline->>P3: 执行 06_cluster_restaurants.py
    activate P3
    P3->>Data: 读取 restaurants_merged.geojson
    P3->>Data: 输出 dining_zones.geojson
    P3-->>Pipeline: ✅ 完成
    deactivate P3

    Pipeline->>P4: 执行 07_cluster_taxi_dropoffs.py
    activate P4
    P4->>Data: 读取 taxi_dropoffs_weighted.parquet
    P4->>Data: 输出 taxi_hotspots.geojson
    P4-->>Pipeline: ✅ 完成
    deactivate P4

    Note over Pipeline: Phase 3, 4 可以并行（当前顺序执行）

    Pipeline->>P5: 执行 08_spatial_intersection.py
    activate P5
    P5->>Data: 读取 dining_zones.geojson
    P5->>Data: 读取 taxi_hotspots.geojson
    P5->>Data: 输出 final_hotspots.geojson
    P5-->>Pipeline: ✅ 完成
    deactivate P5

    Pipeline-->>User: 🎉 流程完成
    deactivate Pipeline

    User->>Data: python app.py
    activate Data
    Data-->>User: Web应用启动 @ http://127.0.0.1:5000
    deactivate Data
```

---

## 6. 配置依赖关系图

```mermaid
graph TB
    YAML[config.yaml]

    subgraph "配置项"
        C1[clustering.restaurants.*]
        C2[clustering.taxi.*]
        C3[temporal.weights.*]
        C4[intersection.*]
        C5[geographic.crs.*]
    end

    subgraph "被使用者"
        P1[02_process_taxi_data.py]
        P3[06_cluster_restaurants.py]
        P4[07_cluster_taxi_dropoffs.py]
        P5[08_spatial_intersection.py]
    end

    YAML --> C1
    YAML --> C2
    YAML --> C3
    YAML --> C4
    YAML --> C5

    C1 --> P3
    C2 --> P4
    C3 --> P1
    C4 --> P5
    C5 --> P1
    C5 --> P3
    C5 --> P4
    C5 --> P5

    style YAML fill:#ff8787,stroke:#c92a2a,stroke-width:3px
```

---

## 7. 第三方库依赖图

```mermaid
graph TD
    subgraph "核心库"
        PD[pandas]
        NP[numpy]
        GP[geopandas]
        SP[shapely]
        PR[pyproj]
    end

    subgraph "机器学习"
        HDB[hdbscan]
        SK[scikit-learn]
        SC[scipy]
    end

    subgraph "数据IO"
        PA[pyarrow]
        FI[fiona]
        YA[pyyaml]
    end

    subgraph "Web与可视化"
        FL[flask]
        FO[folium]
    end

    subgraph "优化库"
        PAN[pandarallel]
        H3[h3]
        RT[rtree]
    end

    subgraph "应用脚本"
        APP[app.py]
        P1[02_process_taxi_data.py]
        P3[06_cluster_restaurants.py]
        P4[07_cluster_taxi_dropoffs.py]
        VIS[01_visualize_results.py]
    end

    APP --> FL
    APP --> GP
    APP --> PD
    APP --> SP

    P1 --> PD
    P1 --> GP
    P1 --> PAN
    P1 --> PA

    P3 --> GP
    P3 --> HDB
    P3 --> SK
    P3 --> YA

    P4 --> GP
    P4 --> HDB
    P4 --> H3

    VIS --> FO
    VIS --> GP

    GP --> SP
    GP --> PR
    GP --> FI

    style APP fill:#4dabf7
    style FL fill:#ff6b6b
    style GP fill:#51cf66
    style HDB fill:#ffd43b
```

---

## 8. 破坏影响分析图

```mermaid
graph TB
    subgraph "🔴 高风险 - 删除将导致系统失败"
        H1[config.yaml]
        H2[config_loader.py]
        H3[taxi_dropoffs_weighted.parquet]
        H4[restaurants_merged.geojson]
        H5[final_hotspots.geojson]
    end

    subgraph "🟡 中风险 - 删除将导致部分功能失败"
        M1[taxi_zones.shp]
        M2[dining_zones.geojson]
        M3[taxi_hotspots.geojson]
    end

    subgraph "⚪ 低风险 - 删除仅影响可选功能"
        L1[01_visualize_results.py]
        L2[isochrone.py]
        L3[cache/*.json]
    end

    subgraph "影响范围"
        I1[❌ 所有处理脚本]
        I2[❌ Phase 1-5]
        I3[❌ Web应用]
        I4[⚠️ 部分Phase]
        I5[ℹ️ 可视化]
    end

    H1 --> I1
    H2 --> I1
    H3 --> I2
    H4 --> I2
    H5 --> I3

    M1 --> I4
    M2 --> I4
    M3 --> I4

    L1 --> I5
    L2 --> I5
    L3 --> I5

    style H1 fill:#ff6b6b
    style H2 fill:#ff6b6b
    style H3 fill:#ff6b6b
    style H4 fill:#ff6b6b
    style H5 fill:#ff6b6b

    style M1 fill:#ffd43b
    style M2 fill:#ffd43b
    style M3 fill:#ffd43b

    style L1 fill:#d0ebff
    style L2 fill:#d0ebff
    style L3 fill:#d0ebff
```

---

## 9. 并行执行潜力图

```mermaid
graph LR
    subgraph "当前执行方式 (顺序)"
        S1[Phase 1] --> S2[Phase 2] --> S3[Phase 3] --> S4[Phase 4] --> S5[Phase 5]
    end

    subgraph "优化后执行方式 (并行)"
        P1[Phase 1<br/>Taxi处理]
        P2[Phase 2<br/>Restaurant合并]
        P3[Phase 3<br/>Restaurant聚类]
        P4[Phase 4<br/>Taxi聚类]
        P5[Phase 5<br/>空间求交]

        P1 --> P4
        P2 --> P3
        P3 --> P5
        P4 --> P5
    end

    subgraph "性能提升"
        GAIN[理论加速: 1.5x - 2x<br/>Phase 1, 2 可并行<br/>Phase 3, 4 可并行]
    end

    style S1 fill:#ffe3e3
    style S2 fill:#ffe3e3
    style S3 fill:#ffe3e3
    style S4 fill:#ffe3e3
    style S5 fill:#ffe3e3

    style P1 fill:#d0ebff
    style P2 fill:#d0ebff
    style P3 fill:#b2f2bb
    style P4 fill:#b2f2bb
    style P5 fill:#ffd43b

    style GAIN fill:#51cf66
```

---

## 图例说明

### 节点颜色
- 🔴 **红色** - 关键组件，不可删除
- 🟡 **黄色** - 重要输出，影响下游
- 🔵 **蓝色** - Web/交互组件
- 🟢 **绿色** - 控制/处理组件
- ⚪ **白色** - 辅助/可选组件

### 连接类型
- **实线箭头** → 强依赖（必需）
- **虚线箭头** -.-> 弱依赖（可选）
- **粗线箭头** ==> 数据流
- **标注** 说明关系类型

---

**文档生成时间:** 2025-11-17
**适用版本:** v1.0
**查看工具推荐:**
- GitHub/GitLab (原生支持)
- VS Code + Markdown Preview Mermaid Support
- Mermaid Live Editor (https://mermaid.live)
