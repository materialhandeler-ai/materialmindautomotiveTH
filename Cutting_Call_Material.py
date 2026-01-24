import streamlit as st
from supabase import create_client
from datetime import datetime

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="Material Handler Dashboard",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# SAFE HELPERS
# ----------------------------
def safe_select(table, columns="*", filters=None, order=None):
    try:
        q = supabase.table(table).select(columns)
        if filters:
            for k, v in filters.items():
                q = q.eq(k, v)
        if order:
            q = q.order(order, desc=True)
        res = q.execute()
        return res.data or []
    except Exception:
        return []

def safe_rpc(name, params):
    try:
        return supabase.rpc(name, params).execute().data
    except Exception:
        return None

# ----------------------------
# UI HEADER
# ----------------------------
st.title("📦 Material Handler Dashboard")
st.caption("Realtime wire request from cutting machines")

mode = st.sidebar.radio(
    "โหมดระบบ",
    [
        "🔧 เรียกสายไฟ (Cutting)",
        "📦 Material Handler",
        "📜 History"
    ]
)

# ==========================================================
# 🔧 MODE 1 : CALL MATERIAL (CUTTING)
# ==========================================================
if mode == "🔧 เรียกสายไฟ (Cutting)":

    st.subheader("🔧 เรียกสายไฟเข้าผลิต")

    # --- ดึง option จาก wire_requirements_staging เท่านั้น
    staging = safe_select("wire_requirements_staging")

    machines = sorted({r["machine_code"] for r in staging if r.get("machine_code")})
    terminals = sorted({r["terminal_pair"] for r in staging if r.get("terminal_pair")})

    machine = st.selectbox("เลือกเครื่องจักร", machines)
    terminal = st.selectbox("เลือกกลุ่ม Terminal", terminals)

    if machine and terminal:
        rows = [
            r for r in staging
            if r["machine_code"] == machine
            and r["terminal_pair"] == terminal
        ]

        if rows:
            st.markdown("📋 รายการสายไฟ")
            st.dataframe(
                [
                    {
                        "Wire size": r.get("wire_size"),
                        "Total length (m)": float(r.get("total_length", 0))
                    }
                    for r in rows
                ],
                use_container_width=True
            )

            if st.button("✅ ยืนยันเรียกสายไฟ"):
                result = safe_rpc(
                    "create_material_request",
                    {
                        "p_machine_code": machine,
                        "p_terminal_pair": terminal
                    }
                )

                if result:
                    st.success("🎉 เรียกสายไฟสำเร็จ")
                else:
                    st.warning("⚠️ ไม่มีข้อมูลที่สามารถเรียกได้ (ระบบไม่ error)")

        else:
            st.info("ยังไม่มี wire requirement สำหรับเงื่อนไขนี้")

# ==========================================================
# 📦 MODE 2 : MATERIAL HANDLER DASHBOARD
# ==========================================================
elif mode == "📦 Material Handler":

    st.subheader("📦 งานที่รอจ่ายสายไฟ")

    dashboard = safe_select("v_material_dashboard")

    if dashboard:
        st.dataframe(dashboard, use_container_width=True)
    else:
        st.info("ไม่มีงานค้างจ่าย")

    st.caption(f"🔄 อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")

# ==========================================================
# 📜 MODE 3 : HISTORY
# ==========================================================
elif mode == "📜 History":

    st.subheader("📜 ประวัติการเรียกสายไฟ")

    history = safe_select("material_requests", order="id")

    if history:
        st.dataframe(history, use_container_width=True)
    else:
        st.info("ยังไม่มีประวัติการเรียกสายไฟ")
