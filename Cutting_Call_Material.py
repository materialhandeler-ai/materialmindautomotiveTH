import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# -----------------------
# Supabase connection
# -----------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------
# Page config
# -----------------------
st.set_page_config(
    page_title="Material Handler Dashboard",
    layout="wide"
)

st.title("📦 Material Handler Dashboard")
st.caption("Realtime wire request from cutting machines")

# auto refresh every 5 sec
st.autorefresh(interval=5000, key="refresh")

# -----------------------
# Load dashboard data
# -----------------------
def load_dashboard():
    res = (
        supabase
        .table("v_wire_dashboard")
        .select("*")
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []

# -----------------------
# Confirm delivery (RPC)
# -----------------------
def confirm_delivery(request_id: str):
    supabase.rpc(
        "confirm_wire_delivery",
        {"p_request_id": request_id}
    ).execute()

# -----------------------
# UI
# -----------------------
data = load_dashboard()

if not data:
    st.success("🎉 ไม่มีรายการค้างจัดส่ง")
    st.stop()

df = pd.DataFrame(data)

# group by machine + terminal
grouped = df.groupby(["machine", "terminal"])

for (machine, terminal), group in grouped:
    st.subheader(f"🔧 เครื่อง: {machine} | Terminal: {terminal}")

    rows = []
    for _, r in group.iterrows():
        wire_text = (
            f"{r['wire_name']} "
            f"{r['wire_size']} "
            f"{r['wire_color']} : "
            f"{r['quantity_meter']} เมตร"
        )
        rows.append({
            "เวลา": pd.to_datetime(r["created_at"]).strftime("%H:%M"),
            "สายไฟ / จำนวน": wire_text,
            "request_id": r["request_id"]
        })

    display_df = pd.DataFrame(rows)

    col1, col2 = st.columns([6, 1])

    with col1:
        st.dataframe(
            display_df[["เวลา", "สายไฟ / จำนวน"]],
            use_container_width=True,
            hide_index=True
        )

    with col2:
        for req_id in display_df["request_id"]:
            if st.button("✅ จัดส่ง", key=req_id):
                confirm_delivery(req_id)
                st.success("จัดส่งแล้ว")
                st.rerun()
