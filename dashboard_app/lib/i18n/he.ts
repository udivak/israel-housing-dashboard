import type { Messages } from "./en";

// Hebrew dictionary. Typed as Messages → missing/extra keys fail the build.
// Drafted by Claude; pending native review.
const he: Messages = {
  // ---- meta ----
  "meta.title": "דיור בישראל — ממודל, ממופה, מתומחר",
  "meta.description":
    "פלטפורמת מודיעין מבוססת בינה מלאכותית לשוק הנדל\"ן הישראלי: עסקאות חיות, שבעה מודלים, מפות אינטראקטיביות.",

  // ---- nav / header ----
  "nav.home": "בית",
  "nav.map": "מפה",
  "nav.stats": "סטטיסטיקות",
  "nav.predict": "חיזוי",
  "nav.settings": "הגדרות",
  "header.brand": "דיור בישראל",
  "header.searchPlaceholder": "חיפוש כתובת, רחוב, עיר…",
  "toggle.aria": "שפה",

  // ---- hero ----
  "hero.live": "חי",
  "hero.titleLead": "שוק הדיור של ישראל,",
  "hero.titleGradient": "ב-{count} ערים — ממודל, ממופה, מתומחר.",
  "hero.subtitle":
    "עסקאות נאספות מדי לילה, מועשרות בהקשר OSM, מאונדקסות בתאי H3 ומתומחרות על ידי שבעה מודלים של למידת מכונה — מוגשות בזמן אמת דרך שכבת FastAPI.",
  "hero.openMap": "← למפה",
  "hero.tryPrediction": "נסו חיזוי",

  // ---- map: filters ----
  "filters.title": "מסננים",
  "filters.reset": "איפוס",
  "filters.clear": "נקה {field}",
  "filters.group.location": "מיקום",
  "filters.group.price": "מחיר (₪)",
  "filters.group.size": "גודל",
  "filters.group.date": "תאריך",
  "filters.group.typeSource": "סוג ומקור",
  "filters.city": "עיר",
  "filters.neighborhood": "שכונה",
  "filters.allCities": "כל הערים",
  "filters.allNeighborhoods": "כל השכונות",
  "filters.min": "מינ׳",
  "filters.max": "מקס׳",
  "filters.minRooms": "מינ׳ חדרים",
  "filters.maxRooms": "מקס׳ חדרים",
  "filters.minArea": "מינ׳ מ״ר",
  "filters.maxArea": "מקס׳ מ״ר",
  "filters.from": "מתאריך",
  "filters.to": "עד תאריך",
  "filters.propertyType": "סוג נכס",
  "filters.source": "מקור",
  "filters.all": "הכול",
  "filters.active.city": "עיר: {value}",
  "filters.active.neighborhood": "שכונה: {value}",
  "filters.active.minPrice": "≥ ₪{value}",
  "filters.active.maxPrice": "≤ ₪{value}",
  "filters.active.minRooms": "≥ {value} חדרים",
  "filters.active.maxRooms": "≤ {value} חדרים",
  "filters.active.minArea": "≥ {value} מ״ר",
  "filters.active.maxArea": "≤ {value} מ״ר",
  "filters.active.fromDate": "מתאריך {value}",
  "filters.active.toDate": "עד תאריך {value}",
  "filters.active.propertyType": "סוג: {value}",
  "filters.active.source": "מקור: {value}",

  // ---- map: property type labels (he value = the Hebrew DB value itself) ----
  "ptype.apartment": "דירה",
  "ptype.apartmentTower": "דירה בבית קומות",
  "ptype.cottage": "קוטג'",
  "ptype.penthouse": "פנטהאוז",
  "ptype.duplex": "דופלקס",
  "ptype.gardenApartment": "דירת גן",

  // ---- map: search / canvas / KPIs ----
  "search.placeholder": "חיפוש רחוב, עיר, כתובת...",
  "kpi.transactions": "עסקאות",
  "kpi.avgPrice": "מחיר ממוצע",
  "kpi.avgPricePerSqm": "ממוצע ₪/מ״ר",
  "kpi.citiesInData": "ערים בנתונים",
  "map.loading": "טוען מפה…",
  "map.error": "שגיאת מפה: {value}",
  "map.truncated": "מוצגות עד 2,000 תוצאות — התקרבו או הוסיפו מסננים",

  // ---- property panel / detail ----
  "property.listedPrice": "מחיר מבוקש",
  "property.pricePerSqm": "₪/מ״ר",
  "property.rooms": "חדרים",
  "property.area": "שטח",
  "property.date": "תאריך",
  "property.openProperty": "פתח נכס",
  "property.fallbackName": "נכס",

  // ---- ai page header ----
  "ai.eyebrow": "בינה מלאכותית",
  "ai.title": "חיזוי מחיר",
  "ai.subtitle":
    "מגרש משחקים להתנסות במאפיינים, החלפה בין מודלים ובחינת הקונצנזוס של האנסמבל.",

  // ---- ai: playground ----
  "pg.title": "מגרש משחקים",
  "pg.subtitle": "כוונון מאפיינים ידני, החלפת מודלים ובדיקת עומס של האנסמבל.",
  "pg.eyebrow": "חיזוי",
  "pg.addressSection": "כתובת הנכס",
  "pg.addressPlaceholder": "לדוגמה: רוטשילד 22, תל אביב",
  "pg.search": "חיפוש",
  "pg.addressNotFound": "הכתובת לא נמצאה",
  "pg.geocodingError": "שגיאת גיאוקודינג",
  "pg.compareAll": "השוואת כל המודלים",
  "pg.champion": "אלוף (ברירת מחדל)",
  "pg.runAll": "הרץ הכול",
  "pg.predict": "חיזוי",
  "pg.predicted": "חזוי · {model}",
  "pg.consensus": "קונצנזוס (חציון)",
  "pg.spreadStddev": "טווח {spread} · סטיית תקן {stddev}",
  "pg.predictionError":
    "שגיאת חיזוי. ודאו ש-prediction_service פועל ושהוגדר מודל אלוף.",
  "pg.field.area": "שטח (מ״ר)",
  "pg.field.rooms": "חדרים",
  "pg.field.floor": "קומה",
  "pg.field.buildingFloors": "קומות בבניין",
  "pg.field.yearBuilt": "שנת בנייה",
  "pg.field.propertyAge": "גיל הנכס (שנים)",
  "pg.field.year": "שנת עסקה",
  "pg.field.month": "חודש (1–12)",
  "pg.field.quarter": "רבעון (1–4)",
  "pg.field.logArea": "log(שטח)",
  "pg.field.logAreaHint": "= ln(area_sqm)",

  // ---- ai: models ----
  "models.title": "מודלים מאומנים",
  "models.subtitle": "ישירות מהרישום. האלוף מניע את חיזויי ברירת המחדל.",
  "models.eyebrow": "גן",
  "models.empty": "אין מודלים זמינים. הפעילו את prediction_service כדי לאכלס רשימה זו.",
  "models.modelTag": "מודל",
  "models.best": "★ הטוב ביותר",
  "metric.r2": "R²",
  "metric.mae": "MAE",
  "metric.mape": "MAPE",

  // ---- home: KPI strip ----
  "home.kpi.listings": "עסקאות",
  "home.kpi.listingsHint": "עסקאות בתחום",
  "home.kpi.avgPriceHint": "בכל הערים",
  "home.kpi.citiesHint": "{count} ערים",
  "home.kpi.bestModel": "R² של המודל הטוב ביותר",
  "home.kpi.noModel": "לא נטען מודל",

  // ---- home: map preview ----
  "home.map.loadingPreview": "טוען תצוגה מקדימה…",
  "home.map.title": "תצוגה מקדימה של המפה",
  "home.map.subtitle": "מפת חום בגווני תכלת-סגול על תאי H3. לחצו כדי לצלול פנימה.",
  "home.map.openMap": "פתח את המפה",
  "home.map.telAviv": "תל אביב–יפו",
  "home.map.explore": "← גלו",
  "home.map.hottest": "השוק החם ביותר",
  "home.map.bestValue": "התמורה הטובה ביותר",
  "home.map.trending": "במגמת עלייה",
  "home.map.perSqm": "{value} /מ״ר",
  "home.map.yoy": "שנה/שנה",

  // ---- home: how it works ----
  "how.title": "מאחורי הקלעים",
  "how.subtitle": "ארבעה שירותים, צינור אחד. בנוי לשחזור מקצה לקצה.",
  "how.eyebrow": "איך זה עובד",
  "how.step1.title": "איסוף",
  "how.step1.body":
    "סריקות Playwright ליליות של nadlan.gov.il ומקורות שותפים מזינות מאגר Mongo.",
  "how.step2.title": "העשרה",
  "how.step2.body":
    "כל עסקה מצורפת להקשר OSM, מאונדקסת בתאי H3 ברמות r5/r7/r8 ומקבלת התאמות מדד מחירים.",
  "how.step3.title": "מידול",
  "how.step3.body":
    "שבעה רגרסורים של scikit-learn / boosting מאומנים על טבלת המאפיינים המועשרת — ונבחר אלוף.",
  "how.step4.title": "הגשה",
  "how.step4.body": "FastAPI + Next.js + MapLibre מזרימים חיזויים, מדדים ואריחים בזמן אמת.",

  // ---- home: inline predict ----
  "home.predict.title": "חיזוי דירה ב-10 שניות",
  "home.predict.subtitle": "נסו כתובת אמיתית. המודל מחזיר הערכה עם טווח ביטחון.",
  "home.predict.address": "כתובת",
  "home.predict.example": "דיזנגוף 99, תל אביב",
  "home.predict.try": "נסו: {example}",
  "home.predict.cta": "חיזוי",
  "home.predict.geoFail": "לא הצלחנו לאתר את \"{address}\".",
  "home.predict.resultLabel": "מחיר חזוי · {model}",
  "home.predict.resultHint": "log-price {value} · המאפיינים נגזרים אוטומטית מהקלט שלך",
  "home.predict.error":
    "החיזוי נכשל. ודאו ש-prediction_service פועל ושהוגדר מודל אלוף.",

  // ---- home: model garden section ----
  "home.garden.title": "שבעה מודלים, חיזוי אחד",
  "home.garden.subtitle":
    "כל דירה מתומחרת על ידי אנסמבל. האלוף מניע את חיזויי ברירת המחדל; האחרים מאפשרים לכם לאתגר אותו.",
  "home.garden.compareAll": "השוואת הכול",

  // ---- settings ----
  "settings.title": "הגדרות",
  "settings.subtitle": "סטטוס המערכת, מודלים ומקורות נתונים.",
  "settings.eyebrow": "תצורה",
  "settings.health": "תקינות המערכת",
  "settings.models": "מודלים",
  "settings.sources": "מקורות נתונים · עדכניות",
  "settings.preferences": "העדפות",
  "settings.online": "מקוון",
  "settings.down": "מושבת",
  "settings.checking": "בודק…",
  "settings.statusDown": "מושבת",
  "settings.apiBaseUrl": "כתובת בסיס של ה-API",
  "settings.apiDocs": "Swagger / תיעוד API",
  "settings.modelsAvailable": "{count} מודלים מאומנים זמינים. החלפת האלוף דורשת:",
  "settings.noData": "אין נתונים עדיין",
  "settings.transactionsCount": "{count} עסקאות",
  "settings.activeFilters": "מסננים פעילים",
  "settings.fieldsCount": "{count} שדות",
  "settings.resetFilters": "איפוס מסננים",

  // ---- stats overview ----
  "stats.title": "סקירת סטטיסטיקות",
  "stats.filtered": "מסונן ל{city}. נקו את השדה לתצוגה הארצית.",
  "stats.defaultSubtitle": "סיכומים ארציים. סננו לפי עיר כדי להתמקד.",
  "stats.eyebrow": "סטטיסטיקות",
  "stats.filterPlaceholder": "סינון לפי עיר…",
  "stats.allCities": "כל הערים",
  "stats.citiesInScope": "ערים בתחום",

  // ---- charts (shared) ----
  "chart.countryWide": "ארצי",
  "chart.avg": "ממוצע",
  "chart.month": "חודש",
  "chart.quarter": "רבעון",
  "chart.year": "שנה",
  "chart.cities": "ערים",
  "chart.neighborhoods": "שכונות",
  "chart.citiesWord": "ערים",
  "chart.neighborhoodsWord": "שכונות",
  "chart.timeseriesTitle": "מחיר ממוצע לאורך זמן",
  "chart.topCitiesTitle": "הערים והשכונות היקרות ביותר",
  "chart.topCitiesSubtitle": "לפי ₪/מ״ר ממוצע · 15 ה{level} המובילות",
  "chart.yoyTitle": "ערים מתחממות",
  "chart.yoySubtitle": "שינוי שנתי ב-₪/מ״ר · 20 המובילות",
  "chart.colCity": "עיר",
  "chart.colYoy": "שנה/שנה",
  "chart.colCurrent": "₪/מ״ר נוכחי",
  "chart.colDeals": "עסקאות",
  "chart.seasonalityTitle": "עונתיות",
  "chart.seasonalitySubtitle": "עסקאות לפי חודש",
  "chart.mon1": "ינו׳",
  "chart.mon2": "פבר׳",
  "chart.mon3": "מרץ",
  "chart.mon4": "אפר׳",
  "chart.mon5": "מאי",
  "chart.mon6": "יוני",
  "chart.mon7": "יולי",
  "chart.mon8": "אוג׳",
  "chart.mon9": "ספט׳",
  "chart.mon10": "אוק׳",
  "chart.mon11": "נוב׳",
  "chart.mon12": "דצמ׳",
  "chart.distributionTitle": "התפלגות",
  "chart.distPrice": "מחיר",
  "chart.bySource": "לפי מקור",
  "chart.records": "{count} רשומות",
  "chart.byPropertyType": "לפי סוג נכס",

  // ---- property detail page ----
  "property.notFound": "הנכס לא נמצא: {id}",
  "property.backToMap": "חזרה למפה",

  // ---- property: prediction panel ----
  "prediction.predicted": "חזוי",
  "prediction.listed": "מבוקש",
  "prediction.vsListed": "{delta}% מול המבוקש",
  "prediction.confidence": "ביטחון המודל (טווח)",
  "prediction.modelLine": "מודל: {model}",
  "prediction.error":
    "שגיאת חיזוי. ודאו ש-prediction_service פועל ושהוגדר מודל אלוף.",

  // ---- property: similar ----
  "similar.title": "נכסים דומים",
  "similar.within": "ברדיוס 800 מ׳",
  "similar.empty": "לא נמצאו נכסים בקרבת מקום",
  "similar.roomsShort": "{count} חד׳",

  // ---- shared ----
  "common.close": "סגור",
  "common.error": "שגיאה",
  "common.loading": "טוען…",
  "unit.sqm": "מ״ר",
};

export default he;
