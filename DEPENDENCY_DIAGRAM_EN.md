# Project Dependency Visualization Diagrams

This document uses Mermaid diagrams to visualize various dependency relationships in the project.

> **Viewing Tip:** Open in a Mermaid-compatible Markdown viewer (such as GitHub, GitLab, VS Code + Mermaid plugin)

---

## 1. Overall System Architecture Diagram

```mermaid
graph TB
    subgraph "User Interface Layer"
        APP[app.py<br/>Flask Web App]
        TEMPLATE[templates/index.html]
        USER((User Browser))
    end

    subgraph "Final Output"
        FINAL[final_hotspots.geojson<br/>🎯Final Recommendations]
    end

    subgraph "Data Processing Pipeline"
        PIPELINE[run_pipeline.py<br/>Pipeline Controller]
        P1[Phase 1<br/>02_process_taxi_data.py]
        P2[Phase 2<br/>02_merge_restaurants.py]
        P3[Phase 3<br/>06_cluster_restaurants.py]
        P4[Phase 4<br/>07_cluster_taxi_dropoffs.py]
        P5[Phase 5<br/>08_spatial_intersection.py]
    end

    subgraph "Utility Modules"
        CONFIG[src/utils/<br/>config_loader.py]
        CLUSTER[src/analysis/<br/>clustering.py]
        ISO[src/analysis/<br/>isochrone.py]
    end

    subgraph "Configuration & Data"
        YAML[config/config.yaml]
        RAW[data/raw/*<br/>Raw Data]
    end

    USER -->|accesses| APP
    APP -->|uses| TEMPLATE
    APP -->|reads| FINAL

    PIPELINE -->|calls| P1
    PIPELINE -->|calls| P2
    PIPELINE -->|calls| P3
    PIPELINE -->|calls| P4
    PIPELINE -->|calls| P5

    P1 -->|outputs| TAXI_W[taxi_dropoffs_weighted.parquet]
    P2 -->|outputs| REST_M[restaurants_merged.geojson]
    P3 -->|outputs| DZONE[dining_zones.geojson]
    P4 -->|outputs| THOT[taxi_hotspots.geojson]
    P5 -->|outputs| FINAL

    TAXI_W -->|inputs| P4
    REST_M -->|inputs| P3
    DZONE -->|inputs| P5
    THOT -->|inputs| P5

    CONFIG -->|imported by| P1
    CONFIG -->|imported by| P2
    CONFIG -->|imported by| P3
    CONFIG -->|imported by| P4
    CONFIG -->|imported by| P5

    YAML -->|reads| CONFIG
    RAW -->|reads| P1
    RAW -->|reads| P2

    style FINAL fill:#ff6b6b,stroke:#c92a2a,stroke-width:4px
    style APP fill:#4dabf7,stroke:#1971c2,stroke-width:3px
    style PIPELINE fill:#51cf66,stroke:#2f9e44,stroke-width:3px
```

---

## 2. Detailed Data Processing Flow Diagram

