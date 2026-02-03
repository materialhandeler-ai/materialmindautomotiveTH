import pandas as pd
import streamlit as st
from supabase import create_client
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# ======================
# CONFIG
# ======================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Cable Request System", layout="wide")
st.title("🔧 Cable Request System")

# ======================
# SAFE WAITING FUNCTION
# ======================
def calc_waiting(df):

    if df.empty:
        return df

    df["requested_at"] = pd.to_datetime(
        df["requested_at"],
        errors="coerce"
    )

    df = df.dropna(subset=["requested_at"])

    now = datetime.now(timezone.utc)

    df["waiting_min"] = (
        now - df["requested_at"]
    ).dt.total_seconds() / 60

    return df


# ======================
# MENU
# ======================
menu = st.sidebar.selectbox(
    "Menu",
    [
        "Request Cable",
        "Material Handler Dashboard",
        "Andon Board",
        "History"
    ]
)

# =====================================================
# REQUEST CABLE
# =====================================================
if menu == "Request Cable":

    st.header("🔧 Request Cable")

    res = supabase.table("cable_requests") \
        .select("*") \
        .eq("status", "Waiting") \
        .execute()

    df = pd.DataFrame(res.data)

    if df.empty:
        st.success("No Waiting Job")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        machine = st.selectbox(
            "Machine",
            sorted(df["machine_code"].dropna().unique())
        )

    df_machine = df[df["machine_code"] == machine]

    with col2:
        terminal = st.selectbox(
            "Terminal Pair",
            sorted(df_machine["terminal_pair"].dropna().unique())
        )

    show_df = df_machine[df_machine["terminal_pair"] == terminal]

    st.dataframe(show_df, use_container_width=True)

    if st.button("🚀 Request Cable"):

        supabase.table("cable_requests") \
            .update({
                "status": "Requested",
                "requested_at": datetime.now(timezone.utc).isoformat()
            }) \
            .eq("machine_code", machine) \
            .eq("terminal_pair", terminal) \
            .eq("status", "Waiting") \
            .execute()

        st.success("Request Created")
        st.rerun()


# =====================================================
# MATERIAL HANDLER DASHBOARD
# =====================================================
elif menu == "Material Handler Dashboard":

    st.header("📦 Material Handler Dashboard")

    res = supabase.table("cable_requests") \
        .select("*") \
        .eq("status", "Requested") \
        .gt("quantity_meter", 0) \
        .execute()

    df = pd.DataFrame(res.data)
    df = calc_waiting(df)

    if df.empty:
        st.info("No pending job")
        st.stop()

    pivot_df = df.groupby([
        "machine_code",
        "terminal_pair",
        "wire_name",
        "wire_size",
        "wire_color"
    ], as_index=False).agg({
        "quantity_meter": "sum",
        "id": list,
        "waiting_min": "max"
    })

    machines = pivot_df["machine_code"].unique()

    for machine in machines:

        machine_df = pivot_df[pivot_df["machine_code"] == machine]

        with st.expander(f"🏭 Machine : {machine}", expanded=True):

            selected_ids = []
            terminals = machine_df["terminal_pair"].unique()

            for terminal in terminals:

                terminal_df = machine_df[
                    machine_df["terminal_pair"] == terminal
                ]

                st.markdown(f"### 🔌 Terminal : {terminal}")

                for i, row in terminal_df.iterrows():

                    wait = row["waiting_min"]

                    if wait > 5:
                        icon = "🔴"
                    elif wait > 3:
                        icon = "🟠"
                    else:
                        icon = "🟢"

                    cable_name = f"{row['wire_name']} {row['wire_size']} {row['wire_color']}"

                    col1, col2 = st.columns([1, 6])

                    with col1:
                        checked = st.checkbox(
                            "",
                            key=f"chk_{machine}_{i}"
                        )

                    with col2:
                        st.write(f"{icon} **Cable :** {cable_name}")
                        st.write(f"Qty : {row['quantity_meter']:.2f} m")
                        st.write(f"Waiting : {wait:.1f} นาที")

                    if checked:
                        selected_ids.extend(row["id"])

                st.divider()

            # ===== Confirm Delivery =====
            if st.button(
                f"✅ Confirm Delivery - {machine}",
                key=f"btn_{machine}"
            ):

                if not selected_ids:
                    st.warning("กรุณาเลือก Cable ก่อน")
                else:

                    supabase.table("cable_requests") \
                        .update({
                            "status": "Finished",
                            "delivered_at": datetime.now(timezone.utc).isoformat()
                        }) \
                        .in_("id", selected_ids) \
                        .execute()

                    st.success(f"Delivery Completed for {machine}")
                    st.rerun()


# =====================================================
# ANDON BOARD
# =====================================================
elif menu == "Andon Board":

    st_autorefresh(interval=10000, key="andon")

    st.title("🏭 Material Andon Board")

    res = supabase.table("cable_requests") \
        .select("*") \
        .eq("status", "Requested") \
        .gt("quantity_meter", 0) \
        .execute()

    df = pd.DataFrame(res.data)
    df = calc_waiting(df)

    if df.empty:
        st.success("🟢 No Material Request")
        st.stop()

    col1, col2, col3 = st.columns(3)

    col1.metric("🔧 Total Request", len(df))
    col2.metric("🟠 > 3 นาที", len(df[df["waiting_min"] > 3]))
    col3.metric("🔴 > 5 นาที", len(df[df["waiting_min"] > 5]))

    st.divider()

    st.subheader("Machine Status")

    machine_df = df.groupby("machine_code").agg({
        "waiting_min": "max"
    }).reset_index()

    m_cols = st.columns(4)

    def get_color(wait):
        if wait > 5:
            return "🔴"
        elif wait > 3:
            return "🟠"
        return "🟢"

    for i, row in machine_df.iterrows():

        with m_cols[i % 4]:

            color = get_color(row["waiting_min"])

            st.markdown(f"""
            ### {row['machine_code']}
            ## {color} {row['waiting_min']:.1f} นาที
            """)

    st.divider()

    pivot_df = df.groupby([
        "machine_code",
        "terminal_pair",
        "wire_name",
        "wire_size",
        "wire_color"
    ], as_index=False).agg({
        "quantity_meter": "sum",
        "waiting_min": "max"
    })

    st.dataframe(pivot_df, use_container_width=True)


# =====================================================
# HISTORY
# =====================================================
elif menu == "History":

    st.header("📜 History")

    res = supabase.table("cable_requests") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()

    df = pd.DataFrame(res.data)

    st.dataframe(df, use_container_width=True)
