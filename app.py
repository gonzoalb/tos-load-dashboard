import streamlit as st
import pandas as pd
import yaml
from datetime import datetime

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


# --- USER DATABASE ---
def load_users():
    """Load user credentials and site assignments."""
    try:
        with open("users.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "admin": {"password": "TOS_Admin_2026!", "role": "admin", "sites": ["ALL"], "name": "Albert Gonzalez"},
        }


def authenticate(username, password):
    """Verify credentials and return user info."""
    users = load_users()
    if username in users and users[username]["password"] == password:
        return users[username]
    return None


def derive_status(row):
    """Derive load status from available data."""
    canceled = row.get("Canceled Load", False)
    if canceled is True or str(canceled).strip().lower() == 'true':
        return "🔴 Cancelled"
    elif pd.notna(row.get("Actual Dest Arrival")) and str(row.get("Actual Dest Arrival")).strip() != '':
        return "✅ Completed"
    elif pd.notna(row.get("Origin Scheduled Depart")) and str(row.get("Origin Scheduled Depart")).strip() != '':
        # Check if departure time has passed
        try:
            depart_time = pd.to_datetime(row.get("Origin Scheduled Depart"))
            if depart_time < pd.Timestamp.now():
                return "🟡 In Transit"
            else:
                return "⚪ Scheduled"
        except:
            return "⚪ Scheduled"
    else:
        return "⚪ Planned"


def load_data():
    """Load and transform data from CSV export."""
    try:
        df = pd.read_csv("data/fmc_export.csv", low_memory=False)
    except FileNotFoundError:
        st.error("❌ No data file found. Please upload CSV export to data/fmc_export.csv")
        return pd.DataFrame()

    # Normalize column names (Hubble exports as lowercase)
    df.columns = [col.strip().title() for col in df.columns]

    # Rename to dashboard-friendly names
    col_map = {
        "Load #": "VRID",
        "Carrier": "Carrier",
        "Subcarrier": "Subcarrier",
        "Lane": "Lane",
        "Shipper Accounts": "Shipper Accounts",
        "Origin Scheduled Depart": "Origin Scheduled Depart",
        "Dest Scheduled Arrival": "Dest Scheduled Arrival",
        "Actual Dest Arrival": "Actual Dest Arrival",
        "Trailer Id": "Trailer ID",
        "Canceled Load": "Canceled Load",
        "Trailer Ready Time": "Trailer Ready Time",
        # Support old FMC format too
        "First Dock Arrival": "Origin Arrival",
        "First Dock Departure": "Origin Departure",
        "Last Dock Arrival": "Actual Dest Arrival",
    }

    rename_cols = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename_cols)

    # Derive status
    df["Status"] = df.apply(derive_status, axis=1)

    # Parse origin and destination from Lane
    df["Origin"] = df["Lane"].apply(
        lambda x: str(x).split("->")[0] if pd.notna(x) and "->" in str(x) else ""
    )
    df["Destination"] = df["Lane"].apply(
        lambda x: str(x).split("->")[-1] if pd.notna(x) and "->" in str(x) else ""
    )

    return df


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
        statuses = sorted(df_filtered["Status"].unique().tolist())
        selected_statuses = st.multiselect("Status", statuses, default=statuses)
        direction = st.radio("Direction", ["All", "Inbound", "Outbound"])

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
    st.markdown("Load tracking for TransfersOutsideServices repair sites")

    # --- METRICS ---
    col1, col2, col3, col4, col5 = st.columns(5)

    total = len(df_display)
    completed = len(df_display[df_display["Status"] == "✅ Completed"])
    in_transit = len(df_display[df_display["Status"] == "🟡 In Transit"])
    scheduled = len(df_display[df_display["Status"] == "⚪ Scheduled"])
    cancelled = len(df_display[df_display["Status"] == "🔴 Cancelled"])

    col1.metric("Total Loads", total)
    col2.metric("Completed", completed)
    col3.metric("In Transit", in_transit)
    col4.metric("Scheduled", scheduled)
    col5.metric("Cancelled", cancelled)

    st.divider()

    # --- DATA TABLE ---
    display_cols = [
        "VRID", "Lane", "Status", "Origin Scheduled Depart",
        "Dest Scheduled Arrival", "Actual Dest Arrival",
        "Trailer ID", "Carrier"
    ]
    display_cols = [c for c in display_cols if c in df_display.columns]

    st.dataframe(
        df_display[display_cols].sort_values(
            by="Origin Scheduled Depart" if "Origin Scheduled Depart" in display_cols else "VRID",
            ascending=False
        ),
        use_container_width=True,
        height=600,
        column_config={
            "VRID": st.column_config.TextColumn("VRID", width="small"),
            "Lane": st.column_config.TextColumn("Lane", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Origin Scheduled Depart": st.column_config.TextColumn("Origin Depart", width="medium"),
            "Dest Scheduled Arrival": st.column_config.TextColumn("Dest ETA", width="medium"),
            "Actual Dest Arrival": st.column_config.TextColumn("Actual Arrival", width="medium"),
            "Trailer ID": st.column_config.TextColumn("Trailer ID", width="medium"),
            "Carrier": st.column_config.TextColumn("Carrier", width="small"),
        }
    )

    # --- ADMIN PANEL ---
    if user["role"] == "admin":
        st.divider()
        st.markdown("### 🔧 Admin Panel")

        tab1, tab2, tab3 = st.tabs(["📊 Site Overview", "👥 User Management", "📤 Upload Data"])

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
            st.info("💡 To add/remove users, edit the `users.yaml` file in the repo.")

        with tab3:
            st.markdown("**Upload fresh data export:**")
            st.markdown("Run your saved query in Hubble Workbench, download CSV, and upload here.")
            uploaded_file = st.file_uploader("Drop CSV here", type=["csv"])
            if uploaded_file is not None:
                try:
                    test_df = pd.read_csv(uploaded_file)
                    if len(test_df) > 0:
                        # Save to data directory
                        uploaded_file.seek(0)
                        with open("data/fmc_export.csv", "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"✅ Uploaded! {len(test_df)} loads. Refresh the page to see updated data.")
                    else:
                        st.error("File appears empty.")
                except Exception as e:
                    st.error(f"Error reading file: {e}")


# --- MAIN APP FLOW ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    show_dashboard()
else:
    show_login()
