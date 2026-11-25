#!/usr/bin/env python3
"""Drishti live feed fetcher.

Pulls public feeds for India and writes one JSON file per database document
into an output folder:  meta.json air.json weather.json fires.json quakes.json
cyclones.json news.json

Usage:  python3 -I fetch_feeds.py <india.json topojson> <out_dir>
Standard library only.
"""
import json, sys, time, math, csv, io, re, os, urllib.request, urllib.parse, datetime as dt, email.utils
import xml.etree.ElementTree as ET

TOPO, OUT = sys.argv[1], sys.argv[2]
ONLY = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
os.makedirs(OUT, exist_ok=True)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
NOW = dt.datetime.now(IST)
UA = {"User-Agent": "drishti-india-desk/1.0"}
STATUS = {}

def get(url, tries=3, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa
            last = e
            time.sleep(4 * (i + 1))
    raise last

# ---------------- cities (lon, lat, state) ----------------
CITIES = [
 ("Srinagar",74.80,34.08,"JK"),("Jammu",74.86,32.73,"JK"),("Leh",77.58,34.15,"LA"),("Kargil",76.13,34.56,"LA"),
 ("Chandigarh",76.78,30.73,"CH"),("Ludhiana",75.86,30.90,"PB"),("Amritsar",74.87,31.63,"PB"),("Bathinda",74.95,30.21,"PB"),
 ("Shimla",77.17,31.10,"HP"),("Dharamshala",76.32,32.22,"HP"),("Dehradun",78.03,30.32,"UK"),("Haldwani",79.51,29.22,"UK"),
 ("Itanagar",93.61,27.08,"AR"),("Jaipur",75.79,26.91,"RJ"),("Jodhpur",73.02,26.24,"RJ"),("Kota",75.86,25.18,"RJ"),
 ("Gurugram",77.03,28.46,"HR"),("Faridabad",77.32,28.41,"HR"),("Panipat",76.97,29.39,"HR"),("Delhi",77.21,28.61,"DL"),
 ("Lucknow",80.95,26.85,"UP"),("Kanpur",80.33,26.45,"UP"),("Ghaziabad",77.44,28.67,"UP"),("Noida",77.39,28.54,"UP"),
 ("Varanasi",82.97,25.32,"UP"),("Agra",78.01,27.18,"UP"),("Patna",85.14,25.59,"BR"),("Muzaffarpur",85.39,26.12,"BR"),
 ("Gaya",85.00,24.79,"BR"),("Gangtok",88.61,27.33,"SK"),("Guwahati",91.74,26.14,"AS"),("Dibrugarh",94.91,27.47,"AS"),
 ("Kohima",94.11,25.67,"NL"),("Ahmedabad",72.57,23.02,"GJ"),("Surat",72.83,21.17,"GJ"),("Vadodara",73.18,22.31,"GJ"),
 ("Rajkot",70.80,22.30,"GJ"),("Bhopal",77.41,23.26,"MP"),("Indore",75.86,22.72,"MP"),("Gwalior",78.18,26.22,"MP"),
 ("Jabalpur",79.93,23.18,"MP"),("Raipur",81.63,21.25,"CG"),("Bilaspur",82.14,22.08,"CG"),("Ranchi",85.31,23.34,"JH"),
 ("Dhanbad",86.43,23.80,"JH"),("Kolkata",88.36,22.57,"WB"),("Siliguri",88.40,26.73,"WB"),("Asansol",86.98,23.68,"WB"),
 ("Shillong",91.89,25.58,"ML"),("Imphal",93.94,24.81,"MN"),("Daman",72.83,20.40,"DH"),("Silvassa",73.01,20.27,"DH"),
 ("Mumbai",72.88,19.08,"MH"),("Pune",73.86,18.52,"MH"),("Nagpur",79.09,21.15,"MH"),("Nashik",73.79,20.00,"MH"),
 ("Chhatrapati Sambhajinagar",75.34,19.88,"MH"),("Hyderabad",78.49,17.39,"TG"),("Warangal",79.59,17.97,"TG"),
 ("Bhubaneswar",85.82,20.30,"OD"),("Cuttack",85.88,20.46,"OD"),("Rourkela",84.85,22.26,"OD"),("Agartala",91.28,23.83,"TR"),
 ("Aizawl",92.72,23.73,"MZ"),("Panaji",73.83,15.49,"GA"),("Bengaluru",77.59,12.97,"KA"),("Mysuru",76.64,12.30,"KA"),
 ("Hubballi",75.12,15.36,"KA"),("Mangaluru",74.86,12.91,"KA"),("Visakhapatnam",83.22,17.69,"AP"),("Vijayawada",80.65,16.51,"AP"),
 ("Tirupati",79.42,13.63,"AP"),("Nellore",79.99,14.44,"AP"),("Sri Vijaya Puram",92.73,11.62,"AN"),("Kavaratti",72.64,10.57,"LD"),
 ("Thiruvananthapuram",76.94,8.52,"KL"),("Kochi",76.27,9.93,"KL"),("Kozhikode",75.78,11.25,"KL"),("Chennai",80.27,13.08,"TN"),
 ("Coimbatore",76.96,11.02,"TN"),("Madurai",78.12,9.93,"TN"),("Puducherry",79.81,11.94,"PY"),
]

# ---------------- state polygons from TopoJSON ----------------
NAMES = {"jammuandkashmir":"JK","ladakh":"LA","chandigarh":"CH","punjab":"PB","himachalpradesh":"HP","uttarakhand":"UK",
 "arunachalpradesh":"AR","rajasthan":"RJ","haryana":"HR","delhi":"DL","uttarpradesh":"UP","bihar":"BR","sikkim":"SK","assam":"AS",
 "nagaland":"NL","gujarat":"GJ","madhyapradesh":"MP","chhattisgarh":"CG","jharkhand":"JH","westbengal":"WB","meghalaya":"ML",
 "manipur":"MN","dadraandnagarhavelianddamananddiu":"DH","maharashtra":"MH","telangana":"TG","odisha":"OD","tripura":"TR",
 "mizoram":"MZ","goa":"GA","karnataka":"KA","andhrapradesh":"AP","andamanandnicobarislands":"AN","lakshadweep":"LD","kerala":"KL",
 "tamilnadu":"TN","puducherry":"PY"}
STATE_NAMES = {v: k for k, v in NAMES.items()}

def load_states(path):
    t = json.load(open(path))
    sc, tr = t["transform"]["scale"], t["transform"]["translate"]
    arcs = []
    for a in t["arcs"]:
        x = y = 0; pts = []
        for p in a:
            x += p[0]; y += p[1]
            pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        arcs.append(pts)
    def arc(i):
        return arcs[i] if i >= 0 else arcs[~i][::-1]
    def ring(ids):
        out = []
        for i in ids:
            pts = arc(i)
            out.extend(pts if not out else pts[1:])
        return out
    states = []
    for g in t["objects"]["states"]["geometries"]:
        code = NAMES.get(re.sub(r"[^a-z]", "", g["properties"]["st_nm"].lower().replace("&", "and")))
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        rings = [[ring(r) for r in poly] for poly in polys]
        xs = [p[0] for poly in rings for p in poly[0]]; ys = [p[1] for poly in rings for p in poly[0]]
        states.append((code, rings, (min(xs), min(ys), max(xs), max(ys))))
    return states

def inside(pt, r):
    x, y = pt; c = False; n = len(r); j = n - 1
    for i in range(n):
        xi, yi = r[i]; xj, yj = r[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            c = not c
        j = i
    return c

STATES = load_states(TOPO)
def state_of(lon, lat):
    for code, rings, bb in STATES:
        if not (bb[0] <= lon <= bb[2] and bb[1] <= lat <= bb[3]):
            continue
        for poly in rings:
            if inside((lon, lat), poly[0]) and not any(inside((lon, lat), h) for h in poly[1:]):
                return code
    return None

# ---------------- Indian National AQI ----------------
BP = {"pm25": [(0,30,0,50),(31,60,51,100),(61,90,101,200),(91,120,201,300),(121,250,301,400),(251,500,401,500)],
      "pm10": [(0,50,0,50),(51,100,51,100),(101,250,101,200),(251,350,201,300),(351,430,301,400),(431,800,401,500)]}
def sub(kind, c):
    if c is None: return None
    c = round(c)
    for lo, hi, ilo, ihi in BP[kind]:
        if c <= hi:
            return round(ilo + (ihi - ilo) * (max(c, lo) - lo) / ((hi - lo) or 1))
    return 500

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# ---------------- AIR (Open-Meteo CAMS) ----------------
def fetch_air():
    out = []; hours = None
    for part in chunks(CITIES, 45):
        q = urllib.parse.urlencode({"latitude": ",".join(str(c[2]) for c in part), "longitude": ",".join(str(c[1]) for c in part),
            "hourly": "pm2_5,pm10", "past_days": 4, "forecast_days": 1, "timezone": "Asia/Kolkata"})
        data = json.loads(get("https://air-quality-api.open-meteo.com/v1/air-quality?" + q))
        if isinstance(data, dict): data = [data]
        for c, d in zip(part, data):
            h = d["hourly"]; times = h["time"]; p25 = h["pm2_5"]; p10 = h["pm10"]
            nowkey = NOW.strftime("%Y-%m-%dT%H:00")
            end = times.index(nowkey) if nowkey in times else len(times) - 1
            start = end - 71
            aqi, pm = [], []
            for i in range(start, end + 1):
                w25 = [v for v in p25[max(0, i - 23):i + 1] if v is not None]
                w10 = [v for v in p10[max(0, i - 23):i + 1] if v is not None]
                subs = [x for x in (sub("pm25", sum(w25) / len(w25) if w25 else None), sub("pm10", sum(w10) / len(w10) if w10 else None)) if x is not None]
                a = max(subs) if subs else None
                aqi.append(a); pm.append(round(p25[i]) if p25[i] is not None else None)
            hours = times[start:end + 1]
            out.append({"n": c[0], "st": c[3], "ll": [c[1], c[2]], "aqi": aqi, "pm25": pm})
        time.sleep(2)
    return {"hours": hours, "cities": out, "src": "CAMS model via Open-Meteo · Indian NAQI from 24 h PM2.5/PM10"}

# ---------------- WEATHER (Open-Meteo) ----------------
def fetch_weather():
    out = []; days = None
    for part in chunks(CITIES, 45):
        q = urllib.parse.urlencode({"latitude": ",".join(str(c[2]) for c in part), "longitude": ",".join(str(c[1]) for c in part),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum", "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "past_days": 7, "forecast_days": 3, "timezone": "Asia/Kolkata"})
        data = None
        for wait in (0, 20, 45, 90):
            time.sleep(wait)
            try:
                data = json.loads(get("https://api.open-meteo.com/v1/forecast?" + q, tries=1)); break
            except Exception as e:
                last = e
        if data is None: raise last
        if isinstance(data, dict): data = [data]
        for c, d in zip(part, data):
            dd = d["daily"]; days = dd["time"]; cur = d.get("current", {})
            out.append({"n": c[0], "st": c[3], "ll": [c[1], c[2]], "tmax": dd["temperature_2m_max"], "tmin": dd["temperature_2m_min"],
                        "rain": dd["precipitation_sum"], "t": cur.get("temperature_2m"), "rh": cur.get("relative_humidity_2m"), "wind": cur.get("wind_speed_10m")})
        time.sleep(2)
    return {"days": days, "today": NOW.strftime("%Y-%m-%d"), "cities": out, "src": "Open-Meteo (ECMWF/GFS blend)"}

# ---------------- FIRES (NASA FIRMS VIIRS) ----------------
def fetch_fires():
    pts = []; seen = set()
    for f in ["noaa-21-viirs-c2/csv/J2_VIIRS_C2_South_Asia_24h.csv", "noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_Asia_24h.csv",
              "suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_24h.csv"]:
        try:
            txt = get("https://firms.modaps.eosdis.nasa.gov/data/active_fire/" + f, tries=2, timeout=90).decode()
        except Exception:
            continue
        for r in csv.DictReader(io.StringIO(txt)):
            lat, lon = float(r["latitude"]), float(r["longitude"])
            if not (66 <= lon <= 98 and 6 <= lat <= 37.5): continue
            key = (round(lon, 2), round(lat, 2))
            if key in seen: continue
            seen.add(key)
            st = state_of(lon, lat)
            if not st: continue
            t = dt.datetime.strptime(r["acq_date"] + r["acq_time"].zfill(4), "%Y-%m-%d%H%M").replace(tzinfo=dt.timezone.utc).astimezone(IST)
            conf = {"l": 0, "n": 1, "h": 2}.get((r.get("confidence") or "n")[0].lower(), 1)
            pts.append([round(lon, 3), round(lat, 3), round(float(r.get("frp") or 0), 1), t.strftime("%Y-%m-%dT%H:%M"), conf, st])
    pts.sort(key=lambda p: -p[2])
    by = {}
    for p in pts: by[p[5]] = by.get(p[5], 0) + 1
    return {"pts": pts[:3500], "total": len(pts), "byState": by, "src": "NASA FIRMS VIIRS 375 m, last 24 h"}

# ---------------- QUAKES (USGS) ----------------
def fetch_quakes():
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).strftime("%Y-%m-%d")
    q = urllib.parse.urlencode({"format": "geojson", "starttime": start, "minlatitude": 4, "maxlatitude": 39, "minlongitude": 64,
                                "maxlongitude": 100, "minmagnitude": 2.5, "orderby": "time"})
    d = json.loads(get("https://earthquake.usgs.gov/fdsnws/event/1/query?" + q))
    out = []
    for f in d["features"]:
        lon, lat, depth = f["geometry"]["coordinates"]
        t = dt.datetime.fromtimestamp(f["properties"]["time"] / 1000, dt.timezone.utc).astimezone(IST)
        out.append({"mag": f["properties"]["mag"], "place": f["properties"]["place"], "ll": [round(lon, 3), round(lat, 3)],
                    "depth": round(depth or 0), "t": t.strftime("%Y-%m-%dT%H:%M"), "st": state_of(lon, lat), "url": f["properties"]["url"]})
    return {"list": out, "src": "USGS FDSN, M ≥ 2.5, last 7 days"}

# ---------------- CYCLONES (GDACS) ----------------
def fetch_cyclones():
    d = json.loads(get("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=TC&alertlevel=Green;Orange;Red&limit=50"))
    out = []
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)
    for f in d.get("features", []):
        lon, lat = f["geometry"]["coordinates"][:2]
        p = f["properties"]
        if not (40 <= lon <= 105 and 0 <= lat <= 30): continue
        try:
            to = dt.datetime.fromisoformat(p.get("todate", "").replace("Z", "")).replace(tzinfo=dt.timezone.utc)
        except Exception:
            to = None
        if to and to < cut: continue
        out.append({"name": p.get("name"), "level": p.get("alertlevel"), "ll": [lon, lat], "to": p.get("todate"),
                    "desc": (p.get("description") or "")[:140], "url": (p.get("url") or {}).get("report")})
    return {"list": out, "src": "GDACS tropical cyclones, North Indian Ocean"}

