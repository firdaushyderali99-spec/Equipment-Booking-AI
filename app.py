
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

bookings, service = load_data()

# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
st.sidebar.image("https://img.icons8.com/color/96/crane.png", width=80)
st.sidebar.title("YOS Booking System")
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigation", [
    "📊 Dashboard",
    "📝 New Booking",
    "🤖 AI Recommendation",
    "⚠️ Conflict Alerts",
    "📅 Service Schedule"
])

st.sidebar.markdown("---")
st.sidebar.info("🏗️ Seatrium (SG) Pte Ltd\nTuas Boulevard Yard\nYard Operations Support")

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_available_equipment(equipment_type, date, service_df, bookings_df):
    """Check which equipment of a type is available on a given date"""
    date = pd.to_datetime(date)
    
    # Equipment under service on that date
    service_on_date = service_df[service_df['Service_Date'] == date]['Equipment_ID'].tolist()
    
    # Equipment already booked on that date
    booked_on_date = bookings_df[
        (bookings_df['Booking_Date'] == date) & 
        (bookings_df['Status'].isin(['Confirmed', 'Pending']))
    ]['Equipment_ID'].tolist()
    
    # All equipment of that type
    all_equipment = service_df[service_df['Equipment_Type'] == equipment_type]['Equipment_ID'].unique().tolist()
    
    # Available = all - service - booked
    unavailable = set(service_on_date + booked_on_date)
    available = [eq for eq in all_equipment if eq not in unavailable]
    
    return available, list(unavailable)

def recommend_equipment(load_weight, location, lift_item, project_phase):
    """AI-based equipment recommendation"""
    recommendations = []
    
    # Rule 1: Match by capacity
    if load_weight <= 5:
        recommendations.append({'type': 'Counterbalance Forklift', 'reason': f'Load {load_weight}T within forklift capacity'})
    elif load_weight <= 25:
        recommendations.append({'type': 'Heavy Duty Forklift', 'reason': f'Load {load_weight}T suitable for heavy duty forklift'})
        recommendations.append({'type': 'Mobile Crane', 'reason': f'Alternative: Mobile crane for {load_weight}T loads'})
    elif load_weight <= 50:
        recommendations.append({'type': 'Level Luffing Crane', 'reason': f'Load {load_weight}T - LLC (50T capacity) recommended'})
        recommendations.append({'type': 'Mobile Crane', 'reason': f'Alternative: Mobile crane for flexibility'})
    elif load_weight <= 100:
        recommendations.append({'type': 'Level Luffing Crane', 'reason': f'Load {load_weight}T - LLC (100T capacity) recommended'})
        recommendations.append({'type': 'Crawler Crane', 'reason': f'Alternative: Crawler crane for heavy lifts'})
    elif load_weight <= 300:
        recommendations.append({'type': 'Goliath Gantry Crane', 'reason': f'Load {load_weight}T - Goliath Gantry (300T) recommended'})
        recommendations.append({'type': 'Level Luffing Crane', 'reason': f'Alternative: LLC 22 (300T capacity)'})
        recommendations.append({'type': 'Crawler Crane', 'reason': f'Alternative: Crawler crane (250T)'})
    elif load_weight <= 600:
        recommendations.append({'type': 'Goliath Gantry Crane', 'reason': f'Load {load_weight}T - Goliath Gantry (600T) required'})
    else:
        recommendations.append({'type': 'Goliath Gantry Crane', 'reason': f'Load {load_weight}T - Only GC-16/GC-17 (15000T) can handle this'})
    
    # Rule 2: Lift item specific
    if lift_item == 'Personnel Access Work':
        recommendations = [{'type': 'MEWP (Boom Lift/Scissor Lift)', 'reason': 'Personnel access requires MEWP, not crane'}]
    elif lift_item in ['Hull Block Section', 'Mega Block Section', 'Offshore Platform Topside']:
        if load_weight > 200:
            recommendations = [{'type': 'Goliath Gantry Crane', 'reason': f'Heavy module ({lift_item}) requires Goliath Gantry'}]
    elif lift_item in ['Steel Plates', 'Pipe Bundles', 'Welding Materials', 'PPE Supplies']:
        if load_weight <= 25:
            recommendations = [{'type': 'Forklift (Heavy Duty)', 'reason': f'Material handling ({lift_item}) - forklift sufficient'}]
    
    return recommendations

