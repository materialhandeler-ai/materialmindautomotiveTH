import streamlit as st
from supabase import create_client
from datetime import datetime

# ----------------------
# CONFIG
# ----------------------
st.set_page_config(page_title="Material Handler System", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]  # ต้องเป็น service_role
)

# ----------------------
# MENU
# ----------------------
menu = st.sidebar.radio(
    "โหมดระบบ",
    ["🔧 เรียกสายไฟ (Cutting)", "📦 Material Handler", "📜 History"]
)

# =====================================================
# MODE 1 : CUTTING
# =====================================================
if menu == "🔧 เรียกสายไฟ (Cutting)":
    st.header("🔧 เรียกสายไฟเข้าผลิต")

    machines = (
        supabase
        .table("machines")
        .select("machine_code")
        .order("machine_code")
        .execute()
        .data
    )

    machine = st.selectbox(
        "เลือกเครื่องจักร",
        [m["machine_code"] for m in machines]
    )

    terminals = (
        supabase
        .from_("wire_requirements_staging")
        .select("terminal_pair")
        .eq("machine_code", machine)
        .execute()
        .data
    )

    terminal = st.selectbox(
        "เลือกกลุ่ม Terminal",
        sorted({t["terminal_pair"] for t in terminals})
    )

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
        st.dataframe(wires, use_container_width=True)

        if st.button("✅ ยืนยันเรียกสายไฟ"):
            res = supabase.rpc(
                "rpc_create_material_request",
                {
                    "p_machine_code": machine,
                    "p_terminal_pair": terminal
                }
            ).execute()

            if res.data is None:
                st.error("❌ ไม่สามารถสร้าง Material Request ได้")
                st.write(res)
            else:
                st.success("🎉 เรียกสายไฟเรียบร้อย ส่งถึง Material Handler แล้ว")

# =====================================================
# MODE 2 : MATERIAL HANDLER
# =====================================================
elif menu == "📦 Material Handler":
    st.header("📦 งานรอจ่ายสายไฟ")

    data = (
        supabase
        .from_("v_material_handler_dashboard")
        .select("*")
        .execute()
        .data
    )

    if not data:
        st.info("ยังไม่มีงานรอจ่าย")
    else:
        st.dataframe(data, use_container_width=True)

        req_id = st.selectbox(
            "เลือก Request",
            sorted({d["request_id"] for d in data})
        )

        if st.button("📤 จ่ายสายไฟ"):
            supabase.table("material_requests") \
                .update({"status": "ISSUED"}) \
                .eq("id", req_id) \
                .execute()

            st.success("✅ จ่ายสายไฟเรียบร้อย")

# =====================================================
# MODE 3 : HISTORY
# =====================================================
else:
    st.header("📜 ประวัติการเรียกสายไฟ")

    history = (
        supabase
        .table("material_requests")
        .select("id, status, created_at")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    st.dataframe(history, use_container_width=True)
    st.caption(f"🔄 อัปเดตล่าสุด {datetime.now().strftime('%H:%M:%S')}")
