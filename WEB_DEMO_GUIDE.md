# Web Demo Usage Guide

Interactive web application for **Where to DINE** - NYC Dining Hotspot Recommender.

---

## 🚀 Quick Start

### 1. Install Flask

If you haven't already installed Flask:

```bash
pip install flask
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run the Data Pipeline (First Time Only)

The web app requires processed data. If you haven't run the pipeline yet:

```bash
python run_pipeline.py
```

This will generate `data/processed/final_hotspots.geojson` which the web app needs.

### 3. Start the Web Server

```bash
python app.py
```

You should see:
```
======================================================
WHERE TO DINE - Web Demo
======================================================

✅ Loaded 45 hotspots

✅ Ready! Open http://127.0.0.1:5000 in your browser
```

### 4. Open in Browser

Navigate to: **http://127.0.0.1:5000**

---

## 🎯 How to Use

### Main Interface

The web app has two main sections:

1. **Interactive Map** (Left): Shows all dining hotspots in NYC
   - Color-coded by popularity score
   - Red = High quality (80-100)
   - Orange = Medium-high (60-80)
   - Gold = Medium (40-60)
   - Yellow = Low (0-40)

2. **Recommendation Panel** (Right): Shows personalized recommendations
   - Initially shows instructions
   - Updates when you click the map

### Getting Recommendations

**Step 1: Click anywhere on the map**
- Example: Click in Times Square, East Village, or Financial District
- A blue marker will appear at your location
- A 2km search radius circle is shown

**Step 2: View recommendations**
- The panel shows nearby hotspots ranked by:
  - **60% Popularity** (restaurant density + taxi activity)
  - **40% Accessibility** (distance from your location)
- Each card shows:
  - Overall rank (#1 = best in entire NYC)
  - Recommendation score (0-100)
  - Distance from your location
  - Number of restaurants
  - Number of taxi dropoffs
  - Average restaurant rating

**Step 3: Explore hotspots**
- Click on any recommendation card
- The map zooms to that hotspot
- A red highlight appears for 3 seconds

### Understanding the Scores

**Popularity Score** (from our pipeline):
- Based on clustering results
- Combines restaurant density + taxi dropoff density
- Higher score = more popular dining area

**Recommendation Score** (calculated in real-time):
```python
recommendation_score = 0.6 × popularity_score + 0.4 × accessibility_score
```

Where:
- `popularity_score`: Pre-calculated from pipeline (0-100)
- `accessibility_score`: Based on distance (closer = higher score)

**Example**:
- Hotspot A: Popularity 95, Distance 0.5km → Recommendation 91.7
- Hotspot B: Popularity 80, Distance 1.8km → Recommendation 58.0

Hotspot A ranks higher because it's both popular AND close!

---

## 🗺️ Features

### 1. Real-time Statistics (Header)
- Total hotspots identified
- Total restaurants in hotspots
- Total taxi dropoffs analyzed
- Average popularity score

### 2. Interactive Map
- Zoom and pan
- Click hotspot polygons to see details in popup
- Click anywhere to search for nearby recommendations
- Color-coded by quality

### 3. Smart Recommendations
- Considers both popularity AND distance
- Ranks up to 10 nearest hotspots within 2km
- Shows detailed metrics for each

### 4. Visual Feedback
- Blue marker: Your selected location
- Dashed circle: 2km search radius
- Red pulse: Highlighted hotspot (when you click a card)

---

## 🎨 User Interface Guide

### Header Section
```
🍽️ Where to DINE
[Total Hotspots] [Restaurants] [Taxi Dropoffs] [Avg Score]
```

### Map Section
- **Polygons**: Dining hotspots (color = quality)
- **Legend** (bottom right): Color scale explanation
- **Controls** (top left): Zoom in/out

### Sidebar Section
- **Instructions**: How to use the app
- **Search Info**: Your location and search details
- **Recommendation Cards**: Ranked list of nearby hotspots

---

## 🔧 API Endpoints

The app provides three REST API endpoints:

### 1. Get All Hotspots
```
GET /api/hotspots
```

Returns: GeoJSON FeatureCollection of all hotspots

**Example**:
```bash
curl http://127.0.0.1:5000/api/hotspots
```

### 2. Get Recommendations
```
POST /api/recommend
Content-Type: application/json