def find_best_dates(equipment_type, preferred_date, days_range=7):
    """Find available dates near preferred date"""
    preferred = pd.to_datetime(preferred_date)
    available_dates = []
    
    for i in range(-days_range, days_range + 1):
        check_date = preferred + timedelta(days=i)
        if check_date.weekday() < 6:  # Skip Sundays
            available, unavailable = get_available_equipment(equipment_type, check_date, service, bookings)
            if available:
                available_dates.append({
                    'date': check_date,
                    'available_units': len(available),
                    'equipment_ids': available[:5],
                    'days_from_preferred': abs(i)
                })
    
    # Sort by closest to preferred date, then by most available units
    available_dates.sort(key=lambda x: (x['days_from_preferred'], -x['available_units']))
    return available_dates[:5]

# ============================================================
# PAGE: DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.title("📊 Equipment Booking Dashboard")
    st.markdown("---")
    
    # KPI Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Bookings", len(bookings))
    with col2:
        st.metric("Confirmed", len(bookings[bookings['Status'] == 'Confirmed']))
    with col3:
        st.metric("Completed", len(bookings[bookings['Status'] == 'Completed']))
    with col4:
        st.metric("Cancelled/Rejected", len(bookings[bookings['Status'].isin(['Cancelled', 'Rejected'])]))
    with col5:
        avg_util = bookings['Crane_Utilization_Pct'].mean()
        st.metric("Avg Utilization", f"{avg_util:.0f}%")
    
    st.markdown("---")
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Bookings by Status")
        status_counts = bookings['Status'].value_counts()
        st.bar_chart(status_counts)
    
    with col2:
        st.subheader("Bookings by Equipment Category")
        cat_counts = bookings['Equipment_Category'].value_counts()
        st.bar_chart(cat_counts)
    
    # Monthly trend
    st.subheader("Monthly Booking Trend")
    bookings['Month'] = bookings['Booking_Date'].dt.to_period('M').astype(str)
    monthly = bookings.groupby('Month').size()
    st.line_chart(monthly)
    
    # Recent bookings table
    st.subheader("Recent Bookings")
    recent = bookings.sort_values('Request_Date', ascending=False).head(20)
    display_cols = ['Booking_ID', 'Booking_Date', 'Equipment_Type', 'Equipment_ID', 'Location', 'Status', 'Priority']
    st.dataframe(recent[display_cols], use_container_width=True)