```mermaid
flowchart TD
    START([Start: run_pipeline.py])

    subgraph "Raw Data Sources"
        TAXI_RAW[12-month Taxi Parquet<br/>~140M records]
        REST_GM[Google Maps<br/>Restaurant Data]
        REST_OSM[OpenStreetMap<br/>Restaurant Data]
        BOUND[NYC Boundaries<br/>nybb.shp]
        ZONES[Taxi Zones<br/>taxi_zones.shp]
    end

    subgraph "Phase 1: Taxi Data Processing"
        P1[02_process_taxi_data.py]
        P1_1[Batch load 12 files]
        P1_2[LocationID → Lat/Lon]
        P1_3[Filter to dining hours]
        P1_4[Apply temporal weights]
        P1_5[NYC boundary filter]
    end

    subgraph "Phase 2: Restaurant Merging"
        P2[02_merge_restaurants.py]
        P2_1[Standardize fields]
        P2_2[Spatial deduplication<br/>KDTree + fuzzy matching]
        P2_3[Merge datasets]
    end

    subgraph "Phase 3: Restaurant Clustering"
        P3[06_cluster_restaurants.py]
        P3_1[Coordinate projection<br/>WGS84 → EPSG:2263]
        P3_2[HDBSCAN clustering<br/>min_size=30, ε=200m]
        P3_3[Generate dining zones<br/>Convex hull+buffer 100m]
        P3_4[Calculate metrics]
    end

    subgraph "Phase 4: Taxi Clustering"
        P4[07_cluster_taxi_dropoffs.py]
        P4_1[Weight-based duplication<br/>weight=1.5→2 copies]
        P4_2[HDBSCAN clustering<br/>min_size=50, ε=250m]
        P4_3[Generate hotspots<br/>Convex hull+buffer 150m]
    end

    subgraph "Phase 5: Spatial Intersection"
        P5[08_spatial_intersection.py]
        P5_1[Spatial intersection<br/>D ∩ T]
        P5_2[Area filter<br/>≥10,000m²]
        P5_3[Overlap filter<br/>≥15%]
        P5_4[Calculate scores<br/>0.5×R + 0.5×T]
        P5_5[Rank output]
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

    FINAL --> END([Complete])

    style START fill:#51cf66
    style END fill:#ff6b6b
    style FINAL fill:#ffd43b,stroke:#f59f00,stroke-width:3px
    style TAXI_W fill:#a9e34b
    style REST_M fill:#a9e34b
    style DZONE fill:#74c0fc
    style THOT fill:#74c0fc
```

---

## 3. Code Module Dependency Graph

```mermaid
graph LR
    subgraph "Entry Files"
        APP[app.py]
        PIPE[run_pipeline.py]
    end

    subgraph "Data Processing Scripts"
        P1[02_process_taxi_data.py]
        P2[02_merge_restaurants.py]
        P3[06_cluster_restaurants.py]
        P4[07_cluster_taxi_dropoffs.py]
        P5[08_spatial_intersection.py]
    end

    subgraph "Analysis Modules"
        CLU[clustering.py]
        ISO[isochrone.py]
    end

    subgraph "Utility Modules"
        CONF[config_loader.py]
    end

    subgraph "Visualization"
        VIS[01_visualize_results.py]
    end

    subgraph "Configuration"
        YAML[config.yaml]
    end

    PIPE -.subprocess calls.-> P1
    PIPE -.subprocess calls.-> P2
    PIPE -.subprocess calls.-> P3
    PIPE -.subprocess calls.-> P4
    PIPE -.subprocess calls.-> P5

    P1 -->|import| CONF
    P2 -->|import| CONF
    P3 -->|import| CONF
    P4 -->|import| CONF
    P5 -->|import| CONF

    CONF -->|reads| YAML

    CLU -.theoretically importable.-> P3
    CLU -.theoretically importable.-> P4

    ISO -.independent function.-> VIS

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

## 4. File Input/Output Dependency Diagram

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

## 5. Execution Sequence Timeline

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

    Pipeline->>P1: Execute 02_process_taxi_data.py
    activate P1
    P1->>Data: Output taxi_dropoffs_weighted.parquet
    P1-->>Pipeline: ✅ Complete
    deactivate P1

    Pipeline->>P2: Execute 02_merge_restaurants.py
    activate P2
    P2->>Data: Output restaurants_merged.geojson
    P2-->>Pipeline: ✅ Complete
    deactivate P2

    Note over Pipeline: Phase 1, 2 must complete before continuing

    Pipeline->>P3: Execute 06_cluster_restaurants.py
    activate P3
    P3->>Data: Read restaurants_merged.geojson
    P3->>Data: Output dining_zones.geojson
    P3-->>Pipeline: ✅ Complete
    deactivate P3

    Pipeline->>P4: Execute 07_cluster_taxi_dropoffs.py
    activate P4
    P4->>Data: Read taxi_dropoffs_weighted.parquet
    P4->>Data: Output taxi_hotspots.geojson
    P4-->>Pipeline: ✅ Complete
    deactivate P4

    Note over Pipeline: Phase 3, 4 can run in parallel (currently sequential)

    Pipeline->>P5: Execute 08_spatial_intersection.py
    activate P5
    P5->>Data: Read dining_zones.geojson
    P5->>Data: Read taxi_hotspots.geojson
    P5->>Data: Output final_hotspots.geojson
    P5-->>Pipeline: ✅ Complete
    deactivate P5

    Pipeline-->>User: 🎉 Pipeline Complete
    deactivate Pipeline

    User->>Data: python app.py
    activate Data
    Data-->>User: Web app started @ http://127.0.0.1:5000
    deactivate Data
```

