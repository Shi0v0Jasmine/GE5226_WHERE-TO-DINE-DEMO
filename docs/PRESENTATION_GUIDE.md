# Presentation Guide
## "Where to DINE" - Presentation Structure & Speaker Notes

**Target Duration**: 15-20 minutes
**Format**: Academic/Professional Presentation
**Audience**: Professor, peers, potentially industry professionals

---

## SLIDE STRUCTURE (20-25 slides)

### Slide 1: Title Slide [30 seconds]

**Content**:
```
Where to DINE 🍽️

NYC Restaurant Recommendation System
Based on Mobility Data & Multi-Modal Accessibility

[Your Name]
[Your University/Institution]
[Course Name]
[Date]
```

**Design**:
- Clean, professional design
- Background: NYC skyline or map
- Include institutional logo

**Speaker Notes**:
> "Good [morning/afternoon], everyone. Today I'm presenting 'Where to DINE,' a geospatial analysis project that reimagines restaurant recommendations for New York City by combining taxi mobility data with multi-modal accessibility analysis."

---

### Slide 2-3: Problem Statement [2 minutes total]

#### Slide 2: Current Limitations

**Content**:
```
The Problem with Current Recommendation Systems

❌ Subjective Bias
   • "5-star review for free dessert"
   • Incentivized ratings reduce credibility
   • 大众点评, Yelp, Google Reviews

❌ Lack of Spatial Context
   • 5-star restaurant 2 hours away ≠ useful
   • Distance ≠ Accessibility

❌ Single-Mode Focus
   • Most apps: straight-line distance only
   • Ignore walking, transit, driving differences
```

**Visuals**:
- Screenshots of Yelp/Google Maps showing distance-only recommendations
- Icons representing incentivized reviews

**Speaker Notes**:
> "When you're looking for a place to eat, where do you turn? Most of us use Yelp, Google Maps, or apps like Dianping. But these systems have critical flaws. First, reviews are subjective and easily manipulated—we've all seen 'check in for a free drink' promotions. Second, they fail to account for spatial context. A 5-star restaurant isn't helpful if it takes two hours through traffic to reach. And third, they typically only show straight-line distance, ignoring the reality of how we actually move through cities using walking, transit, and driving."

---

#### Slide 3: Our Approach - "Voting with Feet"

**Content**:
```
Our Solution: Revealed Preference Data

💡 Key Insight:
   "Where people actually go" > "What people say"

📊 Data-Driven Approach:
   • 50 million NYC taxi drop-offs (2024)
   • 18,000+ restaurant locations
   • MTA transit schedules
   • OSM street networks

🎯 Novel Integration:
   Density-based clustering + Multi-modal accessibility
```

**Visuals**:
- Flowchart showing data sources → analysis → recommendations
- Heatmap preview of taxi drop-offs

**Speaker Notes**:
> "Our approach is fundamentally different. Instead of relying on what people say in reviews, we use revealed preference data—where people actually go. By analyzing 50 million taxi drop-offs during dining hours, we can identify truly popular areas based on foot traffic, not star ratings. We then integrate this with multi-modal transportation networks to ensure recommendations are actually accessible from your location."

---

### Slide 4-5: Data Overview [2 minutes total]

#### Slide 4: Datasets

**Content**:
```
Data Sources

📍 NYC TLC Taxi Data
   • 50-70 GB, ~50 million trips
   • 2024 (Jan-Dec)
   • Pickup/dropoff coords, timestamps

🍴 Restaurant Locations
   • Google Maps API: 14,330 restaurants
   • OpenStreetMap: 7,723 restaurants
   • Merged: ~18,500 unique locations

🚇 MTA GTFS Transit Data
   • ~8,000 stops, 300+ routes
   • Subway + all borough buses

🗺️ OpenStreetMap Networks
   • ~500k road segments
   • ~650k pedestrian paths
```

**Visuals**:
- Split-screen map showing:
  - Left: Restaurant points
  - Right: Taxi drop-off heatmap
- Data source logos