# ============================================================
# PAGE: NEW BOOKING
# ============================================================
elif page == "📝 New Booking":
    st.title("📝 Create New Booking")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Booking Details")
        equipment_category = st.selectbox("Equipment Category", ['Crane', 'MEWP', 'Cometto', 'Forklift'])
        
        if equipment_category == 'Crane':
            equipment_type = st.selectbox("Equipment Type", ['Level Luffing Crane', 'Goliath Gantry Crane', 'Crawler Crane', 'Mobile Crane', 'Tower Crane', 'Workshop Crane'])
        elif equipment_category == 'MEWP':
            equipment_type = st.selectbox("Equipment Type", ['Scissor Lift 10m', 'Boom Lift 20m', 'Articulating Boom Lift 26m', 'Telescopic Boom Lift 30m'])
        elif equipment_category == 'Cometto':
            equipment_type = st.selectbox("Equipment Type", ['Cometto MSPE 8 Axle Lines', 'Cometto Eco500 12 Axle Lines', 'SPMT 16 Axle Lines', 'SPMT 24 Axle Lines'])
        else:
            equipment_type = st.selectbox("Equipment Type", ['Counterbalance Forklift', 'Heavy Duty Forklift', 'Telehandler Forklift', 'Reach Forklift'])
        
        booking_date = st.date_input("Preferred Booking Date", min_value=datetime(2026, 1, 1))
        location = st.selectbox("Location", sorted(bookings['Location'].dropna().unique().tolist()))
        
    with col2:
        st.subheader("Job Details")
        lift_item = st.selectbox("Lift Item", sorted(bookings['Lift_Item'].dropna().unique().tolist()))
        load_weight = st.number_input("Load Weight (Tonnes)", min_value=0.5, max_value=15000.0, value=50.0)
        duration = st.selectbox("Duration", ['Half Day (AM)', 'Half Day (PM)', 'Full Day', '2 Days', '3 Days', '5 Days', '7 Days', '10 Days', '14 Days'])
        shift = st.selectbox("Shift", ['Day Shift (0700-1900)', 'Night Shift (1900-0700)'])
        priority = st.selectbox("Priority", ['Low', 'Medium', 'High', 'Urgent'])
        project = st.selectbox("Project", ['A', 'B', 'C', 'D', 'E', 'F'])
        phase = st.selectbox("Project Phase", ['Planning', 'Fabrication', 'Assembly', 'Outfitting', 'Testing', 'Commissioning'])
    
    st.markdown("---")
    
    if st.button("🔍 Check Availability & Submit", type="primary"):
        available, unavailable = get_available_equipment(equipment_type, booking_date, service, bookings)
        
        if available:
            st.success(f"✅ **{len(available)} unit(s) available** on {booking_date}")
            st.write(f"**Available Equipment:** {', '.join(available[:10])}")
            
            # Check for service conflicts
            service_on_date = service[
                (service['Service_Date'] == pd.to_datetime(booking_date)) & 
                (service['Equipment_Type'] == equipment_type)
            ]
            if not service_on_date.empty:
                st.warning(f"⚠️ Note: {len(service_on_date)} unit(s) of this type are under maintenance on this date: {', '.join(service_on_date['Equipment_ID'].tolist())}")
            
            st.info(f"📋 Booking would be assigned to: **{available[0]}**")
        else:
            st.error(f"❌ **No {equipment_type} available** on {booking_date}")
            st.write("**Reason:** All units are either under maintenance or already booked.")
            
            # Suggest alternative dates
            st.subheader("📅 Suggested Alternative Dates:")
            alt_dates = find_best_dates(equipment_type, booking_date)
            if alt_dates:
                for alt in alt_dates:
                    st.write(f"• **{alt['date'].strftime('%Y-%m-%d')}** ({alt['date'].strftime('%A')}) — {alt['available_units']} unit(s) available")
            else:
                st.write("No alternatives found within ±7 days. Try a different equipment type.")