{
  "lat": 40.7589,
  "lon": -73.9851,
  "max_distance_km": 2.0,  // optional, default 2.0
  "limit": 10              // optional, default 10
}
```

Returns: List of recommended hotspots with distances and scores

**Example**:
```bash
curl -X POST http://127.0.0.1:5000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"lat": 40.7589, "lon": -73.9851}'
```

**Response**:
```json
{
  "user_location": {"lat": 40.7589, "lon": -73.9851},
  "search_radius_km": 2.0,
  "total_found": 5,
  "recommendations": [
    {
      "rank": 3,
      "popularity_score": 89.5,
      "recommendation_score": 87.3,
      "distance_km": 0.45,
      "n_restaurants": 127,
      "n_taxi_dropoffs": 15234,
      "avg_rating": 4.2,
      "centroid_lat": 40.7580,
      "centroid_lon": -73.9855
    },
    ...
  ]
}
```

### 3. Get Statistics
```
GET /api/stats
```

Returns: Overall statistics about the dataset

**Example**:
```bash
curl http://127.0.0.1:5000/api/stats
```

**Response**:
```json
{
  "total_hotspots": 45,
  "total_restaurants": 1823,
  "total_taxi_dropoffs": 487234,
  "avg_popularity_score": 62.3,
  "top_hotspot_score": 95.8,
  "total_area_sqkm": 12.45
}
```

---

## 🛠️ Customization

### Change Search Radius

Edit `templates/index.html` line ~250:

```javascript
// Change from 2km to 3km
userCircle = L.circle([lat, lon], {
    radius: 3000,  // Change this (in meters)
    ...
});

// Also update in fetch request
body: JSON.stringify({
    ...
    max_distance_km: 3.0,  // And this (in km)
    ...
})
```

### Change Number of Recommendations

Edit `templates/index.html` line ~260:

```javascript
body: JSON.stringify({
    ...
    limit: 15  // Show top 15 instead of 10
})
```

### Change Scoring Weights

Edit `app.py` line ~140:

```python
# Change from 60/40 to 70/30 (more emphasis on popularity)
hotspots_nearby['recommendation_score'] = (
    0.7 * hotspots_nearby['popularity_score'] +
    0.3 * hotspots_nearby['accessibility_score']
)
```

### Change Map Style

Edit `templates/index.html` line ~210:

```javascript
// CartoDB Dark Matter theme
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    ...
}).addTo(map);

// Or OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    ...
}).addTo(map);
```

---

## 🐛 Troubleshooting

### Issue: "No data loaded" error

**Cause**: `final_hotspots.geojson` not found

**Solution**:
```bash
# Run the pipeline first
python run_pipeline.py

# Then restart the app
python app.py
```

### Issue: Port 5000 already in use

**Solution**:
```python
# Edit app.py, change port to 5001
app.run(
    host='127.0.0.1',
    port=5001,  # Change this
    debug=True
)
```

Then access: http://127.0.0.1:5001

### Issue: Map not loading

**Cause**: Internet connection required for map tiles

**Solution**: Ensure you have internet connection for Leaflet and CARTO basemap tiles

### Issue: "No hotspots found within 2 km"

**Cause**: Clicked in an area with no nearby hotspots (e.g., outer Queens, Staten Island)

**Solution**: Click closer to Manhattan, Downtown Brooklyn, or increase search radius in code

---

## 📊 Performance

### Expected Performance

- **Load Time**: <2 seconds (depends on number of hotspots)
- **Recommendation Query**: <100ms for 50 hotspots
- **Map Rendering**: Instant (Leaflet.js is optimized)

### Optimization Tips

For larger datasets (>100 hotspots):

1. **Enable clustering on frontend** (Leaflet.markercluster):
```html
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
```

2. **Add spatial indexing** in backend:
```python
# In app.py
from rtree import index
# Build R-tree index for faster spatial queries
```

3. **Cache GeoJSON**:
```python
# Add Flask-Caching
from flask_caching import Cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.cached(timeout=3600)
@app.route('/api/hotspots')
def get_all_hotspots():
    ...
```

---

## 🚀 Deployment (Optional)

To deploy this app publicly:

### Option 1: Heroku

```bash
# Install Heroku CLI
heroku create where-to-dine-nyc
git push heroku main
heroku open
```

### Option 2: Render.com

1. Push code to GitHub
2. Connect Render to your repo
3. Set start command: `python app.py`
4. Deploy

### Option 3: DigitalOcean App Platform

1. Connect GitHub repo
2. Auto-detects Flask app
3. Deploy with one click

**Note**: For production, use `gunicorn` instead of Flask dev server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 📝 Notes

- **Data Freshness**: The app uses static data from `final_hotspots.geojson`. Re-run the pipeline to update.
- **Offline Mode**: Map tiles require internet. For offline, use local tile server.
- **Mobile Friendly**: Interface is responsive and works on tablets/phones.
- **Browser Support**: Works in all modern browsers (Chrome, Firefox, Safari, Edge).

---

## 🎯 Next Steps

Want to enhance the app? Consider adding:

1. **Filter by cuisine type** (if restaurant data has cuisine field)
2. **Time-based recommendations** (breakfast, lunch, dinner hotspots)
3. **User ratings/reviews** integration
4. **Route directions** to selected hotspot (using Mapbox Directions API)
5. **Save favorite hotspots** (requires user accounts)

---

**Enjoy exploring NYC's dining hotspots!** 🍽️🗽
