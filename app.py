import streamlit as st
import pandas as pd
import yaml
import json
import os
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
    .main-header {
        background: linear-gradient(135deg, #232F3E 0%, #37475A 100%);
        padding: 30px 40px;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .main-header h1 { color: white !important; font-size: 2rem; margin-bottom: 4px; }
    .main-header p { color: #ADB5BD; font-size: 0.95rem; margin: 0; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #E9ECEF;
        border-radius: 10px; padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    [data-testid="stMetric"] label {
        color: #6C757D !important; font-size: 0.8rem !important;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #232F3E !important; font-size: 1.8rem !important; font-weight: 700;
    }
    [data-testid="stSidebar"] { background: #F8F9FA; }
    [data-testid="stDataFrame"] {
        border-radius: 10px; overflow: hidden; border: 1px solid #E9ECEF;
    }
    [data-testid="stDataFrame"] [role="columnheader"] {
        font-weight: 700 !important; color: #232F3E !important;
        text-transform: uppercase; font-size: 0.75rem !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- TIMESTAMP TRACKING ---
def get_last_refreshed():
    """Read last refresh timestamp."""
    try:
        with open("data/last_refreshed.json", "r") as f:
            return json.load(f).get("timestamp", "Unknown")
    except:
        return "Unknown"


def set_last_refreshed():
    """Save current time as last refresh."""
    os.makedirs("data", exist_ok=True)
    with open("data/last_refreshed.json", "w") as f:
        json.dump({"timestamp": datetime.now().strftime("%b %d, %Y at %I:%M %p")}, f)


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
        "Load #": "VRID", "Carrier": "Carrier", "Subcarrier": "Subcarrier",
        "Lane": "Lane", "Shipper Accounts": "Shipper Accounts",
        "Origin Scheduled Depart": "Origin Scheduled Depart",
        "Origin Actual Arrival": "Origin Actual Arrival",
        "Dest Scheduled Arrival": "Dest Scheduled Arrival",
        "Dest Actual Arrival": "Dest Actual Arrival",
        "Dest Finish Unload": "Dest Finish Unload",
        "Trailer Id": "Trailer ID", "Canceled Load": "Canceled Load",
        "Trailer Ready Time": "Trailer Ready Time",
        "Origin Late Hours": "Origin Late Hours",
        "Pallet Count": "Pallet Count",
        "Unit Count": "Unit Count",
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


def fmt_time(val):
    if pd.isna(val) or str(val).strip() == '':
        return "—"
    try:
        return pd.to_datetime(val).strftime("%m/%d %H:%M")
    except:
        return str(val)[:16]

def render_timeline_native(row):
    origin = row.get("Origin", "?")
    destination = row.get("Destination", "?")
    status = row.get("Status", "")
    vrid = row.get("VRID", "")
    lane = row.get("Lane", "")
    carrier = row.get("Carrier", "")
    trailer = row.get("Trailer ID", "")
    equipment = row.get("Equipment Type", "")
    origin_sched = row.get("Origin Scheduled Depart", "")
    origin_actual = row.get("Origin Actual Arrival", "")
    dest_sched = row.get("Dest Scheduled Arrival", "")
    dest_actual = row.get("Dest Actual Arrival", "")
    dest_finish = row.get("Dest Finish Unload", "")
    late_hrs = row.get("Origin Late Hours", "")

    # Truck faces right (🚛) and moves along the route based on status
    if "Completed" in status:
        progress = "🟢━━━━━━━━━━━━━━━━━━━━━━━━━🟢🚛"
    elif "Transit" in status:
        progress = "🟢━━━━━━━━━━━━🚛━━━━━━━━━━━━⚪"
    elif "Cancelled" in status:
        progress = "🔴─ ─ ─ ─ ─ ─ ─ ✖ ─ ─ ─ ─ ─ ─🔴"
    elif "Origin" in status:
        progress = "🟢━━━🚛─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─⚪"
    else:
        progress = "🚛─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─⚪"

    equip_short = str(equipment).replace("FIFTY_THREE_FOOT_", "53' ").replace("_", " ").title() if pd.notna(equipment) and str(equipment).strip() else "—"

    late_text = ""
    if pd.notna(late_hrs) and str(late_hrs).strip() != '':
        try:
            hrs = float(late_hrs)
            if hrs > 0:
                late_text = f"⚠️ {hrs:.1f}h late"
        except:
            pass

    with st.container():
        st.markdown("---")
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"**{vrid}** — `{lane}`")
        with col_h2:
            st.markdown(f"**{status}**")

        st.code(f"  {origin:<14}                          {destination:>14}\n  {progress}", language=None)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**📍 Origin: {origin}**")
            st.caption(f"Scheduled: {fmt_time(origin_sched)}")
            if pd.notna(origin_actual) and str(origin_actual).strip():
                st.caption(f"Actual: {fmt_time(origin_actual)}")
            if late_text:
                st.caption(late_text)
        with col2:
            st.markdown("**🚛 En Route**")
            st.caption(f"Carrier: {carrier}")
            if pd.notna(trailer) and str(trailer).strip():
                st.caption(f"Trailer: {trailer}")
            st.caption(f"Equipment: {equip_short}")
            units = row.get("Unit Count", 0)
            if pd.notna(units) and float(units) > 0:
                st.caption(f"📦 Units: {int(float(units)):,}")
            st.markdown(f"**📍 Destination: {destination}**")
            st.caption(f"ETA: {fmt_time(dest_sched)}")
            if pd.notna(dest_actual) and str(dest_actual).strip():
                st.caption(f"Arrived: {fmt_time(dest_actual)}")
            if pd.notna(dest_finish) and str(dest_finish).strip():
                st.caption(f"Unloaded: {fmt_time(dest_finish)}")

            st.markdown(f"**📍 Destination: {destination}**")
            st.caption(f"ETA: {fmt_time(dest_sched)}")
            if pd.notna(dest_actual) and str(dest_actual).strip():
                st.caption(f"Arrived: {fmt_time(dest_actual)}")
            if pd.notna(dest_finish) and str(dest_finish).strip():
                st.caption(f"Unloaded: {fmt_time(dest_finish)}")


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

    df = load_data()
    if df.empty:
        return

    df_filtered = filter_by_sites(df, sites)

    with st.sidebar:
        statuses = sorted(df_filtered["Status"].unique().tolist())
        selected_statuses = st.multiselect("Status", statuses, default=statuses)
        st.markdown("")
        direction = st.radio("Direction", ["All", "Inbound", "Outbound"], horizontal=True)
        st.divider()
        # Last refreshed - prominent
        last_refresh = get_last_refreshed()
        st.markdown("📅 **Data Last Refreshed**")
        st.info(f"🕐 {last_refresh}")

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
    last_refresh = get_last_refreshed()
    st.markdown(f"""
    <div class="main-header">
        <h1>🚛 TOS Load Visibility</h1>
        <p>Real-time load tracking for TransfersOutsideServices repair sites — 14-day rolling window &nbsp;|&nbsp; Last refreshed: {last_refresh}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- SEARCH BAR ---
    search_query = st.text_input("🔍 Search by VRID, Lane, or Trailer ID", placeholder="e.g. 111RTWTRK or RTPX or AZNG-V568285")
    if search_query:
        search_query = search_query.strip().upper()
        mask = (
            df_display["VRID"].str.upper().str.contains(search_query, na=False) |
            df_display["Lane"].str.upper().str.contains(search_query, na=False) |
            df_display["Trailer ID"].fillna("").str.upper().str.contains(search_query, na=False)
        )
        df_display = df_display[mask]
        st.caption(f"Found {len(df_display)} results for \"{search_query}\"")

    st.markdown("")

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
            "Trailer ID", "Carrier", "Equipment Type", "Unit Count"
        ]
        display_cols = [c for c in display_cols if c in df_display.columns]

        st.dataframe(
            df_display[display_cols].sort_values(
                by="Origin Scheduled Depart" if "Origin Scheduled Depart" in display_cols else "VRID",
                ascending=False
            ),
            use_container_width=True, height=500,
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
                "Unit Count": st.column_config.NumberColumn("Units", width="small", format="%d"),
            },
            hide_index=True,
        )

    with view_tab2:
        status_order = {"🟡 In Transit": 0, "🔵 At Origin": 1, "⚪ Scheduled": 2, "✅ Completed": 3, "🔴 Cancelled": 4, "⚪ Planned": 5}
        df_sorted = df_display.copy()
        df_sorted["_sort"] = df_sorted["Status"].map(status_order).fillna(5)
        df_sorted = df_sorted.sort_values(["_sort", "Origin Scheduled Depart"], ascending=[True, True])

        loads_per_page = 10
        total_pages = max(1, (len(df_sorted) + loads_per_page - 1) // loads_per_page)
        if len(df_sorted) > loads_per_page:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, key="timeline_page")
            st.caption(f"Showing {(page-1)*loads_per_page + 1}–{min(page*loads_per_page, len(df_sorted))} of {len(df_sorted)} loads")
        else:
            page = 1

        page_data = df_sorted.iloc[(page-1)*loads_per_page : page*loads_per_page]
        for _, row in page_data.iterrows():
            render_timeline_native(row)

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
                for site in ['RPNC', 'RTPX', 'RPNV', 'RGLD', 'RNRM', 'LNRM', 'RIMG', 'RARC', 'RRPR', 'RITO', 'RIVA']:
                    site_counts[site] = df["Lane"].str.contains(site, na=False).sum()
                site_df = pd.DataFrame(list(site_counts.items()), columns=["Site", "Loads"])
                st.dataframe(site_df.sort_values("Loads", ascending=False), use_container_width=True, hide_index=True)
            with col_b:
                st.markdown("**Status Breakdown**")
                status_counts = df_filtered["Status"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                st.dataframe(status_counts, use_container_width=True, hide_index=True)

        with tab2:
            users = load_users()
            user_list = [{"Username": u, "Name": d.get("name",""), "Role": d.get("role","").title(), "Sites": ", ".join(d.get("sites",[]))} for u, d in users.items()]
            st.dataframe(pd.DataFrame(user_list), use_container_width=True, hide_index=True)
            st.info("💡 Edit `users.yaml` in the GitHub repo to add/remove users.")

        with tab3:
            st.markdown("**Refresh dashboard data:**")
            st.markdown("""
            1. Open your saved query in [Hubble Workbench](https://datacentral.a2z.com/workbench)
            2. Click **Run** → **Download Results**
            3. Upload the CSV below
            """)
            uploaded_file = st.file_uploader("Drop CSV export here", type=["csv"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    test_df = pd.read_csv(uploaded_file)
                    if len(test_df) > 0:
                        uploaded_file.seek(0)
                        with open("data/fmc_export.csv", "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        set_last_refreshed()
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