# ============================================================
# PAGE: AI RECOMMENDATION
# ============================================================
elif page == "🤖 AI Recommendation":
    st.title("🤖 AI Equipment Recommendation")
    st.markdown("*Tell me what you need to do, and I'll suggest the best equipment and date.*")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("What do you need?")
        load_weight = st.number_input("Load Weight (Tonnes)", min_value=0.1, max_value=15000.0, value=50.0, key="ai_load")
        lift_item = st.selectbox("What are you lifting/moving?", 
                                 ['Hull Block Section', 'Engine Module', 'Structural Steel Module', 'Mega Block Section',
                                  'Accommodation Module', 'Pipe Spool', 'Anchor Chain', 'Mooring Winch',
                                  'Transformer Unit', 'Construction Materials', 'Workshop Equipment', 'Turret Assembly',
                                  'Helideck Module', 'Flare Tower Section', 'Riser Assembly', 'Personnel Access Work',
                                  'Steel Plates', 'Pipe Bundles', 'Safety Equipment', 'Insulation Materials',
                                  'Welding Materials', 'PPE Supplies', 'Offshore Platform Topside', 'Jacket Structure'],
                                 key="ai_lift")
        location = st.selectbox("Where?", sorted(bookings['Location'].dropna().unique().tolist()), key="ai_loc")
        preferred_date = st.date_input("When do you need it?", min_value=datetime(2026, 1, 1), key="ai_date")
        project_phase = st.selectbox("Project Phase", ['Planning', 'Fabrication', 'Assembly', 'Outfitting', 'Testing', 'Commissioning'], key="ai_phase")
    
    with col2:
        st.subheader("🎯 AI Recommendations")
        
        if st.button("Get AI Recommendation", type="primary"):
            recommendations = recommend_equipment(load_weight, location, lift_item, project_phase)
            
            if recommendations:
                for i, rec in enumerate(recommendations):
                    if i == 0:
                        st.success(f"**✅ Best Match: {rec['type']}**")
                        st.write(f"   Reason: {rec['reason']}")
                        
                        # Find available dates for top recommendation
                        type_mapping = {
                            'Level Luffing Crane': 'Level Luffing Crane',
                            'Goliath Gantry Crane': 'Goliath Gantry Crane',
                            'Crawler Crane': 'Crawler Crane',
                            'Mobile Crane': 'Mobile Crane',
                            'Tower Crane': 'Tower Crane',
                            'Workshop Crane': 'Workshop Crane',
                        }
                        
                        if rec['type'] in type_mapping:
                            eq_type = type_mapping[rec['type']]
                            available, unavailable = get_available_equipment(eq_type, preferred_date, service, bookings)
                            
                            if available:
                                st.write(f"   📅 **Available on {preferred_date}:** {', '.join(available[:5])}")
                            else:
                                st.warning(f"   ⚠️ Not available on {preferred_date}. Checking alternatives...")
                                alt_dates = find_best_dates(eq_type, preferred_date, 5)
                                if alt_dates:
                                    st.write("   **Suggested dates:**")
                                    for alt in alt_dates[:3]:
                                        st.write(f"   • {alt['date'].strftime('%Y-%m-%d')} ({alt['available_units']} units free)")
                    else:
                        st.info(f"**💡 Alternative {i}: {rec['type']}**")
                        st.write(f"   Reason: {rec['reason']}")
            
            # Safety check
            st.markdown("---")
            st.subheader("⚡ Safety Assessment")
            if load_weight > 200:
                st.warning("🔶 Heavy lift (>200T) — Requires Heavy Lift Specialist certification + Lifting Supervisor")
            if lift_item in ['Offshore Platform Topside', 'Mega Block Section', 'Jacket Structure']:
                st.warning("🔶 Critical lift item — Requires detailed lift plan and safety review")
            else:
                st.success("✅ Standard lift — Normal safety protocols apply")

