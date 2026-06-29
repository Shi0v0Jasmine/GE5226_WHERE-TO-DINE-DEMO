# TravelTimeCalculator 使用指南

## 架构

```
src/travel_time/
├── __init__.py                # 导出 TravelTimeCalculator
├── travel_time_calculator.py  # 主工厂接口
├── proxy_backend.py           # 当前激活（默认）
├── osmnx_backend.py           # OSMnx 离线路网（预留）
├── google_maps_backend.py     # Google API（预留）
└── transit_graph.py           # 手动地铁/公交图（预留，待 Codex 实现）
```

## 当前使用（无需任何依赖）

```python
from src.travel_time import TravelTimeCalculator

# 默认：proxy backend，transit 模式
tt = TravelTimeCalculator(mode='transit', backend='proxy')

# 不同模式：walk, bike, drive, transit
for mode in ['walk', 'drive', 'transit']:
    tt = TravelTimeCalculator(mode=mode, backend='proxy')
    t = tt.single((40.7580, -73.9855), (40.6782, -73.9442))  # Times Square → Brooklyn
    print(f"{mode}: {t:.1f} min")
```

**API 查询参数：**
- `?mode=walk|bike|drive|transit` — 出行方式
- `?access_method=proxy|osmnx|google` — 后端选择

## 下载 NYC 路网（OSMnx 后端）

需要 `osmnx` 和 `networkx`：

```bash
pip install osmnx networkx
```

然后运行下载脚本：

```bash
python scripts/download_nyc_network.py
```

**输出：**
- `data/networks/nyc_walk.graphml` (~500-800 MB)
- `data/networks/nyc_drive.graphml`
- `data/networks/nyc_bike.graphml`

**下载后使用：**
```python
from src.travel_time import TravelTimeCalculator

tt = TravelTimeCalculator(mode='walk', backend='osmnx')
# 自动加载 data/networks/nyc_walk.graphml
matrix = tt.matrix(origins, destinations)
```

## Google Maps API（预留）

```python
import os
os.environ['GOOGLE_MAPS_API_KEY'] = 'YOUR_KEY'

tt = TravelTimeCalculator(mode='transit', backend='google')
matrix = tt.matrix(origins, destinations)
```

**费用：** ~$5/1000 elements。62 个热点 × 1 个用户 = 62 次请求 ≈ $0.31。

## 手动地铁/公交图（TransitGraph，待 Codex 实现）

需要：
1. 下载 MTA GTFS: https://new.mta.info/developers
2. 提取到 `data/transit/mta_gtfs/`
3. 在 `transit_graph.py` 中实现 `_load_gtfs()` 和 `matrix()`

实现时间估算：~4 小时（一集中 session）

## 模式对照

| 模式 | proxy 速度 | OSMnx 速度 | Google 模式 | 适用场景 |
|------|-----------|-----------|------------|---------|
| walk | 5 km/h | 真实路网步行 | walking | 短距离，曼哈顿 |
| bike | 15 km/h | 真实路网骑行 | bicycling | 中距离，布鲁克林 |
| drive | 25 km/h | 真实路网驾车 | driving | 远郊，JFK/LGA |
| transit | 30 km/h | 不支持 | transit | 地铁+公交，首选 |

## 注意

- `transit` 模式在 OSMnx 中不支持，会自动 fallback 到 proxy
- `transit` 在 Google 中是最准确的模式（包含地铁+公交+换乘）
- proxy 的 `transit` 速度 30 km/h 是 NYC 地铁平均速度，未考虑换乘等待
