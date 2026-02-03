import pandas as pd
import streamlit as st
from supabase import create_client
from datetime import datetime, timezone

# ================= CONFIG =================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Cable Request System", layout="wide")

st.title("🔧 Cable Request System")

# ================= MENU =================
menu = st.sidebar.selectbox(
    "Menu",
    ["Request Cable", "Material Handler Dashboard", "History"]
)

# =====================================================
# REQUEST CABLE
# =====================================================
if menu == "Request Cable":

    st.header("🔧 Request Cable")

    df = pd.DataFrame(
        supabase.table("cable_requests")
        .select("*")
        .eq("status", "Waiting")
        .execute()
        .data
    )

    if df.empty:
        st.success("No Waiting Job")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        machine = st.selectbox("Machine", sorted(df["machine_code"].unique()))

    df_machine = df[df["machine_code"] == machine]

    with col2:
        terminal = st.selectbox("Terminal Pair", sorted(df_machine["terminal_pair"].unique()))

    show_df = df_machine[df_machine["terminal_pair"] == terminal]

    st.dataframe(show_df, use_container_width=True)

    if st.button("🚀 Request Cable"):

        supabase.table("cable_requests") \
            .update({"status": "Requested"}) \
            .eq("machine_code", machine) \
            .eq("terminal_pair", terminal) \
            .eq("status", "Waiting") \
            .execute()

        st.success("Request Created")
        st.rerun()


# =====================================================
# MATERIAL HANDLER DASHBOARD
# =====================================================
if menu == "Material Handler Dashboard":

    st.header("📦 Material Handler Dashboard")

    df = pd.DataFrame(
        supabase.table("cable_requests")
        .select("*")
        .eq("status", "Requested")
        .execute()
        .data
    )

    if df.empty:
        st.success("No pending job")
        st.stop()

    # ================= WAITING TIME =================
    now = datetime.now(timezone.utc)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["waiting_min"] = (now - df["created_at"]).dt.total_seconds() / 60

    # ================= PIVOT =================
    pivot_df = df.groupby([
        "machine_code",
        "terminal_pair",
        "wire_name",
        "wire_size",
        "wire_color"
    ], as_index=False).agg({
        "quantity_meter": "sum",
        "waiting_min": "min",
        "id": list
    })

    machines = pivot_df["machine_code"].unique()

    # ================= LOW STOCK ALERT =================
    low_stock = pd.DataFrame(
        supabase.table("wire_stock")
        .select("*")
        .execute()
        .data
    )

    if not low_stock.empty:
        low_stock = low_stock[low_stock["stock_meter"] < low_stock["safety_level"]]

        if not low_stock.empty:
            st.error("⚠️ LOW STOCK ALERT")
            st.dataframe(low_stock, use_container_width=True)

    # ================= LOOP MACHINE =================
    for machine in machines:

        machine_df = pivot_df[pivot_df["machine_code"] == machine]

        with st.expander(f"🏭 Machine : {machine}", expanded=True):

            selected_ids = []

            terminals = machine_df["terminal_pair"].unique()

            for terminal in terminals:

                terminal_df = machine_df[machine_df["terminal_pair"] == terminal]

                st.markdown(f"### 🔌 Terminal : {terminal}")

                for i, row in terminal_df.iterrows():

                    wait = row["waiting_min"]

                    # ===== Color Logic =====
                    if wait >= 5:
                        icon = "🔴"
                    elif wait >= 3:
                        icon = "🟠"
                    else:
                        icon = "🟢"

                    cable_name = f"{row['wire_name']} {row['wire_size']} {row['wire_color']}"
                    qty = row["quantity_meter"]

                    col1, col2 = st.columns([1, 6])

                    with col1:
                        checked = st.checkbox("", key=f"{machine}_{terminal}_{i}")

                    with col2:
                        st.write(f"{icon} **Cable :** {cable_name}")
                        st.write(f"**Qty :** {qty:.2f} m")
                        st.write(f"Waiting : {wait:.1f} นาที")

                    if checked:
                        selected_ids.append(row)

                st.divider()

            # ================= CONFIRM DELIVERY =================
            if st.button(f"✅ Confirm Delivery - {machine}", key=f"btn_{machine}"):

                if len(selected_ids) == 0:
                    st.warning("Select cable first")
                else:

                    for row in selected_ids:

                        # -------- Update Request --------
                        for rid in row["id"]:
                            supabase.table("cable_requests") \
                                .update({"status": "Finished"}) \
                                .eq("id", rid) \
                                .execute()

                        # -------- Insert Log --------
                        supabase.table("delivery_logs").insert({
                            "wire_name": row["wire_name"],
                            "wire_size": row["wire_size"],
                            "wire_color": row["wire_color"],
                            "quantity_meter": row["quantity_meter"],
                            "handler_name": "PC_HANDLER"
                        }).execute()

                        # -------- Cut Stock --------
                        supabase.table("wire_stock") \
                            .update({
                                "stock_meter": supabase.rpc(
                                    "rpc_cut_stock_calc",
                                    {
                                        "p_wire_name": row["wire_name"],
                                        "p_wire_size": row["wire_size"],
                                        "p_wire_color": row["wire_color"],
                                        "p_qty": row["quantity_meter"]
                                    }
                                )
                            }).execute()

                    st.success("Delivery Completed")
                    st.rerun()


# =====================================================
# HISTORY
# =====================================================
if menu == "History":

    st.header("📜 History")

    df = pd.DataFrame(
        supabase.table("cable_requests")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    st.dataframe(df, use_container_width=True)