# ---------------- NEWS (GDELT) ----------------
PLACE = {c[0].lower(): c[3] for c in CITIES}
PLACE.update({"bengaluru": "KA", "bangalore": "KA", "mumbai": "MH", "kolkata": "WB", "chennai": "TN", "gurgaon": "HR", "odisha": "OD",
              "orissa": "OD", "kashmir": "JK", "j&k": "JK", "andaman": "AN", "nicobar": "AN", "port blair": "AN", "trivandrum": "KL",
              "calicut": "KL", "cochin": "KL", "sabarimala": "KL", "vizag": "AP", "noida": "UP", "ncr": "DL", "manipur": "MN",
              "lasalgaon": "MH", "kutch": "GJ", "goa": "GA", "sikkim": "SK", "ladakh": "LA", "tripura": "TR", "mizoram": "MZ",
              "nagaland": "NL", "meghalaya": "ML", "assam": "AS", "bihar": "BR", "jharkhand": "JH", "punjab": "PB", "haryana": "HR",
              "rajasthan": "RJ", "gujarat": "GJ", "kerala": "KL", "karnataka": "KA", "telangana": "TG", "maharashtra": "MH",
              "uttarakhand": "UK", "chhattisgarh": "CG", "delhi": "DL", "puducherry": "PY", "pondicherry": "PY", "lakshadweep": "LD"})
