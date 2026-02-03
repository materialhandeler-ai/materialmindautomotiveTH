import pandas as pd
import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Cable Request System", layout="wide")

st.title("🔧 Cable Request System")

# ======================
# MENU
# ======================

menu = st.sidebar.selectbox(
    "Menu",
    ["Request Cable", "Material Handler Dashboard", "History"]
)

# =====================================================
# REQUEST CABLE PAGE
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

    st.dataframe(show_df)

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
# =====================================================
# MATERIAL HANDLER DASHBOARD (PIVOT VERSION)
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
        st.info("No pending job")
        st.stop()

    # ❗ ตัด qty = 0
    df = df[df["quantity_meter"] > 0]

    # =========================
    # ⭐ PIVOT / GROUP DATA
    # =========================
    pivot_df = df.groupby([
        "machine_code",
        "terminal_pair",
        "wire_name",
        "wire_size",
        "wire_color"
    ], as_index=False).agg({
        "quantity_meter": "sum",
        "id": list   # เก็บ id ไว้ใช้ตอน update
    })

    machines = pivot_df["machine_code"].unique()

    # =========================
    # LOOP MACHINE
    # =========================
    for machine in machines:

        machine_df = pivot_df[pivot_df["machine_code"] == machine]

        with st.expander(f"🏭 Machine : {machine}", expanded=True):

            selected_ids = []

            terminals = machine_df["terminal_pair"].unique()

            for terminal in terminals:

                terminal_df = machine_df[machine_df["terminal_pair"] == terminal]

                st.markdown(f"### 🔌 Terminal : {terminal}")

                for i, row in terminal_df.iterrows():

                    cable_name = f"{row['wire_name']} {row['wire_size']} {row['wire_color']}"
                    total_qty = row["quantity_meter"]

                    col1, col2 = st.columns([1, 6])

                    with col1:
                        checked = st.checkbox("", key=f"chk_{machine}_{i}")

                    with col2:
                        st.write(f"**Cable :** {cable_name}")
                        st.write(f"**Qty :** {total_qty:.2f} m")

                    # ⭐ เก็บ ID ทั้งหมดใน group
                    if checked:
                        selected_ids.extend(row["id"])

                st.divider()

            # =====================
            # CONFIRM DELIVERY
            # =====================
            if st.button(f"✅ Confirm Delivery - {machine}", key=f"btn_{machine}"):

                if len(selected_ids) == 0:
                    st.warning("Please select cable first")
                else:

                    for rid in selected_ids:
                        supabase.table("cable_requests") \
                            .update({"status": "Finished"}) \
                            .eq("id", rid) \
                            .execute()

                    st.success(f"Delivery Completed for {machine}")
                    st.rerun()

# =====================================================
# HISTORY PAGE
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




