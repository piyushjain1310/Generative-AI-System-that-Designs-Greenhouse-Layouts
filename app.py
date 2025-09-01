#streamlit run app.py
import math
import io
from dataclasses import dataclass
from typing import List, Dict
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

st.set_page_config(
    page_title="Generative AI: Greenhouse Layout Designer",
    page_icon="🌿",
    layout="wide",
)

# ---------- Models ----------
@dataclass
class Rect:
    kind: str   # 'bed','aisle','headhouse','buffer','service'
    x: float
    y: float
    w: float
    h: float
    meta: Dict

def pack_repeating_stripes(total: float, stripe: float, gap: float) -> int:
    """Calculate how many beds/benches fit in available space"""
    if stripe <= 0 or total <= 0:
        return 0
    return max(0, math.floor((total + gap) / (stripe + gap))) if gap >= 0 else 0

# ---------- Sidebar Inputs ----------
with st.sidebar:
    st.title("🌿 Greenhouse Parameters")
    colA, colB = st.columns(2)
    with colA:
        W = st.number_input("Interior Width (m)",  value=9.0, min_value=2.0, step=0.5, format="%.2f")
        buffer = st.number_input("Perimeter Buffer (m)", value=0.3, min_value=0.0, step=0.1, format="%.2f")
        headhouse_depth = st.number_input("Headhouse Depth (m) at South", value=2.0, min_value=0.0, step=0.5, format="%.2f")
    with colB:
        L = st.number_input("Interior Length (m)", value=24.0, min_value=3.0, step=0.5, format="%.2f")
        orientation = st.selectbox("Bed Orientation", ["North–South (along length)", "East–West (along width)"])
        include_service = st.checkbox("Center Service Aisle", value=True)
        service_w = st.number_input("Service Aisle Width (m)", value=0.8, min_value=0.0, step=0.1, format="%.2f", disabled=not include_service)

    st.markdown("---")
    st.subheader("🧪 Layout Mode")
    mode = st.selectbox("Choose Layout", ["Soil Beds", "Benches (ebb-flow)"])
    if mode == "Soil Beds":
        bed_w = st.number_input("Bed Width (m)", value=1.2, min_value=0.3, step=0.1, format="%.2f")
        aisle_w = st.number_input("Aisle Width (m)", value=0.5, min_value=0.3, step=0.1, format="%.2f")
    else:
        bed_w = st.number_input("Bench Width (m)", value=1.0, min_value=0.3, step=0.1, format="%.2f")
        aisle_w = st.number_input("Bench Aisle (m)", value=0.6, min_value=0.3, step=0.1, format="%.2f")

    st.markdown("---")
    st.subheader("📦 Export")
    export_dpi = st.slider("PNG Export DPI", 100, 300, 160, 10)

# ---------- Derived dimensions ----------
grow_L = max(0.0, L - headhouse_depth - 2*buffer)
grow_W = max(0.0, W - 2*buffer)

beds_along_length = (orientation.startswith("North"))
if beds_along_length:
    stripes_span = grow_W
    stripe_length = grow_L
else:
    stripes_span = grow_L
    stripe_length = grow_W

n_beds = pack_repeating_stripes(stripes_span, bed_w, aisle_w)

# ---------- Build Rectangles ----------
rects: List[Rect] = []

# Headhouse
if headhouse_depth > 0:
    rects.append(Rect("headhouse", 0.0, 0.0, W, headhouse_depth, {"label": "Headhouse"}))

# Function to place beds/aisles
def place_stripes(start_x, start_y, length, stripe_w, gap_w, count, along_length=True):
    beds, aisles = [], []
    x, y = start_x, start_y
    for i in range(count):
        if along_length:
            beds.append(Rect("bed", x, y, stripe_w, length, {"index": i+1}))
            if i < count-1:
                aisles.append(Rect("aisle", x+stripe_w, y, gap_w, length, {"between": f"{i+1}-{i+2}"}))
                x += stripe_w + gap_w
        else:
            beds.append(Rect("bed", x, y, length, stripe_w, {"index": i+1}))
            if i < count-1:
                aisles.append(Rect("aisle", x, y+stripe_w, length, gap_w, {"between": f"{i+1}-{i+2}"}))
                y += stripe_w + gap_w
    return beds, aisles

start_x = buffer
start_y = headhouse_depth + buffer
beds, aisles = place_stripes(start_x, start_y, stripe_length, bed_w, aisle_w, n_beds, along_length=beds_along_length)
rects.extend(beds)
rects.extend(aisles)

# ---------- KPIs ----------
bed_area = sum(r.w * r.h for r in rects if r.kind == "bed")
aisle_area = sum(r.w * r.h for r in rects if r.kind == "aisle")
headhouse_area = headhouse_depth * W
total_area = W * L

# ---------- Header ----------
st.title("🌱 Generative AI System that Designs Greenhouse Layouts")

# ---------- Top KPIs ----------
k1,k2,k3 = st.columns(3)
k1.metric("Beds", f"{len(beds)}")
k2.metric("Cultivable Area", f"{bed_area:.1f} m²", f"{(100*bed_area/total_area):.1f}%")
k3.metric("Headhouse", f"{headhouse_area:.1f} m²")

# ---------- Layout Plot ----------
fig, ax = plt.subplots(figsize=(8,5))
ax.add_patch(plt.Rectangle((0,0), W, L, fill=False, linewidth=2))

def draw_rect(r: Rect):
    colors = {"bed":"#7cd992","aisle":"#e5e7eb","headhouse":"#fbcfe8"}
    ax.add_patch(plt.Rectangle((r.x, r.y), r.w, r.h,
                               facecolor=colors.get(r.kind,"#ddd"),
                               edgecolor="black", alpha=0.7))

for r in rects:
    draw_rect(r)

ax.set_xlim(-0.1, W+0.6)
ax.set_ylim(-0.1, L+0.6)
ax.set_aspect("equal")
ax.set_xlabel("Width (m)")
ax.set_ylabel("Length (m)")
ax.set_title(f"Layout: {mode} • {orientation}")
st.pyplot(fig)

# ---------- Export ----------
with st.expander("📋 Export & Data"):
    rows = [{"Type": r.kind, "x": r.x, "y": r.y, "width": r.w, "height": r.h, **r.meta} for r in rects]
    df = pd.DataFrame(rows)
    st.dataframe(df)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv_bytes, "layout.csv", "text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=export_dpi, bbox_inches="tight")
    st.download_button("🖼️ Download PNG", buf.getvalue(), "layout.png", "image/png")

st.markdown("---")
st.markdown("**How to run:** Save this file as `app.py`. Then in terminal run: `streamlit run app.py`")