for k, v in {"tamil nadu": "TN", "uttar pradesh": "UP", "madhya pradesh": "MP", "andhra pradesh": "AP", "west bengal": "WB",
             "himachal": "HP", "arunachal": "AR", "chandigarh": "CH"}.items():
    PLACE[k] = v
DOMS = [("quake", r"earthquake|tremor|seismic"),
        ("weather", r"cyclone|rain|flood|imd|monsoon|storm|landslide|cold wave|heatwave|heat wave|snow|fog|depression|thunder"),
        ("air", r"\baqi\b|air quality|pollution|smog|stubble|grap|pm2\.5"),
        ("security", r"army|border|bsf|\bloc\b|\blac\b|militant|terror|navy|coast guard|encounter|infiltrat|security forces|crpf|itbp"),
        ("cyber", r"cyber|upi|hack|data breach|phishing|cert-in|outage|internet"),
        ("health", r"dengue|malaria|nipah|outbreak|hospital|virus|covid|health"),
        ("infra", r"railway|train|flight|airport|metro|power cut|blackout|grid|highway|bridge|derail|accident"),
        ("economy", r"sensex|nifty|rupee|rbi|inflation|gdp|onion|tomato|price|exports|gst|stock")]
SEV = [(4, r"killed|dead|deaths|died|blast|massacre|red alert|tsunami"), (3, r"injured|evacuat|orange alert|severe|attack|collapse|derail|landslide|cyclone"),
       (2, r"alert|warning|outage|disrupt|delay|protest|closed|suspend|shut")]
