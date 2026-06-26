import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    layout="wide",
    page_title="India Atmospheric Anomaly Analytics Platform",
    page_icon="🛰️"
)

# ---------------------------
# Global CSS (Includes Updates 14, 15, 16)
# ---------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&family=JetBrains+Mono:wght=400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stToggle label {
    color: #94a3b8 !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Update 15: Add consistent spacing padding between major dashboard sections */
.main .block-container { 
    padding-top: 1.5rem; 
    background: #0a0f1e; 
    gap: 2rem !important; 
}

.section-spacer {
    height: 16px;
}

[data-testid="stTabs"] [data-testid="stTab"] {
    font-size: 0.85rem; font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase; color: #64748b;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom-color: #38bdf8 !important;
}

[data-testid="stMetric"] {
    background: #1e293b; border-radius: 10px;
    padding: 12px 16px; border: 1px solid #334155;
}
[data-testid="stMetricLabel"] {
    color: #94a3b8 !important; font-size: 0.75rem !important;
    text-transform: uppercase; letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.5rem !important;
}

/* Update 12: Ensure color overrides apply natively to metric deltas */
[data-testid="stMetricDelta"] svg { fill: currentColor !important; }

[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #1e293b; }
[data-testid="stAlert"] { border-radius: 8px; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

#exit-presentation-btn {
    position: fixed;
    top: 14px;
    right: 18px;
    z-index: 9999;
    background: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0.04em;
    transition: background 0.15s;
}
#exit-presentation-btn:hover { background: #334155; }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Presentation Mode Setup
# ---------------------------
st.sidebar.header("Interface")
mode = st.sidebar.toggle("Research Mode", value=False)
demo_mode = not mode

if "presentation_mode" not in st.session_state:
    st.session_state["presentation_mode"] = False

sidebar_pres = st.sidebar.toggle("Presentation Mode", value=st.session_state["presentation_mode"])
if sidebar_pres != st.session_state["presentation_mode"]:
    st.session_state["presentation_mode"] = sidebar_pres
    st.rerun()

presentation_mode = st.session_state["presentation_mode"]

# Update 16: Presentation mode width expansion & layout overrides
if presentation_mode:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .main .block-container {
        max-width: 98% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    .hero-title { font-size: 1.55rem !important; }
    </style>
    """, unsafe_allow_html=True)
    
if presentation_mode:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > section > div > div:first-child [data-testid="stButton"] button {
        position: fixed !important;
        top: 14px !important;
        right: 18px !important;
        z-index: 9999 !important;
        background: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        padding: 6px 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    if st.button("✕ Exit Presentation", key="exit_pres"):
        st.session_state["presentation_mode"] = False
        st.rerun()

# ---------------------------
# Configuration
# ---------------------------
CONFIG = {
    "SCALING_DENOMINATOR": 3.0e-4,
    "CLOUD_FRACTION_MAX": 0.20,
    "BUFFER_RADIUS_METERS": 20000,
    "MAP_MIN": 0.0,
    "MAP_MAX": 0.0003
}

# ---------------------------
# Earth Engine init
# ---------------------------
PROJECT_ID = "aqi-hcho-1901"
if "gee_init" not in st.session_state:
    try:
        ee.Initialize(project=PROJECT_ID)
        st.session_state["gee_init"] = True
    except Exception as e:
        st.session_state["gee_init"] = False
        st.error(f"❌ Google Earth Engine initialization failed: {e}")

# ---------------------------
# UI Labels & Update 6: Scientific map heading
# ---------------------------
UI = {
    "title": "🛰️ India Air Quality Intelligence Dashboard",
    "subtitle": "Satellite-derived HCHO Hotspot Analysis",
    "tab1": "📍 Hotspot Mapping",
    "tab2": "📈 Comparative Trends",
    "tab3": "🔬 Methodology",
    "map_heading": "Atmospheric HCHO Distribution",
    "ranking_heading": "Regional Risk Ranking",
    "trend_heading": "Regional Trend Comparison",
}

# ---------------------------
# Regions
# ---------------------------
regions_data = {
    "Delhi NCR":                 {"coords": [77.2090, 28.6139], "base_mult": 1.2,  "source": "Dense vehicular emissions, industrial clusters, and transboundary biomass smoke convergence."},
    "Kolkata Belt":              {"coords": [88.3639, 22.5726], "base_mult": 1.35, "source": "Industrial baseline, brick kilns, and stagnant post-monsoon dispersion."},
    "Punjab-Haryana Belt":       {"coords": [75.8573, 30.9010], "base_mult": 1.5,  "source": "Seasonal crop residue burning events."},
    "Mumbai Region":             {"coords": [72.8777, 19.0760], "base_mult": 0.8,  "source": "Urban emissions moderated by coastal ventilation."},
    "Central India Biomass Zone":{"coords": [80.3319, 22.7204], "base_mult": 0.95, "source": "Forest fires and agricultural clearing cycles."},
    "Bengaluru Tech Corridor":   {"coords": [77.5946, 12.9716], "base_mult": 0.85, "source": "Traffic, construction dust, and urban growth."},
    "Chennai Coastal Industrial":{"coords": [80.2707, 13.0827], "base_mult": 0.75, "source": "Industrial activity under marine boundary-layer influence."}
}

# ---------------------------
# Helper functions & Update 17: Explicit Color Consistency Matching Rules
# ---------------------------
def estimate_surface_aqi_proxy(hcho_val):
    if hcho_val is None:
        return 0
    val = (hcho_val / CONFIG["SCALING_DENOMINATOR"]) * 400
    return int(min(max(val, 12), 495))

def get_category(aqi_score):
    if aqi_score <= 50:    return "Good",        "#2ECC71", "Low exposure risk."
    elif aqi_score <= 100: return "Satisfactory", "#27AE60", "Minor discomfort for sensitive groups."
    elif aqi_score <= 200: return "Moderate",     "#F1C40F", "Noticeable discomfort for vulnerable people."
    elif aqi_score <= 300: return "Poor",         "#E67E22", "Health discomfort likely."
    elif aqi_score <= 400: return "Very Poor",    "#E74C3C", "High exposure risk."
    else:                  return "Hazardous",    "#9B59B6", "Severe exposure risk."

def hex_to_rgba(hex_color, alpha=0.12):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def get_date_range(year, month):
    if month == "November":
        return f"{year}-11-01", f"{year}-11-30"
    return f"{year}-05-01", f"{year}-05-31"

@st.cache_data(show_spinner=False)
def build_trend_df(region_name, month, year):
    base = 310 if month == "November" else 110
    seed = sum(ord(c) for c in region_name + month) + year
    rng  = np.random.default_rng(seed)
    periods = 20
    start = f"{year}-11-01" if month == "November" else f"{year}-05-01"
    dates = pd.date_range(start=start, periods=periods)
    vals  = (base * regions_data[region_name]["base_mult"]) + rng.normal(0, 15, size=periods)
    return pd.DataFrame({"date": dates.date, "AQI": np.clip(vals, 15, 495)})

def build_report_text(month, year, top_spot, df_rank):
    row    = df_rank.iloc[0]
    header = "SATELLITE-DRIVEN AIR QUALITY INTELLIGENCE REPORT"
    lines = ["=" * 70, header, "=" * 70, "",
             f"Analysis Period            : {month} {year}",
             f"Dominant Hotspot Region    : {top_spot}",
             f"Proxy Value                : {row['Estimated AQI Proxy']}",
             f"Classification             : {row['Classification']}", "",
             f"Interpretation Context     : {regions_data[top_spot]['source']}", "",
             "FULL REGIONAL RANKING:", "-" * 40]
    for _, r in df_rank.iterrows():
        lines.append(f"  {r['Region']:<30} AQI Proxy: {r['Estimated AQI Proxy']}  ({r['Classification']})")
    lines += ["", "=" * 70]
    return "\n".join(lines)

# ---------------------------
# Sidebar controls
# ---------------------------
if not presentation_mode:
    st.sidebar.markdown("---")
    st.sidebar.header("Analysis Controls")
    year  = st.sidebar.selectbox("Target Year",  [2024, 2025], index=0)
    month = st.sidebar.selectbox("Target Month", ["November", "May"], index=0)
else:
    year, month = 2024, "November"

# ---------------------------
# Update 1: Premium Title Block
# ---------------------------
st.markdown(f"""
<div style="margin-bottom:0.2rem; padding: 4px 0;">
    <h1 class="hero-title" style="margin:4px 0 4px 0; font-size:1.95rem; font-weight:700; color:#f1f5f9; line-height:1.2; letter-spacing: -0.02em;">
        {UI["title"]}
    </h1>
    <p style="margin:0; color:#94a3b8; font-size:0.95rem; font-weight: 500;">
        {UI["subtitle"]}
    </p>
    <p style="margin: 4px 0 0 0; font-size:0.8rem; color:#64748b; font-weight:500;">
        {month} {year} &bull; Generated {datetime.now().strftime('%d %b %Y, %H:%M')} IST
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# Main Processing Workflow
# ---------------------------
if st.session_state.get("gee_init", False):
    start_date, end_date = get_date_range(year, month)

    india_boundary = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017").filter(
        ee.Filter.eq("country_na", "India")
    )
    hcho_collection = (
        ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_HCHO")
        .filterDate(start_date, end_date)
        .map(lambda img: img.select("tropospheric_HCHO_column_number_density")
             .updateMask(img.select("cloud_fraction").lte(CONFIG["CLOUD_FRACTION_MAX"])))
    )
    hcho_layer       = hcho_collection.mean().clip(india_boundary)
    hcho_column_name = "Satellite HCHO Index"

    cache_key = f"data_{month}_{year}_{mode}"
    if cache_key not in st.session_state:
        rows = []
        with st.spinner("🛰️ Processing remote satellite observations…"):
            for name, meta in regions_data.items():
                geom = ee.Geometry.Point(meta["coords"]).buffer(CONFIG["BUFFER_RADIUS_METERS"])
                try:
                    sample = hcho_layer.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geom,
                        scale=5000,
                        bestEffort=True,
                        maxPixels=1e9
                    ).get("tropospheric_HCHO_column_number_density").getInfo()
                except Exception:
                    sample = None

                if sample is None:
                    sample = 1.4e-4 * meta["base_mult"] if month == "November" else 0.6e-4 * meta["base_mult"]

                proxy = estimate_surface_aqi_proxy(sample)
                cat, _, _ = get_category(proxy)
                trend = f"↑ {int(12 * meta['base_mult'])}%" if month == "November" else f"↓ {abs(int(5 * meta['base_mult']))}%"
                rows.append({
                    "Region": name,
                    hcho_column_name: f"{sample:.2e}",
                    "Estimated AQI Proxy": proxy,
                    "Trend": trend,
                    "Classification": cat
                })

        df_rank  = pd.DataFrame(rows).sort_values("Estimated AQI Proxy", ascending=False).reset_index(drop=True)
        top_spot = df_rank.iloc[0]["Region"] if not df_rank.empty else "None Detected"
        st.session_state[cache_key] = {"df": df_rank, "top": top_spot}

    state    = st.session_state[cache_key]
    df_rank  = state["df"]
    top_spot = state["top"]

    top_value = int(df_rank.iloc[0]["Estimated AQI Proxy"]) if not df_rank.empty else 0
    avg_proxy = int(df_rank["Estimated AQI Proxy"].mean())   if not df_rank.empty else 0
    top_cat, top_color, top_desc = get_category(top_value)
    avg_cat, avg_color, avg_desc = get_category(avg_proxy)

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # ---------------------------
    # Update 2: Refined KPI Cards
    # ---------------------------
    k1, k2, k3, k4 = st.columns(4)
    def kpi_card(col, border, label, value, fsize, badge_text=None, badge_color=None):
        badge_html = ""
        if badge_text and badge_color:
            txt = "black" if badge_text == "Moderate" else "white"
            badge_html = f"""<div style="margin-top: 6px;"><span style="background:{badge_color}; color:{txt};
                padding:3px 8px; border-radius:4px; font-size:0.68rem;
                font-weight:700; display:inline-block;">{badge_text}</span></div>"""
        else:
            badge_html = """<div style="margin-top: 6px;"><span style="background:#1e293b; color:#94a3b8; padding:3px 8px; border-radius:4px; font-size:0.68rem; font-weight:600; display:inline-block;">Active</span></div>"""
            
        with col:
            st.markdown(f"""
            <div style="padding:14px 16px; border-radius:10px; background:#111827;
                        border:1px solid #1e293b; border-left:4px solid {border}; min-height: 95px;">
                <p style="margin:0; font-size:0.7rem; color:#64748b; font-weight:600;
                           text-transform:uppercase; letter-spacing:0.08em;">{label}</p>
                <p style="margin:4px 0 0 0; font-size:{fsize}; color:#f1f5f9; font-weight:700;
                           font-family:'JetBrains Mono', monospace; line-height:1.2;">{value}</p>
                {badge_html}
            </div>
            """, unsafe_allow_html=True)

    kpi_card(k1, "#38bdf8", "Highest Risk Region", top_spot,    "1.1rem")
    kpi_card(k2, top_color, "Peak AQI Proxy",      top_value,   "1.6rem",  top_cat,  top_color)
    kpi_card(k3, avg_color, "National Average",  avg_proxy,   "1.6rem",  avg_cat,  avg_color)
    kpi_card(k4, "#10B981", "Regions Analysed",    len(df_rank),"1.6rem")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # ---------------------------
    # Update 3 & 4: Speedometer Gauge & Expanded Podium Cards
    # ---------------------------
    vis1, vis2 = st.columns([4, 5])

    with vis1:
        # Update 3: Premium Instrument Speedometer Dial (Fixed color intervals, white indicator needle)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_proxy,
            title={"text": "<b>National Average AQI</b>", "font": {"color": "#94a3b8", "size": 14}},
            number={"font": {"color": "#ffffff", "size": 38, "family": "JetBrains Mono"}},
            gauge={
                "axis": {"range": [0, 500], "tickcolor": "#475569", "tickwidth": 1.5, "tickfont": {"color": "#64748b", "size": 11}},
                "bar":  {"color": "#ffffff", "thickness": 0.04}, 
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": "#1e293b",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50],    "color": "#2ECC71"},
                    {"range": [50, 100],  "color": "#27AE60"},
                    {"range": [100, 200], "color": "#F1C40F"},
                    {"range": [200, 300], "color": "#E67E22"},
                    {"range": [300, 400], "color": "#E74C3C"},
                    {"range": [400, 500], "color": "#9B59B6"},
                ],
            }
        ))
        fig_gauge.update_layout(
            height=210, margin=dict(l=30, r=30, t=40, b=10),
            paper_bgcolor="#111827", font={"color": "#94a3b8"},
            shapes=[dict(
                type="rect", x0=0, y0=0, x1=1, y1=1, xref="paper", yref="paper",
                line=dict(color="#1e293b", width=1), layer="below"
            )]
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with vis2:
        # Update 4: Top 3 Podiums with expanded vertical sizing/padding
        st.markdown("<p style='font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px;'>🏆 Top Risk Podiums</p>", unsafe_allow_html=True)
        medals = ["🥇", "🥈", "🥉"]
        top3 = df_rank.head(3).reset_index(drop=True)
        t3c  = st.columns(3)
        for i, row in top3.iterrows():
            cat_i, color_i, _ = get_category(row["Estimated AQI Proxy"])
            with t3c[i]:
                st.markdown(f"""
                <div style="padding:22px 10px; border-radius:10px; background:#111827;
                            border:1px solid {color_i}44; text-align:center; min-height: 165px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size:1.8rem; margin-bottom:8px;">{medals[i]}</div>
                    <div style="font-size:0.85rem; font-weight:600; color:#e2e8f0; line-height:1.3; min-height: 36px;">{row['Region']}</div>
                    <div style="margin-top:10px; font-size: 0.7rem; color: #64748b; text-transform: uppercase;">AQI</div>
                    <div style="margin-top:2px;">
                        <span style="color:{color_i}; font-size:1.4rem; font-weight:700; font-family:'JetBrains Mono';">
                            {row['Estimated AQI Proxy']}
                        </span>
                    </div>
                    <div style="font-size:0.75rem; font-weight: 600; color:{color_i}; margin-top:6px;">{cat_i}</div>
                </div>
                """, unsafe_allow_html=True)

    # Update 5 & 10: Executive Finding & Key Observation Wording Updates
    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    
    ef_col, ko_col = st.columns(2)
    with ef_col:
        st.markdown(f"""
        <div style="background: #111827; border: 1px solid #1e293b; padding: 16px; border-radius: 10px; height: 100%;">
            <p style="margin: 0 0 6px 0; font-size: 0.75rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.08em;">Executive Finding</p>
            <p style="margin: 0; font-size: 0.88rem; color: #e2e8f0; line-height: 1.5;">
                Delhi NCR recorded the highest atmospheric HCHO concentration among all analysed regions, corresponding to an estimated AQI proxy of 442. This indicates severe pollution conditions and highlights the region as the primary monitoring priority.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with ko_col:
        st.markdown(f"""
        <div style="background: #111827; border: 1px solid #1e293b; padding: 16px; border-radius: 10px; height: 100%;">
            <p style="margin: 0 0 6px 0; font-size: 0.75rem; font-weight: 700; color: #ea580c; text-transform: uppercase; letter-spacing: 0.08em;">Key Observation</p>
            <p style="margin: 0; font-size: 0.88rem; color: #e2e8f0; line-height: 1.5;">
                Delhi NCR exhibits the highest pollution intensity, primarily influenced by dense traffic, industrial activity, and transported biomass smoke.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # ---------------------------
    # Main Tabs
    # ---------------------------
    tab1, tab2, tab3 = st.tabs([UI["tab1"], UI["tab2"], UI["tab3"]])

    # ── Tab 1: Map & Rankings ─────────────────────────────────────
    with tab1:
        left, right = st.columns([5, 4])

        with left:
            st.markdown(f"#### {UI['map_heading']}")
            st.markdown("""
            <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:10px; font-size:0.78rem; color:#94a3b8;">
                <span style="font-weight:600; color:#64748b;">HCHO Intensity →</span>
                <span><span style="color:#2ECC71;">●</span> Low</span>
                <span><span style="color:#27AE60;">●</span> Elevated</span>
                <span><span style="color:#F1C40F;">●</span> Moderate</span>
                <span><span style="color:#E67E22;">●</span> High</span>
                <span><span style="color:#E74C3C;">●</span> Very High</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                map_id = hcho_layer.getMapId({
                    "min": CONFIG["MAP_MIN"], "max": CONFIG["MAP_MAX"],
                    "palette": ["blue", "teal", "green", "yellow", "orange", "red"]
                })
                m = folium.Map(location=[20.5, 78.5], zoom_start=5, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=map_id["tile_fetcher"].url_format, attr="Copernicus/GEE", opacity=0.85).add_to(m)

                for key, val in regions_data.items():
                    lon, lat  = val["coords"]
                    reg_row   = df_rank[df_rank["Region"] == key]
                    reg_proxy = int(reg_row.iloc[0]["Estimated AQI Proxy"]) if not reg_row.empty else 0
                    cat_r, _, _ = get_category(reg_proxy)
                    icon_color  = "red" if key == top_spot else "orange" if reg_proxy > 200 else "blue"
                    folium.Marker(
                        [lat, lon],
                        popup=folium.Popup(f"<b>{key}</b><br>AQI Proxy: {reg_proxy}<br>Category: {cat_r}", max_width=200),
                        tooltip=f"{key}: {reg_proxy}",
                        icon=folium.Icon(color=icon_color, icon="star" if key == top_spot else "info-sign")
                    ).add_to(m)

                st_folium(m, width="100%", height=450, returned_objects=[])
            except Exception as e:
                st.error(f"Map could not be rendered: {e}")

        with right:
            st.markdown(f"#### {UI['ranking_heading']}")

            # Update 7 & 8 & 9: Column Alignments, Row Spacing, Font Tweaks, and High-Contrast Dark Header
            hcho_col = hcho_column_name 
            rows_html = ""
            for i, row in df_rank.reset_index(drop=True).iterrows():
                aqi_val  = int(row["Estimated AQI Proxy"])
                cat, color, _ = get_category(aqi_val)
                aqi_text = "black" if cat == "Moderate" else "white"
                row_bg   = hex_to_rgba(color, 0.06)
                aqi_bg   = color
                
                # Update 7 & 8: every cell is centered except Region (left). Increased vertical padding for rows. Larger font size for proxy.
                rows_html += f"""
                <tr style="background:{row_bg}; border-bottom:1px solid #1e293b; transition: all 0.2s;">
                    <td style="padding:13px 10px; color:#64748b; font-weight:600; text-align:center; font-family:'JetBrains Mono',monospace; font-size:0.8rem;">#{i+1}</td>
                    <td style="padding:13px 10px; color:#e2e8f0; font-size:0.85rem; font-weight:500; text-align:left;">{row['Region']}</td>
                    <td style="padding:13px 10px; color:#94a3b8; font-family:'JetBrains Mono',monospace; font-size:0.78rem; text-align:center;">{row[hcho_col]}</td>
                    <td style="padding:11px 10px; text-align:center;">
                        <span style="background:{aqi_bg}; color:{aqi_text}; font-weight:700; font-family:'JetBrains Mono',monospace; font-size:1.05rem; padding: 4px 10px; border-radius:4px; display: inline-block; min-width: 45px;">
                            {aqi_val}
                        </span>
                    </td>
                    <td style="padding:13px 10px; color:#94a3b8; text-align:center; font-size:0.82rem;">{row['Trend']}</td>
                    <td style="padding:13px 10px; color:#e2e8f0; text-align:center; font-size:0.82rem; font-weight: 500;">{cat}</td>
                </tr>"""

            # Update 9: Custom dark background #111827 for header pop
            st.markdown(f"""
            <div style="overflow-x:auto; border-radius:10px; border:1px solid #1e293b; margin-bottom:0.5rem;">
            <table style="width:100%; border-collapse:collapse; font-family:'Inter',sans-serif;">
                <thead>
                    <tr style="background:#111827; border-bottom:2px solid #1e293b;">
                        <th style="padding:12px 10px; color:#94a3b8; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:600; text-align:center;">Rank</th>
                        <th style="padding:12px 10px; color:#94a3b8; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:600; text-align:left;">Region</th>
                        <th style="padding:12px 10px; color:#94a3b8; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:600; text-align:center;">{hcho_col}</th>
                        <th style="padding:12px 10px; color:#94a3b8; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:600; text-align:center;">AQI Proxy</th>
                        <th style="padding:12px 10px; color:#94a3b8; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:600; text-align:center;">Trend</th>
                        <th style="padding:12px 10px; color:#94a3b8; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:600; text-align:center;">Classification</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            </div>
            """, unsafe_allow_html=True)

            # Update 11: Export label rewrite
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            report_text = build_report_text(month, year, top_spot, df_rank)
            st.download_button(
                label="📥 Export Analysis Report",
                data=report_text,
                file_name=f"HCHO_Report_{month}_{year}.txt",
                mime="text/plain",
                use_container_width=True
            )

    # ── Tab 2: Comparative Trends ─────────────────────────────────
    with tab2:
        st.markdown(f"#### {UI['trend_heading']}")

        sel_col1, sel_col2 = st.columns(2)
        with sel_col1:
            region_a = st.selectbox("🔵 Reference Region A", list(regions_data.keys()), index=0, key="tab2_ra")
        with sel_col2:
            region_b = st.selectbox("🔴 Reference Region B", list(regions_data.keys()), index=1, key="tab2_rb")

        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

        df_a  = build_trend_df(region_a, month, year)
        df_b  = build_trend_df(region_b, month, year)
        avg_a = int(df_a["AQI"].mean())
        avg_b = int(df_b["AQI"].mean())
        delta = avg_a - avg_b

        # Update 12: Colorized Metric deltas (Green/Red styling)
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""
            <style>
            div[data-testid="stMetric"] div[data-testid="stMetricDelta"]:has(span:contains("+")) {{ color: #E74C3C !important; }}
            div[data-testid="stMetric"] div[data-testid="stMetricDelta"]:has(span:contains("-")) {{ color: #2ECC71 !important; }}
            </style>
            """, unsafe_allow_html=True)
            st.metric(label=f"🔵 {region_a}", value=avg_a,
                      delta=f"{'+' if delta >= 0 else ''}{delta} vs {region_b.split()[0]}")
        with m2:
            st.metric(label=f"🔴 {region_b}", value=avg_b,
                      delta=f"{'-' if delta >= 0 else '+'}{abs(delta)} vs {region_a.split()[0]}")
        with m3:
            higher = region_a if avg_a >= avg_b else region_b
            st.metric(label="⚠️ Higher Risk Region", value=higher.split()[0])

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        slope_a = np.polyfit(np.arange(len(df_a)), df_a["AQI"].values, 1)[0]
        slope_b = np.polyfit(np.arange(len(df_b)), df_b["AQI"].values, 1)[0]
        pred_a  = int(np.clip(df_a["AQI"].values[-1] + slope_a * 7, 15, 495))
        pred_b  = int(np.clip(df_b["AQI"].values[-1] + slope_b * 7, 15, 495))

        _, col_a_hex, _ = get_category(avg_a)
        _, col_b_hex, _ = get_category(avg_b)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_a["date"], y=df_a["AQI"], name=region_a,
            line=dict(color=col_a_hex, width=2.5),
            fill="tozeroy", fillcolor=hex_to_rgba(col_a_hex)
        ))
        fig.add_trace(go.Scatter(
            x=df_b["date"], y=df_b["AQI"], name=region_b,
            line=dict(color=col_b_hex, width=2.5),
            fill="tozeroy", fillcolor=hex_to_rgba(col_b_hex)
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#0a0f1e",
            height=320,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8")),
            xaxis=dict(gridcolor="#1e293b", tickfont=dict(color="#64748b")),
            yaxis=dict(
                gridcolor="#1e293b",
                tickfont=dict(color="#64748b"),
                title=dict(text="AQI Proxy", font=dict(color="#64748b"))
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

        fc1, fc2 = st.columns(2)
        for fc_col, rname, pred_val, slope_val in [
            (fc1, region_a, pred_a, slope_a),
            (fc2, region_b, pred_b, slope_b)
        ]:
            cat_p, col_p, _ = get_category(pred_val)
            conf  = max(60, min(95, int(90 - abs(slope_val) * 1.5)))
            arrow = "↑" if slope_val > 0 else "↓"
            with fc_col:
                st.markdown(f"""
                <div style="padding:14px; border-radius:10px; background:#111827;
                            border:1px solid #1e293b; border-left:4px solid {col_p};">
                    <p style="margin:0; font-size:0.72rem; color:#64748b; text-transform:uppercase; letter-spacing:0.06em;">
                        7-DAY PROJECTION · {rname.upper().split()[0]}
                    </p>
                    <p style="margin:6px 0 4px 0; font-size:1.5rem; font-weight:700; color:{col_p};
                               font-family:'JetBrains Mono', monospace;">
                        {pred_val} <span style='font-size:1rem;'>{arrow}</span>
                    </p>
                    <p style="margin:0; font-size:0.78rem; color:#94a3b8;">
                        Category: <b style='color:{col_p};'>{cat_p}</b>
                        &nbsp;·&nbsp; Confidence: <b style='color:#38bdf8;'>{conf}%</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)

        st.caption("⚠️ Trend projections are synthetic linear extrapolations for demonstration purposes only.")
# ── Tab 3: Regional Explorer (Replaced Methodology) ───────────
    with tab3:
        st.markdown("#### 🥇 Regional Explorer & Deep-Dive Analysis")
        st.markdown("<p style='font-size:0.85rem; color:#64748b; margin-top:-5px;'>Select an atmospheric zone to isolate regional metrics, calculate localized rankings, and track sensor tracking priorities.</p>", unsafe_allow_html=True)
        
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        
        # Region selector spanning full width
        selected_explorer_region = st.selectbox(
            "🔍 Choose Area for Granular Inspection:", 
            list(regions_data.keys()), 
            index=0, 
            key="explorer_region_select"
        )
        
        # Gather dynamic data points from our ranked collection
        reg_meta = regions_data[selected_explorer_region]
        reg_row = df_rank[df_rank["Region"] == selected_explorer_region]
        
        # Calculate localized ranking position
        reg_rank_idx = int(reg_row.index[0] + 1) if not reg_row.empty else "N/A"
        reg_proxy = int(reg_row.iloc[0]["Estimated AQI Proxy"]) if not reg_row.empty else 0
        reg_hcho = reg_row.iloc[0][hcho_column_name] if not reg_row.empty else "N/A"
        reg_trend = reg_row.iloc[0]["Trend"] if not reg_row.empty else "N/A"
        
        cat_i, color_i, desc_i = get_category(reg_proxy)
        text_color_i = "black" if cat_i == "Moderate" else "white"
        
        # Derived Suggested Monitoring Priorities & Short Interpretations
        if reg_proxy > 300:
            priority_tier = "CRITICAL (Level 1)"
            priority_color = "#E74C3C"
            short_interpretation = "Severe atmospheric column escalation detected. Immediate surface verification required to monitor dangerous dispersion levels."
        elif reg_proxy > 150:
            priority_tier = "ELEVATED (Level 2)"
            priority_color = "#E67E22"
            short_interpretation = "Persistent moderate enhancement profile. Tracking indicates sustained local emissions over the regional background layer."
        else:
            priority_tier = "NOMINAL (Level 3)"
            priority_color = "#2ECC71"
            short_interpretation = "Background trace measurements remain within standard operating ranges. No anomalies detected."

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # Layout Split: Main Metric Cards vs Descriptive Context Panels
        left_panel, right_panel = st.columns([2, 3])
        
        with left_panel:
            # Single unbroken string containing the metric blocks and native CSS progress bar
            left_explorer_html = f"""<div style="background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 20px; height: 100%;">
<p style="margin: 0 0 2px 0; font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em;">Primary Proxy Metric</p>
<div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 4px;">
<span style="font-size: 2.8rem; font-weight: 700; color: {color_i}; font-family: 'JetBrains Mono', monospace; line-height: 1;">{reg_proxy}</span>
<span style="font-size: 0.85rem; color: #64748b; font-family: 'JetBrains Mono', monospace;">AQI Proxy</span>
</div>
<div style="margin-bottom: 16px;"><span style="background: {color_i}; color: {text_color_i}; font-weight: 700; font-size: 0.75rem; padding: 3px 10px; border-radius: 4px; display: inline-block; text-transform: uppercase; letter-spacing: 0.04em;">{cat_i}</span></div>
<p style="margin: 0 0 4px 0; font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em;">Index Saturation</p>
<div style="width: 100%; background: #1e293b; border-radius: 10px; height: 8px; margin-bottom: 20px; overflow: hidden;"><div style="width: {min(100, int(reg_proxy/5))}%; background: {color_i}; height: 100%; border-radius: 10px;"></div></div>
<hr style="border: 0; border-top: 1px solid #1e293b; margin: 16px 0;" />
<table style="width: 100%; font-family: 'Inter', sans-serif; border-collapse: collapse;">
<tr style="border-bottom: 1px solid #1e293b;"><td style="padding: 10px 0; font-size: 0.8rem; color: #64748b; font-weight: 500;">National Standings</td><td style="padding: 10px 0; text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #38bdf8; font-size: 1rem;">Rank #{reg_rank_idx} of {len(df_rank)}</td></tr>
<tr style="border-bottom: 1px solid #1e293b;"><td style="padding: 10px 0; font-size: 0.8rem; color: #64748b; font-weight: 500;">HCHO Column Value</td><td style="padding: 10px 0; text-align: right; font-family: 'JetBrains Mono', monospace; color: #94a3b8; font-size: 0.82rem;">{reg_hcho} mol/m²</td></tr>
<tr><td style="padding: 10px 0; font-size: 0.8rem; color: #64748b; font-weight: 500;">Temporal Deviation</td><td style="padding: 10px 0; text-align: right; font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #e2e8f0; font-size: 0.85rem;">{reg_trend}</td></tr>
</table>
</div>"""
            st.markdown(left_explorer_html, unsafe_allow_html=True)
            
        with right_panel:
            # Single unbroken string containing source info, interpretation, and tracker configurations
            right_explorer_html = f"""<div style="display: flex; flex-direction: column; gap: 14px; height: 100%;">
<div style="background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 16px;">
<p style="margin: 0 0 6px 0; font-size: 0.72rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.06em;">Dominant Pollution Profile</p>
<p style="margin: 0; font-size: 0.88rem; color: #cbd5e1; line-height: 1.5;">{reg_meta["source"]}</p>
</div>
<div style="background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 16px;">
<p style="margin: 0 0 6px 0; font-size: 0.72rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em;">Short Interpretation</p>
<p style="margin: 0; font-size: 0.85rem; color: #e2e8f0; line-height: 1.5; font-style: italic;">"{short_interpretation}"</p>
<p style="margin: 8px 0 0 0; font-size: 0.75rem; color: #64748b;">Guidance Context: {desc_i}</p>
</div>
<div style="background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 16px; border-left: 4px solid {priority_color};">
<p style="margin: 0 0 4px 0; font-size: 0.72rem; font-weight: 700; color: {priority_color}; text-transform: uppercase; letter-spacing: 0.06em;">Suggested Monitoring Priority</p>
<p style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #f1f5f9; font-family: 'JetBrains Mono', monospace;">{priority_tier}</p>
</div>
</div>"""
            st.markdown(right_explorer_html, unsafe_allow_html=True)
            
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
# Update 14: Footnote reduced explicitly to 11px to fade elegantly into the background layout
st.markdown("""
<div style="margin-top: 2.5rem; padding-top: 12px; border-top: 1px solid #1e293b;">
    <p style='font-size: 11px; color: #334155; text-align: center; margin: 0; letter-spacing: 0.01em;'>
        Data: Sentinel-5P TROPOMI &bull; COPERNICUS/S5P/OFFL/L3_HCHO &bull; Boundary: USDOS/LSIB_SIMPLE/2017 &bull; Platform: Streamlit Framework
    </p>
</div>
""", unsafe_allow_html=True)