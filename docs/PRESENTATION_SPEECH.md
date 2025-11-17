# Presentation Speech Draft
## "Where to DINE" - 15-20 Minute Academic Presentation

**Delivery Style**: Professional yet engaging, passionate about the work
**Audience**: Academic (professor, peers, potentially industry)
**Goal**: Demonstrate technical rigor while maintaining accessibility

---

## OPENING [0:00-0:30]

**[Slide 1: Title]**

Good [morning/afternoon], everyone. Thank you for being here.

Today, I'm excited to present **"Where to DINE"**—a geospatial analysis project that reimagines how we discover dining destinations in New York City.

The core idea is simple but powerful: instead of relying on subjective reviews that can be manipulated, we use **revealed preference data**—analyzing where people actually go based on 50 million taxi trips—and combine this with sophisticated multi-modal accessibility analysis.

Let me start by explaining the problem we're trying to solve.

**[TRANSITION TO SLIDE 2]**

---

## PROBLEM STATEMENT [0:30-2:30]

**[Slide 2: Current Limitations]**

When you're looking for a place to eat in a new city, what do you do?

*[Pause for audience to mentally answer]*

Most of us pull out our phones and open Yelp, Google Maps, or if you're in China, 大众点评.

But here's the problem: **these systems have critical flaws.**

**First, subjective bias.** We've all seen the signs: "Check in for a free drink!" or "Five-star review for a free dessert." These incentivized ratings significantly reduce the credibility of recommendation systems. A restaurant could have a 4.8-star rating simply because they're giving away freebies, not because the food is actually exceptional.

**Second, lack of spatial context.** Let me give you a real example: When I searched for pizza on Google Maps from Brooklyn Bridge, the top result was rated 4.9 stars. Sounds great, right? Except it was in Queens—a 90-minute trip through traffic, even on a weekend. A 5-star restaurant isn't useful if it takes two hours to reach.

**Third, they don't account for multi-modal accessibility.** Most apps show you straight-line distance—"as the crow flies." But we're not crows. We walk, we take subways, we drive through traffic. A restaurant 2 miles away might take 10 minutes by subway or 45 minutes walking. Distance doesn't equal accessibility.

**[TRANSITION TO SLIDE 3]**

**[Slide 3: Our Approach]**

This leads to our core innovation: **"voting with feet."**

Instead of asking "what do people say?" we ask "**where do people actually go?**"

This is the difference between *stated preference*—what people claim in reviews—and **revealed preference**—what their behavior demonstrates.

We leverage four massive datasets:
- **50 million** NYC taxi drop-offs from 2024
- **18,000+** restaurant locations from Google Maps and OpenStreetMap
- MTA transit schedules covering subways and all borough buses
- And OpenStreetMap's detailed street networks

By integrating density-based clustering with multi-modal accessibility analysis, we create recommendations that are both objective and spatially aware.

Now let me show you what data went into this.

**[TRANSITION TO SLIDE 4]**

---

## DATA OVERVIEW [2:30-4:30]

**[Slide 4: Datasets]**

Let me walk you through our data sources, because the quality of any analysis depends on the quality of the input data.

**First, NYC Taxi & Limousine Commission trip records.** This is public data from the city's Open Data portal. It's massive—50 to 70 gigabytes covering approximately 50 million trips throughout 2024. Each record contains pickup and dropoff coordinates, timestamps, and fare information.

**Second, restaurant locations.** We pulled 14,330 restaurants from Google Maps API, which gave us ratings, price levels, and cuisine types. We also got 7,723 restaurants from OpenStreetMap, which has excellent coverage for smaller, ethnic restaurants that might not advertise heavily. We merged these datasets and deduplicated, ending up with about 18,500 unique restaurant locations.

**Third, transit data from the MTA.** This is in GTFS format—General Transit Feed Specification—the standard for public transit schedules. It includes about 8,000 stops and 300+ routes covering subways and buses across all five boroughs.

**And finally, OpenStreetMap networks**—about 500,000 road segments and 650,000 pedestrian paths. This gives us the detailed connectivity data we need for routing.

