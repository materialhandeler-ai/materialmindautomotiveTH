import streamlit as st
from supabase import create_client

# ================= CONFIG =================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Material Request System", layout="wide")

# ================= MODE =================
mode = st.sidebar.radio(
    "🧭 Select Mode",
    ["🔧 Production / Cutting", "📦 Material Handler", "📜 History"]
)

# =================================================
# 🔧 PRODUCTION / CUTTING
# =================================================
if mode == "🔧 Production / Cutting":
    st.title("🔧 Production – Call Material")

    machines = supabase.table("machines") \
        .select("id, machine_code") \
        .order("machine_code") \
        .execute().data

    terminals = supabase.table("terminal_groups") \
        .select("id, terminal_pair") \
        .order("terminal_pair") \
        .execute().data

    machine = st.selectbox(
        "Machine",
        machines,
        format_func=lambda x: x["machine_code"]
    )

    terminal = st.selectbox(
        "Terminal Pair",
        terminals,
        format_func=lambda x: x["terminal_pair"]
    )

    if st.button("📞 Call Material", type="primary"):
        supabase.rpc(
            "rpc_create_material_request",
            {
                "p_machine_id": machine["id"],
                "p_terminal_group_id": terminal["id"]
            }
        ).execute()
        st.success("✅ Material request submitted")

# =================================================
# 📦 MATERIAL HANDLER
# =================================================
elif mode == "📦 Material Handler":
    st.title("📦 Material Handler Dashboard")

    rows = supabase.table("v_material_handler_dashboard").select("*").execute().data

    if not rows:
        st.info("ไม่มีงานค้าง")
    else:
        from collections import defaultdict
        grouped = defaultdict(list)

        for r in rows:
            grouped[r["request_id"]].append(r)

        for request_id, items in grouped.items():
            header = items[0]

            with st.container(border=True):
                st.markdown(
                    f"""
                    **Machine:** {header['machine_code']}  
                    **Terminal:** {header['terminal_pair']}  
                    **Status:** `{header['status']}`
                    """
                )

                all_checked = True

                for it in items:
                    checked = st.checkbox(
                        f"Wire ID: {it['wire_id']} | Length: {it['total_length']} m",
                        value=it["is_delivered"],
                        key=f"chk_{it['item_id']}"
                    )

                    if checked != it["is_delivered"]:
                        supabase.table("material_request_items") \
                            .update({"is_delivered": checked}) \
                            .eq("id", it["item_id"]) \
                            .execute()

                    if not checked:
                        all_checked = False

                if header["status"] == "REQUESTED":
                    if st.button("🟡 รับงาน", key=f"start_{request_id}"):
                        supabase.rpc(
                            "rpc_handler_start_request",
                            {"p_request_id": request_id}
                        ).execute()
                        st.rerun()

                elif header["status"] == "IN_PROGRESS":
                    if all_checked:
                        if st.button("✅ ส่งของ", key=f"done_{request_id}"):
                            supabase.rpc(
                                "rpc_handler_finish_request",
                                {"p_request_id": request_id}
                            ).execute()
                            st.rerun()
                    else:
                        st.warning("⚠️ ต้องเลือกสายไฟครบทุกเส้นก่อนส่งของ")

# =================================================
# 📜 HISTORY
# =================================================
elif mode == "📜 History":
    st.title("📜 Material Request History")

    status_filter = st.multiselect(
        "Status",
        ["REQUESTED", "IN_PROGRESS", "DELIVERED"],
        default=["DELIVERED"]
    )

    query = supabase.table("material_requests").select(
        "id,status,requested_at,delivered_at,"
        "machines(machine_code),"
        "terminal_groups(terminal_pair)"
    )

    if status_filter:
        query = query.in_("status", status_filter)

    rows = query.order("requested_at", desc=True).execute().data

    st.dataframe(
        [{
            "Machine": r["machines"]["machine_code"],
            "Terminal Pair": r["terminal_groups"]["terminal_pair"],
            "Status": r["status"],
            "Requested At": r["requested_at"],
            "Delivered At": r["delivered_at"]
        } for r in rows],
        use_container_width=True
    )
