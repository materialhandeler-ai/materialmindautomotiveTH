import streamlit as st
import pandas as pd
from supabase import create_client

# ================= CONFIG =================
supabase = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["anon_key"]
)

st.set_page_config(page_title="Cable Request PRO", layout="wide")

mode = st.sidebar.radio(
    "Select Mode",
    ["📥 Upload Master", "🔧 Request Cable", "📦 Material Handler", "📜 History"]
)

# =====================================================
# 📥 UPLOAD MASTER
# =====================================================
if mode == "📥 Upload Master":

    st.title("📥 Upload Master Excel")

    file = st.file_uploader("Upload Excel", type=["xlsx"])

    if file:

        df = pd.read_excel(file)

        required_cols = [
            "machine_code",
            "terminal_pair",
            "wire_name",
            "wire_size",
            "wire_color",
            "quantity_meter"
        ]

        if not all(c in df.columns for c in required_cols):
            st.error("Excel format incorrect")
            st.stop()

        if st.button("Upload"):

            # deactivate old batch
            supabase.table("master_upload_batches") \
                .update({"is_active": False}) \
                .eq("is_active", True) \
                .execute()

            # create new batch
            batch = supabase.table("master_upload_batches") \
                .insert({"is_active": True}) \
                .execute().data[0]

            batch_id = batch["id"]

            df["batch_id"] = batch_id

            supabase.table("cable_requirement_master") \
                .insert(df.to_dict("records")) \
                .execute()

            st.success("Upload complete")

# =====================================================
# 🔧 REQUEST CABLE
# =====================================================
elif mode == "🔧 Request Cable":

    st.title("🔧 Request Cable")

    machines = supabase.table("v_request_machine").select("*").execute().data

    if not machines:
        st.warning("No active master")
        st.stop()

    machine = st.selectbox(
        "Machine",
        [m["machine_code"] for m in machines]
    )

    terminals = supabase.table("v_request_terminal") \
        .select("*") \
        .eq("machine_code", machine) \
        .execute().data

    terminal = st.selectbox(
        "Terminal Pair",
        [t["terminal_pair"] for t in terminals]
    )

    if st.button("Call Cable", type="primary"):

        res = supabase.rpc(
            "rpc_create_cable_request",
            {
                "p_machine_code": machine,
                "p_terminal_pair": terminal
            }
        ).execute()

        st.success(f"Request Created: {res.data}")

# =====================================================
# 📦 MATERIAL HANDLER
# =====================================================
elif mode == "📦 Material Handler":

    st.title("📦 Material Handler Dashboard")

    rows = supabase.table("v_handler_dashboard") \
        .select("*") \
        .order("requested_at") \
        .execute().data

    if not rows:
        st.info("No pending job")
        st.stop()

    import collections
    grouped = collections.defaultdict(list)

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

            # start button
            if head["status"] == "REQUESTED":
                if st.button("Start Job", key=f"start_{header_id}"):

                    supabase.rpc(
                        "rpc_handler_start_request",
                        {"p_header_id": header_id}
                    ).execute()

                    st.rerun()

            # finish button
            if head["status"] == "IN_PROGRESS":

                if all_done:
                    if st.button("Finish Delivery", key=f"finish_{header_id}"):

                        supabase.rpc(
                            "rpc_handler_finish_request",
                            {"p_header_id": header_id}
                        ).execute()

                        st.rerun()
                else:
                    st.warning("Complete all items first")

# =====================================================
# 📜 HISTORY
# =====================================================
elif mode == "📜 History":

    st.title("📜 Delivery History")

    rows = supabase.table("cable_request_headers") \
        .select("*") \
        .order("requested_at", desc=True) \
        .execute().data

    if rows:
        st.dataframe(rows, use_container_width=True)