**[TRANSITION TO SLIDE 5]**

**[Slide 5: Data Processing]**

Now, you might be wondering: how do you process 50 gigabytes of taxi data?

The answer is **strategic filtering.**

We reduced the data by 90%—from 50 gigabytes down to about 5—by keeping only trips relevant to dining behavior.

**Temporal filtering**: We defined dining hours based on meal periods. 7 to 10 AM for breakfast, 11 AM to 2 PM for lunch, 5 to 10 PM for dinner, and 10 PM to 1 AM for late-night dining. Any trips outside these windows were excluded.

**Spatial filtering**: We kept only drop-offs within NYC proper, filtering out trips to airports, suburbs, or obvious data errors like coordinates in the middle of the ocean.

For restaurants, we performed **deduplication**. If two restaurants from different sources were within 50 meters of each other and had similar names—measured using Levenshtein string distance—we considered them the same establishment.

This preprocessing was essential. Without it, the clustering algorithms would have taken days to run instead of hours.

All right, now let's dive into the methodology—this is where it gets interesting.

**[TRANSITION TO SLIDE 6]**

---

## METHODOLOGY [4:30-10:00]

**[Slide 6: Three-Phase Approach]**

Our methodology consists of three phases.

**Phase 1** identifies dining hotspots by clustering restaurant locations and taxi drop-offs separately, then intersecting them to find areas that are both dense with restaurants *and* popular with actual diners.

**Phase 2** builds a multi-modal transportation network and calculates isochrones—these are polygons showing everywhere you can reach within a given time limit.

**Phase 3** is the recommendation engine itself, which combines hotspots with accessibility to produce ranked recommendations tailored to your location and travel mode.

Let me explain each phase in detail.

**[TRANSITION TO SLIDE 7]**

**[Slide 7: HDBSCAN Clustering]**

For clustering, we use an algorithm called **HDBSCAN**—Hierarchical Density-Based Spatial Clustering of Applications with Noise.

Why this particular algorithm?

*[Point to comparison visual]*

If you look at this comparison, K-means—the algorithm many people learn first—assumes clusters are circular or spherical. But real urban dining districts aren't perfect circles. Little Italy, Chinatown, Koreatown—these have irregular, organic shapes following streets and neighborhoods.

HDBSCAN discovers clusters of **varying shapes and densities**. It automatically identifies noise points—those random isolated restaurants—and it doesn't force you to specify the number of clusters in advance. You don't need to tell it "find exactly 15 clusters." It figures that out from the data.

Now, that doesn't mean it's parameter-free. We had to carefully tune two key parameters:

**min_cluster_size = 30**: This means at least 30 restaurants are required to form a viable dining cluster. Why 30? Through experimentation and literature review, we found that smaller values produced too many tiny, fragmented clusters. Larger values missed legitimate smaller dining districts.

**cluster_selection_epsilon = 200 meters**: This is roughly two city blocks in Manhattan. Points within this distance can be part of the same cluster. This value was calibrated to NYC's urban density.

How do we know the clustering is any good?

We use a metric called the **silhouette score**, which ranges from -1 to 1. Values above 0.3 are considered decent; above 0.5 is excellent. Our restaurant clustering achieved 0.42—right in the "good" range.

**[TRANSITION TO SLIDE 8]**

**[Slide 8: Temporal Weighting]**

Now, here's a critical innovation that distinguishes our work from naive trip counting: **temporal weighting**.

Not all dining times are created equal.

Think about it: a taxi drop-off at 7 PM on a Saturday is fundamentally different from one at 1 PM on a Tuesday. Saturday dinner reflects peak dining-out culture—people taking their time, going to nicer restaurants. Tuesday lunch is often grab-and-go, people constrained by work schedules.

So we developed this weighting function. Weekend dinners—6 to 10 PM on Fridays, Saturdays, and Sundays—get weighted 1.5 times. That's our highest weight. Weekday dinners are the baseline at 1.0. Weekday lunch gets 0.8 because people have shorter time budgets. Breakfast is only 0.5 because far fewer people dine out for breakfast compared to lunch or dinner. And late-night dining gets 0.7 on weekends, 0.4 on weekdays.