QUERIES = ['sourcecountry:IN sourcelang:english',
           '(earthquake OR cyclone OR flood OR landslide OR "heavy rain" OR "cold wave" OR fog) sourcecountry:IN sourcelang:english',
           '(AQI OR "air quality" OR pollution OR stubble) sourcecountry:IN sourcelang:english',
           '(border OR army OR "coast guard" OR BSF OR navy OR militants) sourcecountry:IN sourcelang:english',
           '(railway OR airport OR "power cut" OR outage OR UPI OR cyber) sourcecountry:IN sourcelang:english',
           '(dengue OR outbreak OR "price rise" OR RBI OR rupee) sourcecountry:IN sourcelang:english',
           '(accident OR fire OR collapse OR derailment OR stampede) sourcecountry:IN sourcelang:english',
           '(landslide OR avalanche OR "cold wave" OR snowfall OR lightning) sourcecountry:IN sourcelang:english']
def clean_title(title):
    title = re.sub(r"\s+", " ", title or "")
    title = re.sub(r"\s+([,:;.%?!])", r"\1", title)
    return re.sub(r"\s+[-|–]\s+[^-|–]{2,45}$", "", title).strip(" |-")

def find_state(low):
    for name in sorted(PLACE, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", low):
            return PLACE[name]
    return None

SPORT = re.compile(r"cricket|hockey|\bvs\b|semi-final|semifinal|\bmatch\b|asia cup|world cup|fifa|\bipl\b|t20|\bodi\b|wicket|tennis|olympic|medal|box office|bollywood|movie|trailer")
def ingest(items, seen_words, title, url, src, seen, need_state=True, need_dom=True, extra=None):
    title = clean_title(title)
    if len(title) < 25 or SPORT.search(title.lower()): return
    words = set(w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 3)
    dup = next((k for k, o in seen_words if len(words & o) / max(1, len(words | o)) > 0.5), None)
    if dup:
        it = items.get(dup)
        if it is not None:
            it["n"] = it.get("n", 1) + 1
            if src and src not in it["srcs"] and len(it["srcs"]) < 6: it["srcs"].append(src)
        return
    key = re.sub(r"[^a-z]", "", title.lower())[:60]
    if key in items: return
    low = title.lower()
    st = find_state(low)
    dom = next((d for d, rx in DOMS if re.search(rx, low)), None)
    if (need_state and not st) or (need_dom and not dom): return
    sev = next((s for s, rx in SEV if re.search(rx, low)), 1)
    seen_words.append((key, words))
    it = {"t": title[:180], "url": url, "src": src, "seen": seen.strftime("%Y-%m-%dT%H:%M"), "st": st, "dom": dom, "sev": sev, "n": 1, "srcs": [src] if src else []}
    if extra: it.update(extra(low))
    items[key] = it

def gnews(q, n=60):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    root = ET.fromstring(get(url, tries=3, timeout=40))
    out = []
    for it in root.findall(".//item")[:n]:
        try:
            seen = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(IST)
        except Exception:
            seen = NOW
        out.append((it.findtext("title") or "", it.findtext("link"), it.findtext("source") or "Google News", seen))
    return out

GN_QUERIES = ["India (flood OR landslide OR cyclone OR \"heavy rain\" OR earthquake OR \"cold wave\") when:1d",
              "India (AQI OR pollution OR smog OR stubble) when:1d",
              "India (train OR flight OR airport OR highway OR \"power cut\" OR outage) when:1d",
              "India (army OR BSF OR \"coast guard\" OR navy OR border OR militants OR encounter) when:1d",
              "India (dengue OR outbreak OR hospital OR virus) when:1d",
              "India (Sensex OR Nifty OR rupee OR RBI OR inflation OR prices) when:1d",
              "India (cyber OR UPI OR hack OR fraud OR scam) when:1d",
              "India (accident OR fire OR collapse OR stampede OR derail) when:1d",
              "(Kerala OR \"Tamil Nadu\" OR Karnataka OR \"Andhra Pradesh\" OR Telangana) when:1d",
              "(\"Uttar Pradesh\" OR Bihar OR \"West Bengal\" OR Odisha OR Jharkhand) when:1d",
              "(Maharashtra OR Gujarat OR Rajasthan OR \"Madhya Pradesh\" OR Goa) when:1d",
              "(Assam OR Manipur OR Meghalaya OR Nagaland OR Mizoram OR Tripura OR Arunachal OR Sikkim) when:1d",
              "(\"Jammu and Kashmir\" OR Ladakh OR Punjab OR Haryana OR Himachal OR Uttarakhand OR Delhi) when:1d"]

def fetch_news():
    items = {}; seen_words = []
    for q in GN_QUERIES:
        try:
            for t, u, src, seen in gnews(q):
                ingest(items, seen_words, t, u, src, seen)
        except Exception as e:
            print("gnews fail", q[:30], e)
        time.sleep(1)
    for q in QUERIES[:3]:
        url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode({"query": q, "mode": "artlist", "maxrecords": 150, "format": "json", "timespan": "24h", "sort": "datedesc"})
        try:
            d = json.loads(get(url, tries=2, timeout=60))
        except Exception:
            continue
        for a in d.get("articles", []):
            seen = dt.datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).astimezone(IST)
            ingest(items, seen_words, a.get("title"), a.get("url"), a.get("domain"), seen)
        time.sleep(5)
    lst = sorted(items.values(), key=lambda x: x["seen"], reverse=True)[:160]
    return {"items": lst, "src": "Google News and GDELT, Indian English-language press, last 24 h"}

