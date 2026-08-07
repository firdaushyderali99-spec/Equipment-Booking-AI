
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="YOS Equipment Booking System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# PRODUCTION-GRADE DARK THEME CSS
# ============================================================
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stApp p, .stApp span, .stApp label, .stApp li, .stApp td, .stApp th,
    .stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #fafafa !important;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] * {
        color: #e6edf3 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        background-color: #21262d;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 4px;
        border: 1px solid #30363d;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #30363d;
        border-color: #58a6ff;
    }
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px 20px;
    }
    [data-testid="stMetricLabel"] p {
        color: #8b949e !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-size: 32px !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"] {
        color: #8b949e !important;
    }
    h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
    }
    h2, h3, h4 {
        color: #e6edf3 !important;
        font-weight: 600 !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] p {
        color: #8b949e !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
        border-radius: 10px;
        padding: 4px;
        gap: 4px;
        border: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8b949e !important;
        border-radius: 8px;
        font-weight: 500;
        padding: 8px 16px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1f6feb !important;
        color: #ffffff !important;
    }
    .stButton > button {
        background-color: #238636 !important;
        color: #ffffff !important;
        border: 1px solid #2ea043 !important;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        font-size: 14px;
    }
    .stButton > button:hover {
        background-color: #2ea043 !important;
        border-color: #3fb950 !important;
        box-shadow: 0 0 10px rgba(46, 160, 67, 0.3);
    }
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #30363d;
    }
    .stSelectbox > div > div,
    .stDateInput > div > div,
    .stNumberInput > div > div {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        color: #e6edf3 !important;
    }
    .stSelectbox label, .stDateInput label, .stNumberInput label {
        color: #8b949e !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }
    [data-testid="stVegaLiteChart"] {
        background-color: #161b22 !important;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #30363d;
    }
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        color: #e6edf3 !important;
    }
    .streamlit-expanderContent {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-top: none !important;
    }
    hr {
        border: none;
        height: 1px;
        background-color: #30363d;
        margin: 24px 0;
    }
    .stMarkdown table {
        background-color: #161b22;
        border-radius: 8px;
        overflow: hidden;
    }
    .stMarkdown th {
        background-color: #21262d !important;
        color: #e6edf3 !important;
        padding: 10px 16px !important;
    }
    .stMarkdown td {
        color: #c9d1d9 !important;
        padding: 10px 16px !important;
        border-color: #30363d !important;
    }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #0d1117; }
    ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #484f58; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_data():
    bookings = pd.read_excel('Updated_Equipment_Bookings_AI_Training.xlsx')
    service = pd.read_excel('Crane_Service_Schedule_2026.xlsx')
    bookings['Booking_Date'] = pd.to_datetime(bookings['Booking_Date'])
    bookings['Request_Date'] = pd.to_datetime(bookings['Request_Date'])
    service['Service_Date'] = pd.to_datetime(service['Service_Date'])
    
    # FIX: Recalculate utilization correctly = Load / Capacity * 100
    # The data may have wrong utilization values, so we recalculate
    bookings['Crane_Utilization_Pct'] = np.where(
        (bookings['Ton_Capacity'] > 0) & (bookings['Ton_Capacity'].notna()),
        (bookings['Load_Weight_T'] / bookings['Ton_Capacity'] * 100).round(1),
        0
    )
    
    # Assign risk level based on 80% SWL industry standard
    # Low: <50%, Medium: 50-80%, High: >80%
    bookings['Risk_Level'] = pd.cut(
        bookings['Crane_Utilization_Pct'],
        bins=[-1, 50, 80, 200],
        labels=['Low', 'Medium', 'High']
    )
    
    return bookings, service

try:
    bookings, service = load_data()
    data_loaded = True
