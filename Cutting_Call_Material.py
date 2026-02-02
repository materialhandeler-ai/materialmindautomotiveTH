import streamlit as st
from supabase import create_client
from datetime import datetime
import pandas as pd

# ----------------------
# CONFIG
# ----------------------
st.set_page_config(page_title="Material Handler System", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]  # ต้องเป็น Service Role

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------
# MENU
# ----------------------
menu = st.sidebar.radio(
    "โหมดระบบ",
    ["🔧 เรียกสายไฟ (Cutting)", "📦 Material Handler", "📜 History"]
)

# =====================================================
# MODE 1 : CUTTING (Call Material)
# =====================================================
if menu == "🔧 เรียกสายไฟ (Cutting)":
    st.header("🔧 เรียกสายไฟเข้าผลิต")

    # --- เลือกเครื่องจักร ---
    machines = supabase.table("machines").select("machine_code").order("machine_code").execute().data
    machine_codes = [m["machine_code"] for m in machines]

    if not machine_codes:
        st.warning("❌ ไม่มีเครื่องจักรในระบบ")
    else:
        machine = st.selectbox("เลือกเครื่องจักร", machine_codes)

        # --- เลือก Terminal ---
        terminals = (
            supabase
            .from_("wire_requirements_staging")
            .select("terminal_pair")
            .eq("machine_code", machine)
            .execute()
            .data
        )
        terminal_list = sorted(list({t["terminal_pair"] for t in terminals if t.get("terminal_pair")}))
        terminal = st.selectbox("เลือกกลุ่ม Terminal", terminal_list)

        # --- ดูรายการสายไฟ ---
        wires = (
            supabase
            .from_("v_cutting_wire_request")
            .select("*")
            .eq("machine_code", machine)
            .eq("terminal_pair", terminal)
            .execute()
            .data
        )

        if not wires:
            st.warning("ยังไม่มี wire requirement สำหรับเงื่อนไขนี้")
        else:
            st.subheader("📋 รายการสายไฟ")
            df = pd.DataFrame(wires)
            st.dataframe(df, use_container_width=True)

            # --- ปุ่ม CALL (RPC) ---
            if st.button("✅ ยืนยันเรียกสายไฟ"):
                res = supabase.rpc(
                    "rpc_create_material_request",
                    {"p_machine_code": machine, "p_terminal_pair": terminal}
                ).execute()

                if res.error:
                    st.error(f"❌ เกิดปัญหา: {res.error.message}")
                    st.write(res.error)
                else:
                    st.success("🎉 เรียกสายไฟเรียบร้อย ส่งถึง Material Handler แล้ว")
                    st.write("📌 Request ID:", res.data)

# =====================================================
# MODE 2 : MATERIAL HANDLER
# =====================================================
elif menu == "📦 Material Handler":
    st.header("📦 งานรอจ่ายสายไฟ")

    # --- ดึงจาก View ---
    data = (
        supabase
        .from_("v_material_handler_dashboard")
        .select("*")
        .order("request_time", desc=True)
        .execute()
        .data
    )

    if not data:
        st.info("🎯 ไม่มีงานรอจ่ายสายไฟ")
    else:
        df2 = pd.DataFrame(data)
        st.dataframe(df2, use_container_width=True)

        request_ids = sorted({d["request_id"] for d in data})
        selected = st.selectbox("เลือก Request", request_ids)

        if st.button("📤 จ่ายสายไฟ"):
            upd = supabase.table("material_requests") \
                .update({"status": "ISSUED"}) \
                .eq("id", selected) \
                .execute()

            if upd.error:
                st.error("❌ ไม่สามารถอัปเดตสถานะได้")
                st.write(upd.error.message)
            else:
                st.success("📦 สถานะจ่ายสายไฟเรียบร้อย")

# =====================================================
# MODE 3 : HISTORY
# =====================================================
else:
    st.header("📜 ประวัติการเรียกสายไฟ")

    history = (
        supabase
        .from_("material_requests")
        .select("id, status, created_at")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    if not history:
        st.info("📭 ยังไม่มีประวัติการเรียกสายไฟ")
    else:
        df3 = pd.DataFrame(history)
        st.dataframe(df3, use_container_width=True)

    st.caption(f"🔄 อัปเดตล่าสุด: {datetime.now().strftime('%H:%M:%S')}")