# ---------------- WORLD → INDIA ----------------
REGIONS = [("China", r"china|chinese|beijing|xi jinping|\blac\b"),
           ("Pakistan", r"pakistan|islamabad|\bpak\b|rawalpindi"),
           ("Neighbourhood", r"bangladesh|dhaka|nepal|kathmandu|sri lanka|colombo|maldives|bhutan|myanmar|afghanistan|taliban"),
           ("US & trade", r"\bus\b|u\.s\.|united states|america|washington|trump|tariff|wto|h-1b|visa"),
           ("Gulf & energy", r"gulf|saudi|uae|dubai|qatar|iran|israel|opec|crude|oil|brent|red sea|hormuz"),
           ("Russia & Europe", r"russia|moscow|putin|ukraine|europe|\beu\b|britain|\buk\b|germany|france"),
           ("Indian Ocean", r"indian ocean|maritime|navy|chagos|diego garcia|malacca|andaman"),
           ("Global markets", r"\bfed\b|federal reserve|global markets|dollar|imf|world bank|recession|wall street")]
CHANNELS = [("Security", r"border|military|army|terror|missile|navy|defence|defense|attack|ceasefire"),
            ("Trade", r"tariff|trade|export|import|duty|deal|fta|sanction"),
            ("Energy", r"oil|crude|gas|lng|energy|opec|fuel"),
            ("Diaspora", r"indians|indian nationals|diaspora|visa|h-1b|students|evacuat|workers"),
            ("Markets", r"rupee|sensex|nifty|fed|dollar|markets|investors|fii|bond"),
            ("Climate", r"climate|cyclone|flood|monsoon|glacier|heatwave|cop\d")]
