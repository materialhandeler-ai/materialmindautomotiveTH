import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# -------------------------
# Supabase
# -------------------------
url = st.secrets.get("SUPABASE_URL")
key = st.secrets.get("SUPABASE_ANON_KEY")

if not url or not key:
    st.error("❌ Supabase URL หรือ KEY ไม่ถูกตั้งค่า")
    st.stop()

supabase = create_client(url, key)

# -------------------------
# Helpers
# -------------------------
@st.cache_data(ttl=5)
def load_dashboard():
    res = supabase.table("v_material_dashboard") \
        .select("*") \
        .order("request_id", desc=True) \
        .execute()
    return res.data or []

@st.cache_data(ttl=30)
def load_staging():
    return supabase.table("wire_requirements_staging") \
        .select("*") \
        .execute().data or []

def call_material(machine, terminal):
    supabase.rpc(
        "create_material_request",
        {
            "p_machine_code": machine,
            "p_terminal_pair": terminal
        }
    ).execute()

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="Material System", layout="wide")

mode = st.sidebar.radio(
    "โหมดระบบ",
    ["🔧 เรียกสายไฟ (Cutting)", "📦 Material Handler", "📜 History"]
)

# =========================
# 🔧 CUTTING
# =========================
if mode == "🔧 เรียกสายไฟ (Cutting)":
    st.header("🔧 เรียกสายไฟเข้าผลิต")

    staging = load_staging()
    df = pd.DataFrame(staging)

    if df.empty:
        st.info("🕒 ไม่มีงานรอเรียก")
        st.stop()

    machine = st.selectbox(
        "เลือกเครื่องจักร",
        sorted(df["machine_code"].unique())
    )

    terminals = df[df["machine_code"] == machine]["terminal_pair"].unique()
    terminal = st.selectbox("เลือกกลุ่ม Terminal", terminals)

    preview = df[
        (df["machine_code"] == machine) &
        (df["terminal_pair"] == terminal)
    ]

    st.subheader("📋 รายการสายไฟ")
    st.dataframe(
        preview[[
            "wire_name",
            "wire_size",
            "wire_color",
            "quantity_meter"
        ]]
    )

    if st.button("✅ เรียกสายไฟ"):
        call_material(machine, terminal)
        st.success("เรียกสายไฟเรียบร้อย")
        st.cache_data.clear()

# =========================
# 📦 MATERIAL HANDLER
# =========================
elif mode == "📦 Material Handler":
    st.header("📦 Material Handler Dashboard")
    st.caption("Realtime wire request from cutting machines")

    data = load_dashboard()

    if not data:
        st.warning("⚠️ ยังไม่มีข้อมูลเรียกวัตถุดิบ")
        st.stop()

    df = pd.DataFrame(data)
    st.dataframe(
        df[[
            "machine",
            "terminal",
            "wire_detail",
            "status"
        ]],
        use_container_width=True
    )

# =========================
# 📜 HISTORY
# =========================
else:
    st.header("📜 History")

    res = supabase.table("material_requests") \
        .select(
            "id,status,"
            "machines(machine_code),"
            "terminal_groups(terminal_pair)"
        ) \
        .order("id", desc=True) \
        .execute()

    st.dataframe(pd.DataFrame(res.data))