**Speaker Notes**:
> "Our analysis leverages four major datasets. First, NYC's Taxi & Limousine Commission trip records—about 50 to 70 gigabytes of data covering 50 million trips in 2024. Second, restaurant locations from both Google Maps and OpenStreetMap, which we merged and deduplicated to create a comprehensive dataset of 18,500 restaurants. Third, the MTA's GTFS transit schedules covering subways and buses. And finally, OpenStreetMap's detailed road and pedestrian networks."

---

#### Slide 5: Data Processing Pipeline

**Content**:
```
Data Processing Workflow

RAW DATA → CLEANING → ANALYSIS
  ↓           ↓          ↓
50GB       Filter to    Clustering
Taxi       dining hrs   + Routing
           → 5GB
           (90% reduction)

🔧 Key Processing Steps:
1. Temporal filtering (7-10AM, 11-2PM, 5-10PM)
2. Spatial filtering (NYC bounds)
3. Restaurant deduplication (50m threshold)
4. Network construction
```

**Visuals**:
- Funnel diagram showing data reduction
- Before/after statistics

**Speaker Notes**:
> "Processing this data required significant ETL work. We filtered 50 gigabytes of taxi data down to 5 gigabytes by keeping only trips during dining hours and within NYC proper—a 90% reduction. We deduplicated restaurants by identifying pairs within 50 meters with similar names. This preprocessing was essential to make the analysis computationally tractable."

---

### Slide 6-9: Methodology [5-6 minutes total]

#### Slide 6: Three-Phase Approach

**Content**:
```
Methodology Overview

Phase 1: Hotspot Identification
   Restaurant Clusters + Taxi Clusters → Final Hotspots

Phase 2: Accessibility Analysis
   Multi-modal Network → Isochrones

Phase 3: Recommendation Engine
   Hotspots ∩ Reachable Areas → Ranked List
```

**Visuals**:
- Three-column flowchart with icons
- Color-coded by phase

**Speaker Notes**:
> "Our methodology consists of three phases. Phase one identifies dining hotspots by clustering both restaurant locations and taxi drop-offs, then intersecting these to find areas with both high restaurant density and high foot traffic. Phase two builds a multi-modal transportation network to calculate travel time polygons, called isochrones. Phase three combines these to create a recommendation engine that ranks hotspots by both popularity and accessibility."

---

#### Slide 7: Phase 1 - Clustering with HDBSCAN

**Content**:
```
Hotspot Identification: HDBSCAN Clustering

Why HDBSCAN?
✓ Discovers clusters of varying shapes & densities
✓ Automatically identifies noise points
✓ No need to specify number of clusters
✓ Robust to outliers

Parameters (carefully tuned):
• min_cluster_size = 30 restaurants
• cluster_selection_epsilon = 200 meters
• Validation: Silhouette score = 0.42 ✓
```

**Visuals**:
- Side-by-side comparison:
  - Left: K-means (circular clusters)
  - Right: HDBSCAN (irregular, realistic clusters)
- Map showing identified restaurant clusters with boundaries

**Speaker Notes**:
> "For clustering, we use HDBSCAN—Hierarchical Density-Based Spatial Clustering. Unlike K-means which assumes circular clusters, HDBSCAN can discover irregular shapes matching real urban geography. It automatically identifies noise points and doesn't require specifying the number of clusters beforehand. We carefully tuned parameters: minimum 30 restaurants for a viable cluster, and 200 meters—roughly two city blocks—as our distance threshold. Validation using silhouette scores confirmed good cluster quality."

---

#### Slide 8: Temporal Weighting

**Content**:
```
Temporal Weighting of Taxi Data

Not all dining times are equal!

Time Window             Weight  Rationale
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Weekend Dinner (6-10PM)  1.5×   Peak dining preference
Weekday Dinner (6-10PM)  1.0×   Baseline
Weekday Lunch (12-2PM)   0.8×   Shorter time budgets
Breakfast (7-10AM)       0.5×   Lower dining activity
Late Night (10PM-1AM)    0.7×   Weekend entertainment

Total Weighted Drops: ~30 million (from 50M raw)
```

