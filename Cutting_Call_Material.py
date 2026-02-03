import streamlit as st
import pandas as pd
from supabase import create_client

# ================= SUPABASE CONNECT =================
try:
    supabase = create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"]
    )
except Exception as e:
    st.error("Supabase connection error")
    st.stop()

st.set_page_config(page_title="Cable Request PRO", layout="wide")

mode = st.sidebar.radio(
    "Select Mode",
    ["🔧 Request Cable", "📦 Material Handler", "📜 History"]
)

# =====================================================
# 🔧 REQUEST CABLE
# =====================================================
if mode == "🔧 Request Cable":

    st.title("🔧 Request Cable")

    try:
        res = supabase.table("v_request_machine").select("*").execute()
        machines = res.data if res.data else []
    except Exception as e:
        st.error("Cannot load machine list")
        st.stop()

    if len(machines) == 0:
        st.warning("No active master data")
        st.stop()

    machine_list = [m["machine_code"] for m in machines]

    machine = st.selectbox("Machine", machine_list)

    try:
        res = (
            supabase.table("v_request_terminal")
            .select("*")
            .eq("machine_code", machine)
            .execute()
        )
        terminals = res.data if res.data else []
    except:
        st.error("Cannot load terminal list")
        st.stop()

    if len(terminals) == 0:
        st.warning("No terminal found")
        st.stop()

    terminal_list = [t["terminal_pair"] for t in terminals]

    terminal = st.selectbox("Terminal Pair", terminal_list)

    if st.button("📞 Call Cable", type="primary"):

        try:
            res = supabase.rpc(
                "rpc_create_cable_request",
                {
                    "p_machine_code": machine,
                    "p_terminal_pair": terminal
                }
            ).execute()

            st.success(f"Request Created : {res.data}")

        except Exception as e:
            st.error("Request failed")

# =====================================================
# 📦 MATERIAL HANDLER
# =====================================================
elif mode == "📦 Material Handler":

    st.title("📦 Material Handler Dashboard")

    try:
        res = (
            supabase.table("v_handler_dashboard")
            .select("*")
            .order("requested_at")
            .execute()
        )
        rows = res.data if res.data else []
    except:
        st.error("Cannot load dashboard")
        st.stop()

    if len(rows) == 0:
        st.info("No pending job")
        st.stop()

    from collections import defaultdict
    grouped = defaultdict(list)

    for r in rows:
        grouped[r["header_id"]].append(r)

    for header_id, items in grouped.items():

        head = items[0]

        with st.expander(
            f"{head['machine_code']} | {head['terminal_pair']} | {head['status']}"
        ):

            all_done = True

            for it in items:

                checked = st.checkbox(
                    f"{it['wire_name']} {it['wire_size']} {it['wire_color']} ({it['quantity_meter']}m)",
                    value=it["is_delivered"],
                    key=it["item_id"]
                )

                if checked != it["is_delivered"]:
                    supabase.table("cable_request_items") \
                        .update({"is_delivered": checked}) \
                        .eq("id", it["item_id"]) \
                        .execute()

                if not checked:
                    all_done = False

            # Start Job
            if head["status"] == "REQUESTED":

                if st.button("🟡 Start Job", key=f"start_{header_id}"):

                    supabase.rpc(
                        "rpc_handler_start_request",
                        {"p_header_id": header_id}
                    ).execute()

                    st.rerun()

            # Finish Job
            if head["status"] == "IN_PROGRESS":

                if all_done:
                    if st.button("✅ Finish Delivery", key=f"finish_{header_id}"):

                        supabase.rpc(
                            "rpc_handler_finish_request",
                            {"p_header_id": header_id}
                        ).execute()

                        st.rerun()
                else:
                    st.warning("Deliver all items first")

# =====================================================
# 📜 HISTORY
# =====================================================
elif mode == "📜 History":

    st.title("📜 Request History")

    try:
        res = (
            supabase.table("cable_request_headers")
            .select("*")
            .order("requested_at", desc=True)
            .execute()
        )
        rows = res.data if res.data else []
    except:
        st.error("Cannot load history")
        st.stop()

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No history")