This scheme transforms raw trip counts into **meaningful popularity scores**.

Now, you might ask: where did these weights come from? Full transparency: they're currently **heuristic**, informed by urban dining literature and our own analysis of temporal patterns. In future work, we'd like to optimize these using machine learning—perhaps by training against Yelp check-in data as ground truth.

**[TRANSITION TO SLIDE 9]**

**[Slide 9: Spatial Intersection]**

This is where the magic happens—the intersection of restaurant clusters and taxi hotspots.

*[Point to Venn diagram]*

Imagine two sets: areas with high restaurant density, and areas with high taxi traffic during dining hours. The **intersection**—where both conditions are true—represents authentic dining hotspots.

An area with tons of restaurants but no taxi traffic? Probably not actually popular, maybe a wholesale district or food processing area. Conversely, high taxi traffic but few restaurants? Might be a transit hub or office district, not a dining destination.

We apply two filters: First, the overlap area must be at least 10,000 square meters—that's about 0.01 square kilometers, or roughly 2.5 acres. This ensures we're capturing meaningful districts, not just tiny pockets.

Second, we score each hotspot using a composite metric: 50% based on restaurant count, normalized to the maximum, and 50% based on total weighted taxi drops. This balanced approach ensures we're not overly biased toward either just quantity of restaurants or just foot traffic—we want both.

The result? **47 final dining hotspots** across New York City.

**[TRANSITION TO SLIDE 10]**

**[Slide 10: Multi-Modal Accessibility]**

Phase two is about accessibility. Because remember, popularity means nothing if you can't actually get there.

We construct three separate networks:

For **walking**, we use OpenStreetMap's pedestrian network—sidewalks, crosswalks, pedestrian paths—and assign a standard walking speed of 4.8 kilometers per hour. That's based on urban walking studies.

For **driving**, we use OSM's road network with an urban average speed of 25 kilometers per hour. Now, this is obviously a simplification—NYC traffic varies wildly by time of day—but for a static analysis, 25 km/h represents a reasonable average.

For **transit**, this is the most complex. We use the MTA's GTFS schedule data. Ideally, we'd implement full schedule-based routing where the system knows that the 2 train arrives at Times Square at 3:47 PM. For this initial version, we simplified to a representative time window—7 to 10 AM weekdays—to build the transit graph.

For any origin point, we can now calculate **isochrones**.

*[Point to map with isochrones]*

This map shows isochrones from Times Square with a 15-minute limit. The blue polygon shows everywhere you can walk in 15 minutes. Green shows driving. And purple shows public transit.

Notice how transit extends reach dramatically along subway lines. You can reach parts of Brooklyn in 15 minutes by subway that would take 40 minutes walking. This is the power of multi-modal analysis.

**[TRANSITION TO SLIDE 11]**

---

## RESULTS [10:00-13:30]

**[Slide 11: Top Hotspots]**

All right, let's see what we actually found.

Here are the top 10 dining hotspots identified by our system.

**Times Square** ranks number one. 127 restaurants, taxi score of 95.3 out of 100, final composite score of 92.1. No surprise there—it's one of the most visited places on Earth.

**Financial District** is second. Interestingly, it scores high largely due to weekday lunch traffic. Thousands of office workers taking lunch breaks drive those taxi drop-offs.

**Chinatown** is third with 112 restaurants. This validates our approach—Chinatown is a globally known dining destination.

What I find particularly interesting is number five: **Williamsburg** in Brooklyn. Our system successfully identifies outer-borough hotspots, not just Manhattan. 103 restaurants, taxi score of 78.4.

And look at number eight: **Little Italy**. Only 56 restaurants, so it doesn't win on density alone. But it scores 72.3 because of consistent taxi traffic, especially on weekends when tourists visit.

This table demonstrates that our system captures both well-known districts and perhaps less obvious but genuinely popular areas.

**[TRANSITION TO SLIDE 12]**

**[Slide 12: Validation]**

Of course, the critical question is: **are these results actually accurate?**

We performed three types of validation.