---

## 6. Configuration Dependency Graph

```mermaid
graph TB
    YAML[config.yaml]

    subgraph "Configuration Items"
        C1[clustering.restaurants.*]
        C2[clustering.taxi.*]
        C3[temporal.weights.*]
        C4[intersection.*]
        C5[geographic.crs.*]
    end

    subgraph "Consumers"
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

## 7. Third-Party Library Dependency Graph

```mermaid
graph TD
    subgraph "Core Libraries"
        PD[pandas]
        NP[numpy]
        GP[geopandas]
        SP[shapely]
        PR[pyproj]
    end

    subgraph "Machine Learning"
        HDB[hdbscan]
        SK[scikit-learn]
        SC[scipy]
    end

    subgraph "Data I/O"
        PA[pyarrow]
        FI[fiona]
        YA[pyyaml]
    end

    subgraph "Web & Visualization"
        FL[flask]
        FO[folium]
    end

    subgraph "Optimization"
        PAN[pandarallel]
        H3[h3]
        RT[rtree]
    end

    subgraph "Application Scripts"
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

## 8. Failure Impact Analysis Diagram

```mermaid
graph TB
    subgraph "🔴 High Risk - Deletion causes system failure"
        H1[config.yaml]
        H2[config_loader.py]
        H3[taxi_dropoffs_weighted.parquet]
        H4[restaurants_merged.geojson]
        H5[final_hotspots.geojson]
    end

    subgraph "🟡 Medium Risk - Deletion causes partial failure"
        M1[taxi_zones.shp]
        M2[dining_zones.geojson]
        M3[taxi_hotspots.geojson]
    end

    subgraph "⚪ Low Risk - Deletion affects optional features only"
        L1[01_visualize_results.py]
        L2[isochrone.py]
        L3[cache/*.json]
    end

    subgraph "Impact Scope"
        I1[❌ All processing scripts]
        I2[❌ Phase 1-5]
        I3[❌ Web application]
        I4[⚠️ Some phases]
        I5[ℹ️ Visualization]
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

## 9. Parallel Execution Potential Diagram

```mermaid
graph LR
    subgraph "Current Execution (Sequential)"
        S1[Phase 1] --> S2[Phase 2] --> S3[Phase 3] --> S4[Phase 4] --> S5[Phase 5]
    end

    subgraph "Optimized Execution (Parallel)"
        P1[Phase 1<br/>Taxi Processing]
        P2[Phase 2<br/>Restaurant Merging]
        P3[Phase 3<br/>Restaurant Clustering]
        P4[Phase 4<br/>Taxi Clustering]
        P5[Phase 5<br/>Spatial Intersection]

        P1 --> P4
        P2 --> P3
        P3 --> P5
        P4 --> P5
    end

    subgraph "Performance Gain"
        GAIN[Theoretical speedup: 1.5x - 2x<br/>Phase 1, 2 can run in parallel<br/>Phase 3, 4 can run in parallel]
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

## Legend

### Node Colors
- 🔴 **Red** - Critical component, cannot be deleted
- 🟡 **Yellow** - Important output, affects downstream
- 🔵 **Blue** - Web/interactive components
- 🟢 **Green** - Control/processing components
- ⚪ **White** - Auxiliary/optional components

### Connection Types
- **Solid arrow** → Strong dependency (required)
- **Dashed arrow** -.-> Weak dependency (optional)
- **Thick arrow** ==> Data flow
- **Label** Describes relationship type

---

**Document Generated:** 2025-11-17
**Applicable Version:** v1.0
**Recommended Viewing Tools:**
- GitHub/GitLab (native support)
- VS Code + Markdown Preview Mermaid Support
- Mermaid Live Editor (https://mermaid.live)