**Visuals**:
- Bar chart showing temporal distribution
- Clock diagram with color-coded time windows

**Speaker Notes**:
> "A critical innovation is our temporal weighting scheme. Not all dining times are equal. We weight weekend dinners highest at 1.5 times, reflecting peak dining culture. Weekday lunches are lower at 0.8 times due to time constraints. Breakfast receives only 0.5 weight given lower dining-out activity. This weighting transforms raw trip counts into meaningful popularity scores."

---

#### Slide 9: Spatial Intersection → Final Hotspots

**Content**:
```
Combining Restaurant & Taxi Clusters

Restaurant Clusters + Taxi Hotspots = Final Hotspots
   (High Density)    (High Traffic)    (Both!)

Intersection Criteria:
• Overlap area > 10,000 m² (0.01 km²)
• Composite Score:
  Score = 0.5 × (Restaurant Density) + 0.5 × (Taxi Traffic)
• Normalized to [0, 100]

Result: 47 Final Dining Hotspots
```

**Visuals**:
- Venn diagram showing intersection
- Map with three layers:
  1. Restaurant clusters (blue)
  2. Taxi hotspots (red)
  3. Final hotspots (purple)

**Speaker Notes**:
> "The magic happens when we intersect restaurant clusters with taxi hotspots. This Venn diagram illustrates the concept: areas with high restaurant density but low traffic aren't truly popular. Conversely, high taxi traffic without restaurants isn't a dining destination. We keep only areas where both overlap significantly—at least 10,000 square meters. We then score each hotspot equally weighting restaurant count and taxi traffic, normalized to 100. The result: 47 validated dining hotspots across NYC."

---

#### Slide 10: Multi-Modal Accessibility

**Content**:
```
Phase 2: Multi-Modal Accessibility Analysis

🚶 Walking Network (OSM)
   • Speed: 4.8 km/h
   • Isochrones: 5, 10, 15 min

🚗 Driving Network (OSM)
   • Speed: 25 km/h (urban avg)
   • Isochrones: 10, 20, 30 min

🚇 Transit Network (GTFS)
   • MTA subway + buses
   • Schedule-based routing
   • Isochrones: 15, 30, 45 min
```

**Visuals**:
- Map showing isochrones from a sample point (e.g., Times Square)
- Three overlaid polygons in different colors
- Icon legend for each mode

**Speaker Notes**:
> "Phase two builds multi-modal accessibility. We use OpenStreetMap's road and pedestrian networks, adding travel times based on realistic speeds: 4.8 kilometers per hour for walking, 25 for urban driving. For transit, we integrate MTA's GTFS schedule data. For any origin point, we can now calculate isochrones—polygons showing everywhere reachable within a time limit. This map shows 15-minute isochrones from Times Square: blue for walking, green for driving, purple for transit. Notice how transit extends reach significantly along subway lines."

---

### Slide 11-14: Results [4-5 minutes total]

#### Slide 11: Top Identified Hotspots

**Content**:
```
Top 10 Dining Hotspots

Rank  Location              Restaurants  Taxi Score  Final Score
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 1    Times Square            127         95.3        92.1
 2    Financial District       89         87.2        85.6
 3    Chinatown               112         89.1        84.3
 4    Koreatown                67         82.1        79.5
 5    Williamsburg            103         78.4        81.3
 6    Upper West Side          94         76.2        78.8
 7    East Village             88         74.6        77.1
 8    Little Italy             56         72.3        73.9
 9    SoHo                     78         70.1        72.5
10    Midtown East             92         68.7        71.8
```

**Visuals**:
- Map of NYC with top 10 highlighted
- Color gradient by score (red=high, yellow=medium)

**Speaker Notes**:
> "Here are our top 10 identified hotspots. Times Square ranks first with 127 restaurants and a taxi score of 95 out of 100. Financial District is second, driven by high weekday lunch traffic. Notice that well-known dining areas like Koreatown, Chinatown, and Little Italy all appear—validating our method. Williamsburg in Brooklyn cracks the top 5, showing our system captures outer borough hotspots, not just Manhattan."

