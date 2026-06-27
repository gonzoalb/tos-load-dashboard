import streamlit as st
import pandas as pd
import yaml
from datetime import datetime, timedelta
import hashlib

# ============================================================
# TOS LOAD VISIBILITY DASHBOARD
# TransfersOutsideServices - External Repair Site Visibility
# Admin: gonzoalb@amazon.com
# ============================================================

st.set_page_config(
    page_title="TOS Load Tracker",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURATION ---
SITE_GROUPS = {
    "RARC": ["RARC"],
    "RIMG": ["RIMG"],
    "RITO": ["RITO"],
    "RIVA": ["RIVA"],
    "RTPX": ["RTPX"],
    "RRPR": ["RRPR"],
    "RPNV_RPNC": ["RPNV", "RPNC"],
    "RNRM_LNRM": ["RNRM", "LNRM"],
}

# --- USER DATABASE (stored in secrets or yaml) ---
def load_users():
    """Load user credentials and site assignments."""
    try:
        with open("users.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Default users if no file exists
        return {
            "admin": {
                "password": "admin2026",
                "role": "admin",
                "sites": ["ALL"],
                "name": "Albert Gonzalez"
            },
            "rtpx_user": {
                "password": "rtpx2026",
                "role": "site",
                "sites": ["RTPX"],
                "name": "RTPX Operations"
            },
            "rpnv_rpnc_user": {
                "password": "rpnv2026",
                "role": "site",
                "sites": ["RPNV", "RPNC"],
                "name": "RPNV/RPNC Operations"
            },
            "rnrm_lnrm_user": {
                "password": "rnrm2026",
                "role": "site",
                "sites": ["RNRM", "LNRM"],
                "name": "RNRM/LNRM Operations"
            },
            "rarc_user": {
                "password": "rarc2026",
                "role": "site",
                "sites": ["RARC"],
                "name": "RARC Operations"
            },
            "rimg_user": {
                "password": "rimg2026",
                "role": "site",
                "sites": ["RIMG"],
                "name": "RIMG Operations"
            },
            "rito_user": {
                "password": "rito2026",
                "role": "site",
                "sites": ["RITO"],
                "name": "RITO Operations"
            },
            "riva_user": {
                "password": "riva2026",
                "role": "site",
                "sites": ["RIVA"],
                "name": "RIVA Operations"
            },
            "rrpr_user": {
                "password": "rrpr2026",
                "role": "site",
                "sites": ["RRPR"],
                "name": "RRPR Operations"
            },
        }


def authenticate(username, password):
    """Verify credentials and return user info."""
    users = load_users()
    if username in users and users[username]["password"] == password:
        return users[username]


def derive_status(row):
    """Derive load status from available data."""
    # Handle both boolean and string representations of Canceled Load
    canceled = row["Canceled Load"]
    if canceled is True or str(canceled).strip().lower() == 'true':
        return "🔴 Cancelled"
    elif pd.notna(row.get("Destination Arrival")) and str(row.get("Destination Arrival")).strip() != '':
        return "✅ Completed"
    elif pd.notna(row.get("Origin Departure")) and str(row.get("Origin Departure")).strip() != '':
        return "🟡 In Transit"
    elif pd.notna(row.get("Origin Arrival")) and str(row.get("Origin Arrival")).strip() != '':
        return "🔵 At Origin"
    else:
        return "⚪ Planned"

    """Load and transform FMC CSV data."""
    try:
        df = pd.read_csv("data/fmc_export.csv", low_memory=False)
    except FileNotFoundError:
        st.error("❌ No data file found. Please upload FMC CSV export to data/fmc_export.csv")
        return pd.DataFrame()

    # Select and rename key columns
    cols_map = {
        "Load #": "VRID",
        "Lane": "Lane",
        "Canceled Load": "Canceled Load",
        "Carrier": "Carrier Code",
        "Trailer Id": "Trailer ID",
        "First Dock Arrival": "Origin Arrival",
        "First Dock Departure": "Origin Departure",
        "Last Dock Arrival": "Destination Arrival",
        "Scheduled Truck Arrival - 1 date": "Scheduled Date (Origin)",
        "Scheduled Truck Arrival - 1 time": "Scheduled Time (Origin)",
        "Scheduled Truck Arrival - 2 date": "Scheduled Date (Dest)",
        "Scheduled Truck Arrival - 2 time": "Scheduled Time (Dest)",
        "Corresponding CPT": "CPT",
        "Equipment Type": "Equipment",
        "Total Distance": "Distance",
    }

    available_cols = {k: v for k, v in cols_map.items() if k in df.columns}
    df_clean = df[list(available_cols.keys())].rename(columns=available_cols)

    # Derive status
    df_clean["Status"] = df_clean.apply(derive_status, axis=1)

    # Parse origin and destination from Lane
    df_clean["Origin"] = df_clean["Lane"].apply(
        lambda x: x.split("->")[0] if pd.notna(x) and "->" in str(x) else ""
    )
    df_clean["Destination"] = df_clean["Lane"].apply(
        lambda x: x.split("->")[-1] if pd.notna(x) and "->" in str(x) else ""
    )

    # Build scheduled arrival strings
    if "Scheduled Date (Origin)" in df_clean.columns and "Scheduled Time (Origin)" in df_clean.columns:
        df_clean["Scheduled Origin Arrival"] = (
            df_clean["Scheduled Date (Origin)"].fillna("") + " " + 
            df_clean["Scheduled Time (Origin)"].fillna("")
        ).str.strip()

    if "Scheduled Date (Dest)" in df_clean.columns and "Scheduled Time (Dest)" in df_clean.columns:
        df_clean["Scheduled Dest Arrival"] = (
            df_clean["Scheduled Date (Dest)"].fillna("") + " " + 
            df_clean["Scheduled Time (Dest)"].fillna("")
        ).str.strip()

    return df_clean


def filter_by_sites(df, sites):
    """Filter dataframe to only show loads for specified sites."""
    if "ALL" in sites:
        return df

    mask = pd.Series([False] * len(df))
    for site in sites:
        mask = mask | df["Lane"].str.contains(site, na=False)
    return df[mask]


# --- LOGIN PAGE ---
def show_login():
    """Display login form."""
    st.markdown("""
    <div style='text-align: center; padding: 50px 0;'>
        <h1>🚛 TOS Load Visibility</h1>
        <h3 style='color: gray;'>TransfersOutsideServices - External Repair Sites</h3>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("Sign In")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                user = authenticate(username, password)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        st.markdown("""
        <div style='text-align: center; padding-top: 20px; color: gray; font-size: 12px;'>
            Contact program administrator for access credentials.
        </div>
        """, unsafe_allow_html=True)


# --- MAIN DASHBOARD ---
def show_dashboard():
    """Display the main dashboard view."""
    user = st.session_state["user"]
    sites = user["sites"]

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.markdown(f"**Role:** {'Administrator' if user['role'] == 'admin' else 'Site Viewer'}")
        if "ALL" not in sites:
            st.markdown(f"**Sites:** {', '.join(sites)}")
        else:
            st.markdown("**Sites:** All Sites")

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.divider()
        st.markdown("**Filters**")

    # Load data
    df = load_data()
    if df.empty:
        return

    # Filter by user's assigned sites
    df_filtered = filter_by_sites(df, sites)

    # Sidebar filters
    with st.sidebar:
        # Status filter
        statuses = df_filtered["Status"].unique().tolist()
        selected_statuses = st.multiselect("Status", statuses, default=statuses)

        # Direction filter (inbound/outbound)
        direction = st.radio("Direction", ["All", "Inbound", "Outbound"])

        # Date filter - only if we have scheduled dates
        if "Scheduled Date (Origin)" in df_filtered.columns:
            date_options = sorted(df_filtered["Scheduled Date (Origin)"].dropna().unique())
            if date_options:
                date_filter = st.select_slider(
                    "Date Range",
                    options=["All"] + list(date_options),
                    value="All"
                )

    # Apply filters
    df_display = df_filtered[df_filtered["Status"].isin(selected_statuses)]

    if direction == "Inbound" and "ALL" not in sites:
        mask = pd.Series([False] * len(df_display))
        for site in sites:
            mask = mask | (df_display["Destination"] == site)
        df_display = df_display[mask]
    elif direction == "Outbound" and "ALL" not in sites:
        mask = pd.Series([False] * len(df_display))
        for site in sites:
            mask = mask | (df_display["Origin"] == site)
        df_display = df_display[mask]

    # --- HEADER ---
    st.markdown("# 🚛 TOS Load Visibility Dashboard")
    st.markdown("Real-time load tracking for TransfersOutsideServices repair sites")

    # --- METRICS ---
    col1, col2, col3, col4, col5 = st.columns(5)

    total = len(df_display)
    completed = len(df_display[df_display["Status"] == "✅ Completed"])
    in_transit = len(df_display[df_display["Status"] == "🟡 In Transit"])
    planned = len(df_display[df_display["Status"] == "⚪ Planned"])
    cancelled = len(df_display[df_display["Status"] == "🔴 Cancelled"])

    col1.metric("Total Loads", total)
    col2.metric("Completed", completed)
    col3.metric("In Transit", in_transit)
    col4.metric("Planned", planned)
    col5.metric("Cancelled", cancelled)

    st.divider()

    # --- DATA TABLE ---
    display_cols = [
        "VRID", "Lane", "Status", "Scheduled Origin Arrival", 
        "Scheduled Dest Arrival", "Origin Arrival", "Origin Departure",
        "Destination Arrival", "Trailer ID", "Carrier Code"
    ]

    # Only show columns that exist
    display_cols = [c for c in display_cols if c in df_display.columns]

    st.dataframe(
        df_display[display_cols].sort_values(
            by="Scheduled Origin Arrival" if "Scheduled Origin Arrival" in display_cols else "VRID",
            ascending=False
        ),
        use_container_width=True,
        height=600,
        column_config={
            "VRID": st.column_config.TextColumn("VRID", width="small"),
            "Lane": st.column_config.TextColumn("Lane", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Trailer ID": st.column_config.TextColumn("Trailer ID", width="medium"),
            "Carrier Code": st.column_config.TextColumn("Carrier", width="small"),
        }
    )

    # --- ADMIN: Site filter override ---
    if user["role"] == "admin":
        st.divider()
        st.markdown("### 🔧 Admin Panel")

        tab1, tab2 = st.tabs(["📊 Site Overview", "👥 User Management"])

        with tab1:
            st.markdown("**Load counts by site:**")
            site_counts = {}
            all_sites = ['RARC', 'RIMG', 'RITO', 'RIVA', 'RNRM', 'LNRM', 'RPNC', 'RPNV', 'RTPX', 'RRPR']
            for site in all_sites:
                site_counts[site] = df["Lane"].str.contains(site, na=False).sum()

            site_df = pd.DataFrame(list(site_counts.items()), columns=["Site", "Total Loads"])
            site_df = site_df.sort_values("Total Loads", ascending=False)
            st.dataframe(site_df, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("**Current Users:**")
            users = load_users()
            user_list = []
            for uname, udata in users.items():
                user_list.append({
                    "Username": uname,
                    "Name": udata.get("name", ""),
                    "Role": udata.get("role", ""),
                    "Sites": ", ".join(udata.get("sites", [])),
                })
            st.dataframe(pd.DataFrame(user_list), use_container_width=True, hide_index=True)

            st.info("💡 To add/remove users, edit the `users.yaml` file in the app directory.")


# --- MAIN APP FLOW ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    show_dashboard()
else:
    show_login()
