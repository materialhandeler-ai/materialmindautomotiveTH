import streamlit as st
from supabase import create_client
import pandas as pd
import uuid
from datetime import datetime

# ---------------------------
# Supabase Config
# ---------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Cable Request", layout="wide")

st.title("🔧 Request Cable")

# ---------------------------
# GET ACTIVE MASTER BATCH
# ---------------------------
batch_res = supabase.table("master_upload_batches") \
    .select("*") \
    .eq("is_active", True) \
    .limit(1) \
    .execute()

if len(batch_res.data) == 0:
    st.error("No active master batch")
    st.stop()

active_batch_id = batch_res.data[0]["id"]

# ---------------------------
# LOAD MASTER DATA
# ---------------------------
master_res = supabase.table("cable_requirement_master") \
    .select("*") \
    .eq("batch_id", active_batch_id) \
    .execute()

master_df = pd.DataFrame(master_res.data)

if master_df.empty:
    st.warning("No master data found")
    st.stop()

# ---------------------------
# CREATE WIRE FULL NAME
# ---------------------------
master_df["wire_full_name"] = (
    master_df["wire_name"] + " " +
    master_df["wire_size"].astype(str) + " " +
    master_df["wire_color"]
)

# ---------------------------
# SELECT MACHINE
# ---------------------------
machines = sorted(master_df["machine_code"].unique())

machine = st.selectbox("Machine", machines)

# ---------------------------
# FILTER TERMINAL BY MACHINE
# ---------------------------
machine_df = master_df[master_df["machine_code"] == machine]

terminals = sorted(machine_df["terminal_pair"].unique())

terminal = st.selectbox("Terminal Pair", terminals)

# ---------------------------
# FILTER BY TERMINAL
# ---------------------------
terminal_df = machine_df[machine_df["terminal_pair"] == terminal]

# ---------------------------
# GROUP WIRE (รวมสายซ้ำ)
# ---------------------------
summary_df = (
    terminal_df
    .groupby("wire_full_name", as_index=False)["quantity_meter"]
    .sum()
)

# ---------------------------
# DASHBOARD
# ---------------------------
st.subheader("📊 Required Cable Summary")

st.dataframe(summary_df, use_container_width=True)

total_meter = summary_df["quantity_meter"].sum()

st.metric("Total Required Meter", f"{total_meter:,.2f} m")

# ---------------------------
# REQUEST BUTTON
# ---------------------------
if st.button("✅ Request Cable"):

    request_rows = []

    for _, row in terminal_df.iterrows():

        request_rows.append({
            "id": str(uuid.uuid4()),
            "batch_id": active_batch_id,
            "machine_code": machine,
            "terminal_pair": terminal,
            "wire_name": row["wire_name"],
            "wire_size": row["wire_size"],
            "wire_color": row["wire_color"],
            "quantity_meter": float(row["quantity_meter"]),
            "requested_at": datetime.utcnow().isoformat()
        })

    supabase.table("cable_requests").insert(request_rows).execute()

    st.success("Cable Requested Successfully")
