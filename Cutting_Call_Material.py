import streamlit as st
from supabase import create_client
from datetime import datetime

st.set_page_config(page_title="Material Handler System", layout="wide")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ----------------------
# COMMON
# ----------------------
menu = st.sidebar.radio(
    "โหมดระบบ",
    ["🔧 เรียกสายไฟ (Cutting)", "📦 Material Handler", "📜 History"]
)

# ----------------------
# MODE 1 : CUTTING
# ----------------------
if menu == "🔧 เรียกสายไฟ (Cutting)":
    st.header("🔧 เรียกสายไฟเข้าผลิต")

    machines = supabase.table("machines").select("machine_code").execute().data
    machine = st.selectbox("เลือกเครื่องจักร", [m["machine_code"] for m in machines])

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
        sorted(list(set(t["terminal_pair"] for t in terminals)))
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
        st.dataframe(wires, use_container_width=True)

        if st.button("✅ ยืนยันเรียกสายไฟ"):
            req = supabase.table("material_requests").insert({
                "machine_code": machine,
                "terminal_pair": terminal
            }).execute()

            req_id = req.data[0]["id"]

            for w in wires:
                supabase.table("material_request_items").insert({
                    "request_id": req_id,
                    "wire_name": w["wire_name"],
                    "wire_size": w["wire_size"],
                    "wire_color": w["wire_color"],
                    "total_length": w["total_length"]
                }).execute()

            st.success("🎉 เรียกสายไฟเรียบร้อย ส่งถึง Material Handler แล้ว")

# ----------------------
# MODE 2 : MATERIAL HANDLER
# ----------------------
elif menu == "📦 Material Handler":
    st.header("📦 งานรอจ่ายสายไฟ")

    data = supabase.from_("v_material_handler_dashboard").select("*").execute().data

    if not data:
        st.info("ยังไม่มีงานรอจ่าย")
    else:
        st.dataframe(data, use_container_width=True)

        req_ids = list(set(d["request_id"] for d in data))
        req = st.selectbox("เลือก Request", req_ids)

        if st.button("📤 จ่ายสายไฟ"):
            supabase.table("material_requests").update(
                {"status": "ISSUED"}
            ).eq("id", req).execute()

            st.success("จ่ายสายไฟเรียบร้อย")

# ----------------------
# MODE 3 : HISTORY
# ----------------------
else:
    st.header("📜 ประวัติการเรียกสายไฟ")

    history = (
        supabase
        .from_("material_requests")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    st.dataframe(history, use_container_width=True)
    st.caption(f"🔄 อัปเดตล่าสุด {datetime.now().strftime('%H:%M:%S')}")
