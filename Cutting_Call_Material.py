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

    st.header("📦 Material Handler Dashboard")

    data = supabase.table("v_material_handler_dashboard").select("*").execute().data

    if not data:
        st.info("No pending job")
        st.stop()

    df = pd.DataFrame(data)

    for req_id in df["request_id"].unique():

        req_df = df[df["request_id"] == req_id]

        with st.expander(
            f"Machine : {req_df.iloc[0]['machine_code']} | "
            f"Terminal : {req_df.iloc[0]['terminal_pair']}"
        ):

            for _, row in req_df.iterrows():

                col1, col2 = st.columns([3,1])

                with col1:
                    st.checkbox(
                        f"{row['wire_code']} | {row['quantity_meter']} m",
                        key=row["item_id"],
                        value=row["is_delivered"]
                    )

            if st.button("✅ Finish Delivery", key=req_id):

                # update item delivery
                for _, row in req_df.iterrows():

                    if st.session_state.get(row["item_id"]):

                        supabase.table("material_request_items") \
                            .update({"is_delivered": True}) \
                            .eq("id", row["item_id"]) \
                            .execute()

                supabase.rpc(
                    "rpc_handler_finish_request",
                    {"p_request_id": req_id}
                ).execute()

                st.success("Delivery Completed")
                st.rerun()

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

