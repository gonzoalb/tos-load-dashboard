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

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #232F3E 0%, #37475A 100%);
        padding: 30px 40px;
        border-radius: 12px;
        margin-bottom: 24px;
        color: white;
    }
    .main-header h1 { color: white !important; font-size: 2rem; margin-bottom: 4px; }
    .main-header p { color: #ADB5BD; font-size: 0.95rem; margin: 0; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E9ECEF;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    [data-testid="stMetric"] label {
        color: #6C757D !important; font-size: 0.8rem !important;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #232F3E !important; font-size: 1.8rem !important; font-weight: 700;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #F8F9FA; }

    /* Data table headers */
    [data-testid="stDataFrame"] {
        border-radius: 10px; overflow: hidden; border: 1px solid #E9ECEF;
    }
    [data-testid="stDataFrame"] [role="columnheader"] {
        font-weight: 700 !important; color: #232F3E !important;
        text-transform: uppercase; font-size: 0.75rem !important; letter-spacing: 0.3px;
    }

    /* Timeline card */
    .timeline-card {
        background: white;
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .timeline-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #F0F0F0;
    }
    .timeline-vrid {
        font-size: 1.1rem;
        font-weight: 700;
        color: #232F3E;
    }
    .timeline-status {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-completed { background: #D4EDDA; color: #155724; }
    .status-transit { background: #FFF3CD; color: #856404; }
    .status-scheduled { background: #E2E3E5; color: #383D41; }
    .status-cancelled { background: #F8D7DA; color: #721C24; }

    /* Timeline progress bar */
    .timeline-progress {
        display: flex;
        align-items: center;
        margin: 20px 0;
        position: relative;
    }
    .timeline-node {
        width: 14px; height: 14px;
        border-radius: 50%;
        border: 3px solid #232F3E;
        background: white;
        z-index: 2;
    }
    .timeline-node.active { background: #FF9900; border-color: #FF9900; }
    .timeline-node.completed { background: #28A745; border-color: #28A745; }
    .timeline-line {
        flex-grow: 1;
        height: 4px;
        background: #E9ECEF;
        margin: 0 -1px;
    }
    .timeline-line.filled { background: #28A745; }
    .timeline-line.partial { background: linear-gradient(to right, #28A745 50%, #E9ECEF 50%); }

    .timeline-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 8px;
    }
    .timeline-label {
        text-align: center;
        font-size: 0.75rem;
        color: #6C757D;
    }
    .timeline-label strong {
        display: block;
        color: #232F3E;
        font-size: 0.85rem;
    }
    .timeline-meta {
        display: flex;
        gap: 24px;
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px solid #F0F0F0;
        font-size: 0.8rem;
        color: #6C757D;
    }
    .timeline-meta span { display: flex; align-items: center; gap: 4px; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- USER DATABASE ---
def load_users():
    try:
        with open("users.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {"admin": {"password": "TOS_Admin_2026!", "role": "admin", "sites": ["ALL"], "name": "Albert Gonzalez"}}


def authenticate(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return users[username]
    return None


def derive_status(row):
    canceled = row.get("Canceled Load", False)
    if canceled is True or str(canceled).strip().lower() == 'true':
        return "🔴 Cancelled"
    elif pd.notna(row.get("Dest Actual Arrival")) and str(row.get("Dest Actual Arrival")).strip() != '':
        return "✅ Completed"
    elif pd.notna(row.get("Origin Actual Arrival")) and str(row.get("Origin Actual Arrival")).strip() != '':
        try:
            depart_time = pd.to_datetime(row.get("Origin Scheduled Depart"))
            if depart_time < pd.Timestamp.now():
                return "🟡 In Transit"
            else:
                return "🔵 At Origin"
        except:
            return "🟡 In Transit"
    elif pd.notna(row.get("Origin Scheduled Depart")):
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
    try:
        df = pd.read_csv("data/fmc_export.csv", low_memory=False)
    except FileNotFoundError:
        st.error("❌ No data file found.")
        return pd.DataFrame()

    df.columns = [col.strip().title() for col in df.columns]

    col_map = {
        "Load #": "VRID",
        "Carrier": "Carrier",
        "Subcarrier": "Subcarrier",
        "Lane": "Lane",
        "Shipper Accounts": "Shipper Accounts",
        "Origin Scheduled Depart": "Origin Scheduled Depart",
        "Origin Actual Arrival": "Origin Actual Arrival",
        "Dest Scheduled Arrival": "Dest Scheduled Arrival",
        "Dest Actual Arrival": "Dest Actual Arrival",
        "Dest Finish Unload": "Dest Finish Unload",
        "Trailer Id": "Trailer ID",
        "Canceled Load": "Canceled Load",
        "Trailer Ready Time": "Trailer Ready Time",
        "Origin Late Hours": "Origin Late Hours",
        "Equipment Type": "Equipment Type",
    }

    rename_cols = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename_cols)
    df["Status"] = df.apply(derive_status, axis=1)
    df["Origin"] = df["Lane"].apply(lambda x: str(x).split("->")[0] if pd.notna(x) and "->" in str(x) else "")
    df["Destination"] = df["Lane"].apply(lambda x: str(x).split("->")[-1] if pd.notna(x) and "->" in str(x) else "")

    return df


def filter_by_sites(df, sites):
    if "ALL" in sites:
        return df
    mask = pd.Series([False] * len(df))
    for site in sites:
        mask = mask | df["Lane"].str.contains(site, na=False)
    return df[mask]


def render_timeline_card(row):
    """Render a visual timeline card for a single load."""
    origin = row.get("Origin", "?")
    destination = row.get("Destination", "?")
    status = row.get("Status", "")
    vrid = row.get("VRID", "")
    lane = row.get("Lane", "")
    carrier = row.get("Carrier", "")
    trailer = row.get("Trailer ID", "—")
    equipment = row.get("Equipment Type", "—")

    # Timestamps
    origin_sched = row.get("Origin Scheduled Depart", "—")
    origin_actual = row.get("Origin Actual Arrival", "")
    dest_sched = row.get("Dest Scheduled Arrival", "—")
    dest_actual = row.get("Dest Actual Arrival", "")
    dest_finish = row.get("Dest Finish Unload", "")
    late_hrs = row.get("Origin Late Hours", "")

    # Format timestamps for display
    def fmt_time(val):
        if pd.isna(val) or str(val).strip() == '':
            return "—"
        try:
            dt = pd.to_datetime(val)
            return dt.strftime("%m/%d %H:%M")
        except:
            return str(val)[:16]

    # Determine progress
    if "Completed" in status:
        status_class = "status-completed"
        status_text = "COMPLETED"
        line1_class = "filled"
        line2_class = "filled"
        node1_class = "completed"
        node2_class = "completed"
        node3_class = "completed"
    elif "Transit" in status:
        status_class = "status-transit"
        status_text = "IN TRANSIT"
        line1_class = "filled"
        line2_class = ""
        node1_class = "completed"
        node2_class = "active"
        node3_class = ""
    elif "Cancelled" in status:
        status_class = "status-cancelled"
        status_text = "CANCELLED"
        line1_class = ""
        line2_class = ""
        node1_class = ""
        node2_class = ""
        node3_class = ""
    else:
        status_class = "status-scheduled"
        status_text = "SCHEDULED"
        line1_class = ""
        line2_class = ""
        node1_class = "active"
        node2_class = ""
        node3_class = ""

    # Late indicator
    late_badge = ""
    if pd.notna(late_hrs) and str(late_hrs).strip() != '' and str(late_hrs) != '—':
        try:
            hrs = float(late_hrs)
            if hrs > 0:
                late_badge = f'<span style="color: #DC3545; font-weight: 600;">⚠️ {hrs:.1f}h late at origin</span>'
        except:
            pass

    # Equipment short name
    equip_short = str(equipment).replace("FIFTY_THREE_FOOT_", "53ft ").replace("_", " ").title() if pd.notna(equipment) else "—"

    html = f"""
    <div class="timeline-card">
        <div class="timeline-header">
            <div>
                <span class="timeline-vrid">{vrid}</span>
                <span style="color: #6C757D; font-size: 0.85rem; margin-left: 12px;">{lane}</span>
            </div>
            <span class="timeline-status {status_class}">{status_text}</span>
        </div>

        <div class="timeline-progress">
            <div class="timeline-node {node1_class}"></div>
            <div class="timeline-line {line1_class}"></div>
            <div class="timeline-node {node2_class}"></div>
            <div class="timeline-line {line2_class}"></div>
            <div class="timeline-node {node3_class}"></div>
        </div>

        <div class="timeline-labels">
            <div class="timeline-label">
                <strong>{origin}</strong>
                Depart: {fmt_time(origin_sched)}
                {"<br>Actual: " + fmt_time(origin_actual) if pd.notna(origin_actual) and str(origin_actual).strip() else ""}
            </div>
            <div class="timeline-label">
                <strong>🚛 En Route</strong>
                {late_badge}
            </div>
            <div class="timeline-label">
                <strong>{destination}</strong>
                ETA: {fmt_time(dest_sched)}
                {"<br>Arrived: " + fmt_time(dest_actual) if pd.notna(dest_actual) and str(dest_actual).strip() else ""}
                {"<br>Unloaded: " + fmt_time(dest_finish) if pd.notna(dest_finish) and str(dest_finish).strip() else ""}
            </div>
        </div>

        <div class="timeline-meta">
            <span>🚚 {carrier}</span>
            <span>📋 {trailer if pd.notna(trailer) and str(trailer).strip() else '—'}</span>
            <span>📦 {equip_short}</span>
        </div>
    </div>
    """
    return html


# --- LOGIN PAGE ---
def show_login():
    st.markdown("")
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 40px 0 20px 0;'>
            <div style='font-size: 3.5rem; margin-bottom: 8px;'>🚛</div>
            <h1 style='color: #232F3E; font-size: 1.8rem; margin-bottom: 4px;'>TOS Load Visibility</h1>
            <p style='color: #6C757D; font-size: 0.95rem;'>TransfersOutsideServices — External Repair Sites</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            st.markdown("")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted:
                user = authenticate(username, password)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("Invalid credentials. Contact your program administrator.")
        st.markdown("""
        <div style='text-align: center; padding-top: 24px; color: #ADB5BD; font-size: 0.75rem;'>
            Managed by Line Haul Field — VAR | Contact: gonzoalb@amazon.com
        </div>
        """, unsafe_allow_html=True)


# --- MAIN DASHBOARD ---
def show_dashboard():
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
        st.markdown("#### 🔍 Filters")

    # Load data
    df = load_data()
    if df.empty:
        return

    df_filtered = filter_by_sites(df, sites)

    # Sidebar filters
    with st.sidebar:
        statuses = sorted(df_filtered["Status"].unique().tolist())
        selected_statuses = st.multiselect("Status", statuses, default=statuses)
        st.markdown("")
        direction = st.radio("Direction", ["All", "Inbound", "Outbound"], horizontal=True)
        st.divider()
        try:
            import os
            mod_time = os.path.getmtime("data/fmc_export.csv")
            last_updated = datetime.fromtimestamp(mod_time).strftime("%b %d, %Y at %I:%M %p")
            st.markdown(f"📅 **Last Updated**")
            st.caption(f"{last_updated}")
        except:
            pass

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
    st.markdown("""
    <div class="main-header">
        <h1>🚛 TOS Load Visibility</h1>
        <p>Real-time load tracking for TransfersOutsideServices repair sites — 14-day rolling window</p>
    </div>
    """, unsafe_allow_html=True)

    # --- METRICS ---
    col1, col2, col3, col4, col5 = st.columns(5)
    total = len(df_display)
    completed = len(df_display[df_display["Status"] == "✅ Completed"])
    in_transit = len(df_display[df_display["Status"] == "🟡 In Transit"])
    scheduled = len(df_display[df_display["Status"] == "⚪ Scheduled"])
    cancelled = len(df_display[df_display["Status"] == "🔴 Cancelled"])
    col1.metric("Total Loads", f"{total:,}")
    col2.metric("Completed", f"{completed:,}")
    col3.metric("In Transit", f"{in_transit:,}")
    col4.metric("Scheduled", f"{scheduled:,}")
    col5.metric("Cancelled", f"{cancelled:,}")

    st.markdown("")

    # --- VIEW TOGGLE ---
    view_tab1, view_tab2 = st.tabs(["📋 Table View", "🗺️ Timeline View"])

    with view_tab1:
        display_cols = [
            "VRID", "Lane", "Status", "Origin Scheduled Depart",
            "Dest Scheduled Arrival", "Dest Actual Arrival",
            "Trailer ID", "Carrier", "Equipment Type"
        ]
        display_cols = [c for c in display_cols if c in df_display.columns]

        st.dataframe(
            df_display[display_cols].sort_values(
                by="Origin Scheduled Depart" if "Origin Scheduled Depart" in display_cols else "VRID",
                ascending=False
            ),
            use_container_width=True,
            height=500,
            column_config={
                "VRID": st.column_config.TextColumn("VRID", width="small"),
                "Lane": st.column_config.TextColumn("Lane", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Origin Scheduled Depart": st.column_config.TextColumn("Origin Depart", width="medium"),
                "Dest Scheduled Arrival": st.column_config.TextColumn("ETA at Dest", width="medium"),
                "Dest Actual Arrival": st.column_config.TextColumn("Actual Arrival", width="medium"),
                "Trailer ID": st.column_config.TextColumn("Trailer", width="medium"),
                "Carrier": st.column_config.TextColumn("Carrier", width="small"),
                "Equipment Type": st.column_config.TextColumn("Equipment", width="medium"),
            },
            hide_index=True,
        )

    with view_tab2:
        # Sort: In Transit first, then Scheduled, then Completed
        status_order = {"🟡 In Transit": 0, "🔵 At Origin": 1, "⚪ Scheduled": 2, "✅ Completed": 3, "🔴 Cancelled": 4, "⚪ Planned": 5}
        df_sorted = df_display.copy()
        df_sorted["_sort"] = df_sorted["Status"].map(status_order).fillna(5)
        df_sorted = df_sorted.sort_values(["_sort", "Origin Scheduled Depart"], ascending=[True, True])

        # Pagination
        loads_per_page = 10
        total_pages = max(1, (len(df_sorted) + loads_per_page - 1) // loads_per_page)

        col_pg1, col_pg2, col_pg3 = st.columns([1, 2, 1])
        with col_pg2:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

        st.caption(f"Showing loads {(page-1)*loads_per_page + 1}–{min(page*loads_per_page, len(df_sorted))} of {len(df_sorted)}")

        page_data = df_sorted.iloc[(page-1)*loads_per_page : page*loads_per_page]

        for _, row in page_data.iterrows():
            st.markdown(render_timeline_card(row), unsafe_allow_html=True)

    # --- ADMIN PANEL ---
    if user["role"] == "admin":
        st.markdown("")
        st.markdown("---")
        st.markdown("### 🔧 Admin Panel")

        tab1, tab2, tab3 = st.tabs(["📊 Site Overview", "👥 Users", "📤 Upload Data"])

        with tab1:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Loads by Site**")
                site_counts = {}
                all_sites = ['RPNC', 'RTPX', 'RPNV', 'RNRM', 'LNRM', 'RIMG', 'RARC', 'RRPR', 'RITO', 'RIVA']
                for site in all_sites:
                    site_counts[site] = df["Lane"].str.contains(site, na=False).sum()
                site_df = pd.DataFrame(list(site_counts.items()), columns=["Site", "Loads"])
                site_df = site_df.sort_values("Loads", ascending=False)
                st.dataframe(site_df, use_container_width=True, hide_index=True, height=400)
            with col_b:
                st.markdown("**Status Breakdown**")
                status_counts = df_filtered["Status"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                st.dataframe(status_counts, use_container_width=True, hide_index=True)
                st.markdown("")
                st.markdown("**Data Window**")
                if "Origin Scheduled Depart" in df.columns:
                    dates = pd.to_datetime(df["Origin Scheduled Depart"], errors='coerce')
                    st.caption(f"Earliest: {dates.min().strftime('%b %d, %Y') if pd.notna(dates.min()) else 'N/A'}")
                    st.caption(f"Latest: {dates.max().strftime('%b %d, %Y') if pd.notna(dates.max()) else 'N/A'}")
                    st.caption(f"Total records: {len(df):,}")

        with tab2:
            users = load_users()
            user_list = []
            for uname, udata in users.items():
                user_list.append({
                    "Username": uname,
                    "Name": udata.get("name", ""),
                    "Role": udata.get("role", "").title(),
                    "Sites": ", ".join(udata.get("sites", [])),
                })
            st.dataframe(pd.DataFrame(user_list), use_container_width=True, hide_index=True)
            st.info("💡 Edit `users.yaml` in the GitHub repo to add/remove users.")

        with tab3:
            st.markdown("**Refresh dashboard data:**")
            st.markdown("""
            1. Open your saved query in [Hubble Workbench](https://datacentral.a2z.com/workbench)
            2. Click **Run** → **Download Results**
            3. Upload the CSV below
            """)
            st.markdown("")
            uploaded_file = st.file_uploader("Drop CSV export here", type=["csv"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    test_df = pd.read_csv(uploaded_file)
                    if len(test_df) > 0:
                        uploaded_file.seek(0)
                        with open("data/fmc_export.csv", "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"✅ Success! Uploaded {len(test_df):,} loads. Refresh the page to see updated data.")
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
