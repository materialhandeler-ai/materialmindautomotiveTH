import streamlit as st
from supabase import create_client
from datetime import datetime
import time

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="📦 Material Handler Dashboard",
    layout="wide"
)

st.title("📦 Material Handler Dashboard")
st.caption("Realtime wire request from cutting machines")

# ===============================
# AUTO REFRESH (แทน st.autorefresh)
# ===============================
time.sleep(0.1)
st.session_state["_last_refresh"] = datetime.now()

# ===============================
# SUPABASE CONNECT
# ===============================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase URL หรือ KEY ไม่ถูกตั้งค่าใน Streamlit Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# LOAD DATA
# ===============================
@st.cache_data(ttl=5)
def load_dashboard():
    try:
        response = (
            supabase
            .table("cutting_call_material")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data

    except Exception as e:
        st.error("❌ ไม่สามารถเชื่อมต่อ Supabase ได้")
        st.code(str(e))
        return []

# ===============================
# DISPLAY
# ===============================
data = load_dashboard()

if not data:
    st.warning("⚠️ ยังไม่มีข้อมูลเรียกวัตถุดิบ")
else:
    st.success(f"📊 พบข้อมูล {len(data)} รายการ")
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )

# ===============================
# FOOTER + AUTO RERUN
# ===============================
st.divider()
st.caption(f"🔄 อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")

time.sleep(5)
st.experimental_rerun()