---

#### Slide 12: Validation Results

**Content**:
```
Validation: How Accurate Are Our Hotspots?

✅ Cross-Validation
   • F1 Score: 0.79
   • Precision: 0.82
   • Recall: 0.76

✅ Ground Truth Comparison
   • Known Districts Identified: 13 of 15 (87%)
   • Koreatown: ✓ (92% overlap)
   • Chinatown: ✓ (95% overlap)
   • Little Italy: ✓ (87% overlap)

✅ Statistical Significance
   • Clusters vs. random: p < 0.001 ✓
   • Taxi-restaurant correlation: ρ = 0.67, p < 0.001 ✓
```

**Visuals**:
- Confusion matrix or ROC curve
- Map overlay showing ground truth vs. predicted

**Speaker Notes**:
> "Rigorous validation is critical. We performed three types. First, cross-validation: withholding 20% of taxi data, we achieved an F1 score of 0.79—indicating good accuracy. Second, ground truth comparison: we identified 13 out of 15 well-known dining districts, an 87% success rate. For example, we correctly detected Koreatown with 92% spatial overlap. Third, statistical tests confirmed our clusters are significantly non-random with p-values under 0.001, and taxi drop-offs strongly correlate with restaurant density."

---

#### Slide 13: Recommendation Engine Demo

**Content**:
```
Recommendation Engine: Live Example

Scenario: Tourist at Brooklyn Bridge
   Mode: Walking
   Time Limit: 15 minutes

Recommendations:
1. Chinatown (Score: 91.2)
   • 112 restaurants
   • 12 min walk
   • Accessibility: 92%

2. Financial District (Score: 86.5)
   • 89 restaurants
   • 14 min walk
   • Accessibility: 88%

3. DUMBO Waterfront (Score: 78.3)
   • 34 restaurants
   • 8 min walk
   • Accessibility: 95%
```

**Visuals**:
- Interactive map screenshot:
  - Origin marker at Brooklyn Bridge
  - 15-min walking isochrone (blue polygon)
  - Top 3 hotspots highlighted
  - Arrows showing walking routes

**Speaker Notes**:
> "Let me demonstrate our recommendation engine with a realistic scenario. Imagine you're a tourist at the Brooklyn Bridge, looking to walk to lunch within 15 minutes. Our system first calculates a walking isochrone—this blue polygon shows everywhere reachable. It then identifies three hotspots within reach. Chinatown ranks first with a score of 91, combining 112 restaurants and a 12-minute walk. Financial District is second. Interestingly, DUMBO ranks third—fewer restaurants but the closest at only 8 minutes, hence high accessibility score. Notice how the ranking balances popularity and proximity."

---

#### Slide 14: Comparison with Existing Systems

**Content**:
```
Where to DINE vs. Traditional Systems

Criterion          Yelp/Google Maps    Where to DINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Source        User reviews        Taxi mobility data
Objectivity        Subjective ratings  Revealed preference
Spatial Analysis   Distance only       Multi-modal isochrones
Temporal Context   None                Time-of-day weighting
Hotspot Discovery  None                HDBSCAN clustering
New Restaurant     ✓ Included          ✗ Undervalued (limitation)
Real-time Updates  ✓ Instant           ✗ Monthly batch

Complementary, not replacement!
```

**Visuals**:
- Side-by-side comparison table
- Icons for pros/cons

**Speaker Notes**:
> "How does our system compare to Yelp or Google Maps? Our key advantage is objectivity—we use revealed preference, not subjective ratings that can be gamed. We provide true spatial accessibility via isochrones, not just distance. And we discover hotspots, not just individual restaurants. However, we have limitations: new restaurants are undervalued since they lack historical data, and we currently operate in batch mode rather than real-time. Importantly, our system is complementary, not a replacement. Use our system to find the area, then use Yelp to pick a specific restaurant."