except Exception as e:
    data_loaded = False
    st.error(f"⚠️ Data loading error: {e}")
    st.info("Ensure 'Updated_Equipment_Bookings_AI_Training.xlsx' and 'Crane_Service_Schedule_2026.xlsx' are in the repo.")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🏗️ YOS Booking")
    st.caption("Seatrium (SG) Pte Ltd • Tuas Boulevard Yard")
    st.markdown("---")
    
    page = st.radio("Navigation", [
        "📊 Dashboard",
        "📝 New Booking",
        "🤖 AI Recommendation",
        "⚠️ Conflict Alerts",
        "📅 Service Schedule"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    if data_loaded:
        st.markdown("**System Status**")
        st.caption(f"📋 {len(bookings):,} bookings")
        st.caption(f"🔧 {service['Equipment_ID'].nunique()} equipment")
        st.caption(f"📅 {len(service):,} service records")
        st.caption(f"🟢 System Online")
    st.markdown("---")
    st.caption("v3.2 • Production Build")

if not data_loaded:
    st.stop()

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def parse_max_swl(swl_str):
    if pd.isna(swl_str) or str(swl_str) in ['N/A', 'nan', 'None', '']:
        return None
    swl_str = str(swl_str).upper().replace('TON', '').replace('T', '').strip()
    if '/' in swl_str:
        parts = swl_str.split('/')
        return max([float(p.strip()) for p in parts if p.strip()])
    try:
        return float(swl_str)
    except:
        return None

def get_utilization_level(load_weight, capacity):
    """Industry standard: 80% SWL is the safe working limit"""
    if not capacity or capacity == 0:
        return 'N/A'
    pct = (load_weight / capacity) * 100
    if pct > 80:
        return 'High'
    elif pct >= 50:
        return 'Medium'
    else:
        return 'Low'

def get_equipment_registry():
    reg = service.drop_duplicates('Equipment_ID')[['Equipment_ID', 'Equipment_Category', 'Equipment_Type', 'SWL_Capacity', 'Location']].copy()
    reg['Max_SWL'] = reg['SWL_Capacity'].apply(parse_max_swl)
    return reg

def get_available_equipment(equipment_type, date, service_df, bookings_df):
    date = pd.to_datetime(date)
    service_on_date = service_df[service_df['Service_Date'] == date]['Equipment_ID'].tolist()
    booked_on_date = bookings_df[
        (bookings_df['Booking_Date'] == date) & 
        (bookings_df['Status'].isin(['Confirmed', 'Pending']))
    ]['Equipment_ID'].tolist()
    all_equipment = service_df[service_df['Equipment_Type'] == equipment_type]['Equipment_ID'].unique().tolist()
    unavailable = set(service_on_date + booked_on_date)
    available = [eq for eq in all_equipment if eq not in unavailable]
    return available, list(unavailable)

def get_suitable_equipment(equipment_type, load_weight, date):
    reg = get_equipment_registry()
    candidates = reg[reg['Equipment_Type'] == equipment_type].copy()
    candidates = candidates[candidates['Max_SWL'] >= load_weight]
    available_ids, _ = get_available_equipment(equipment_type, date, service, bookings)
    candidates['Available'] = candidates['Equipment_ID'].isin(available_ids)
    candidates['Utilization_Pct'] = (load_weight / candidates['Max_SWL'] * 100).round(1)
    candidates['Risk'] = candidates.apply(lambda r: get_utilization_level(load_weight, r['Max_SWL']), axis=1)
    candidates = candidates.sort_values(['Available', 'Utilization_Pct'], ascending=[False, False])
    return candidates

def get_equipment_swl(equipment_id):
    equip = service[service['Equipment_ID'] == equipment_id]
    if len(equip) > 0:
        return equip.iloc[0]['SWL_Capacity']
    return 'N/A'

def recommend_equipment(load_weight, lift_item):
    recommendations = []
    equip_registry = get_equipment_registry()
    
    if lift_item in ['Personnel Access Work', 'Inspection Work', 'Painting Work']:
        mewp_equip = equip_registry[equip_registry['Equipment_Category'] == 'MEWP']
        for _, eq in mewp_equip.sample(min(3, len(mewp_equip))).iterrows():
            recommendations.append({
                'equipment_id': eq['Equipment_ID'],
                'type': eq['Equipment_Type'],
                'capacity': eq['SWL_Capacity'] if pd.notna(eq['SWL_Capacity']) else 'N/A',
                'max_swl': eq['Max_SWL'],
                'location': eq['Location'],
                'reason': f'MEWP suitable for {lift_item}',
                'match_score': 95
            })
        return recommendations
    
    if lift_item in ['Block Transportation', 'Module Transportation', 'Equipment Relocation']:
        cometto_equip = equip_registry[equip_registry['Equipment_Category'] == 'Cometto']
        for _, eq in cometto_equip.sample(min(3, len(cometto_equip))).iterrows():
            recommendations.append({
                'equipment_id': eq['Equipment_ID'],
                'type': eq['Equipment_Type'],
                'capacity': eq['SWL_Capacity'] if pd.notna(eq['SWL_Capacity']) else 'N/A',
                'max_swl': eq['Max_SWL'],
                'location': eq['Location'],
                'reason': f'Cometto/SPMT for {lift_item}',
                'match_score': 90
            })
        return recommendations
    
    if lift_item in ['Steel Plates', 'Pipe Bundles', 'Welding Materials', 'PPE Supplies', 'Insulation Materials', 'Safety Equipment']:
        flt_equip = equip_registry[(equip_registry['Equipment_Category'] == 'Forklift') & (equip_registry['Max_SWL'] >= load_weight)]
        if len(flt_equip) == 0:
            flt_equip = equip_registry[equip_registry['Equipment_Category'] == 'Forklift'].nlargest(3, 'Max_SWL')
        for _, eq in flt_equip.sample(min(3, len(flt_equip))).iterrows():
            risk = get_utilization_level(load_weight, eq['Max_SWL'])
            score = 90 if (eq['Max_SWL'] and eq['Max_SWL'] >= load_weight) else 60
            recommendations.append({
                'equipment_id': eq['Equipment_ID'],
                'type': eq['Equipment_Type'],
                'capacity': eq['SWL_Capacity'] if pd.notna(eq['SWL_Capacity']) else 'N/A',
                'max_swl': eq['Max_SWL'],
                'location': eq['Location'],
                'reason': f'Forklift for {lift_item} (Risk: {risk})',
                'match_score': score
            })
        return recommendations
    
    # Crane items
    crane_equip = equip_registry[
        (equip_registry['Equipment_Category'] == 'Crane') & 
        (equip_registry['Max_SWL'] >= load_weight)
    ].copy()
    
    if len(crane_equip) == 0:
        crane_equip = equip_registry[equip_registry['Equipment_Category'] == 'Crane'].nlargest(5, 'Max_SWL')
    
    crane_equip = crane_equip.copy()
    crane_equip['efficiency'] = load_weight / crane_equip['Max_SWL'] * 100
    crane_equip = crane_equip.sort_values('efficiency', ascending=False)
    
    if lift_item in ['Mega Block Section', 'Offshore Platform Topside', 'Jacket Structure'] and load_weight > 200:
        preferred = crane_equip[crane_equip['Equipment_Type'] == 'Goliath Gantry Crane']
        if len(preferred) > 0:
            crane_equip = pd.concat([preferred, crane_equip[crane_equip['Equipment_Type'] != 'Goliath Gantry Crane']])
    
    for _, eq in crane_equip.head(5).iterrows():
        risk = get_utilization_level(load_weight, eq['Max_SWL'])
        score = min(95, max(50, eq['efficiency'])) if 'efficiency' in eq.index else 70
        recommendations.append({
            'equipment_id': eq['Equipment_ID'],
            'type': eq['Equipment_Type'],
            'capacity': eq['SWL_Capacity'] if pd.notna(eq['SWL_Capacity']) else 'N/A',
            'max_swl': eq['Max_SWL'],
            'location': eq['Location'],
            'reason': f'Capacity {eq["Max_SWL"]:.0f}T handles {load_weight}T (Risk: {risk})',
            'match_score': int(score)
        })
    
    return recommendations

def find_best_dates(equipment_type, preferred_date, days_range=7):
    preferred = pd.to_datetime(preferred_date)
    available_dates = []
    for i in range(-days_range, days_range + 1):
        check_date = preferred + timedelta(days=i)
        if check_date.weekday() < 6:
            available, _ = get_available_equipment(equipment_type, check_date, service, bookings)
            if available:
                available_dates.append({
                    'date': check_date,
                    'available_units': len(available),
                    'equipment_ids': available[:5],
                    'days_from_preferred': abs(i)
                })
    available_dates.sort(key=lambda x: (x['days_from_preferred'], -x['available_units']))
    return available_dates[:5]

# ============================================================
# PAGE: DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.markdown("# 📊 Dashboard")
    st.caption("Equipment booking overview • Tuas Boulevard Yard • 2026")
    st.markdown("---")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    total = len(bookings)
    with col1:
        st.metric("Total Bookings", f"{total:,}")
    with col2:
        comp = len(bookings[bookings['Status'] == 'Completed'])
        st.metric("Completed", f"{comp:,}", f"{comp/total*100:.0f}%")
    with col3:
        active = len(bookings[bookings['Status'].isin(['Confirmed', 'Pending'])])
        st.metric("Active", f"{active:,}", f"{active/total*100:.0f}%")
    with col4:
        rej = len(bookings[bookings['Status'] == 'Rejected'])
        st.metric("Rejected", f"{rej:,}", f"{rej/total*100:.0f}%")
    with col5:
        canc = len(bookings[bookings['Status'] == 'Cancelled'])
        st.metric("Cancelled", f"{canc:,}", f"{canc/total*100:.0f}%")
    with col6:
        high_risk = len(bookings[bookings['Risk_Level'] == 'High'])
        st.metric("High Risk", f"{high_risk:,}", "⚠️")
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["Overview", "Analysis", "Bookings Table"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Status Breakdown")
            status_data = bookings['Status'].value_counts()
            st.bar_chart(status_data)
        with col2:
            st.markdown("#### Equipment Category")
            cat_data = bookings['Equipment_Category'].value_counts()
            st.bar_chart(cat_data)
        
        st.markdown("#### Monthly Trend")
        monthly = bookings.copy()
        monthly['Month'] = monthly['Booking_Date'].dt.to_period('M').astype(str)
        trend = monthly.groupby('Month').size()
        st.line_chart(trend)
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Top Equipment (by bookings)")
            top_eq = bookings['Equipment_ID'].value_counts().head(10)
            st.bar_chart(top_eq)
        with col2:
            st.markdown("#### Risk Level Distribution")
            risk_data = bookings['Risk_Level'].value_counts()
            st.bar_chart(risk_data)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### High Risk by Equipment Type")
            high_risk_type = bookings[bookings['Risk_Level'] == 'High'].groupby('Equipment_Type').size().sort_values(ascending=False).head(10)
            st.bar_chart(high_risk_type)
        with col2:
            st.markdown("#### By Project")
            proj = bookings['Project'].value_counts()
            st.bar_chart(proj)
    
    with tab3:
        st.markdown("#### All Bookings")
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            f_status = st.multiselect("Filter Status", bookings['Status'].unique().tolist(), default=bookings['Status'].unique().tolist())
        with fcol2:
            f_cat = st.selectbox("Filter Category", ['All'] + bookings['Equipment_Category'].unique().tolist(), key="dash_cat")
        with fcol3:
            f_risk = st.selectbox("Filter Risk", ['All', 'High', 'Medium', 'Low'], key="dash_risk")
        
        filtered_bookings = bookings[bookings['Status'].isin(f_status)]
        if f_cat != 'All':
            filtered_bookings = filtered_bookings[filtered_bookings['Equipment_Category'] == f_cat]
        if f_risk != 'All':
            filtered_bookings = filtered_bookings[filtered_bookings['Risk_Level'] == f_risk]
        
        st.caption(f"Showing {len(filtered_bookings):,} of {len(bookings):,} bookings")
        st.dataframe(
            filtered_bookings[['Booking_ID', 'Booking_Date', 'Equipment_Type', 'Equipment_ID', 'Ton_Capacity', 'Load_Weight_T', 'Risk_Level', 'Location', 'Status']].sort_values('Booking_Date', ascending=False),
            use_container_width=True,
            hide_index=True,
            height=500
        )

# ============================================================
# PAGE: NEW BOOKING (with equipment picker + SWL filter)
# ============================================================
elif page == "📝 New Booking":
    st.markdown("# 📝 New Booking")
    st.caption("Create a new equipment booking with real-time availability and capacity checking")
    st.markdown("---")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("#### Equipment Selection")
        equipment_category = st.selectbox("Category", ['Crane', 'MEWP', 'Cometto', 'Forklift'])
        
        type_map = {
            'Crane': ['Level Luffing Crane', 'Goliath Gantry Crane', 'Crawler Crane', 'Mobile Crane', 'Tower Crane', 'Workshop Crane'],
            'MEWP': ['Scissor Lift 10m', 'Boom Lift 20m', 'Articulating Boom Lift 26m', 'Telescopic Boom Lift 30m'],
            'Cometto': ['Cometto MSPE 8 Axle Lines', 'Cometto Eco500 12 Axle Lines', 'SPMT 16 Axle Lines', 'SPMT 24 Axle Lines'],
            'Forklift': ['Counterbalance Forklift', 'Heavy Duty Forklift', 'Telehandler Forklift', 'Reach Forklift']
        }
        equipment_type = st.selectbox("Type", type_map[equipment_category])
        
        # Get all equipment of this type with their SWL
        reg = get_equipment_registry()
        type_equipment = reg[reg['Equipment_Type'] == equipment_type].sort_values('Max_SWL', ascending=False)
        
        # Build dropdown: Equipment ID + Capacity
        equip_options = ['Auto-select (best match)']
        equip_details = {}
        for _, eq in type_equipment.iterrows():
            swl_display = f"{eq['Max_SWL']:.0f}T" if pd.notna(eq['Max_SWL']) else "N/A"
            label = f"{eq['Equipment_ID']} — SWL: {swl_display} — {eq['Location']}"
            equip_options.append(label)
            equip_details[label] = {
                'id': eq['Equipment_ID'],
                'max_swl': eq['Max_SWL'],
                'location': eq['Location'],
                'swl_capacity': eq['SWL_Capacity']
            }
        
        selected_equip = st.selectbox("Specific Equipment (optional)", equip_options)
        booking_date = st.date_input("Date", value=datetime(2026, 9, 1), min_value=datetime(2026, 8, 1))
        
        # Availability check
        available_ids, _ = get_available_equipment(equipment_type, booking_date, service, bookings)
        if selected_equip != 'Auto-select (best match)':
            chosen_id = equip_details[selected_equip]['id']
            if chosen_id in available_ids:
                st.success(f"✅ {chosen_id} is available on {booking_date.strftime('%d %b %Y')}")
            else:
                st.error(f"❌ {chosen_id} is NOT available on {booking_date.strftime('%d %b %Y')}")
        else:
            if available_ids:
                st.success(f"✅ {len(available_ids)} unit(s) available on {booking_date.strftime('%d %b %Y')}")
            else:
                st.error(f"❌ No {equipment_type} available on this date")
    
    with col2:
        st.markdown("#### Job Details")
        
        items_map = {
            'Crane': ['Hull Block Section', 'Engine Module', 'Structural Steel Module', 'Mega Block Section',
                     'Accommodation Module', 'Pipe Spool', 'Anchor Chain', 'Mooring Winch',
                     'Transformer Unit', 'Construction Materials', 'Workshop Equipment', 'Turret Assembly',
                     'Helideck Module', 'Flare Tower Section', 'Riser Assembly', 'Offshore Platform Topside', 'Jacket Structure'],
            'MEWP': ['Personnel Access Work', 'Inspection Work', 'Painting Work'],
            'Cometto': ['Block Transportation', 'Module Transportation', 'Equipment Relocation'],
            'Forklift': ['Steel Plates', 'Pipe Bundles', 'Welding Materials', 'PPE Supplies', 'Insulation Materials', 'Safety Equipment']
        }
        
        lift_item = st.selectbox("Lift Item", items_map.get(equipment_category, ['General']))
        load_weight = st.number_input("Load Weight (T)", min_value=0.1, max_value=15000.0, value=50.0)
        duration = st.selectbox("Duration", ['Half Day (AM)', 'Half Day (PM)', 'Full Day', '2 Days', '3 Days', '5 Days', '7 Days'])
        shift = st.selectbox("Shift", ['Day Shift (0700-1900)', 'Night Shift (1900-0700)'])
        project = st.selectbox("Project", ['Project Alpha', 'Project Beta', 'Project Gamma', 'Project Delta', 'Project Echo', 'Project Foxtrot'])
    
    st.markdown("---")
    
    if st.button("🔍 Check Availability & Submit", type="primary", use_container_width=True):
        st.markdown("---")
        st.markdown("### Results")
        
        if selected_equip != 'Auto-select (best match)':
            chosen = equip_details[selected_equip]
            chosen_id = chosen['id']
            max_swl = chosen['max_swl']
            
            if max_swl and load_weight > max_swl:
                st.error(f"❌ **REJECTED** — Load {load_weight}T exceeds {chosen_id} capacity ({max_swl:.0f}T)")
                st.warning("Select a higher-capacity equipment or reduce load weight.")
                
                # Show alternatives that CAN handle it
                st.markdown("**Equipment that can handle this load:**")
                suitable = reg[(reg['Equipment_Type'] == equipment_type) & (reg['Max_SWL'] >= load_weight)]
                if len(suitable) > 0:
                    for _, s in suitable.head(5).iterrows():
                        avail_mark = "🟢" if s['Equipment_ID'] in available_ids else "🔴"
                        risk = get_utilization_level(load_weight, s['Max_SWL'])
                        st.write(f"{avail_mark} **{s['Equipment_ID']}** — SWL: {s['Max_SWL']:.0f}T — Risk: {risk} — {s['Location']}")
                else:
                    st.warning(f"No {equipment_type} can handle {load_weight}T. Try a different type.")
            
            elif chosen_id in available_ids:
                risk = get_utilization_level(load_weight, max_swl)
                st.success(f"✅ **APPROVED** — {chosen_id} available and can handle the load")
                st.write(f"• **Equipment:** {chosen_id}")
                st.write(f"• **Capacity:** {max_swl:.0f}T")
                st.write(f"• **Load:** {load_weight}T")
                st.write(f"• **Risk Level:** {risk}")
                st.write(f"• **Location:** {chosen['location']}")
                if risk == 'High':
                    st.warning(f"⚠️ High risk — load exceeds 80% of SWL. Consider a larger crane.")
            else:
                st.error(f"❌ {chosen_id} is not available on {booking_date.strftime('%d %b %Y')}")
                st.markdown("**Alternative dates:**")
                for i in range(1, 8):
                    alt_date = pd.to_datetime(booking_date) + timedelta(days=i)
                    alt_avail, _ = get_available_equipment(equipment_type, alt_date, service, bookings)
                    if chosen_id in alt_avail:
                        st.write(f"• ✅ **{alt_date.strftime('%d %b %Y')}** ({alt_date.strftime('%A')})")
        
        else:
            # Auto-select: only show equipment where SWL >= load weight
            suitable = get_suitable_equipment(equipment_type, load_weight, booking_date)
            
            if len(suitable) == 0:
                st.error(f"❌ No {equipment_type} can handle {load_weight}T load")
                st.warning("Consider a different equipment type with higher capacity.")
            else:
                available_suitable = suitable[suitable['Available'] == True]
                
                if len(available_suitable) > 0:
                    st.success(f"✅ {len(available_suitable)} suitable unit(s) available (SWL ≥ {load_weight}T)")
                    st.markdown("**Recommended (sorted by best fit):**")
                    
                    for idx, (_, eq) in enumerate(available_suitable.head(5).iterrows()):
                        risk = get_utilization_level(load_weight, eq['Max_SWL'])
                        if idx == 0:
                            st.success(f"🎯 **Best: {eq['Equipment_ID']}** — SWL: {eq['Max_SWL']:.0f}T — Risk: {risk} — {eq['Location']}")
                        else:
                            st.write(f"• **{eq['Equipment_ID']}** — SWL: {eq['Max_SWL']:.0f}T — Risk: {risk} — {eq['Location']}")
                else:
                    st.warning(f"⚠️ Equipment exists but none available on {booking_date.strftime('%d %b %Y')}")
                    st.markdown("**Try these dates:**")
                    alt_dates = find_best_dates(equipment_type, booking_date)
                    for alt in alt_dates[:3]:
                        st.write(f"• ✅ **{alt['date'].strftime('%d %b %Y')}** — {alt['available_units']} unit(s)")

# ============================================================
# PAGE: AI RECOMMENDATION
# ============================================================
elif page == "🤖 AI Recommendation":
    st.markdown("# 🤖 AI Recommendation")
    st.caption("Describe your job — AI suggests the best equipment, checks capacity, and finds available dates")
    st.markdown("---")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("#### What do you need?")
        
        all_items = ['Hull Block Section', 'Engine Module', 'Structural Steel Module', 'Mega Block Section',
             'Accommodation Module', 'Pipe Spool', 'Anchor Chain', 'Mooring Winch',
             'Transformer Unit', 'Construction Materials', 'Workshop Equipment', 'Turret Assembly',
             'Helideck Module', 'Flare Tower Section', 'Riser Assembly', 'Personnel Access Work',
             'Steel Plates', 'Pipe Bundles', 'Safety Equipment', 'Insulation Materials',
             'Welding Materials', 'PPE Supplies', 'Offshore Platform Topside', 'Jacket Structure',
             'Inspection Work', 'Painting Work', 'Block Transportation', 'Module Transportation', 'Equipment Relocation']
        
        ai_lift = st.selectbox("Task / Lift Item", all_items)
        ai_load = st.number_input("Load Weight (T)", min_value=0.1, max_value=15000.0, value=50.0, key="ai_wt")
        ai_date = st.date_input("Preferred Date", value=datetime(2026, 9, 15), min_value=datetime(2026, 8, 1), key="ai_dt")
        
        get_rec = st.button("🤖 Get Recommendation", type="primary", use_container_width=True)
    
    with col2:
        st.markdown("#### Recommendations")
        
        if get_rec:
            recs = recommend_equipment(ai_load, ai_lift)
            
            if recs:
                best = recs[0]
                risk = get_utilization_level(ai_load, best.get('max_swl'))
                st.success(f"**Best Match: {best['equipment_id']}**")
                st.write(f"**Type:** {best['type']}")
                st.write(f"**Capacity:** {best['max_swl']:.0f}T" if best.get('max_swl') else f"**Capacity:** {best['capacity']}")
                st.write(f"**Location:** {best['location']}")
                st.write(f"**Risk Level:** {risk}")
                st.write(f"**Reason:** {best['reason']}")
                
                # Availability
                available, _ = get_available_equipment(best['type'], ai_date, service, bookings)
                if best['equipment_id'] in available:
                    st.success(f"📅 Available on {ai_date.strftime('%d %b %Y')}")
                else:
                    st.warning(f"⚠️ Not available on {ai_date.strftime('%d %b %Y')}")
                    alt_dates = find_best_dates(best['type'], ai_date, 5)
                    if alt_dates:
                        st.write("**Nearest dates:**")
                        for alt in alt_dates[:3]:
                            st.write(f"• {alt['date'].strftime('%d %b %Y')} — {alt['available_units']} units")
                
                # Alternatives
                if len(recs) > 1:
                    st.markdown("---")
                    st.markdown("**Alternatives:**")
                    for i, rec in enumerate(recs[1:], 1):
                        with st.expander(f"Option {i+1}: {rec['equipment_id']} ({rec['type']})"):
                            cap_display = f"{rec['max_swl']:.0f}T" if rec.get('max_swl') else str(rec['capacity'])
                            alt_risk = get_utilization_level(ai_load, rec.get('max_swl'))
                            st.write(f"Capacity: {cap_display}")
                            st.write(f"Location: {rec['location']}")
                            st.write(f"Risk: {alt_risk}")
                            st.write(f"Reason: {rec['reason']}")
                
                # Safety
                st.markdown("---")
                st.markdown("**Safety Assessment:**")
                if ai_load > 200:
                    st.warning("🔶 Heavy Lift — Heavy Lift Specialist + Lift Plan required")
                elif ai_load > 50:
                    st.info("🔵 Medium Lift — Advanced cert + Standard Lift Plan")
                else:
                    st.success("✅ Standard Lift — Normal protocols")
            else:
                st.warning("No suitable equipment found. Adjust parameters.")
        else:
            st.info("Fill in requirements and click Get Recommendation.")

# ============================================================
# PAGE: CONFLICT ALERTS (FIXED - Risk Levels instead of %)
# ============================================================
elif page == "⚠️ Conflict Alerts":
    st.markdown("# ⚠️ Conflict Alerts")
    st.caption("Booking conflicts, maintenance overlaps, and risk monitoring")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["Active Conflicts", "Upcoming Maintenance", "Risk Warnings"])
    
    with tab1:
        st.markdown("#### Booking vs Maintenance Conflicts")
        
        conflicts = []
        active_bk = bookings[bookings['Status'].isin(['Confirmed', 'Pending'])]
        
        for _, bk in active_bk.iterrows():
            svc_match = service[
                (service['Service_Date'] == bk['Booking_Date']) & 
                (service['Equipment_ID'] == bk['Equipment_ID'])
            ]
            if not svc_match.empty:
                conflicts.append({
                    'Booking': bk['Booking_ID'],
                    'Equipment': bk['Equipment_ID'],
                    'Type': bk['Equipment_Type'],
                    'Date': bk['Booking_Date'].strftime('%d %b %Y'),
                    'Service': svc_match.iloc[0]['Service_Type'],
                    'Action': 'Reschedule required'
                })
        
        if conflicts:
            st.error(f"🔴 {len(conflicts)} active conflict(s) found")
            st.dataframe(pd.DataFrame(conflicts), use_container_width=True, hide_index=True)
        else:
            st.success("✅ No conflicts — all bookings clear of maintenance")
        
        st.markdown("---")
        st.markdown("#### Historical Conflicts")
        hist_conflicts = bookings[bookings['Service_Conflict'] == True]
        if len(hist_conflicts) > 0:
            st.warning(f"{len(hist_conflicts)} past bookings had conflicts")
            st.dataframe(
                hist_conflicts[['Booking_ID', 'Equipment_ID', 'Booking_Date', 'Status', 'Status_Reason']].head(15),
                use_container_width=True, hide_index=True
            )
    
    with tab2:
        st.markdown("#### Next 14 Days Maintenance")
        today = pd.to_datetime('2026-08-07')
        upcoming = service[
            (service['Service_Date'] >= today) & 
            (service['Service_Date'] <= today + timedelta(days=14))
        ].sort_values('Service_Date')
        
        if not upcoming.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("This Week", len(upcoming[upcoming['Service_Date'] <= today + timedelta(days=7)]))
            with col2:
                st.metric("Next Week", len(upcoming[upcoming['Service_Date'] > today + timedelta(days=7)]))
            with col3:
                st.metric("Equipment Affected", upcoming['Equipment_ID'].nunique())
            
            st.dataframe(
                upcoming[['Equipment_ID', 'Equipment_Type', 'Location', 'Service_Date', 'Service_Type', 'Service_Duration_Hours']],
                use_container_width=True, hide_index=True
            )
        else:
            st.success("No maintenance in next 14 days.")
    
    with tab3:
        st.markdown("#### Risk Warnings")
        st.caption("Industry standard: Safe working limit is 80% of SWL. Bookings above 80% are flagged as High risk.")
        st.markdown("---")
        
        # Show HIGH risk bookings (>80% of SWL)
        high_risk_bookings = bookings[
            (bookings['Risk_Level'] == 'High') & 
            (bookings['Status'].isin(['Confirmed', 'Pending']))
        ].sort_values('Crane_Utilization_Pct', ascending=False).copy()
        
        if not high_risk_bookings.empty:
            st.error(f"🔴 {len(high_risk_bookings)} HIGH risk bookings (load exceeds 80% of SWL)")
            
            display_df = high_risk_bookings[['Booking_ID', 'Equipment_ID', 'Equipment_Type', 'Ton_Capacity', 'Load_Weight_T', 'Risk_Level', 'Lift_Item', 'Location']].copy()
            display_df.columns = ['Booking', 'Equipment', 'Type', 'SWL (T)', 'Load (T)', 'Risk', 'Lift Item', 'Location']
            
            st.dataframe(
                display_df.head(20),
                use_container_width=True, hide_index=True
            )
            
            st.markdown("---")
            st.info("💡 **Recommendation:** For High risk bookings, consider using a larger capacity equipment to maintain safety margin below 80% SWL.")
        else:
            st.success("✅ No high risk bookings for active jobs")
        
        st.markdown("---")
        
        # Summary of all risk levels
        st.markdown("#### Risk Distribution (Active Bookings)")
        active_only = bookings[bookings['Status'].isin(['Confirmed', 'Pending'])]
        col1, col2, col3 = st.columns(3)
        with col1:
            low_count = len(active_only[active_only['Risk_Level'] == 'Low'])
            st.metric("🟢 Low Risk (<50%)", f"{low_count}")
        with col2:
            med_count = len(active_only[active_only['Risk_Level'] == 'Medium'])
            st.metric("🟡 Medium Risk (50-80%)", f"{med_count}")
        with col3:
            high_count = len(active_only[active_only['Risk_Level'] == 'High'])
            st.metric("🔴 High Risk (>80%)", f"{high_count}")
        
        st.markdown("---")
        st.markdown("#### Rejection Analysis")
        st.caption("Common reasons bookings get rejected")
        rejected = bookings[bookings['Status'] == 'Rejected']
        reason_counts = rejected['Status_Reason'].value_counts().head(8)
        st.bar_chart(reason_counts)

# ============================================================
# PAGE: SERVICE SCHEDULE
# ============================================================
elif page == "📅 Service Schedule":
    st.markdown("# 📅 Service Schedule")
    st.caption("2026 maintenance schedule for all yard equipment")
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f_cat = st.selectbox("Category", ['All'] + sorted(service['Equipment_Category'].unique().tolist()), key="svc_cat")
    with col2:
        if f_cat != 'All':
            opts = sorted(service[service['Equipment_Category'] == f_cat]['Equipment_Type'].unique().tolist())
        else:
            opts = sorted(service['Equipment_Type'].unique().tolist())
        f_type = st.selectbox("Type", ['All'] + opts, key="svc_type")
    with col3:
        f_status = st.selectbox("Status", ['All', 'Completed', 'Scheduled'], key="svc_status")
    with col4:
        months = ['All'] + [f"{i:02d} - {datetime(2026,i,1).strftime('%B')}" for i in range(1, 13)]
        f_month = st.selectbox("Month", months, key="svc_month")
    
    filtered = service.copy()
    if f_cat != 'All':
        filtered = filtered[filtered['Equipment_Category'] == f_cat]
    if f_type != 'All':
        filtered = filtered[filtered['Equipment_Type'] == f_type]
    if f_status != 'All':
        filtered = filtered[filtered['Service_Status'] == f_status]
    if f_month != 'All':
        m = int(f_month.split(' - ')[0])
        filtered = filtered[filtered['Service_Date'].dt.month == m]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Records", f"{len(filtered):,}")
    with col2:
        st.metric("Completed", f"{len(filtered[filtered['Service_Status'] == 'Completed']):,}")
    with col3:
        st.metric("Scheduled", f"{len(filtered[filtered['Service_Status'] == 'Scheduled']):,}")
    with col4:
        st.metric("Equipment", f"{filtered['Equipment_ID'].nunique()}")
    
    st.markdown("---")
    st.dataframe(
        filtered.sort_values('Service_Date'),
        use_container_width=True,
        hide_index=True,
        height=600
    )

