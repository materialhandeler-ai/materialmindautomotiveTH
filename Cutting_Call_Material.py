import streamlit as st
from supabase import create_client
import pandas as pd

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="📦 Wire Request Dashboard",
    layout="wide"
)

# -----------------------------
# SUPABASE
# -----------------------------
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

st.title("📦 Wire Request Dashboard")

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=3)
def load_dashboard():
    res = supabase.table("v_wire_dashboard") \
        .select("*") \
        .order("created_at") \
        .execute()
    return pd.DataFrame(res.data)

df = load_dashboard()

if df.empty:
    st.success("🎉 ไม่มีรายการรอจัดส่ง")
    st.stop()

# -----------------------------
# FORMAT
# -----------------------------
df["เวลา"] = pd.to_datetime(df["created_at"]).dt.strftime("%H:%M")
df["สายไฟ / จำนวน"] = (
    df["wire_name"] + " " +
    df["wire_size"].astype(str) + " " +
    df["wire_color"] + " : " +
    df["quantity_meter"].astype(str) + " เมตร"
)

# -----------------------------
# TABLE
# -----------------------------
st.markdown("""
| เวลา | เครื่อง | Terminal | สายไฟ / จำนวน | สถานะ | Action |
|---|---|---|---|---|---|
""")

for _, row in df.iterrows():
    c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,4,1,1])

    c1.write(row["เวลา"])
    c2.write(row["machine"])
    c3.write(row["terminal"])
    c4.markdown(row["สายไฟ / จำนวน"])
    c5.write("⏳")

    if c6.button("✅", key=row["request_id"]):
        supabase.rpc(
            "confirm_wire_delivery",
            {"p_request_id": row["request_id"]}
        ).execute()

        st.cache_data.clear()
        st.rerun()