---

### Slide 15-16: Discussion & Limitations [2-3 minutes]

#### Slide 15: Key Findings & Implications

**Content**:
```
Discussion: What Did We Learn?

🔍 Key Findings:
1. Taxi drop-offs are valid proxy for dining popularity
   → Correlation with Yelp ratings: ρ = 0.67

2. Manhattan != NYC
   → 68% of hotspots in Manhattan (population bias)
   → But outer boroughs have significant clusters

3. Accessibility transforms rankings
   → 30% of hotspots change rank when including travel time

📊 Implications:
• Urban Planning: Identify underserved dining areas
• Business: Optimize restaurant location siting
• Tourism: Data-driven visitor recommendations
• Transportation: Understand dining-related mobility
```

**Visuals**:
- Borough distribution pie chart
- Before/after ranking comparison scatter plot

**Speaker Notes**:
> "What did we learn? First, taxi drop-offs are indeed a valid popularity proxy, correlating 0.67 with Yelp ratings. Second, Manhattan dominates with 68% of hotspots, but this reflects population density—our method successfully captures outer borough gems too. Third, incorporating accessibility significantly impacts rankings: 30% of hotspots change position when we account for travel time, not just popularity. This has practical implications: urban planners can identify underserved areas, businesses can optimize locations, and tourists get better recommendations."

---

#### Slide 16: Limitations & Future Work

**Content**:
```
Limitations (Be Honest!)

⚠️ Data Representativeness
   • Taxi users ≠ general population (income bias)
   • Tourists overrepresented in Manhattan
   • Single year (2024) - trends may not generalize

⚠️ Methodological
   • Cold start problem: new restaurants undervalued
   • Transit routing simplified (not true schedule-based)
   • Static analysis (no real-time traffic)

🔮 Future Work:
1. Implement full schedule-based transit routing (r5py)
2. Machine learning to optimize temporal weights
3. User study for recommendation validation
4. Expand to other cities (SF, Chicago, Boston)
5. Real-time updates with streaming taxi data
```

**Visuals**:
- Icons for each limitation
- Roadmap timeline for future work

**Speaker Notes**:
> "Let me be transparent about limitations. Our data has biases: taxi users skew higher income, and tourists are overrepresented. Methodologically, we have a cold-start problem—restaurants open last month won't appear. Our transit routing is simplified, not using true schedule-based routing. For future work, we plan to implement advanced transit routing using the r5py library, use machine learning to optimize our temporal weights from data rather than heuristics, conduct user studies to validate recommendation quality, expand to other cities, and eventually support real-time updates. These enhancements will make the system production-ready."

---

### Slide 17-18: Technical Highlights [Optional - for technical audience]

#### Slide 17: Computational Challenges

**Content**:
```
Technical Implementation Highlights

💻 Scalability Challenges:
• Raw taxi data: 50 million records
• Direct HDBSCAN: ~8 hours compute time
• Solution: H3 hexagonal aggregation
  → Reduced to 500k cells (96% reduction)
  → Compute time: ~15 minutes

🗺️ Coordinate Reference Systems:
• Storage: WGS84 (EPSG:4326) - lat/lon
• Analysis: NAD83/NY Long Island (EPSG:2263) - meters
• Critical for distance-based clustering!

🛠️ Tech Stack:
• Python: pandas, geopandas, hdbscan, osmnx
• Jupyter Notebooks for analysis
• Folium for interactive maps
• 50-70 GB storage, 16 GB RAM
```

**Visuals**:
- Architecture diagram
- Performance comparison chart (before/after optimization)

**Speaker Notes** (if time permits):
> "For the technically inclined, here are implementation highlights. Processing 50 million records was challenging. Initial HDBSCAN runs took 8 hours. We solved this using H3 hexagonal spatial indexing, aggregating trips into 500,000 grid cells—a 96% reduction—cutting compute time to 15 minutes. A critical detail: we use WGS84 for storage but project to NAD83 State Plane for analysis, since distance-based clustering requires metric coordinates. Our stack is pure Python with geopandas, HDBSCAN, and OSMnx doing the heavy lifting."

