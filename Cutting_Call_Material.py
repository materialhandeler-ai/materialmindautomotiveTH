import streamlit as st
from supabase import create_client
from datetime import datetime

# ================= CONFIG =================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="Material Request System",
    layout="wide"
)

# ================= MODE SELECT =================
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
        try:
            supabase.rpc(
                "rpc_create_material_request",
                {
                    "p_machine_id": machine["id"],
                    "p_terminal_group_id": terminal["id"]
                }
            ).execute()

            st.success("✅ Material request submitted")

        except Exception as e:
            st.error(f"❌ {e}")

# =================================================
# 📦 MATERIAL HANDLER DASHBOARD
# =================================================
elif mode == "📦 Material Handler":
    st.title("📦 Material Handler Dashboard")

    rows = supabase.table("v_material_handler_dashboard") \
        .select("*") \
        .order("requested_at") \
        .execute().data

    if not rows:
        st.info("📭 No pending requests")
    else:
        for r in rows:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 3, 2, 2])

                c1.markdown(f"**Machine**: {r['machine_code']}")
                c2.markdown(f"**Terminal**: {r['terminal_pair']}")
                c3.markdown(f"**Status**: `{r['status']}`")

                # ===== ACTION =====
                if r["status"] == "REQUESTED":
                    if c4.button(
                        "🟡 รับงาน",
                        key=f"start_{r['request_id']}"
                    ):
                        supabase.table("material_requests") \
                            .update({"status": "IN_PROGRESS"}) \
                            .eq("id", r["request_id"]) \
                            .execute()
                        st.rerun()

                elif r["status"] == "IN_PROGRESS":
                    if c4.button(
                        "✅ ส่งของ",
                        key=f"done_{r['request_id']}"
                    ):
                        supabase.table("material_requests") \
                            .update({
                                "status": "DELIVERED",
                                "delivered_at": datetime.utcnow().isoformat()
                            }) \
                            .eq("id", r["request_id"]) \
                            .execute()
                        st.rerun()

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

    query = supabase.table("material_requests") \
        .select("""
            id,
            status,
            requested_at,
            delivered_at,
            machines(machine_code),
            terminal_groups(terminal_pair)
        """)

    if status_filter:
        query = query.in_("status", status_filter)

    rows = query.order("requested_at", desc=True).execute().data

    if rows:
        st.dataframe([
            {
                "Machine": r["machines"]["machine_code"],
                "Terminal Pair": r["terminal_groups"]["terminal_pair"],
                "Status": r["status"],
                "Requested At": r["requested_at"],
                "Delivered At": r["delivered_at"]
            }
            for r in rows
        ], use_container_width=True)
    else:
        st.info("📭 No history found")
