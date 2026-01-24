import streamlit as st
from supabase import create_client
from datetime import datetime

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="Material Handler Dashboard", layout="wide")

SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase URL หรือ KEY ไม่ถูกตั้งค่าใน Streamlit Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# Data loaders (cache)
# -------------------------
@st.cache_data(ttl=5)
def load_pending():
    res = (
        supabase
        .table("v_material_dashboard_pending")
        .select("*")
        .order("request_id", desc=False)
        .execute()
    )
    return res.data or []

@st.cache_data(ttl=5)
def load_delivered():
    res = (
        supabase
        .table("v_material_dashboard_delivered")
        .select("*")
        .order("request_id", desc=True)
        .execute()
    )
    return res.data or []

def confirm_delivery(request_id: str):
    return supabase.rpc(
        "confirm_material_delivery",
        {"p_request_id": request_id}
    ).execute()

# -------------------------
# UI
# -------------------------
st.title("📦 Material Handler Dashboard")
st.caption("Realtime wire request from cutting machines")

mode = st.sidebar.radio(
    "โหมดการทำงาน",
    ["⏳ Pending Requests", "📜 Delivered History"],
)

# -------------------------
# MODE: PENDING
# -------------------------
if mode == "⏳ Pending Requests":
    data = load_pending()

    if not data:
        st.info("⚠️ ยังไม่มีรายการรอจัดส่ง")
    else:
        for row in data:
            with st.container(border=True):
                cols = st.columns([2, 2, 5, 1])

                cols[0].markdown(f"**เครื่อง**\n\n{row['machine_code']}")
                cols[1].markdown("**สถานะ**\n\n⏳ Pending")
                cols[2].markdown(f"**สายไฟ / จำนวน**\n\n{row['wire_summary'].replace(chr(10), '<br>')}", unsafe_allow_html=True)

                if cols[3].button("✅ จัดส่ง", key=row["request_id"]):
                    try:
                        confirm_delivery(row["request_id"])
                        st.success("จัดส่งเรียบร้อย")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ จัดส่งไม่สำเร็จ: {e}")

# -------------------------
# MODE: DELIVERED
# -------------------------
else:
    data = load_delivered()

    if not data:
        st.info("📭 ยังไม่มีประวัติการจัดส่ง")
    else:
        for row in data:
            with st.container(border=True):
                st.markdown(
                    f"""
                    **เครื่อง:** {row['machine_code']}  
                    **สถานะ:** ✅ Delivered  

                    **สายไฟ / จำนวน:**  
                    {row['wire_summary'].replace(chr(10), '<br>')}
                    """,
                    unsafe_allow_html=True
                )

st.caption(f"🔄 อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")