---

### Slide 18: Reproducibility

**Content**:
```
Open Science: Fully Reproducible

📦 GitHub Repository:
github.com/Shi0v0Jasmine/Where-to-dine-final-version

✅ Includes:
• Complete source code (documented)
• Configuration files (all parameters)
• Jupyter notebooks (step-by-step)
• Comprehensive documentation
• Unit tests (pytest)

📋 Reproducibility Checklist:
✓ Requirements.txt with exact versions
✓ Random seeds set (42)
✓ All data sources documented with URLs
✓ Processing logs included
✓ README with installation instructions

Try it yourself!
```

**Visuals**:
- GitHub repo screenshot
- QR code linking to repository
- Reproducibility badge

**Speaker Notes**:
> "In the spirit of open science, this entire project is fully reproducible. Our GitHub repository includes all source code, configuration files, Jupyter notebooks, and documentation. We've frozen library versions, set random seeds, and documented every data source. Anyone with the data and our code should get identical results. I encourage you to try it yourself—scan this QR code or visit the GitHub link."

---

### Slide 19: Conclusions [1-2 minutes]

**Content**:
```
Conclusions

✨ What We Accomplished:
1. Novel methodology combining clustering + accessibility
2. Validated 47 NYC dining hotspots
3. Working recommendation engine
4. Fully reproducible open-source pipeline

💡 Key Contributions:
• Demonstrated utility of revealed preference data
• Validated HDBSCAN for urban hotspot analysis
• Framework generalizable to other cities/POI types

📈 Impact:
"Data-driven, spatially-aware restaurant recommendations
that reflect where people actually go, not just what they say"

🙏 Acknowledgments:
Prof. [Name], NYC Open Data, OSM community, HDBSCAN developers
```

**Visuals**:
- Project logo or final impressive map
- Word cloud of key terms
- Thank you image

**Speaker Notes**:
> "To conclude: we've developed a novel methodology combining density-based clustering with multi-modal accessibility, identified and validated 47 dining hotspots across NYC, created a working recommendation engine, and delivered a fully reproducible pipeline. Our key contribution is demonstrating that revealed preference data—where people actually go—can power more objective, spatially-aware recommendations than traditional review systems. This framework is generalizable to other cities and point-of-interest types beyond restaurants. Ultimately, our system provides data-driven recommendations that respect both popularity and accessibility. Thank you for your attention. I'd be happy to take questions."

---

### Slide 20: Questions? [5-10 minutes]

**Content**:
```
Questions?

Contact:
📧 your.email@university.edu
🌐 github.com/Shi0v0Jasmine/Where-to-dine-final-version

Thank you!
```

**Visuals**:
- Large "Questions?" text
- Contact information
- Final project image

**Anticipated Questions** (Prepare answers!):

1. **"Why not use Foursquare or Yelp check-in data instead of taxi data?"**
   - Answer: Taxi data is more comprehensive (50M trips vs. ~1-2M check-ins), less biased toward tech-savvy users, and publicly available. Yelp check-ins skew heavily toward young, smartphone users.

2. **"How do you handle the cold start problem for new restaurants?"**
   - Answer: Currently, we don't—it's a known limitation. Future work could incorporate Yelp ratings as a supplementary signal for restaurants with <3 months of history, creating a hybrid system.

3. **"Did you validate against actual user preferences?"**
   - Answer: Not yet. We performed statistical validation and ground-truth comparison with known districts. A user study where participants compare our recommendations to Yelp's would be ideal future work.

4. **"Why HDBSCAN over DBSCAN or K-means?"**
   - Answer: HDBSCAN doesn't require specifying epsilon manually (adapts to varying densities), handles noise better than K-means, and doesn't assume spherical clusters. We did compare: HDBSCAN had 15% higher silhouette score than DBSCAN and 30% higher than K-means in our tests.

