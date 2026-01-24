import streamlit as st
from supabase import create_client
from datetime import datetime

st.set_page_config(page_title="Cutting Call Material", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)

# -------------------------
# Loaders
# -------------------------
@st.cache_data(ttl=10)
def load_machines():
    return supabase.table("machines").select("id,machine_code").execute().data

@st.cache_data(ttl=10)
def load_terminal_groups():
    return supabase.table("terminal_groups").select("id,terminal_pair").execute().data

@st.cache_data(ttl=5)
def load_pending():
    return supabase.table("v_material_dashboard_pending").select("*").execute().data

@st.cache_data(ttl=5)
def load_delivered():
    return supabase.table("v_material_dashboard_delivered").select("*").execute().data

# -------------------------
# Sidebar
# -------------------------
mode = st.sidebar.radio(
    "โหมดระบบ",
    [
        "🔧 เรียกสายไฟ (Cutting)",
        "📦 Material Handler",
        "📜 History"
    ]
)

# =========================================================
# MODE 1: CALL MATERIAL
# =========================================================
if mode == "🔧 เรียกสายไฟ (Cutting)":
    st.header("🔧 เรียกสายไฟเข้าผลิต")

    machines = load_machines()
    terminals = load_terminal_groups()

    m_map = {m["machine_code"]: m["id"] for m in machines}
    t_map = {t["terminal_pair"]: t["id"] for t in terminals}

    machine = st.selectbox("เลือกเครื่องจักร", m_map.keys())
    terminal = st.selectbox("เลือกกลุ่ม Terminal", t_map.keys())

    if st.button("📢 เรียกสายไฟ"):
        res = supabase.rpc(
            "create_material_request",
            {
                "p_machine_id": m_map[machine],
                "p_terminal_group_id": t_map[terminal]
            }
        ).execute()

        st.success(f"✅ เรียกสายไฟเรียบร้อย (Request ID: {res.data})")
        st.cache_data.clear()

# =========================================================
# MODE 2: MATERIAL HANDLER
# =========================================================
elif mode == "📦 Material Handler":
    st.header("📦 Material Handler Dashboard")

    data = load_pending()

    if not data:
        st.info("ยังไม่มีรายการรอจัดส่ง")
    else:
        for r in data:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2,2,5,1])

                c1.write(f"เครื่อง: **{r['machine_code']}**")
                c2.write("⏳ Pending")
                c3.markdown(
                    r["wire_summary"].replace("\n", "<br>"),
                    unsafe_allow_html=True
                )

                if c4.button("✅", key=r["request_id"]):
                    supabase.rpc(
                        "confirm_material_delivery",
                        {"p_request_id": r["request_id"]}
                    ).execute()
                    st.cache_data.clear()
                    st.rerun()

# =========================================================
# MODE 3: HISTORY
# =========================================================
else:
    st.header("📜 ประวัติการจัดส่ง")

    data = load_delivered()
    if not data:
        st.info("ยังไม่มีข้อมูล")
    else:
        for r in data:
            st.markdown(
                f"""
                **เครื่อง:** {r['machine_code']}  
                **สายไฟ:**  
                {r['wire_summary'].replace("\n", "<br>")}
                """,
                unsafe_allow_html=True
            )

st.caption(f"🕒 {datetime.now().strftime('%H:%M:%S')}")