# ============================================================
# PAGE: CONFLICT ALERTS
# ============================================================
elif page == "⚠️ Conflict Alerts":
    st.title("⚠️ Booking & Service Conflict Alerts")
    st.markdown("---")
    
    # Find conflicts: bookings on service dates
    st.subheader("🔴 Active Conflicts (Bookings on Maintenance Days)")
    
    conflicts = []
    confirmed_bookings = bookings[bookings['Status'].isin(['Confirmed', 'Pending'])]
    
    for _, booking in confirmed_bookings.iterrows():
        service_match = service[
            (service['Service_Date'] == booking['Booking_Date']) & 
            (service['Equipment_ID'] == booking['Equipment_ID'])
        ]
        if not service_match.empty:
            conflicts.append({
                'Booking_ID': booking['Booking_ID'],
                'Equipment_ID': booking['Equipment_ID'],
                'Equipment_Type': booking['Equipment_Type'],
                'Booking_Date': booking['Booking_Date'].strftime('%Y-%m-%d'),
                'Service_Type': service_match.iloc[0]['Service_Type'],
                'Status': booking['Status'],
                'Priority': booking['Priority'],
                'Conflict': '🔴 MAINTENANCE CONFLICT'
            })
    
    if conflicts:
        conflict_df = pd.DataFrame(conflicts)
        st.error(f"Found **{len(conflicts)} conflict(s)** — Bookings scheduled on maintenance days!")
        st.dataframe(conflict_df, use_container_width=True)
    else:
        st.success("✅ No active conflicts found!")
    
    st.markdown("---")
    
    # Upcoming maintenance that may affect bookings
    st.subheader("🟡 Upcoming Maintenance (Next 14 Days)")
    today = pd.to_datetime('2026-07-31')
    upcoming_service = service[
        (service['Service_Date'] >= today) & 
        (service['Service_Date'] <= today + timedelta(days=14))
    ].sort_values('Service_Date')
    
    if not upcoming_service.empty:
        st.write(f"**{len(upcoming_service)} maintenance events** in the next 14 days:")
        display_cols = ['Equipment_ID', 'Equipment_Type', 'Location', 'Service_Date', 'Service_Type', 'Service_Duration_Hours']
        st.dataframe(upcoming_service[display_cols].head(30), use_container_width=True)
    else:
        st.info("No upcoming maintenance in the next 14 days.")
    
    st.markdown("---")
    
    # High utilization warnings
    st.subheader("🟠 High Utilization Warnings (>90%)")
    high_util = bookings[
        (bookings['Crane_Utilization_Pct'] > 90) & 
        (bookings['Status'].isin(['Confirmed', 'Pending']))
    ][['Booking_ID', 'Equipment_ID', 'Equipment_Type', 'Booking_Date', 'Crane_Utilization_Pct', 'Priority']]
    
    if not high_util.empty:
        st.warning(f"**{len(high_util)} bookings** with utilization >90% — risk of overloading schedule")
        st.dataframe(high_util.head(20), use_container_width=True)
    else:
        st.success("✅ No high utilization warnings.")
    
    # Rejection analysis
    st.markdown("---")
    st.subheader("📊 Rejection & Cancellation Reasons")
    rejected = bookings[bookings['Status'].isin(['Rejected', 'Cancelled', 'Rescheduled'])]
    reason_counts = rejected['Status_Reason'].value_counts().head(10)
    st.bar_chart(reason_counts)

# ============================================================
# PAGE: SERVICE SCHEDULE
# ============================================================
elif page == "📅 Service Schedule":
    st.title("📅 Equipment Service Schedule 2026")
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        cat_filter = st.selectbox("Equipment Category", ['All'] + sorted(service['Equipment_Category'].unique().tolist()))
    with col2:
        type_filter = st.selectbox("Equipment Type", ['All'] + sorted(service['Equipment_Type'].unique().tolist()))
    with col3:
        status_filter = st.selectbox("Service Status", ['All', 'Completed', 'Scheduled'])
    
    # Apply filters
    filtered = service.copy()
    if cat_filter != 'All':
        filtered = filtered[filtered['Equipment_Category'] == cat_filter]
    if type_filter != 'All':
        filtered = filtered[filtered['Equipment_Type'] == type_filter]
    if status_filter != 'All':
        filtered = filtered[filtered['Service_Status'] == status_filter]
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Services", len(filtered))
    with col2:
        st.metric("Completed", len(filtered[filtered['Service_Status'] == 'Completed']))
    with col3:
        st.metric("Scheduled", len(filtered[filtered['Service_Status'] == 'Scheduled']))
    with col4:
        st.metric("Equipment Units", filtered['Equipment_ID'].nunique())
    
    st.markdown("---")
    st.dataframe(filtered, use_container_width=True)

# ============================================================
# FOOTER
# ============================================================
st.sidebar.markdown("---")
st.sidebar.caption("v1.0 | AI-Powered Equipment Booking System")
st.sidebar.caption("© 2026 Seatrium YOS")

