import streamlit as st
from supabase import create_client
from datetime import datetime

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Material Handler Dashboard",
    layout="wide"
)

st.title("📦 Material Handler Dashboard")
st.caption("Realtime wire request from cutting machines")

# -------------------------
# Supabase connection
# -------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase URL หรือ KEY ไม่ถูกตั้งค่าใน Streamlit Secrets")
    st.stop()

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("❌ ไม่สามารถเชื่อมต่อ Supabase ได้")
    st.write(e)
    st.stop()

# -------------------------
# Load data
# -------------------------
@st.cache_data(ttl=5)
def load_dashboard():
    try:
        res = (
            supabase
            .table("cutting_call_material")  # 👈 ตรวจชื่อ table ให้ตรง
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data
    except Exception as e:
        st.error("❌ ไม่สามารถดึงข้อมูลจาก Supabase ได้")
        st.write(e)
        return []

data = load_dashboard()

# -------------------------
# Display
# -------------------------
if not data:
    st.warning("⚠️ ยังไม่มีข้อมูลเรียกวัตถุดิบ")
else:
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )

st.divider()

st.caption(f"🔄 อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")

# -------------------------
# Auto refresh (ปลอดภัย)
# -------------------------
st.button("🔄 Refresh now")