**First, cross-validation.** We held out 20% of the taxi data and trained our clustering on the remaining 80%. Then we tested whether the holdout trips fell within our predicted hotspots. We achieved an F1 score of 0.79—that's a harmonic mean of precision and recall—indicating good accuracy.

**Second, ground truth comparison.** We manually identified 15 well-known dining districts based on travel guides, Wikipedia, and local knowledge. Examples: Koreatown, Little Italy, Chinatown, Williamsburg, East Village, and so on.

Our system correctly identified **13 out of 15**—that's an 87% success rate.

For Koreatown, we had 92% spatial overlap between our predicted hotspot boundary and the commonly accepted Koreatown area. Chinatown: 95% overlap. These aren't just close—they're highly accurate.

**Third, statistical significance testing.** We ran Monte Carlo simulations generating random point patterns and clustering them. Our observed clustering is significantly stronger than random chance, with p-values under 0.001. We also tested whether taxi drop-offs correlate with restaurant density using Spearman's correlation. We got rho = 0.67 with p < 0.001—a strong, statistically significant correlation.

All of this gives us confidence that our hotspots are real, not artifacts of the algorithm.

**[TRANSITION TO SLIDE 13]**

**[Slide 13: Recommendation Demo]**

Let me demonstrate the recommendation engine with a realistic scenario.

Imagine you're a tourist visiting the Brooklyn Bridge, and you want to walk to lunch within 15 minutes. You pull up our app, click your location on the map, select "walking" mode, and set the time limit to 15 minutes.

The system first calculates this blue isochrone polygon showing everywhere reachable on foot in 15 minutes.

It then identifies hotspots within that polygon. Three qualify:

**Number one: Chinatown.** Score of 91.2. It's got 112 restaurants and is only a 12-minute walk from Brooklyn Bridge. The accessibility score is 92% because you're using 12 of your 15 available minutes—very efficient.

**Number two: Financial District.** Score 86.5. 89 restaurants, 14-minute walk. Slightly farther, hence slightly lower accessibility score at 88%.

**Number three: DUMBO Waterfront.** Score 78.3. Now this is interesting. DUMBO only has 34 restaurants, so it's not winning on popularity. But it's the *closest*—only an 8-minute walk—so it gets a 95% accessibility score. For someone on a tight schedule, this might actually be the best choice despite lower overall popularity.

This demonstrates how our system balances **quality** and **convenience**. You're not just getting the most popular area; you're getting the best combination of popularity and reachability from your specific location.

**[TRANSITION TO SLIDE 14]**

**[Slide 14: Comparison with Existing Systems]**

How does this compare to Yelp or Google Maps?

Our key advantage is **objectivity**. We're using revealed preference—actual behavior—not reviews that can be manipulated.

We provide **true spatial accessibility** through isochrones. Yelp will tell you "2.3 miles away." We tell you "12 minutes via subway, 25 minutes walking, or 18 minutes driving in current traffic conditions."

We discover **hotspots**, not just individual restaurants. This answers the question "where should I go?" before "which specific restaurant?"

However, we have limitations. **New restaurants** are undervalued because they lack historical taxi data. If an amazing restaurant opened last month, it won't show up yet. And we currently operate in **batch mode**—monthly updates—not real-time like Yelp.

Importantly, **our system is complementary, not a replacement**. Use our system to discover the *area*, then use Yelp to pick a specific restaurant within that area. Best of both worlds.

**[TRANSITION TO SLIDE 15]**

---

## DISCUSSION & LIMITATIONS [13:30-16:00]

**[Slide 15: Key Findings]**

Let me summarize our key findings and their implications.

**Finding one**: Taxi drop-offs are indeed a valid proxy for dining popularity. They correlate 0.67 with Yelp ratings, which is a strong positive relationship.

**Finding two**: Manhattan dominates with 68% of hotspots, but this reflects population density and taxi availability. Our method still successfully captures outer borough gems—Williamsburg, Astoria, and parts of Brooklyn show up prominently.

