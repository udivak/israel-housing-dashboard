// English dictionary — source of truth for all UI strings.
// he.ts is typed against `Messages` so any missing/extra key is a compile error.
const en = {
  // ---- meta ----
  "meta.title": "Israel Housing — modeled, mapped, priced",
  "meta.description":
    "AI-powered intelligence platform for the Israeli real-estate market: live listings, seven models, interactive maps.",

  // ---- nav / header ----
  "nav.home": "Home",
  "nav.map": "Map",
  "nav.stats": "Stats",
  "nav.predict": "Predict",
  "nav.settings": "Settings",
  "header.brand": "Israel Housing",
  "header.searchPlaceholder": "Search address, street, city…",
  "toggle.aria": "Language",

  // ---- hero ----
  "hero.live": "Live",
  "hero.titleLead": "Israel’s housing market,",
  "hero.titleGradient": "across {count} cities — modeled, mapped, priced.",
  "hero.subtitle":
    "Listings collected nightly, enriched with OSM context, indexed by H3 cells, and priced by seven ML models — served live through a FastAPI stack.",
  "hero.openMap": "Open the map →",
  "hero.tryPrediction": "Try a prediction",

  // ---- map: filters ----
  "filters.title": "Filters",
  "filters.reset": "Reset",
  "filters.clear": "Clear {field}",
  "filters.group.location": "Location",
  "filters.group.price": "Price (₪)",
  "filters.group.size": "Size",
  "filters.group.date": "Date",
  "filters.group.typeSource": "Type & source",
  "filters.city": "City",
  "filters.neighborhood": "Neighborhood",
  "filters.allCities": "All cities",
  "filters.allNeighborhoods": "All neighborhoods",
  "filters.min": "Min",
  "filters.max": "Max",
  "filters.minRooms": "Min rooms",
  "filters.maxRooms": "Max rooms",
  "filters.minArea": "Min m²",
  "filters.maxArea": "Max m²",
  "filters.from": "From",
  "filters.to": "To",
  "filters.propertyType": "Property type",
  "filters.source": "Source",
  "filters.all": "All",
  "filters.active.city": "City: {value}",
  "filters.active.neighborhood": "Neighborhood: {value}",
  "filters.active.minPrice": "≥ ₪{value}",
  "filters.active.maxPrice": "≤ ₪{value}",
  "filters.active.minRooms": "≥ {value} rooms",
  "filters.active.maxRooms": "≤ {value} rooms",
  "filters.active.minArea": "≥ {value}m²",
  "filters.active.maxArea": "≤ {value}m²",
  "filters.active.fromDate": "From {value}",
  "filters.active.toDate": "To {value}",
  "filters.active.propertyType": "Type: {value}",
  "filters.active.source": "Source: {value}",

  // ---- map: property type labels (he value = the Hebrew DB value itself) ----
  "ptype.apartment": "Apartment",
  "ptype.apartmentTower": "Apartment in tower",
  "ptype.cottage": "Cottage",
  "ptype.penthouse": "Penthouse",
  "ptype.duplex": "Duplex",
  "ptype.gardenApartment": "Garden apartment",

  // ---- map: search / canvas / KPIs ----
  "search.placeholder": "Search street, city, address...",
  "kpi.transactions": "Transactions",
  "kpi.avgPrice": "Avg price",
  "kpi.avgPricePerSqm": "Avg ₪/m²",
  "kpi.citiesInData": "Cities in data",
  "map.loading": "Loading map…",
  "map.error": "Map error: {value}",
  "map.truncated": "Showing up to 2,000 results — zoom in or add filters",

  // ---- property panel / detail ----
  "property.listedPrice": "Listed price",
  "property.pricePerSqm": "₪/m²",
  "property.rooms": "Rooms",
  "property.area": "Area",
  "property.date": "Date",
  "property.openProperty": "Open property",
  "property.fallbackName": "Property",

  // ---- ai page header ----
  "ai.eyebrow": "AI",
  "ai.title": "Price prediction",
  "ai.subtitle":
    "Playground to experiment with features, swap between models, and inspect ensemble consensus.",

  // ---- ai: playground ----
  "pg.title": "Playground",
  "pg.subtitle": "Tune features by hand, swap models, and stress-test the ensemble.",
  "pg.eyebrow": "Predict",
  "pg.addressSection": "Property address",
  "pg.addressPlaceholder": "e.g., Rothschild 22, Tel Aviv",
  "pg.search": "Search",
  "pg.addressNotFound": "Address not found",
  "pg.geocodingError": "Geocoding error",
  "pg.compareAll": "Compare all models",
  "pg.champion": "Champion (default)",
  "pg.runAll": "Run all",
  "pg.predict": "Predict",
  "pg.predicted": "Predicted · {model}",
  "pg.consensus": "Consensus (median)",
  "pg.spreadStddev": "spread {spread} · stddev {stddev}",
  "pg.predictionError":
    "Prediction error. Check that prediction_service is running and a champion model is set.",
  "pg.field.area": "Area (m²)",
  "pg.field.rooms": "Rooms",
  "pg.field.floor": "Floor",
  "pg.field.buildingFloors": "Building floors",
  "pg.field.yearBuilt": "Year built",
  "pg.field.propertyAge": "Property age (yr)",
  "pg.field.year": "Transaction year",
  "pg.field.month": "Month (1–12)",
  "pg.field.quarter": "Quarter (1–4)",
  "pg.field.logArea": "log(area)",
  "pg.field.logAreaHint": "= ln(area_sqm)",

  // ---- ai: models ----
  "models.title": "Trained models",
  "models.subtitle": "Live from the registry. The champion drives default predictions.",
  "models.eyebrow": "Garden",
  "models.empty": "No models available. Start the prediction_service to populate this list.",
  "models.modelTag": "model",
  "models.best": "★ best",
  "metric.r2": "R²",
  "metric.mae": "MAE",
  "metric.mape": "MAPE",

  // ---- home: KPI strip ----
  "home.kpi.listings": "Listings",
  "home.kpi.listingsHint": "transactions in scope",
  "home.kpi.avgPriceHint": "across all cities",
  "home.kpi.citiesHint": "{count} cities",
  "home.kpi.bestModel": "Best model R²",
  "home.kpi.noModel": "no model loaded",

  // ---- home: map preview ----
  "home.map.loadingPreview": "Loading preview…",
  "home.map.title": "Live map preview",
  "home.map.subtitle": "Cyan-to-violet heat across H3 cells. Click to dive in.",
  "home.map.openMap": "Open the map",
  "home.map.telAviv": "Tel Aviv–Yafo",
  "home.map.explore": "Explore →",
  "home.map.hottest": "Hottest market",
  "home.map.bestValue": "Best value",
  "home.map.trending": "Trending up",
  "home.map.perSqm": "{value} /m²",
  "home.map.yoy": "YoY",

  // ---- home: how it works ----
  "how.title": "Under the hood",
  "how.subtitle": "Four services, one pipeline. Built to be reproducible end-to-end.",
  "how.eyebrow": "How it works",
  "how.step1.title": "Collect",
  "how.step1.body":
    "Nightly Playwright crawls of nadlan.gov.il and partner sources feed a Mongo store.",
  "how.step2.title": "Enrich",
  "how.step2.body":
    "Each transaction joins OSM context, indexes into H3 r5/r7/r8 cells, and gets price-index adjustments.",
  "how.step3.title": "Model",
  "how.step3.body":
    "Seven scikit-learn / boosting regressors are trained on the enriched feature table — a champion is elected.",
  "how.step4.title": "Serve",
  "how.step4.body": "FastAPI + Next.js + MapLibre stream predictions, KPIs, and tiles live.",

  // ---- home: inline predict ----
  "home.predict.title": "Predict an apartment in 10 seconds",
  "home.predict.subtitle":
    "Try a real address. The model returns an estimate with a confidence range.",
  "home.predict.address": "Address",
  "home.predict.example": "Dizengoff 99, Tel Aviv",
  "home.predict.try": "Try: {example}",
  "home.predict.cta": "Predict",
  "home.predict.geoFail": "Couldn’t locate \"{address}\".",
  "home.predict.resultLabel": "Predicted price · {model}",
  "home.predict.resultHint": "log-price {value} · features auto-derived from your inputs",
  "home.predict.error":
    "Prediction failed. Verify the prediction_service is running and a champion model is set.",

  // ---- home: model garden section ----
  "home.garden.title": "Seven models, one prediction",
  "home.garden.subtitle":
    "Each apartment is priced by an ensemble. The champion drives default predictions; the others let you challenge it.",
  "home.garden.compareAll": "Compare all",

  // ---- settings ----
  "settings.title": "Settings",
  "settings.subtitle": "System status, models, and data sources.",
  "settings.eyebrow": "Configuration",
  "settings.health": "System health",
  "settings.models": "Models",
  "settings.sources": "Data sources · freshness",
  "settings.preferences": "Preferences",
  "settings.online": "online",
  "settings.down": "down",
  "settings.checking": "checking…",
  "settings.statusDown": "DOWN",
  "settings.apiBaseUrl": "API base URL",
  "settings.apiDocs": "Swagger / API docs",
  "settings.modelsAvailable": "{count} trained models available. Switching the champion requires:",
  "settings.noData": "No data yet",
  "settings.transactionsCount": "{count} transactions",
  "settings.activeFilters": "Active filters",
  "settings.fieldsCount": "{count} fields",
  "settings.resetFilters": "Reset filters",

  // ---- stats overview ----
  "stats.title": "Stats overview",
  "stats.filtered": "Filtered to {city}. Clear the field to see the country-wide view.",
  "stats.defaultSubtitle": "Country-wide rollups. Filter by city to focus.",
  "stats.eyebrow": "Statistics",
  "stats.filterPlaceholder": "Filter by city…",
  "stats.allCities": "all cities",
  "stats.citiesInScope": "Cities in scope",

  // ---- charts (shared) ----
  "chart.countryWide": "Country-wide",
  "chart.avg": "avg",
  "chart.month": "Month",
  "chart.quarter": "Quarter",
  "chart.year": "Year",
  "chart.cities": "Cities",
  "chart.neighborhoods": "Neighborhoods",
  "chart.citiesWord": "cities",
  "chart.neighborhoodsWord": "neighborhoods",
  "chart.timeseriesTitle": "Average price over time",
  "chart.topCitiesTitle": "Most expensive cities & neighborhoods",
  "chart.topCitiesSubtitle": "By avg ₪/m² · top 15 {level}",
  "chart.yoyTitle": "Heating cities",
  "chart.yoySubtitle": "YoY ₪/m² change · top 20",
  "chart.colCity": "City",
  "chart.colYoy": "YoY",
  "chart.colCurrent": "Current ₪/m²",
  "chart.colDeals": "Deals",
  "chart.seasonalityTitle": "Seasonality",
  "chart.seasonalitySubtitle": "Transactions by month",
  "chart.mon1": "Jan",
  "chart.mon2": "Feb",
  "chart.mon3": "Mar",
  "chart.mon4": "Apr",
  "chart.mon5": "May",
  "chart.mon6": "Jun",
  "chart.mon7": "Jul",
  "chart.mon8": "Aug",
  "chart.mon9": "Sep",
  "chart.mon10": "Oct",
  "chart.mon11": "Nov",
  "chart.mon12": "Dec",
  "chart.distributionTitle": "Distribution",
  "chart.distPrice": "Price",
  "chart.bySource": "By source",
  "chart.records": "{count} records",
  "chart.byPropertyType": "By property type",

  // ---- property detail page ----
  "property.notFound": "Property not found: {id}",
  "property.backToMap": "Back to map",

  // ---- property: prediction panel ----
  "prediction.predicted": "Predicted",
  "prediction.listed": "Listed",
  "prediction.vsListed": "{delta}% vs listed",
  "prediction.confidence": "Model confidence (spread)",
  "prediction.modelLine": "Model: {model}",
  "prediction.error":
    "Prediction error. Verify prediction_service is running and a champion model is set.",

  // ---- property: similar ----
  "similar.title": "Similar properties",
  "similar.within": "within 800m",
  "similar.empty": "No nearby properties found",
  "similar.roomsShort": "{count} rm",

  // ---- shared ----
  "common.close": "Close",
  "common.error": "error",
  "common.loading": "Loading…",
  "unit.sqm": "m²",
} as const;

// Keys are fixed (typo in a t("…") call fails the build); values are any string,
// so he.ts must supply every key but with its own translated text.
export type Messages = Record<keyof typeof en, string>;
export default en;
