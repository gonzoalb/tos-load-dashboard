# TOS Load Visibility Dashboard
## TransfersOutsideServices - External Repair Site Load Tracker

### Overview
This dashboard provides external 3P repair sites with visibility into 
inbound/outbound loads without requiring Amazon credentials.

### Sites Covered
| Site | Location | Co-located With |
|------|----------|-----------------|
| RARC | - | - |
| RIMG | - | - |
| RITO | - | - |
| RIVA | - | - |
| RTPX | - | - |
| RRPR | - | - |
| RPNV | - | RPNC (shared view) |
| RPNC | - | RPNV (shared view) |
| RNRM | - | LNRM (shared view) |
| LNRM | - | RNRM (shared view) |

### Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Place FMC CSV export in `data/fmc_export.csv`
3. Run: `streamlit run app.py`

### Data Refresh
1. Download CSV from FMC (https://trans-logistics.amazon.com/fmc/execution/Ge47T3)
2. Replace `data/fmc_export.csv` with new file
3. Dashboard auto-refreshes on next page load

### User Management
Edit `users.yaml` to add/remove/modify user access:
- `role: admin` = sees all sites + admin panel
- `role: site` = sees only assigned sites
- `sites: ["RPNV", "RPNC"]` = co-located pair (shared view)

### Deployment (Streamlit Cloud - Free)
1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Connect your GitHub repo
4. Set main file: app.py
5. Deploy → get shareable URL

### Admin
- Program: TransfersOutsideServices
- Owner: gonzoalb@amazon.com
- Data Source: FMC (Freight Management Console)