**Finding three**: Incorporating accessibility **significantly changes rankings**. When we compared popularity-only rankings to our full accessibility-aware rankings, 30% of hotspots changed position. Some highly popular areas rank lower because they're hard to reach. Some moderately popular areas rank higher because they're extremely accessible.

What are the implications?

For **urban planning**, this identifies underserved areas. If a neighborhood has residential density but no dining hotspots within a 15-minute walk, that's a gap.

For **business**, if you're opening a restaurant, our hotspot scores plus accessibility analysis can inform location decisions. Find an area with high accessibility but currently lower restaurant density—market opportunity.

For **tourism**, give visitors data-driven recommendations that account for where they're staying and how they prefer to travel.

**[TRANSITION TO SLIDE 16]**

**[Slide 16: Limitations & Future Work]**

Now, let me be completely transparent about limitations, because every study has them.

**First, data representativeness.** Taxi users are not the general population. They skew higher income. Tourists are overrepresented in Manhattan. People taking taxis to dinner might prefer different restaurants than people who walk. These are real biases we need to acknowledge.

**Second, the cold start problem.** A restaurant that opened last month has no historical taxi data, so our system won't recommend it even if it's fantastic. This is a known limitation of all behavior-based systems.

**Third, our transit routing is simplified.** True schedule-based routing—where the system knows the 2 train leaves at 3:47 PM—is complex. We approximated with a representative time window, but that's not as accurate as it could be.

**Fourth, static analysis.** We don't account for real-time traffic, construction, service disruptions, or weather. A rainy day changes accessibility dramatically.

For future work, we have an exciting roadmap:

1. Implement full schedule-based transit routing using the r5py library, which is state-of-the-art for multi-modal routing.

2. Use machine learning to optimize our temporal weights from data rather than relying on heuristics.

3. Conduct a **user study**. We want actual participants to compare our recommendations against Yelp's and tell us which they prefer. That's the gold standard for validation.

4. **Expand to other cities**—San Francisco, Chicago, Boston. Does this approach generalize?

5. Eventually, support **real-time updates** using streaming taxi data and live GTFS-RT feeds.

**[TRANSITION TO SLIDE 17]** (optional, if time permits)

---

## TECHNICAL HIGHLIGHTS [16:00-17:00] (Optional)

**[Slide 17: Computational Challenges]**

For the more technically inclined folks in the room, let me share some implementation highlights.

Processing 50 million records was computationally challenging. Our initial HDBSCAN runs took about 8 hours. That's not viable for iterative experimentation.

We solved this using **H3 hexagonal spatial indexing**—a system developed by Uber for geospatial aggregation. We aggregated taxi trips into hexagonal grid cells at resolution 10, which is about 15-meter edge length.

This reduced our 50 million individual points to about 500,000 hexagons—a 96% data reduction. Compute time dropped from 8 hours to about 15 minutes.

Another critical detail: **coordinate reference systems**. We store data in WGS84—standard latitude/longitude—for compatibility. But for analysis, we project to EPSG 2263, which is NAD83 State Plane for New York Long Island. This gives us metric coordinates where distances are meaningful. You cannot use latitude/longitude directly in Euclidean distance-based clustering—you'll get distorted results.

Our tech stack is pure Python: pandas and geopandas for data manipulation, HDBSCAN for clustering, OSMnx for network analysis, and Folium for interactive web maps.

**[TRANSITION TO SLIDE 18]**

**[Slide 18: Reproducibility]**

In the spirit of open science, this entire project is **fully reproducible**.

Our GitHub repository contains all source code with comprehensive documentation, configuration files specifying every parameter, Jupyter notebooks walking through each analysis step, unit tests using pytest, and a detailed README with installation instructions.

We've frozen all library versions in requirements.txt, set random seeds to 42 for any stochastic algorithms, and documented every data source with URLs and download dates.

Anyone with the data and our code should get identical results. I encourage you to try it yourself.

*[Point to QR code if displayed]*

Scan this QR code or visit the GitHub link on the slide.

---

## CONCLUSIONS [17:00-18:00]

**[Slide 19: Conclusions]**

Let me wrap up.

**What we accomplished:**