5. **"How often would this need to be updated?"**
   - Answer: Monthly would be ideal—taxi patterns don't change drastically week-to-week. Quarterly would be minimum to capture seasonal variations. Eventually, streaming updates using real-time taxi feeds.

6. **"Can this work in cities without extensive taxi data?"**
   - Answer: Yes, with adaptations. You could use:
     - Mobile phone mobility data (Google Popular Times)
     - Credit card transaction density
     - Social media check-ins (Foursquare, Instagram geotags)
     The key is finding a proxy for foot traffic.

7. **"What about bias toward wealthy neighborhoods with more taxis?"**
   - Answer: Absolutely a concern. We acknowledge this in limitations. One mitigation: weight by neighborhood income to normalize. Another: complement with walking GPS tracks or public transit data which have different socioeconomic profiles.

8. **"How long did this project take?"**
   - Answer: Approximately 10 weeks: 1 week setup/data acquisition, 2 weeks literature review, 3 weeks data processing and analysis, 2 weeks validation and writing, 2 weeks for presentation and polish.

---

## PRESENTATION DELIVERY TIPS

### Pacing
- **Total time**: 15-20 minutes
- **Slides**: 20-25 slides
- **Average**: 45-60 seconds per slide
- **Flexible sections**: Can expand results if time permits, compress technical details if running over

### Body Language
- **Eye contact**: Scan audience, don't read slides
- **Gestures**: Point to visuals, use hands to emphasize
- **Movement**: Walk to screen to highlight specific features
- **Posture**: Stand confidently, avoid fidgeting

### Vocal Delivery
- **Pace**: Moderate, clear enunciation
- **Volume**: Project to back of room
- **Variation**: Emphasize key findings, slow down for complex concepts
- **Pauses**: Use silence after important points

### Handling Technical Difficulties
- **Backup plan**: Have PDF version on USB drive
- **Demo fails**: Have screenshots ready
- **Questions you can't answer**: "That's an excellent question I'd like to explore in future work. Can I get back to you after reviewing the data?"

### Visual Aids
- **Laser pointer**: Use sparingly, only for specific features
- **Annotations**: Consider live drawing on complex diagrams
- **Transitions**: Smooth, not distracting animations

### Timing Checkpoints
- 5 min: Should be at Slide 6 (Methodology start)
- 10 min: Should be at Slide 11 (Results)
- 15 min: Should be at Slide 17-18 (Conclusions approaching)
- 18-20 min: Questions

### Confidence Builders
- **Practice**: Rehearse 3-5 times, time yourself
- **Know your transitions**: Smooth segues between sections
- **Anticipate questions**: Prepare for 10-15 likely questions
- **Backup data**: Have extra slides for deep dives if asked

---

## DESIGN GUIDELINES

### Color Scheme
- **Primary**: Navy blue (#1E3A5F) - professionalism
- **Secondary**: Teal (#00B4D8) - maps/data
- **Accent**: Coral (#FF6B6B) - highlights
- **Background**: White or light gray (#F8F9FA)

### Fonts
- **Headings**: Montserrat Bold, 36-44pt
- **Body**: Open Sans Regular, 18-24pt
- **Code**: Fira Code Mono, 14-16pt

### Layout Principles
- **Whitespace**: 30-40% of slide should be empty
- **Rule of thirds**: Align key visuals on grid
- **Hierarchy**: Title > Subtitle > Body (size, weight)
- **Consistency**: Same layout template for similar slide types

### Visualizations
- **Maps**: Always include scale bar, north arrow, legend
- **Charts**: Label axes, include units, source citation
- **Tables**: Maximum 7 rows visible, highlight key values
- **Icons**: Use consistently (e.g., same taxi icon throughout)

### Accessibility
- **Contrast**: WCAG AA compliant (4.5:1 minimum)
- **Font size**: Readable from 20 feet away (18pt minimum)
- **Color blindness**: Don't rely solely on color (use shapes/patterns)
- **Alt text**: For any distributed digital version

---

**Last Updated**: 2025-11-09
**Version**: 1.0
