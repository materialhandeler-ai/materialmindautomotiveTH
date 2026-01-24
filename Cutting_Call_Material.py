import streamlit as st
from supabase import create_client
from datetime import datetime
import time

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(
    page_title="📦 Material Handler Dashboard",
    layout="wide"
)

st.title("📦 Material Handler Dashboard")
st.caption("Realtime wire request from cutting machines")

# -------------------------------
# SUPABASE CONNECTION
# -------------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase URL หรือ KEY ไม่ถูกตั้งค่าใน Streamlit Secrets")
    st.stop()

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("❌ ไม่สามารถเชื่อมต่อ Supabase ได้")
    st.exception(e)
    st.stop()

# -------------------------------
# LOAD DASHBOARD DATA
# -------------------------------
def load_dashboard():
    try:
        res = (
            supabase
            .table("v_material_dashboard")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        st.error("❌ ไม่สามารถดึงข้อมูลจาก Supabase ได้")
        st.exception(e)
        return []

# -------------------------------
# CONFIRM DELIVERY
# -------------------------------
def confirm_delivery(request_id):
    try:
        supabase.rpc(
            "confirm_wire_delivery",
            {"p_request_id": request_id}
        ).execute()
        st.success("✅ ยืนยันการจัดส่งแล้ว")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error("❌ ยืนยันการจัดส่งไม่สำเร็จ")
        st.exception(e)

# -------------------------------
# MAIN
# -------------------------------
data = load_dashboard()

if not data:
    st.warning("⚠️ ยังไม่มีข้อมูลเรียกวัตถุดิบ")
else:
    st.subheader("📋 รายการเรียกวัตถุดิบ")

    for row in data:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1.5, 3, 1])

            with col1:
                st.write("⏱ เวลา")
                st.write(
                    datetime.fromisoformat(row["created_at"]).strftime("%H:%M")
                )

            with col2:
                st.write("🖥 เครื่อง")
                st.write(row["machine_code"])

            with col3:
                st.write("🔌 Terminal")
                st.write(row["terminal_pair"])

            with col4:
                st.write("🧵 สายไฟ / จำนวน")
                st.markdown(
                    f"""
                    **{row['wire_type']}**
                    - ขนาด: {row['wire_size']}
                    - สี: {row['wire_color']}
                    - จำนวน: **{row['quantity_meter']} เมตร**
                    """
                )

            with col5:
                if not row["is_delivered"]:
                    if st.button(
                        "✅",
                        key=f"confirm_{row['request_item_id']}"
                    ):
                        confirm_delivery(row["request_item_id"])
                else:
                    st.success("ส่งแล้ว")

# -------------------------------
# AUTO REFRESH (ปลอดภัย)
# -------------------------------
st.divider()
st.caption(f"🔄 อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(5)
st.rerun()