We developed a novel methodology integrating density-based clustering with multi-modal accessibility analysis. We identified and validated 47 dining hotspots across New York City with 87% accuracy against ground truth. We created a working recommendation engine that successfully balances popularity and accessibility. And we delivered a fully reproducible open-source pipeline that others can build upon.

**Our key contribution** is demonstrating that revealed preference data—where people actually go—can power more objective, spatially-aware recommendations than traditional review-based systems.

This framework is generalizable. It's not limited to restaurants or New York City. The same approach could identify popular nightlife areas, cultural venues, or parks. It could work in any city with mobility data.

Ultimately, our system provides data-driven recommendations that respect both **what's popular** and **what's reachable**. It answers the question: "Where should I dine?" with geographic intelligence, not just crowdsourced opinions.

Before I close, I want to acknowledge those who made this possible: Professor [Name] for invaluable guidance, NYC Open Data for providing these rich datasets, the OpenStreetMap community for maintaining such detailed geographic data, and the developers of HDBSCAN and OSMnx for creating the tools that made this analysis feasible.

Thank you for your attention. I'm happy to take questions.

**[TRANSITION TO SLIDE 20]**

---

## Q&A PREPARATION [18:00-25:00]

**[Slide 20: Questions?]**

### Sample Responses to Anticipated Questions:

**Q: "Why not use Yelp check-in data instead of taxi data?"**

A: "Great question. Yelp check-ins would be more directly related to dining, but they have two problems. First, coverage: Yelp has maybe 1-2 million check-ins per year in NYC compared to our 50 million taxi trips. Second, user bias: Yelp check-ins skew heavily toward young, tech-savvy smartphone users. Taxi data, while imperfect, captures a broader demographic. That said, combining both sources would be ideal for future work."

---

**Q: "How do you address the cold start problem for new restaurants?"**

A: "That's actually one of our acknowledged limitations. Currently, we don't handle it well. A restaurant that opened two months ago simply won't appear in our hotspots yet. One solution we're exploring for future work is a hybrid approach: use our taxi-based hotspots for established areas, but supplement with Yelp ratings for restaurants with less than, say, 3-6 months of history. That way we get the best of both worlds."

---

**Q: "Did you validate against actual user preferences through a study?"**

A: "Not yet, and that's our number one priority for future work. We did statistical validation and ground-truth comparison, which gave us confidence in the technical accuracy. But the real test is: do users actually prefer our recommendations over Yelp's? We're designing a user study where participants get recommendations from both systems and rate them on relevance, usefulness, and satisfaction. That will be the gold standard validation."

---

**Q: "Why HDBSCAN specifically over other clustering methods?"**

A: "We actually compared several. K-means was too rigid—it assumes spherical clusters and forces every point into a cluster, including outliers. Standard DBSCAN is better but requires manually setting epsilon, the neighborhood radius, which is tricky when density varies across the city. HDBSCAN extends DBSCAN by using a hierarchy of densities, so it adapts to varying cluster densities automatically. In our experiments, HDBSCAN achieved silhouette scores 15% higher than DBSCAN and 30% higher than K-means. Plus, it handles noise elegantly, which is important for those random isolated restaurants."

---

**Q: "How often would you need to update this?"**

A: "Excellent question. Dining patterns are relatively stable—they don't change week to week. I'd say **monthly updates** would be ideal to capture new restaurant openings and emerging trends. Quarterly would be the minimum to stay current. Seasonally might be necessary to account for, say, outdoor dining in summer versus indoor-only in winter. Long-term, we envision **streaming updates**: as new taxi data comes in each day, incrementally update the hotspot scores. That's technically feasible using online clustering algorithms, though we haven't implemented it yet."

---

**Q: "Could this work in cities without taxi data?"**

A: "Absolutely, with adaptations. You'd need a proxy for foot traffic. Options include: Google Popular Times data, which shows hourly visit patterns based on anonymized mobile location. Credit card transaction density from companies like Visa if you can get that data. Social media check-ins from Foursquare, Instagram geotags, or Twitter. Or even pedestrian counts from sensors if the city has them. The key principle is finding any data source that reflects actual behavior at dining establishments. NYC is great because taxi data is public and comprehensive, but the framework generalizes."

