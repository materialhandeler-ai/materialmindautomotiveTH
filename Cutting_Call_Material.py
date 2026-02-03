import streamlit as st
from supabase import create_client
import pandas as pd

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

mode = st.sidebar.radio("Mode",[
    "Request",
    "Handler",
    "Dashboard",
    "History"
])

# ============================
# REQUEST
# ============================
if mode=="Request":

    master = supabase.table("cable_requirement_master").select("*").execute()
    df = pd.DataFrame(master.data)

    machines = sorted(df.machine_code.unique())
    machine = st.selectbox("Machine", machines)

    terminals = sorted(df[df.machine_code==machine].terminal_pair.unique())
    terminal = st.selectbox("Terminal", terminals)

    if st.button("Call Cable"):

        supabase.rpc(
            "rpc_create_cable_request",
            {
                "p_machine":machine,
                "p_terminal":terminal
            }
        ).execute()

        st.success("Request Sent")

# ============================
# HANDLER
# ============================
if mode=="Handler":

    view = supabase.table("v_pending_dashboard").select("*").execute()
    df = pd.DataFrame(view.data)

    headers = df.header_id.unique()

    for h in headers:

        sub = df[df.header_id==h]

        st.subheader(
            f"{sub.machine_code.iloc[0]} | {sub.terminal_pair.iloc[0]}"
        )

        items = supabase.table("cable_request_items").select("*").eq("header_id",h).execute()
        items_df = pd.DataFrame(items.data)

        for _,r in items_df.iterrows():

            if st.checkbox(
                f"{r.wire_name} {r.wire_size} {r.wire_color} {r.quantity_meter}",
                key=r.id
            ):
                supabase.rpc(
                    "rpc_deliver_cable_item",
                    {"p_item":r.id}
                ).execute()

        if st.button("Close Job",key=h):

            supabase.rpc(
                "rpc_close_request",
                {"p_header":h}
            ).execute()

            st.success("Closed")

# ============================
# DASHBOARD
# ============================
if mode=="Dashboard":

    dash = supabase.table("v_pending_dashboard").select("*").execute()
    st.dataframe(pd.DataFrame(dash.data))

# ============================
# HISTORY
# ============================
if mode=="History":

    log = supabase.table("cable_delivery_log").select("*").execute()
    st.dataframe(pd.DataFrame(log.data))
