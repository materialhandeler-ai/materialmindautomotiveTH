import streamlit as st
from supabase import create_client

# ================= CONFIG =================
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="Material Request System",
    layout="wide"
)

# ================= MODE =================
mode = st.sidebar.radio(
    "Select Mode",
    ["🔧 Request Cable", "📦 Material Handler", "📜 History"]
)

# =====================================================
# 🔧 REQUEST CABLE
# =====================================================
if mode == "🔧 Request Cable":

    st.title("🔧 Request Cable")

    # ---- Machine list from master ----
    machines = (
        supabase.table("cable_requirement_master")
        .select("machine_code")
        .execute()
        .data
    )

    machine_list = sorted(list(set([m["machine_code"] for m in machines])))

    machine = st.selectbox("Machine", machine_list)

    # ---- Terminal by machine ----
    terminals = (
        supabase.table("cable_requirement_master")
        .select("terminal_pair")
        .eq("machine_code", machine)
        .execute()
        .data
    )

    terminal_list = sorted(list(set([t["terminal_pair"] for t in terminals])))

    terminal = st.selectbox("Terminal Pair", terminal_list)

    if st.button("📞 Call Cable", type="primary"):

        try:
            supabase.rpc(
                "rpc_create_material_request",
                {
                    "p_machine_code": machine,
                    "p_terminal_pair": terminal
                }
            ).execute()

            st.success("Request created")

        except Exception as e:
            st.error(e)

# =====================================================
# 📦 MATERIAL HANDLER
# =====================================================
elif mode == "📦 Material Handler":

    st.title("📦 Material Handler Dashboard")

    rows = (
        supabase.table("v_material_handler_dashboard")
        .select("*")
        .execute()
        .data
    )

    if not rows:
        st.info("No pending request")
        st.stop()

    # group by request
    from collections import defaultdict
    requests = defaultdict(list)

    for r in rows:
        requests[r["request_id"]].append(r)

    for req_id, items in requests.items():

        header = items[0]

        with st.expander(
            f"Machine: {header['machine_code']} | Terminal: {header['terminal_pair']} | Status: {header['status']}",
            expanded=False
        ):

            all_checked = True

            for it in items:

                wire_label = f"{it['wire_name']} {it['wire_size']} {it['wire_color']} ({it['quantity_meter']} m)"

                checked = st.checkbox(
                    wire_label,
                    value=it["is_delivered"],
                    key=f"{it['item_id']}"
                )

                if checked != it["is_delivered"]:
                    supabase.table("material_request_items") \
                        .update({"is_delivered": checked}) \
                        .eq("id", it["item_id"]) \
                        .execute()

                if not checked:
                    all_checked = False

            # ----- START -----
            if header["status"] == "REQUESTED":

                if st.button("🟡 Start Job", key=f"start_{req_id}"):

                    supabase.rpc(
                        "rpc_handler_start_request",
                        {"p_request_id": req_id}
                    ).execute()

                    st.rerun()

            # ----- FINISH -----
            elif header["status"] == "IN_PROGRESS":

                if all_checked:

                    if st.button("✅ Deliver", key=f"done_{req_id}"):

                        supabase.rpc(
                            "rpc_handler_finish_request",
                            {"p_request_id": req_id}
                        ).execute()

                        st.rerun()
                else:
                    st.warning("Select all cable before deliver")

# =====================================================
# 📜 HISTORY
# =====================================================
elif mode == "📜 History":

    st.title("📜 Request History")

    rows = (
        supabase.table("material_requests")
        .select("*")
        .order("requested_at", desc=True)
        .execute()
        .data
    )

    if not rows:
        st.info("No history")
    else:
        st.dataframe(rows, use_container_width=True)
