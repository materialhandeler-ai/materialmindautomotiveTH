import streamlit as st
import pandas as pd
from supabase import create_client

# ------------------------
# Config
# ------------------------
st.set_page_config(
    page_title="📦 Material Handler Dashboard",
    layout="wide"
)

st.title("📦 Material Handler Dashboard")
st.caption("Realtime wire request from cutting machines")

# ------------------------
# Supabase Connection
# ------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase URL หรือ KEY ไม่ถูกตั้งค่าใน Streamlit Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------
# Load Dashboard Data
# ------------------------
def load_dashboard():
    try:
        res = (
            supabase
            .table("v_material_dashboard_pending")
            .select("*")
            .execute()
        )
        return res.data
    except Exception as e:
        st.error("❌ ไม่สามารถดึงข้อมูลจาก Supabase ได้")
        st.exception(e)
        return []

# ------------------------
# Confirm Delivery
# ------------------------
def confirm_request(request_id: str):
    try:
        supabase.table("material_requests") \
            .update({"status": "DELIVERED"}) \
            .eq("id", request_id) \
            .execute()
        st.success("✅ ยืนยันการจัดส่งเรียบร้อย")
    except Exception as e:
        st.error("❌ ไม่สามารถอัปเดตสถานะได้")
        st.exception(e)

# ------------------------
# UI
# ------------------------
data = load_dashboard()

if not data:
    st.warning("⚠️ ยังไม่มีข้อมูลเรียกวัตถุดิบ")
else:
    df = pd.DataFrame(data)

    for _, row in df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 2, 4, 1])

        with col1:
            st.write(row["machine_code"])

        with col2:
            st.write(row["terminal_pair"])

        with col3:
            st.markdown("⏳ **PENDING**")

        with col4:
            st.text(row["wire_summary"])

        with col5:
            if st.button("✅ Confirm", key=row["request_id"]):
                confirm_request(row["request_id"])
                st.rerun()
