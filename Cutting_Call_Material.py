import pandas as pd
import streamlit as st
import requests
from supabase import create_client
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# ======================
# CONFIG
# ======================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Cable Request System", layout="wide")
st.title("🔧 Cable Request System")

# ======================
# TELEGRAM FUNCTION
# ======================
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

# ======================
# SAFE WAITING FUNCTION
# ======================
def calc_waiting(df):

    if df.empty:
        return df

    df["requested_at"] = pd.to_datetime(df["requested_at"], errors="coerce")
    df = df.dropna(subset=["requested_at"])

    now = datetime.now(timezone.utc)
    df["waiting_min"] = (now - df["requested_at"]).dt.total_seconds() / 60

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
        "Andon TV Mode",
        "History"
        "— WH SYSTEM —",
        "WH Request",
        "WH Handler",
        "WH Andon Board",
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

        # 🔔 TELEGRAM
        send_telegram(
            f"🔧 <b>NEW CABLE REQUEST</b>\n"
            f"🏭 Machine : <b>{machine}</b>\n"
            f"🔌 Terminal : <b>{terminal}</b>\n"
            f"⏱ Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

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

    for machine in pivot_df["machine_code"].unique():

        machine_df = pivot_df[pivot_df["machine_code"] == machine]

        with st.expander(f"🏭 Machine : {machine}", expanded=True):

            selected_ids = []

            for _, row in machine_df.iterrows():

                wait = row["waiting_min"]
                icon = "🔴" if wait > 7 else "🟠" if wait > 4 else "🟢"
                cable = f"{row['wire_name']} {row['wire_size']} {row['wire_color']}"

                col1, col2 = st.columns([1, 6])

                with col1:
                    checked = st.checkbox("", key=f"chk_{machine}_{row['id'][0]}")

                with col2:
                    st.write(f"{icon} **Cable:** {cable}")
                    st.write(f"Qty: {row['quantity_meter']:.2f} m")
                    st.write(f"Waiting: {wait:.1f} min")

                if checked:
                    selected_ids.extend(row["id"])

            if st.button(f"✅ Confirm Delivery - {machine}"):

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

                    # 🔔 TELEGRAM
                    send_telegram(
                        f"✅ <b>DELIVERY COMPLETED</b>\n"
                        f"🏭 Machine : <b>{machine}</b>\n"
                        f"📦 Items : {len(selected_ids)}\n"
                        f"⏱ Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )

                    st.success("Delivery Completed")
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
    col2.metric("🟠 > 4 min", len(df[df["waiting_min"] > 3]))
    col3.metric("🔴 > 7 min", len(df[df["waiting_min"] > 5]))

    st.divider()

    st.subheader("Machine Status")

    machine_df = df.groupby("machine_code").agg({
        "waiting_min": "max"
    }).reset_index()

    m_cols = st.columns(4)

    def get_color(wait):
        if wait > 7:
            return "🔴"
        elif wait > 4:
            return "🟠"
        return "🟢"

    for i, row in machine_df.iterrows():

        with m_cols[i % 4]:

            color = get_color(row["waiting_min"])

            st.markdown(f"""
            ### {row['machine_code']}
            ## {color} {row['waiting_min']:.1f} min
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
# ANDON TV MODE (FULLSCREEN FACTORY SCREEN)
# =====================================================
elif menu == "Andon TV Mode":

    # ===== Hide Sidebar + Menu =====
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    header {visibility:hidden;}
    </style>
    """, unsafe_allow_html=True)

    # ===== Auto Refresh 5 sec =====
    st_autorefresh(interval=5000, key="tv_refresh")

    st.markdown("""
    <h1 style='text-align:center;font-size:60px'>
    🏭 MATERIAL ANDON BOARD
    </h1>
    """, unsafe_allow_html=True)

    # ===== Load Data =====
    res = supabase.table("cable_requests") \
        .select("*") \
        .eq("status", "Requested") \
        .gt("quantity_meter", 0) \
        .execute()

    df = pd.DataFrame(res.data)
    df = calc_waiting(df)

    if df.empty:
        st.markdown("""
        <h2 style='text-align:center;color:green;font-size:50px'>
        ✅ NO MATERIAL REQUEST
        </h2>
        """, unsafe_allow_html=True)
        st.stop()

    # ===== KPI =====
    total = len(df)
    warn = len(df[df["waiting_min"] > 4])
    danger = len(df[df["waiting_min"] > 7])

    k1, k2, k3 = st.columns(3)

    k1.markdown(f"""
    <h1 style='text-align:center;font-size:50px'>
    🔧 {total}
    </h1>
    <h3 style='text-align:center'>Total Request</h3>
    """, unsafe_allow_html=True)

    k2.markdown(f"""
    <h1 style='text-align:center;font-size:50px;color:orange'>
    🟠 {warn}
    </h1>
    <h3 style='text-align:center'>Waiting > 4 Min</h3>
    """, unsafe_allow_html=True)

    k3.markdown(f"""
    <h1 style='text-align:center;font-size:50px;color:red'>
    🔴 {danger}
    </h1>
    <h3 style='text-align:center'>Waiting 7 Min</h3>
    """, unsafe_allow_html=True)

    st.divider()

    # ===== MACHINE STATUS BIG CARD =====
    machine_df = df.groupby("machine_code").agg({
        "waiting_min": "max"
    }).reset_index()

    cols = st.columns(4)

    def get_color(wait):
        if wait > 7:
            return "red"
        elif wait > 4:
            return "orange"
        return "green"

    for i, row in machine_df.iterrows():

        color = get_color(row["waiting_min"])

        with cols[i % 4]:

            st.markdown(f"""
            <div style="
                background:{color};
                padding:40px;
                border-radius:20px;
                text-align:center;
                color:white;
                margin-bottom:20px;
            ">
                <h2 style="font-size:35px">{row['machine_code']}</h2>
                <h1 style="font-size:60px">{row['waiting_min']:.1f} min</h1>
            </div>
            """, unsafe_allow_html=True)

    # ===== DETAIL TABLE =====
    st.markdown("<h2>📦 REQUEST DETAIL</h2>", unsafe_allow_html=True)

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

    st.dataframe(
        pivot_df,
        use_container_width=True,
        height=400
    )

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
if menu == "WH Request":

    st.header("🏭 WH Request Material")

    # โหลด master
    master = supabase.table("wh_master_part") \
        .select("code,name,location,unit,full_package") \
        .eq("is_active", True) \
        .execute()

    df_master = pd.DataFrame(master.data)

    if df_master.empty:
        st.error("❌ No Master Data")
        st.stop()

    col1, col2, col3 = st.columns(3)

    with col1:
        part_code = st.selectbox(
            "Part Code",
            sorted(df_master["code"].unique())
        )

    part = df_master[df_master["code"] == part_code].iloc[0]

    with col2:
        qty = st.number_input(
            f"Quantity ({part['unit']})",
            min_value=0.0,
            step=1.0
        )

    with col3:
        location = st.text_input(
            "Request Location",
            value=part["location"] if part["location"] != "Not found location" else ""
        )

    st.info(
        f"📦 **{part['name']}**  \n"
        f"📍 Location : {location or '-'}  \n"
        f"📐 Full Package : {part['full_package']} {part['unit']}"
    )

    if st.button("🚀 Send WH Request"):

        supabase.table("wh_request").insert({
            "part_code": part_code,
            "part_name": part["name"],
            "request_qty": qty,
            "unit": part["unit"],
            "request_location": location,
            "status": "WAITING",
            "requested_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        send_telegram(
            f"📦 <b>WH REQUEST</b>\n"
            f"🔢 {part_code}\n"
            f"📦 {part['name']}\n"
            f"🔢 Qty : {qty} {part['unit']}\n"
            f"📍 {location}"
        )

        st.success("✅ Request Sent")
        st.rerun()
elif menu == "WH Handler":

    st.header("📦 WH Handler")

    res = supabase.table("vw_wh_request") \
        .select("*") \
        .eq("status", "WAITING") \
        .execute()

    df = pd.DataFrame(res.data)
    df = calc_waiting(df)

    if df.empty:
        st.success("🟢 No Waiting Request")
        st.stop()

    selected = []

    for _, row in df.iterrows():

        icon = "🔴" if row["waiting_min"] > 7 else "🟠" if row["waiting_min"] > 4 else "🟢"

        col1, col2 = st.columns([1, 6])

        with col1:
            chk = st.checkbox("", key=row["id"])

        with col2:
            st.markdown(
                f"{icon} **{row['part_name']}**  \n"
                f"Qty : **{row['request_qty']} {row['unit']}**  \n"
                f"Location : {row['location']}  \n"
                f"Waiting : {row['waiting_min']:.1f} min"
            )

        if chk:
            selected.append(row["id"])

    if st.button("✅ Confirm Pick & Delivery"):

        if not selected:
            st.warning("กรุณาเลือกอย่างน้อย 1 รายการ")
        else:
            supabase.table("wh_request") \
                .update({
                    "status": "DELIVERED",
                    "delivered_at": datetime.now(timezone.utc).isoformat()
                }) \
                .in_("id", selected) \
                .execute()

            send_telegram(
                f"✅ <b>WH DELIVERY</b>\n"
                f"📦 Items : {len(selected)}"
            )

            st.success("Delivery Completed")
            st.rerun()
elif menu == "WH Andon Board":

    st_autorefresh(interval=10000, key="wh_andon")

    st.title("🏭 WH ANDON BOARD")

    res = supabase.table("vw_wh_request") \
        .select("*") \
        .eq("status", "WAITING") \
        .execute()

    df = pd.DataFrame(res.data)
    df = calc_waiting(df)

    if df.empty:
        st.success("🟢 NO WH REQUEST")
        st.stop()

    c1, c2, c3 = st.columns(3)

    c1.metric("📦 Total", len(df))
    c2.metric("🟠 > 4 min", len(df[df["waiting_min"] > 4]))
    c3.metric("🔴 > 7 min", len(df[df["waiting_min"] > 7]))

    st.divider()

    show = df[[
        "part_code",
        "part_name",
        "request_qty",
        "unit",
        "location",
        "waiting_min"
    ]]

    st.dataframe(show, use_container_width=True)