WORLD_Q = ["India (China OR Pakistan OR Bangladesh OR Nepal OR \"Sri Lanka\" OR Maldives OR Myanmar OR Bhutan) when:1d",
           "India (US OR tariff OR trade deal OR visa OR H-1B) when:1d",
           "India (oil OR crude OR Gulf OR Iran OR \"Red Sea\" OR OPEC OR Saudi OR UAE) when:1d",
           "India (Russia OR Ukraine OR Europe OR EU OR Britain) when:1d",
           "India (\"Indian Ocean\" OR maritime OR navy) international when:1d",
           "India (rupee OR Fed OR \"global markets\" OR IMF OR \"World Bank\") when:1d"]
def world_extra(low):
    reg = next((r for r, rx in REGIONS if re.search(rx, low)), None)
    ch = [c for c, rx in CHANNELS if re.search(rx, low)][:2]
    return {"region": reg, "ch": ch}
def fetch_world():
    items = {}; seen_words = []
    for q in WORLD_Q:
        try:
            for t, u, src, seen in gnews(q, 50):
                ingest(items, seen_words, t, u, src, seen, need_state=False, need_dom=False, extra=world_extra)
        except Exception as e:
            print("world fail", e)
        time.sleep(1)
    lst = [x for x in items.values() if x.get("region")]
    lst = sorted(lst, key=lambda x: x["seen"], reverse=True)[:90]
    for x in lst: x.pop("st", None); x.pop("dom", None)
    return {"items": lst, "src": "Google News, international stories that mention India, last 24 h"}

