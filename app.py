
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
# CUSTOM CSS FOR MODERN LOOK
# ============================================================
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown li,
    [data-testid="stSidebar"] label {
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] .stRadio label span {
        color: #ffffff !important;
        font-size: 15px !important;
    }
    
    /* Card-like containers */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    [data-testid="stMetricLabel"] p {
        font-size: 13px !important;
        color: #6c757d !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #1a1a2e !important;
    }
    
    /* Headers */
    h1 {
        color: #1a1a2e !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    h2, h3 {
        color: #16213e !important;
        font-weight: 600 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0f3460 0%, #1a1a2e 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(15, 52, 96, 0.4);
    }
    
    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }
    
    /* Success/Warning/Error boxes */
    .stAlert {
        border-radius: 10px !important;
    }
    
    /* Selectbox and inputs */
    .stSelectbox, .stDateInput, .stNumberInput {
        margin-bottom: 8px;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #dee2e6, transparent);
        margin: 20px 0;
    }
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
    return bookings, service

try:
    bookings, service = load_data()
    data_loaded = True
except Exception as e:
    data_loaded = False
    st.error(f"Error loading data: {e}")

# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown("### 🏗️ YOS Booking System")
    st.markdown("##### Seatrium (SG) Pte Ltd")
    st.caption("Tuas Boulevard Yard")
    st.markdown("---")
    
    page = st.radio("", [
        "📊 Dashboard",
        "📝 New Booking",
        "🤖 AI Recommendation",
        "⚠️ Conflict Alerts",
        "📅 Service Schedule"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("##### ⚙️ Quick Stats")
    if data_loaded:
        st.caption(f"📋 {len(bookings)} total bookings")
        st.caption(f"🔧 {service['Equipment_ID'].nunique()} equipment tracked")
        st.caption(f"📅 {len(service)} service events")
    
    st.markdown("---")
    st.caption("v2.0 | AI-Powered Booking System")
    st.caption("© 2026 Seatrium YOS")

if not data_loaded:
    st.stop()

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_available_equipment(equipment_type, date, service_df, bookings_df):
    """Check which equipment of a type is available on a given date"""
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

def get_equipment_swl(equipment_id):
    """Get SWL capacity for an equipment"""
    equip = service[service['Equipment_ID'] == equipment_id]
    if len(equip) > 0:
        return equip.iloc[0]['SWL_Capacity']
    return 'N/A'

def parse_max_swl(swl_str):
    """Extract maximum tonnage from SWL string"""
    if pd.isna(swl_str) or str(swl_str) == 'N/A' or str(swl_str) == 'nan':
        return None
    swl_str = str(swl_str).upper().replace('TON', '').replace('T', '').strip()
    if '/' in swl_str:
        parts = swl_str.split('/')
        return max([float(p.strip()) for p in parts if p.strip()])
    try:
        return float(swl_str)
    except:
        return None

def recommend_equipment(load_weight, lift_item):
    """AI-based equipment recommendation - LOGICAL matching"""
    recommendations = []
    
    # Build equipment registry with max SWL
    equip_registry = service.drop_duplicates('Equipment_ID')[['Equipment_ID', 'Equipment_Category', 'Equipment_Type', 'SWL_Capacity', 'Location']].copy()
    equip_registry['Max_SWL'] = equip_registry['SWL_Capacity'].apply(parse_max_swl)
    
    # MEWP items - no crane needed
    if lift_item in ['Personnel Access Work', 'Inspection Work', 'Painting Work']:
        mewp_equip = equip_registry[equip_registry['Equipment_Category'] == 'MEWP']
        for _, eq in mewp_equip.sample(min(3, len(mewp_equip))).iterrows():
            recommendations.append({
                'equipment_id': eq['Equipment_ID'],
                'type': eq['Equipment_Type'],
                'capacity': eq['SWL_Capacity'],
                'location': eq['Location'],
                'reason': f'MEWP suitable for {lift_item}',
                'match_score': 95
            })
        return recommendations
    
    # Cometto items - transportation
    if lift_item in ['Block Transportation', 'Module Transportation', 'Equipment Relocation']:
        cometto_equip = equip_registry[equip_registry['Equipment_Category'] == 'Cometto']
        for _, eq in cometto_equip.sample(min(3, len(cometto_equip))).iterrows():
            recommendations.append({
                'equipment_id': eq['Equipment_ID'],
                'type': eq['Equipment_Type'],
                'capacity': eq['SWL_Capacity'],
                'location': eq['Location'],
                'reason': f'Cometto/SPMT suitable for {lift_item}',
                'match_score': 90
            })
        return recommendations
    
    # Forklift items
    if lift_item in ['Steel Plates', 'Pipe Bundles', 'Welding Materials', 'PPE Supplies', 'Insulation Materials', 'Safety Equipment']:
        flt_equip = equip_registry[(equip_registry['Equipment_Category'] == 'Forklift') & (equip_registry['Max_SWL'] >= load_weight)]
        if len(flt_equip) == 0:
            flt_equip = equip_registry[equip_registry['Equipment_Category'] == 'Forklift']
        for _, eq in flt_equip.sample(min(3, len(flt_equip))).iterrows():
            score = 90 if (eq['Max_SWL'] and eq['Max_SWL'] >= load_weight) else 60
            recommendations.append({
                'equipment_id': eq['Equipment_ID'],
                'type': eq['Equipment_Type'],
                'capacity': eq['SWL_Capacity'],
                'location': eq['Location'],
                'reason': f'Forklift for material handling ({lift_item})',
                'match_score': score
            })
        return recommendations
    
    # Crane items - match by capacity
    crane_equip = equip_registry[
        (equip_registry['Equipment_Category'] == 'Crane') & 
        (equip_registry['Max_SWL'] >= load_weight)
    ].copy()
    
    if len(crane_equip) == 0:
        crane_equip = equip_registry[equip_registry['Equipment_Category'] == 'Crane'].nlargest(5, 'Max_SWL')
    
    # Sort by closest capacity match (most efficient use)
    crane_equip = crane_equip.copy()
    crane_equip['efficiency'] = load_weight / crane_equip['Max_SWL'] * 100
    crane_equip = crane_equip.sort_values('efficiency', ascending=False)
    
    # Prioritize by lift item type
    if lift_item in ['Mega Block Section', 'Offshore Platform Topside', 'Jacket Structure'] and load_weight > 200:
        preferred = crane_equip[crane_equip['Equipment_Type'] == 'Goliath Gantry Crane']
        if len(preferred) > 0:
            crane_equip = pd.concat([preferred, crane_equip[crane_equip['Equipment_Type'] != 'Goliath Gantry Crane']])
    
    for _, eq in crane_equip.head(5).iterrows():
        utilization = round((load_weight / eq['Max_SWL']) * 100, 1) if eq['Max_SWL'] else 0
        score = min(95, max(50, utilization))
        recommendations.append({
            'equipment_id': eq['Equipment_ID'],
            'type': eq['Equipment_Type'],
            'capacity': eq['SWL_Capacity'],
            'location': eq['Location'],
            'reason': f'SWL {eq["SWL_Capacity"]} handles {load_weight}T (utilization: {utilization}%)',
            'match_score': int(score)
        })
    
    return recommendations

def find_best_dates(equipment_type, preferred_date, days_range=7):
    """Find available dates near preferred date"""
    preferred = pd.to_datetime(preferred_date)
    available_dates = []
    for i in range(-days_range, days_range + 1):
        check_date = preferred + timedelta(days=i)
        if check_date.weekday() < 6:
            available, unavailable = get_available_equipment(equipment_type, check_date, service, bookings)
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
    st.markdown("# 📊 Equipment Booking Dashboard")
    st.caption("Real-time overview of all equipment bookings and utilization across Tuas Boulevard Yard")
    st.markdown("---")
    
    # KPI Row
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Bookings", f"{len(bookings):,}")
    with col2:
        completed = len(bookings[bookings['Status'] == 'Completed'])
        st.metric("Completed", f"{completed}", f"{completed/len(bookings)*100:.0f}%")
    with col3:
        confirmed = len(bookings[bookings['Status'].isin(['Confirmed', 'Pending'])])
        st.metric("Active", f"{confirmed}", "Confirmed + Pending")
    with col4:
        rejected = len(bookings[bookings['Status'] == 'Rejected'])
        st.metric("Rejected", f"{rejected}", f"{rejected/len(bookings)*100:.0f}%")
    with col5:
        cancelled = len(bookings[bookings['Status'] == 'Cancelled'])
        st.metric("Cancelled", f"{cancelled}", f"{cancelled/len(bookings)*100:.0f}%")
    with col6:
        avg_util = bookings['Crane_Utilization_Pct'].mean()
        st.metric("Avg Utilization", f"{avg_util:.1f}%")
    
    st.markdown("---")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "🔍 Detailed Analysis", "📋 Recent Bookings"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Bookings by Status")
            status_df = bookings['Status'].value_counts().reset_index()
            status_df.columns = ['Status', 'Count']
            st.bar_chart(status_df.set_index('Status'))
        
        with col2:
            st.markdown("#### Bookings by Equipment Category")
            cat_df = bookings['Equipment_Category'].value_counts().reset_index()
            cat_df.columns = ['Category', 'Count']
            st.bar_chart(cat_df.set_index('Category'))
        
        st.markdown("#### Monthly Booking Trend")
        bookings_copy = bookings.copy()
        bookings_copy['Month'] = bookings_copy['Booking_Date'].dt.to_period('M').astype(str)
        monthly = bookings_copy.groupby('Month').agg(
            Total=('Booking_ID', 'count'),
            Completed=('Status', lambda x: (x == 'Completed').sum()),
            Rejected=('Status', lambda x: (x == 'Rejected').sum())
        )
        st.line_chart(monthly)
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Top 10 Equipment by Bookings")
            top_equip = bookings['Equipment_ID'].value_counts().head(10).reset_index()
            top_equip.columns = ['Equipment', 'Bookings']
            st.bar_chart(top_equip.set_index('Equipment'))
        
        with col2:
            st.markdown("#### Priority Distribution")
            priority_df = bookings['Priority'].value_counts().reset_index()
            priority_df.columns = ['Priority', 'Count']
            st.bar_chart(priority_df.set_index('Priority'))
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Avg Utilization by Equipment Type")
            util_by_type = bookings.groupby('Equipment_Type')['Crane_Utilization_Pct'].mean().sort_values(ascending=False).head(10)
            st.bar_chart(util_by_type)
        
        with col2:
            st.markdown("#### Bookings by Project")
            proj_df = bookings['Project'].value_counts().reset_index()
            proj_df.columns = ['Project', 'Count']
            st.bar_chart(proj_df.set_index('Project'))
    
    with tab3:
        st.markdown("#### Recent Bookings")
        recent = bookings.sort_values('Request_Date', ascending=False).head(25)
        display_cols = ['Booking_ID', 'Booking_Date', 'Equipment_Type', 'Equipment_ID', 'Ton_Capacity', 'Load_Weight_T', 'Location', 'Status', 'Priority']
        st.dataframe(
            recent[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Booking_ID": st.column_config.TextColumn("Booking ID", width="small"),
                "Booking_Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                "Load_Weight_T": st.column_config.NumberColumn("Load (T)", format="%.1f"),
            }
        )

# ============================================================
# PAGE: NEW BOOKING
# ============================================================
elif page == "📝 New Booking":
    st.markdown("# 📝 Create New Booking")
    st.caption("Submit a new equipment booking request with automatic availability checking")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("#### 🏗️ Equipment Selection")
        equipment_category = st.selectbox("Equipment Category", ['Crane', 'MEWP', 'Cometto', 'Forklift'])
        
        type_options = {
            'Crane': ['Level Luffing Crane', 'Goliath Gantry Crane', 'Crawler Crane', 'Mobile Crane', 'Tower Crane', 'Workshop Crane'],
            'MEWP': ['Scissor Lift 10m', 'Boom Lift 20m', 'Articulating Boom Lift 26m', 'Telescopic Boom Lift 30m'],
            'Cometto': ['Cometto MSPE 8 Axle Lines', 'Cometto Eco500 12 Axle Lines', 'SPMT 16 Axle Lines', 'SPMT 24 Axle Lines'],
            'Forklift': ['Counterbalance Forklift', 'Heavy Duty Forklift', 'Telehandler Forklift', 'Reach Forklift']
        }
        equipment_type = st.selectbox("Equipment Type", type_options[equipment_category])
        
        booking_date = st.date_input("Preferred Booking Date", value=datetime(2026, 9, 1), min_value=datetime(2026, 8, 1))
        
        # Show available equipment count for selected type and date
        available, unavailable = get_available_equipment(equipment_type, booking_date, service, bookings)
        if available:
            st.success(f"✅ {len(available)} unit(s) available on this date")
        else:
            st.error(f"❌ No units available on this date")
        
        location_options = sorted(service[service['Equipment_Type'] == equipment_type]['Location'].unique().tolist())
        location = st.selectbox("Location", location_options if location_options else ['N/A'])
        
    with col2:
        st.markdown("#### 📋 Job Details")
        
        lift_items_by_cat = {
            'Crane': ['Hull Block Section', 'Engine Module', 'Structural Steel Module', 'Mega Block Section',
                     'Accommodation Module', 'Pipe Spool', 'Anchor Chain', 'Mooring Winch',
                     'Transformer Unit', 'Construction Materials', 'Workshop Equipment', 'Turret Assembly',
                     'Helideck Module', 'Flare Tower Section', 'Riser Assembly', 'Offshore Platform Topside', 'Jacket Structure'],
            'MEWP': ['Personnel Access Work', 'Inspection Work', 'Painting Work'],
            'Cometto': ['Block Transportation', 'Module Transportation', 'Equipment Relocation'],
            'Forklift': ['Steel Plates', 'Pipe Bundles', 'Welding Materials', 'PPE Supplies', 'Insulation Materials', 'Safety Equipment']
        }
        
        lift_item = st.selectbox("Lift Item / Task", lift_items_by_cat.get(equipment_category, ['General']))
        load_weight = st.number_input("Load Weight (Tonnes)", min_value=0.1, max_value=15000.0, value=50.0)
        duration = st.selectbox("Duration", ['Half Day (AM)', 'Half Day (PM)', 'Full Day', '2 Days', '3 Days', '5 Days', '7 Days'])
        shift = st.selectbox("Shift", ['Day Shift (0700-1900)', 'Night Shift (1900-0700)'])
        priority = st.selectbox("Priority", ['Low', 'Medium', 'High', 'Urgent'])
        project = st.selectbox("Project", ['Project Alpha', 'Project Beta', 'Project Gamma', 'Project Delta', 'Project Echo', 'Project Foxtrot'])
        phase = st.selectbox("Project Phase", ['Planning', 'Fabrication', 'Assembly', 'Outfitting', 'Testing', 'Commissioning'])
    
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        submit = st.button("🔍 Check Availability & Submit Booking", type="primary", use_container_width=True)
    
    if submit:
        st.markdown("---")
        st.markdown("### 📊 Availability Results")
        
        available, unavailable = get_available_equipment(equipment_type, booking_date, service, bookings)
        
        if available:
            st.success(f"✅ **{len(available)} unit(s) available** on {booking_date.strftime('%d %B %Y')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Available Equipment:**")
                for eq in available[:8]:
                    swl = get_equipment_swl(eq)
                    st.write(f"• **{eq}** — SWL: {swl}")
            
            with col2:
                recommended_eq = available[0]
                swl = get_equipment_swl(recommended_eq)
                max_swl = parse_max_swl(swl)
                
                st.markdown("**🎯 Recommended Assignment:**")
                st.info(f"**{recommended_eq}** (SWL: {swl})")
                
                if max_swl and load_weight <= max_swl:
                    util = round((load_weight / max_swl) * 100, 1)
                    st.write(f"• Load: {load_weight}T / Capacity: {max_swl}T")
                    st.write(f"• Utilization: {util}%")
                    st.write(f"• ✅ Safe to proceed")
                elif max_swl:
                    st.error(f"⚠️ Load {load_weight}T EXCEEDS capacity {max_swl}T!")
                    st.write("Please select a higher-capacity equipment.")
        else:
            st.error(f"❌ **No {equipment_type} available** on {booking_date.strftime('%d %B %Y')}")
            
            st.markdown("**📅 Suggested Alternative Dates:**")
            alt_dates = find_best_dates(equipment_type, booking_date)
            if alt_dates:
                for alt in alt_dates:
                    st.write(f"• **{alt['date'].strftime('%d %B %Y')}** ({alt['date'].strftime('%A')}) — {alt['available_units']} unit(s) available")
            else:
                st.warning("No alternatives found within ±7 days. Consider a different equipment type.")

# ============================================================
# PAGE: AI RECOMMENDATION
# ============================================================
elif page == "🤖 AI Recommendation":
    st.markdown("# 🤖 AI Equipment Recommendation")
    st.caption("Tell us what you need to do — our AI will suggest the best equipment and optimal date")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("#### 🎯 What do you need?")
        
        ai_lift_item = st.selectbox("What are you doing?", 
            ['Hull Block Section', 'Engine Module', 'Structural Steel Module', 'Mega Block Section',
             'Accommodation Module', 'Pipe Spool', 'Anchor Chain', 'Mooring Winch',
             'Transformer Unit', 'Construction Materials', 'Workshop Equipment', 'Turret Assembly',
             'Helideck Module', 'Flare Tower Section', 'Riser Assembly', 'Personnel Access Work',
             'Steel Plates', 'Pipe Bundles', 'Safety Equipment', 'Insulation Materials',
             'Welding Materials', 'PPE Supplies', 'Offshore Platform Topside', 'Jacket Structure',
             'Inspection Work', 'Painting Work', 'Block Transportation', 'Module Transportation', 'Equipment Relocation'],
            key="ai_lift")
        
        ai_load = st.number_input("Load Weight (Tonnes)", min_value=0.1, max_value=15000.0, value=50.0, key="ai_load")
        ai_date = st.date_input("When do you need it?", value=datetime(2026, 9, 15), min_value=datetime(2026, 8, 1), key="ai_date")
        ai_phase = st.selectbox("Project Phase", ['Planning', 'Fabrication', 'Assembly', 'Outfitting', 'Testing', 'Commissioning'], key="ai_phase")
        
        get_rec = st.button("🤖 Get AI Recommendation", type="primary", use_container_width=True)
    
    with col2:
        st.markdown("#### 💡 AI Recommendations")
        
        if get_rec:
            recommendations = recommend_equipment(ai_load, ai_lift_item)
            
            if recommendations:
                for i, rec in enumerate(recommendations):
                    if i == 0:
                        st.success(f"**✅ Best Match: {rec['equipment_id']}**")
                        st.markdown(f"""
| Detail | Value |
|--------|-------|
| **Equipment** | {rec['equipment_id']} |
| **Type** | {rec['type']} |
| **Capacity** | {rec['capacity']} |
| **Location** | {rec['location']} |
| **Match Score** | {rec['match_score']}% |
| **Reason** | {rec['reason']} |
                        """)
                        
                        # Check availability on requested date
                        available, _ = get_available_equipment(rec['type'], ai_date, service, bookings)
                        if rec['equipment_id'] in available:
                            st.info(f"📅 **{rec['equipment_id']} is AVAILABLE** on {ai_date.strftime('%d %B %Y')}")
                        else:
                            st.warning(f"⚠️ {rec['equipment_id']} not available on {ai_date.strftime('%d %B %Y')}")
                            alt_dates = find_best_dates(rec['type'], ai_date, 5)
                            if alt_dates:
                                st.write("**Nearest available dates:**")
                                for alt in alt_dates[:3]:
                                    st.write(f"• {alt['date'].strftime('%d %B %Y')} ({alt['available_units']} units)")
                    else:
                        with st.expander(f"💡 Alternative {i}: {rec['equipment_id']} ({rec['type']})"):
                            st.write(f"• **Capacity:** {rec['capacity']}")
                            st.write(f"• **Location:** {rec['location']}")
                            st.write(f"• **Match Score:** {rec['match_score']}%")
                            st.write(f"• **Reason:** {rec['reason']}")
                
                # Safety assessment
                st.markdown("---")
                st.markdown("#### ⚡ Safety Assessment")
                if ai_load > 200:
                    st.warning("🔶 **Heavy Lift (>200T)** — Requires Heavy Lift Specialist + Lifting Supervisor + Detailed Lift Plan")
                elif ai_load > 50:
                    st.info("🔵 **Medium Lift (50-200T)** — Requires Advanced certification + Standard Lift Plan")
                else:
                    st.success("✅ **Standard Lift (<50T)** — Normal safety protocols apply")
                
                if ai_lift_item in ['Offshore Platform Topside', 'Mega Block Section', 'Jacket Structure']:
                    st.warning("🔶 **Critical Lift Item** — Requires MOM permit + detailed lift plan + safety review")
            else:
                st.warning("No suitable equipment found for this configuration. Please adjust parameters.")
        else:
            st.info("👈 Fill in your requirements and click **Get AI Recommendation** to see suggestions.")

# ============================================================
# PAGE: CONFLICT ALERTS
# ============================================================
elif page == "⚠️ Conflict Alerts":
    st.markdown("# ⚠️ Conflict & Alert Center")
    st.caption("Monitor booking conflicts, maintenance overlaps, and high-risk situations")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["🔴 Active Conflicts", "🟡 Upcoming Maintenance", "🟠 Risk Warnings"])
    
    with tab1:
        st.markdown("#### Bookings Conflicting with Maintenance Schedule")
        
        conflicts = []
        active_bookings = bookings[bookings['Status'].isin(['Confirmed', 'Pending'])]
        
        for _, booking in active_bookings.iterrows():
            service_match = service[
                (service['Service_Date'] == booking['Booking_Date']) & 
                (service['Equipment_ID'] == booking['Equipment_ID'])
            ]
            if not service_match.empty:
                conflicts.append({
                    'Booking ID': booking['Booking_ID'],
                    'Equipment': booking['Equipment_ID'],
                    'Type': booking['Equipment_Type'],
                    'Date': booking['Booking_Date'].strftime('%d %b %Y'),
                    'Service Type': service_match.iloc[0]['Service_Type'],
                    'Priority': booking['Priority'],
                    'Action Required': '🔴 Reschedule booking or defer maintenance'
                })
        
        if conflicts:
            st.error(f"⚠️ Found **{len(conflicts)} active conflict(s)**")
            conflict_df = pd.DataFrame(conflicts)
            st.dataframe(conflict_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No active conflicts detected! All bookings are clear of maintenance windows.")
        
        # Service conflict bookings from data
        st.markdown("---")
        st.markdown("#### Historical Conflicts (from booking data)")
        service_conflicts = bookings[bookings['Service_Conflict'] == True]
        if len(service_conflicts) > 0:
            st.warning(f"📊 {len(service_conflicts)} bookings had service conflicts flagged")
            st.dataframe(
                service_conflicts[['Booking_ID', 'Equipment_ID', 'Booking_Date', 'Status', 'Status_Reason']].head(20),
                use_container_width=True, hide_index=True
            )
    
    with tab2:
        st.markdown("#### Upcoming Maintenance (Next 14 Days)")
        today = pd.to_datetime('2026-08-07')
        upcoming = service[
            (service['Service_Date'] >= today) & 
            (service['Service_Date'] <= today + timedelta(days=14))
        ].sort_values('Service_Date')
        
        if not upcoming.empty:
            st.info(f"📅 **{len(upcoming)} maintenance events** scheduled in the next 14 days")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("This Week", len(upcoming[upcoming['Service_Date'] <= today + timedelta(days=7)]))
            with col2:
                st.metric("Next Week", len(upcoming[upcoming['Service_Date'] > today + timedelta(days=7)]))
            with col3:
                st.metric("Equipment Affected", upcoming['Equipment_ID'].nunique())
            
            st.dataframe(
                upcoming[['Equipment_ID', 'Equipment_Type', 'Location', 'Service_Date', 'Service_Type', 'Service_Duration_Hours']],
                use_container_width=True, hide_index=True,
                column_config={
                    "Service_Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                }
            )
        else:
            st.success("No maintenance scheduled in the next 14 days.")
    
    with tab3:
        st.markdown("#### High Utilization Warnings (>85%)")
        high_util = bookings[
            (bookings['Crane_Utilization_Pct'] > 85) & 
            (bookings['Status'].isin(['Confirmed', 'Pending']))
        ].sort_values('Crane_Utilization_Pct', ascending=False)
        
        if not high_util.empty:
            st.warning(f"⚠️ **{len(high_util)} bookings** with utilization >85% — approaching equipment limits")
            st.dataframe(
                high_util[['Booking_ID', 'Equipment_ID', 'Ton_Capacity', 'Load_Weight_T', 'Crane_Utilization_Pct', 'Priority']].head(20),
                use_container_width=True, hide_index=True,
                column_config={
                    "Crane_Utilization_Pct": st.column_config.ProgressColumn("Utilization %", min_value=0, max_value=100),
                }
            )
        else:
            st.success("✅ No high utilization warnings for active bookings.")
        
        st.markdown("---")
        st.markdown("#### Rejection Analysis")
        rejected = bookings[bookings['Status'] == 'Rejected']
        reason_counts = rejected['Status_Reason'].value_counts().head(8)
        st.bar_chart(reason_counts)

# ============================================================
# PAGE: SERVICE SCHEDULE
# ============================================================
elif page == "📅 Service Schedule":
    st.markdown("# 📅 Equipment Service Schedule 2026")
    st.caption("Complete maintenance schedule for all yard equipment — filter by category, type, or status")
    st.markdown("---")
    
    # Filters in a clean row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        cat_filter = st.selectbox("Category", ['All'] + sorted(service['Equipment_Category'].unique().tolist()))
    with col2:
        if cat_filter != 'All':
            svc_type_options = sorted(service[service['Equipment_Category'] == cat_filter]['Equipment_Type'].unique().tolist())
        else:
            svc_type_options = sorted(service['Equipment_Type'].unique().tolist())
        type_filter = st.selectbox("Equipment Type", ['All'] + svc_type_options)
    with col3:
        status_filter = st.selectbox("Status", ['All', 'Completed', 'Scheduled'])
    with col4:
        month_filter = st.selectbox("Month", ['All'] + [f'{i:02d} - {datetime(2026,i,1).strftime("%B")}' for i in range(1, 13)])
    
    # Apply filters
    filtered = service.copy()
    if cat_filter != 'All':
        filtered = filtered[filtered['Equipment_Category'] == cat_filter]
    if type_filter != 'All':
        filtered = filtered[filtered['Equipment_Type'] == type_filter]
    if status_filter != 'All':
        filtered = filtered[filtered['Service_Status'] == status_filter]
    if month_filter != 'All':
        month_num = int(month_filter.split(' - ')[0])
        filtered = filtered[filtered['Service_Date'].dt.month == month_num]
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Services", f"{len(filtered):,}")
    with col2:
        st.metric("Completed", f"{len(filtered[filtered['Service_Status'] == 'Completed']):,}")
    with col3:
        st.metric("Scheduled", f"{len(filtered[filtered['Service_Status'] == 'Scheduled']):,}")
    with col4:
        st.metric("Equipment Units", f"{filtered['Equipment_ID'].nunique()}")
    
    st.markdown("---")
    
    # Display table
    st.dataframe(
        filtered.sort_values('Service_Date'),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Service_Date": st.column_config.DateColumn("Service Date", format="DD MMM YYYY"),
            "Service_Duration_Hours": st.column_config.NumberColumn("Duration (hrs)", format="%d"),
        }
    )