---

**Q: "Doesn't this bias toward wealthy neighborhoods with more taxis?"**

A: "Yes, that's a real concern we address in our limitations section. Taxi usage definitely skews higher income and toward Manhattan tourist areas. One mitigation we're considering is **socioeconomic weighting**: normalize taxi drop-off counts by neighborhood median income to account for different baseline taxi usage rates. Another approach is to supplement with data sources that have different demographic profiles—public transit data, for instance, has much broader socioeconomic coverage. A truly unbiased system would integrate multiple mobility data sources."

---

**Q: "How do you handle special events—like Restaurant Week or New Year's Eve?"**

A: "Currently, we don't explicitly account for special events, which is a limitation. Our temporal weights are based on typical weekly patterns. A more sophisticated version would: one, identify anomalous spikes in the data and either exclude them or weight them differently; two, integrate an events calendar—NYC has public data on parades, festivals, street fairs—and apply special handling; three, model seasonality explicitly using time series methods. For a production system serving real users, that would be essential. For our research prototype demonstrating the methodology, we stuck with typical patterns."

---

**Q: "What's the biggest technical challenge you faced?"**

A: "Honestly, **data size**. Fifty gigabytes doesn't sound huge in the era of big data, but when you're clustering tens of millions of spatial points with HDBSCAN—which has O(n log n) complexity—it pushes the limits of consumer hardware. H3 spatial aggregation saved us. The second challenge was coordinate reference systems. Mixing WGS84 and projected coordinates seems trivial in theory, but getting it wrong leads to subtle bugs where distances are off by factors of two or more. We spent several days debugging phantom errors that turned out to be CRS mismatches."

---

**Q: "How long did this take you?"**

A: "End to end, about 10 weeks. Week one was setup and data acquisition. Weeks two was literature review—reading 40-some papers on clustering, accessibility, and urban mobility. Weeks three and four were data processing: writing the ETL pipelines, cleaning data, merging datasets. Weeks five and six were analysis: clustering experiments, parameter tuning, building the recommendation engine. Week seven was validation. Weeks eight and nine were writing the report and creating visualizations. Week ten was presentation prep and final polish. If I were doing it again, I'd budget 12 weeks to allow for unexpected challenges."

---

**Closing Remarks if Time Remains:**

"I just want to emphasize: this project demonstrates the power of geospatial data science. We took multiple large, messy, real-world datasets, applied rigorous statistical methods, and produced insights that could genuinely help people discover better dining experiences. That's the promise of GIS—not just making maps, but answering real questions with spatial thinking. Thank you again."

---

## TIMING GUIDE

| Time | Slide | Section | Key Action |
|------|-------|---------|------------|
| 0:00 | 1 | Opening | Hook audience with project overview |
| 0:30 | 2 | Problem | Explain limitations of existing systems |
| 1:30 | 3 | Solution | Introduce "voting with feet" concept |
| 2:30 | 4 | Data | Describe datasets |
| 3:30 | 5 | Processing | Show data reduction pipeline |
| 4:30 | 6 | Methodology | Three-phase overview |
| 5:00 | 7 | Clustering | Explain HDBSCAN in depth |
| 7:00 | 8 | Weighting | Temporal weighting rationale |
| 8:30 | 9 | Intersection | Hotspot identification |
| 9:30 | 10 | Accessibility | Multi-modal networks |
| 10:30 | 11 | Results | Top hotspots |
| 11:30 | 12 | Validation | Statistical rigor |
| 12:30 | 13 | Demo | Recommendation example |
| 14:00 | 14 | Comparison | vs. existing systems |
| 15:00 | 15 | Findings | Implications |
| 16:00 | 16 | Limitations | Honesty about weaknesses |
| 17:00 | 17-18 | Technical (optional) | Implementation details |
| 17:30 | 19 | Conclusions | Wrap up |
| 18:00 | 20 | Q&A | Questions |

**Total: 18-20 minutes + Q&A**

---

**Last Updated**: 2025-11-09
**Version**: 1.0