# ---------------- SOCIAL (Bluesky, Mastodon) ----------------
BSKY = ["thehindu.com", "scroll.in", "thewire.in", "ndtv.com", "reuters.com", "apnews.com"]
MASTO_TAGS = ["india", "indianews", "delhi", "kerala", "mumbai", "bengaluru", "chennai", "kolkata", "airpollution", "monsoon"]
def strip_html(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").strip()
def fetch_social():
    out = []; seenk = set(); cut = dt.datetime.now(IST) - dt.timedelta(hours=48)
    def add(text, url, who, plat, when):
        if when < cut: return
        text = text[:240]; low = text.lower()
        k = re.sub(r"[^a-z]", "", low)[:50]
        if k in seenk or len(text) < 30: return
        st = find_state(low)
        if plat == "Bluesky" and who in ("reuters.com", "apnews.com") and not re.search(r"india|indian|delhi|modi|mumbai", low): return
        dom = next((d for d, rx in DOMS if re.search(rx, low)), None)
        if SPORT.search(low) or (plat == "Mastodon" and (not dom or "reddit.com" in low or not (st or re.search(r"\bindia|indian\b", low)))): return
        seenk.add(k)
        out.append({"t": text, "url": url, "who": who, "plat": plat, "seen": when.strftime("%Y-%m-%dT%H:%M"), "st": st, "dom": dom})
    for h in BSKY:
        try:
            d = json.loads(get("https://api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?" + urllib.parse.urlencode({"actor": h, "limit": 40, "filter": "posts_no_replies"}), tries=2, timeout=30))
            for f in d.get("feed", []):
                p = f["post"]; rec = p.get("record", {})
                when = dt.datetime.fromisoformat(rec.get("createdAt", "").replace("Z", "+00:00")).astimezone(IST)
                rkey = p["uri"].split("/")[-1]
                add(rec.get("text", ""), "https://bsky.app/profile/" + h + "/post/" + rkey, h, "Bluesky", when)
        except Exception as e:
            print("bsky fail", h, e)
    for tag in MASTO_TAGS:
        try:
            d = json.loads(get("https://mastodon.social/api/v1/timelines/tag/" + tag + "?limit=40", tries=2, timeout=30))
            for s in d:
                if s.get("sensitive") or s.get("language") != "en": continue
                when = dt.datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")).astimezone(IST)
                add(strip_html(s.get("content")), s.get("url") or s.get("uri"), "@" + s["account"]["acct"], "Mastodon", when)
        except Exception as e:
            print("masto fail", tag, e)
    out.sort(key=lambda x: x["seen"], reverse=True)
    return {"items": out[:150], "src": "Public Bluesky news accounts and Mastodon hashtags, last 48 h"}

# ---------------- SCHEME NEWS ----------------
def fetch_schemenews():
    items = {}; seen_words = []
    for q in ["(scheme OR yojana) India government launch OR beneficiaries OR instalment when:2d",
              "(scheme OR yojana) (Kerala OR \"Tamil Nadu\" OR Karnataka OR Telangana OR \"Andhra Pradesh\" OR Maharashtra OR Gujarat) when:2d",
              "(scheme OR yojana) (\"Uttar Pradesh\" OR Bihar OR \"Madhya Pradesh\" OR Rajasthan OR Odisha OR \"West Bengal\" OR Assam OR Punjab OR Haryana OR Delhi) when:2d"]:
        try:
            for t, u, src, seen in gnews(q, 50):
                ingest(items, seen_words, t, u, src, seen, need_state=False, need_dom=False)
        except Exception as e:
            print("scheme news fail", e)
        time.sleep(1)
    lst = [x for x in items.values() if re.search(r"scheme|yojana|abhiyan|mission|benefit|beneficiar", x["t"].lower())]
    lst = sorted(lst, key=lambda x: x["seen"], reverse=True)[:80]
    for x in lst: x.pop("dom", None)
    return {"items": lst, "src": "Google News, scheme announcements and updates, last 48 h"}

# ---------------- OFFICIAL ALERTS (NDMA SACHET CAP) ----------------
CAPNS = "{urn:oasis:names:tc:emergency:cap:1.2}"
SENDER_ST = {"chennai": "TN", "thiruvananthapuram": "KL", "visakhapatnam": "AP", "amaravati": "AP", "raipur": "CG", "mumbai": "MH",
             "kolkata": "WB", "guwahati": "AS", "hyderabad": "TG", "bengaluru": "KA", "bhubaneswar": "OD", "patna": "BR", "lucknow": "UP",
             "jaipur": "RJ", "bhopal": "MP", "ahmedabad": "GJ", "chandigarh": "PB", "shimla": "HP", "dehradun": "UK", "srinagar": "JK",
             "ranchi": "JH", "gangtok": "SK", "agartala": "TR", "imphal": "MN", "aizawl": "MZ", "shillong": "ML", "itanagar": "AR",
             "kohima": "NL", "goa": "GA", "new delhi": "DL", "delhi": "DL", "port blair": "AN", "incois": None, "cwc": None}
def simplify(pts, n=60):
    if len(pts) <= n: return pts
    step = len(pts) / n
    out = [pts[int(i * step)] for i in range(n)]
    out.append(pts[0]); return out
def sender_state(sender):
    low = sender.lower().replace("-", " ")
    for name in sorted(STATE_NAMES.values(), key=len, reverse=True):
        pass
    for code, key in STATE_NAMES.items():
        if key and key in re.sub(r"[^a-z]", "", low): return code
    for k, v in SENDER_ST.items():
        if k in low: return v
    return None
def _cap_one(it):
    link = it["link"]; ident = it["guid"]
    try:
        cap = ET.fromstring(get(link, tries=2, timeout=25))
    except Exception:
        return None
    infos = cap.findall(CAPNS + "info")
    info = next((i for i in infos if (i.findtext(CAPNS + "language") or "").lower().startswith("en")), infos[0] if infos else None)
    if info is None: return None
    exp = info.findtext(CAPNS + "expires") or ""
    try:
        if dt.datetime.fromisoformat(exp) < dt.datetime.now(IST): return None
    except Exception:
        pass
    head = re.sub(r"\s+", " ", info.findtext(CAPNS + "headline") or "").strip()
    area = re.sub(r"\s+", " ", info.findtext(CAPNS + "area/" + CAPNS + "areaDesc") or "").strip()
    sender = cap.findtext(CAPNS + "sender") or it["author"]
    return {"event": info.findtext(CAPNS + "event") or "Alert", "head": head[:220], "area": area[:200],
            "sev": {"Extreme": 4, "Severe": 3, "Moderate": 2}.get(info.findtext(CAPNS + "severity") or "", 1),
            "urg": info.findtext(CAPNS + "urgency"), "sender": sender.replace("-", " "), "eff": (info.findtext(CAPNS + "effective") or "")[:16],
            "exp": exp[:16], "url": link, "ident": ident}
def _poly_one(a):
    polys = []
    try:
        px = ET.fromstring(get("https://sachet.ndma.gov.in/cap_public_website/FetchPolygonXMLFile?identifier=" + a["ident"], tries=2, timeout=40))
        for pe in px.iter("polygon"):
            pts = []
            for pair in (pe.text or "").split():
                la, lo = pair.split(",")[:2]; pts.append([round(float(lo), 3), round(float(la), 3)])
            if len(pts) >= 3: polys.append(simplify(pts))
    except Exception:
        pass
    a["polys"] = sorted(polys, key=len, reverse=True)[:6]
    st = None
    if a["polys"]:
        pg = a["polys"][0]; st = state_of(sum(p[0] for p in pg) / len(pg), sum(p[1] for p in pg) / len(pg))
    a["st"] = st or sender_state(a["sender"])
    del a["ident"]
    return a
def fetch_alerts():
    from concurrent.futures import ThreadPoolExecutor
    rss = ET.fromstring(get("https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml").decode("utf-8-sig"))
    raw = []; seen = set()
    for it in rss.findall(".//item"):
        k = it.findtext("guid")
        if k in seen: continue
        seen.add(k); raw.append({"link": it.findtext("link") or "", "guid": it.findtext("guid") or "", "author": it.findtext("author") or ""})
    raw = raw[:70]
    with ThreadPoolExecutor(6) as ex:
        caps = [c for c in ex.map(_cap_one, raw) if c]
    uniq = []; seen = set()
    for c in caps:
        k = (c["event"], c["area"][:80], c["sender"])
        if k in seen: continue
        seen.add(k); uniq.append(c)
    uniq = uniq[:40]
    with ThreadPoolExecutor(6) as ex:
        out = list(ex.map(_poly_one, uniq))
    return {"list": out, "src": "NDMA SACHET common alerting protocol (IMD, SDMAs, CWC, INCOIS)"}

# ---------------- OFFICIAL RELEASES (RBI, PIB) ----------------
def rss_items(url, n):
    root = ET.fromstring(get(url, tries=3).decode("utf-8-sig"))
    out = []
    for it in root.findall(".//item")[:n]:
        t = re.sub(r"<[^>]+>", "", it.findtext("title") or "").strip()
        pub = it.findtext("pubDate") or ""
        try:
            seen = email.utils.parsedate_to_datetime(pub).astimezone(IST).strftime("%Y-%m-%dT%H:%M")
        except Exception:
            seen = NOW.strftime("%Y-%m-%dT%H:%M")
        out.append({"t": t[:180], "url": it.findtext("link"), "seen": seen})
    return out
def fetch_official():
    out = []
    try:
        for x in rss_items("https://www.rbi.org.in/pressreleases_rss.xml", 15):
            if re.search(r"auction|money market operations|treasury bills|reserve money|weekly statistical", x["t"], re.I): continue
            x.update({"src": "RBI", "st": "MH", "dom": "economy", "sev": 2 if re.search(r"penalty|cancel|repo|policy|restrict", x["t"], re.I) else 1}); out.append(x)
    except Exception as e:
        print("rbi fail", e)
    try:
        for x in rss_items("https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", 25):
            if not re.search(r"[A-Za-z]{4}", x["t"]): continue
            low = x["t"].lower()
            dom = next((d for d, rx in DOMS if re.search(rx, low)), "economy")
            st = next((PLACE[n] for n in sorted(PLACE, key=len, reverse=True) if re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", low)), "DL")
            x.update({"src": "PIB", "st": st, "dom": dom, "sev": 1}); out.append(x)
    except Exception as e:
        print("pib fail", e)
    return {"items": out, "src": "RBI press releases and PIB (Government of India) RSS"}

JOBS = [("air", fetch_air), ("weather", fetch_weather), ("fires", fetch_fires), ("quakes", fetch_quakes), ("cyclones", fetch_cyclones), ("news", fetch_news), ("alerts", fetch_alerts), ("official", fetch_official), ("world", fetch_world), ("social", fetch_social), ("schemenews", fetch_schemenews)]
try:
    meta = json.load(open(os.path.join(OUT, "meta.json"))) if ONLY else None
except Exception:
    meta = None
meta = meta or {"feeds": {}}
meta["updated"] = NOW.strftime("%Y-%m-%dT%H:%M")
for name, fn in JOBS:
    if ONLY and name not in ONLY: continue
    try:
        doc = fn(); doc["at"] = NOW.strftime("%Y-%m-%dT%H:%M")
        s = json.dumps(doc, separators=(",", ":"))
        if len(s.encode()) > 250_000:
            raise ValueError("document too large: %d bytes" % len(s.encode()))
        open(os.path.join(OUT, name + ".json"), "w").write(s)
        meta["feeds"][name] = {"ok": True, "at": doc["at"], "bytes": len(s.encode())}
        print("ok", name, len(s.encode()), "bytes")
    except Exception as e:
        if os.path.exists(os.path.join(OUT, name + ".json")):
            meta["feeds"][name] = dict(meta["feeds"].get(name, {}), stale=True, err=str(e)[:200]); print("FAIL (kept previous)", name, e); continue
        meta["feeds"][name] = {"ok": False, "err": str(e)[:200], "at": NOW.strftime("%Y-%m-%dT%H:%M")}
        print("FAIL", name, e)
open(os.path.join(OUT, "meta.json"), "w").write(json.dumps(meta, separators=(",", ":")))
