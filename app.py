
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Equipment Booking AI - Conflict Resolution",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .score-win {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .score-lose {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

DURATION_MAP = {
    'Half Day (AM)': 0.5,
    'Half Day (PM)': 0.5,
    'Full Day': 1,
    '2 Days': 2,
    '3 Days': 3,
    '5 Days': 5,
    '7 Days': 7,
    '10 Days': 10,
    '14 Days': 14,
}

PRIORITY_SCORES = {"Low": 1, "Medium": 2, "High": 3, "Urgent": 4}

PHASE_SCORES = {
    'Commissioning': 5,
    'Testing': 4,
    'Assembly': 3,
    'Fabrication': 2,
    'Planning': 1,
    'Outfitting': 1,
}


@st.cache_data
def load_data():
    """Load the equipment bookings dataset."""
    df = pd.read_excel('Equipment_Bookings_AI_Training.xlsx', engine='openpyxl')
    return df


def calculate_end_date(booking_date, duration):
    """Calculate end date based on booking date and duration."""
    days = DURATION_MAP.get(duration, 1)
    if days >= 1:
        return booking_date + timedelta(days=int(days) - 1)
    return booking_date


def suggest_equipment(df, category, load_weight):
    """Suggest equipment type and unit based on category and load weight."""
    available = df[df['Equipment_Category'] == category].copy()

    if 'Ton_Capacity' in available.columns and load_weight > 0:
        suitable = available[available['Ton_Capacity'] >= load_weight * 1.2]
        if suitable.empty:
            suitable = available[available['Ton_Capacity'] >= load_weight]
        if suitable.empty:
            suitable = available
    else:
        suitable = available

    suggested_types = sorted(suitable['Equipment_Type'].unique().tolist())
    return suitable, suggested_types


def detect_conflicts(df, new_booking):
    """Detect conflicts between a new booking and existing bookings."""
    new_start = pd.to_datetime(new_booking['Booking_Date'])
    new_end = calculate_end_date(new_start, new_booking['Duration'])
    new_equipment = new_booking['Equipment_ID']
    new_shift = new_booking['Shift']

    same_equipment = df[
        (df['Equipment_ID'] == new_equipment) &
        (df['Shift'] == new_shift) &
        (df['Status'].isin(['Confirmed', 'Pending', 'Completed']))
    ].copy()

    if same_equipment.empty:
        return pd.DataFrame(), False

    same_equipment['Booking_Date_dt'] = pd.to_datetime(same_equipment['Booking_Date'])
    same_equipment['End_Date_dt'] = same_equipment.apply(
        lambda row: calculate_end_date(row['Booking_Date_dt'], row['Duration']), axis=1
    )

    conflicts = same_equipment[
        (same_equipment['Booking_Date_dt'] <= new_end) &
        (same_equipment['End_Date_dt'] >= new_start)
    ]

    return conflicts, len(conflicts) > 0


# ============================================================
# AI PRIORITY SCORE SYSTEM
# ============================================================

def calculate_ai_priority_score(booking, df, equipment_info):
    """
    Calculate composite AI Priority Score (5-25).
    Score = Project Criticality + Schedule Impact + Urgency + Equipment Suitability + Location Efficiency
    """
    score_breakdown = {}

    # --- 1. PROJECT CRITICALITY (1-5) ---
    phase = booking.get('Project_Phase', 'Fabrication')
    project_criticality = PHASE_SCORES.get(phase, 2)
    score_breakdown['Project Criticality'] = {
        'score': project_criticality,
        'max': 5,
        'reason': f"{phase} phase"
    }

    # --- 2. SCHEDULE IMPACT (1-5) ---
    lead_time = (pd.to_datetime(booking['Booking_Date']) - pd.to_datetime(booking['Request_Date'])).days

    if lead_time <= 1:
        schedule_impact = 5
    elif lead_time <= 3:
        schedule_impact = 4
    elif lead_time <= 5:
        schedule_impact = 3
    elif lead_time <= 9:
        schedule_impact = 2
    else:
        schedule_impact = 1

    if booking.get('Rescheduled', False):
        schedule_impact = min(5, schedule_impact + 1)

    score_breakdown['Schedule Impact'] = {
        'score': schedule_impact,
        'max': 5,
        'reason': f"Lead time: {lead_time} days"
    }

    # --- 3. URGENCY (1-5) ---
    priority = booking.get('Priority', 'Medium')
    urgency_map = {'Urgent': 5, 'High': 4, 'Medium': 3, 'Low': 2}
    urgency = urgency_map.get(priority, 3)

    if priority == 'Low' and lead_time > 10:
        urgency = 1

    score_breakdown['Urgency'] = {
        'score': urgency,
        'max': 5,
        'reason': f"{priority} priority"
    }

    # --- 4. EQUIPMENT SUITABILITY (1-5) ---
    load_weight = booking.get('Load_Weight', 0)
    equipment_capacity = 100
    if isinstance(equipment_info, pd.Series) and 'Ton_Capacity' in equipment_info.index:
        equipment_capacity = equipment_info.get('Ton_Capacity', 100)
    elif isinstance(equipment_info, dict):
        equipment_capacity = equipment_info.get('Ton_Capacity', 100)

    equipment_type = booking.get('Equipment_Type', '')
    available_units = df[df['Equipment_Type'] == equipment_type]['Equipment_ID'].nunique()

    if available_units <= 1:
        equipment_suitability = 5
    elif equipment_capacity > 0 and load_weight > 0:
        utilization_ratio = load_weight / equipment_capacity
        if utilization_ratio >= 0.8:
            equipment_suitability = 5
        elif utilization_ratio >= 0.6:
            equipment_suitability = 4
        elif utilization_ratio >= 0.4:
            equipment_suitability = 3
        elif utilization_ratio >= 0.2:
            equipment_suitability = 2
        else:
            equipment_suitability = 1
    else:
        equipment_suitability = 3

    pct = (load_weight / max(equipment_capacity, 1)) * 100
    score_breakdown['Equipment Suitability'] = {
        'score': equipment_suitability,
        'max': 5,
        'reason': f"{load_weight}T on {equipment_capacity}T capacity ({pct:.0f}%)"
    }

    # --- 5. LOCATION EFFICIENCY (1-5) ---
    booking_location = booking.get('Location', '')
    equipment_id = booking.get('Equipment_ID', '')

    recent_bookings = df[
        (df['Equipment_ID'] == equipment_id) &
        (pd.to_datetime(df['Booking_Date']) < pd.to_datetime(booking['Booking_Date']))
    ].sort_values('Booking_Date', ascending=False)

    if not recent_bookings.empty:
        last_location = recent_bookings.iloc[0]['Location']
        if last_location == booking_location:
            location_efficiency = 5
            loc_reason = f"Equipment already at {booking_location}"
        elif str(last_location).split(' ')[0] == str(booking_location).split(' ')[0]:
            location_efficiency = 4
            loc_reason = f"Equipment nearby ({last_location} → {booking_location})"
        else:
            location_efficiency = 2
            loc_reason = f"Equipment at {last_location}, needs relocation to {booking_location}"
    else:
        location_efficiency = 3
        loc_reason = f"No prior location data"

    score_breakdown['Location Efficiency'] = {
        'score': location_efficiency,
        'max': 5,
        'reason': loc_reason
    }

    # --- TOTAL ---
    total_score = (project_criticality + schedule_impact + urgency +
                   equipment_suitability + location_efficiency)

    return total_score, score_breakdown


def resolve_conflict_ai(new_booking, conflicts, df):
    """Resolve conflict using composite AI Priority Score."""
    eq_rows = df[df['Equipment_ID'] == new_booking['Equipment_ID']]
    eq_info_new = eq_rows.iloc[0] if len(eq_rows) > 0 else {}

    new_score, new_breakdown = calculate_ai_priority_score(new_booking, df, eq_info_new)

    results = []

    for _, conflict in conflicts.iterrows():
        conflict_booking = {
            'Request_Date': conflict['Request_Date'],
            'Booking_Date': conflict['Booking_Date'],
            'Priority': conflict['Priority'],
            'Equipment_Type': conflict['Equipment_Type'],
            'Equipment_ID': conflict['Equipment_ID'],
            'Location': conflict['Location'],
            'Load_Weight': conflict.get('Load_Weight', 10),
            'Project_Phase': conflict.get('Project_Phase', 'Fabrication'),
            'Rescheduled': conflict.get('Rescheduled', False),
        }

        eq_rows_c = df[df['Equipment_ID'] == conflict['Equipment_ID']]
        eq_info_conflict = eq_rows_c.iloc[0] if len(eq_rows_c) > 0 else {}

        conflict_score, conflict_breakdown = calculate_ai_priority_score(conflict_booking, df, eq_info_conflict)

        if new_score > conflict_score:
            resolution = f"Your booking ({new_score}/25) beats existing ({conflict_score}/25)"
            new_wins = True
        elif new_score < conflict_score:
            resolution = f"Existing ({conflict_score}/25) beats your booking ({new_score}/25)"
            new_wins = False
        else:
            if pd.to_datetime(new_booking['Request_Date']) <= pd.to_datetime(conflict['Request_Date']):
                resolution = f"TIED ({new_score}/25) — First-Come-First-Served: You requested first"
                new_wins = True
            else:
                resolution = f"TIED ({conflict_score}/25) — First-Come-First-Served: Existing requested first"
                new_wins = False

        results.append({
            'Conflicting_Booking': conflict['Booking_ID'],
            'Your_Score': new_score,
            'Existing_Score': conflict_score,
            'Conflict_Priority': conflict['Priority'],
            'Conflict_Project': conflict.get('Project', 'N/A'),
            'Conflict_Lift_Item': conflict.get('Lift_Item', 'N/A'),
            'Resolution': resolution,
            'New_Booking_Wins': new_wins,
            'Conflict_Breakdown': conflict_breakdown,
        })

    return pd.DataFrame(results), new_score, new_breakdown


def display_score_breakdown(label, score, breakdown):
    """Display a visual score breakdown card."""
    st.markdown(f"#### {label} — Score: **{score}/25**")

    for factor, details in breakdown.items():
        col_a, col_b, col_c = st.columns([2, 3, 3])
        with col_a:
            st.markdown(f"**{factor}**")
        with col_b:
            st.progress(details['score'] / details['max'])
        with col_c:
            st.markdown(f"**{details['score']}/{details['max']}** — {details['reason']}")


@st.cache_resource
def train_model(df):
    """Train ML model for conflict resolution prediction."""
    df_model = df.copy()
    df_model['Priority_Score'] = df_model['Priority'].map(PRIORITY_SCORES)
    df_model['Duration_Days'] = df_model['Duration'].map(DURATION_MAP)
    df_model['Request_Date_dt'] = pd.to_datetime(df_model['Request_Date'])
    df_model['Booking_Date_dt'] = pd.to_datetime(df_model['Booking_Date'])
    df_model['Lead_Time'] = (df_model['Booking_Date_dt'] - df_model['Request_Date_dt']).dt.days

    le_equipment_cat = LabelEncoder()
    le_equipment_type = LabelEncoder()
    le_shift = LabelEncoder()
    le_project = LabelEncoder()
    le_weather = LabelEncoder()

    df_model['Equipment_Category_Enc'] = le_equipment_cat.fit_transform(df_model['Equipment_Category'].astype(str))
    df_model['Equipment_Type_Enc'] = le_equipment_type.fit_transform(df_model['Equipment_Type'].astype(str))
    df_model['Shift_Enc'] = le_shift.fit_transform(df_model['Shift'].astype(str))
    df_model['Project_Enc'] = le_project.fit_transform(df_model['Project'].astype(str))
    df_model['Weather_Enc'] = le_weather.fit_transform(df_model['Weather_Condition'].astype(str))

    if 'Wins_Equipment' in df_model.columns:
        df_model['Target'] = (df_model['Wins_Equipment'] == 'Yes').astype(int)
    else:
        df_model['Target'] = 1

    features = ['Priority_Score', 'Duration_Days', 'Lead_Time',
                'Equipment_Category_Enc', 'Equipment_Type_Enc',
                'Shift_Enc', 'Project_Enc', 'Weather_Enc',
                'Wind_Speed_Knots', 'Crane_Utilization_Pct']

    X = df_model[features].fillna(0)
    y = df_model['Target']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    encoders = {
        'equipment_cat': le_equipment_cat,
        'equipment_type': le_equipment_type,
        'shift': le_shift,
        'project': le_project,
        'weather': le_weather,
    }

    return model, encoders, accuracy, features, classification_report(y_test, y_pred, output_dict=True)


# ============================================================
# MAIN APP
# ============================================================

st.markdown('<div class="main-header">🏗️ Equipment Booking AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Intelligent Conflict Detection & Resolution System for Shipyard Operations</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🏗️ Navigation")
    st.markdown("---")

    page = st.radio(
        "Select Module",
        ["📊 Dashboard", "📋 Booking Manager", "🤖 Booking", "📈 Analytics"],
        index=0
    )

    st.markdown("---")
    st.markdown("### System Info")
    st.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
    st.info("🔄 Model: Gradient Boosting")

# Load data
try:
    df = load_data()
    st.sidebar.success(f"📦 Loaded: {len(df)} bookings")
except Exception as e:
    st.error(f"⚠️ Error loading data: {e}")
    st.info("Please ensure 'Equipment_Bookings_AI_Training.xlsx' is in the repo root.")
    st.stop()

# Load AI model
with st.sidebar:
    try:
        model, encoders, accuracy, features, report = train_model(df)
        st.success(f"🤖 AI Model: {accuracy*100:.1f}% accuracy")
    except Exception as e:
        model = None
        st.warning("⚠️ AI model unavailable")


# ============================================================
# PAGE: DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.header("📊 Operations Dashboard")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Bookings", len(df))
    with col2:
        if 'Has_Conflict' in df.columns:
            conflict_count = len(df[df['Has_Conflict'] == 'Yes'])
        else:
            conflict_count = "N/A"
        st.metric("Conflicts", conflict_count)
    with col3:
        st.metric("Equipment Units", df['Equipment_ID'].nunique())
    with col4:
        st.metric("Projects", df['Project'].nunique())
    with col5:
        completion_rate = len(df[df['Status'] == 'Completed']) / len(df) * 100
        st.metric("Completion Rate", f"{completion_rate:.1f}%")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Bookings by Equipment Category")
        st.bar_chart(df['Equipment_Category'].value_counts())

    with col2:
        st.subheader("Bookings by Priority")
        st.bar_chart(df['Priority'].value_counts())

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Status Distribution")
        st.bar_chart(df['Status'].value_counts())

    with col2:
        st.subheader("Bookings by Project")
        st.bar_chart(df['Project'].value_counts())

    if 'Conflict_Resolution' in df.columns:
        st.markdown("---")
        st.subheader("⚠️ Conflict Resolution Summary")
        resolution_counts = df[df['Conflict_Resolution'] != 'No Conflict']['Conflict_Resolution'].value_counts()
        if not resolution_counts.empty:
            st.dataframe(resolution_counts.reset_index().rename(
                columns={'Conflict_Resolution': 'Resolution Method', 'count': 'Count'}
            ), use_container_width=True)


# ============================================================
# PAGE: BOOKING MANAGER
# ============================================================
elif page == "📋 Booking Manager":
    st.header("📋 Booking Manager")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filter_category = st.multiselect("Equipment Category", sorted(df['Equipment_Category'].unique()))
    with col2:
        filter_project = st.multiselect("Project", sorted(df['Project'].unique()))
    with col3:
        filter_priority = st.multiselect("Priority", ['Low', 'Medium', 'High', 'Urgent'])
    with col4:
        filter_status = st.multiselect("Status", sorted(df['Status'].unique()))

    filtered_df = df.copy()
    if filter_category:
        filtered_df = filtered_df[filtered_df['Equipment_Category'].isin(filter_category)]
    if filter_project:
        filtered_df = filtered_df[filtered_df['Project'].isin(filter_project)]
    if filter_priority:
        filtered_df = filtered_df[filtered_df['Priority'].isin(filter_priority)]
    if filter_status:
        filtered_df = filtered_df[filtered_df['Status'].isin(filter_status)]

    st.markdown(f"**Showing {len(filtered_df)} of {len(df)} bookings**")

    display_cols = ['Booking_ID', 'Booking_Date', 'Equipment_Category', 'Equipment_Type',
                    'Equipment_ID', 'Location', 'Project', 'Lift_Item', 'Duration',
                    'Priority', 'Status']
    if 'Has_Conflict' in filtered_df.columns:
        display_cols.extend(['Has_Conflict', 'Conflict_Resolution', 'Wins_Equipment'])

    available_cols = [c for c in display_cols if c in filtered_df.columns]
    st.dataframe(filtered_df[available_cols], use_container_width=True, height=500)


# ============================================================
# PAGE: BOOKING (UNIFIED WITH AI PRIORITY SCORE)
# ============================================================
elif page == "🤖 Booking":
    st.header("🤖 Equipment Booking")
    st.markdown("Submit a booking request. AI will suggest equipment, detect conflicts, and evaluate priority using a **5-factor scoring system**.")

    st.markdown("---")

    # --- BOOKING FORM ---
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 Booking Details")

        book_request_date = st.date_input("Request Date", datetime.now(), key='book_req')
        book_booking_date = st.date_input("Booking Date", datetime.now() + timedelta(days=3), key='book_date')

        book_project = st.selectbox("Project", sorted(df['Project'].unique()), key='book_proj')

        # Project Phase
        phases = list(PHASE_SCORES.keys())
        book_phase = st.selectbox("Project Phase", phases, key='book_phase')

        book_lift_item = st.text_input("Lift Item / Description", "Steel Block Section", key='book_lift')
        book_load_weight = st.number_input("Load Weight (Tonnes)", min_value=0.1, max_value=500.0, value=10.0, step=0.5, key='book_weight')

        book_category = st.selectbox("Equipment Category", sorted(df['Equipment_Category'].unique()), key='book_cat')

        # AI suggests equipment based on category and weight
        suitable_df, suggested_types = suggest_equipment(df, book_category, book_load_weight)

        if suggested_types:
            st.markdown("💡 *AI Suggested equipment based on your load weight:*")
            book_type = st.selectbox("Equipment Type (AI Suggested)", suggested_types, key='book_type')

            suggested_units = sorted(suitable_df[suitable_df['Equipment_Type'] == book_type]['Equipment_ID'].unique().tolist())
            if suggested_units:
                unit_capacities = suitable_df[suitable_df['Equipment_Type'] == book_type][['Equipment_ID', 'Ton_Capacity']].drop_duplicates()
                unit_options = []
                for _, row in unit_capacities.iterrows():
                    cap = f" ({row['Ton_Capacity']}T)" if pd.notna(row['Ton_Capacity']) else ""
                    unit_options.append(f"{row['Equipment_ID']}{cap}")

                book_unit_display = st.selectbox("Equipment Unit (AI Suggested)", unit_options, key='book_unit')
                book_id = book_unit_display.split(" (")[0]
            else:
                book_id = st.selectbox("Equipment Unit", sorted(df[df['Equipment_Type'] == book_type]['Equipment_ID'].unique()), key='book_unit2')
        else:
            st.warning("⚠️ No suitable equipment found for this weight. Showing all options.")
            all_types = sorted(df[df['Equipment_Category'] == book_category]['Equipment_Type'].unique())
            book_type = st.selectbox("Equipment Type", all_types, key='book_type_all')
            book_id = st.selectbox("Equipment Unit", sorted(df[df['Equipment_Type'] == book_type]['Equipment_ID'].unique()), key='book_unit_all')

        book_duration = st.selectbox("Duration", list(DURATION_MAP.keys()), key='book_dur')
        book_priority = st.selectbox("Priority", ['Low', 'Medium', 'High', 'Urgent'], key='book_pri')

        book_locations = sorted(df['Location'].unique().tolist())
        book_location = st.selectbox("Location", book_locations, key='book_loc')

    with col2:
        st.subheader("🤖 AI Evaluation")

        if st.button("📋 Submit Booking Request", type="primary", use_container_width=True):
            # Build booking object
            new_booking = {
                'Request_Date': book_request_date,
                'Booking_Date': book_booking_date,
                'Equipment_Category': book_category,
                'Equipment_Type': book_type,
                'Equipment_ID': book_id,
                'Duration': book_duration,
                'Shift': 'Day Shift (0700-1900)',
                'Priority': book_priority,
                'Project': book_project,
                'Project_Phase': book_phase,
                'Location': book_location,
                'Lift_Item': book_lift_item,
                'Load_Weight': book_load_weight,
                'Rescheduled': False,
                'Status': 'Confirmed',
            }

            lead_time = (pd.to_datetime(book_booking_date) - pd.to_datetime(book_request_date)).days

            # Booking Summary
            st.markdown("### 📋 Booking Summary")
            summary = {
                'Field': ['Project', 'Phase', 'Lift Item', 'Load Weight', 'Equipment', 'Unit ID',
                          'Booking Date', 'Duration', 'Priority', 'Location', 'Lead Time'],
                'Value': [book_project, book_phase, book_lift_item, f"{book_load_weight} T",
                          book_type, book_id, str(book_booking_date), book_duration,
                          book_priority, book_location, f"{lead_time} days"]
            }
            st.table(pd.DataFrame(summary))

            st.markdown("---")

            # Check for conflicts
            conflicts, has_conflict = detect_conflicts(df, new_booking)

            if has_conflict:
                st.error(f"⚠️ **CONFLICT DETECTED** — {len(conflicts)} existing booking(s) overlap with your request.")

                # Show conflicting bookings
                st.markdown("### 📌 Existing Bookings in Conflict")
                conflict_display_cols = ['Booking_ID', 'Booking_Date', 'Duration', 'Priority', 'Project', 'Lift_Item']
                available_display = [c for c in conflict_display_cols if c in conflicts.columns]
                st.dataframe(conflicts[available_display], use_container_width=True)

                st.markdown("---")

                # AI Priority Score Evaluation
                st.markdown("### 🤖 AI Priority Score Evaluation")
                st.markdown("*Score = Project Criticality + Schedule Impact + Urgency + Equipment Suitability + Location Efficiency*")

                resolution_df, new_score, new_breakdown = resolve_conflict_ai(new_booking, conflicts, df)

                # Display YOUR score breakdown
                st.markdown("---")
                display_score_breakdown("📗 Your Booking", new_score, new_breakdown)

                # Display each conflict's score
                for _, res in resolution_df.iterrows():
                    st.markdown("---")
                    display_score_breakdown(
                        f"📕 Existing: {res['Conflicting_Booking']}",
                        res['Existing_Score'],
                        res['Conflict_Breakdown']
                    )

                # Final AI Decision
                st.markdown("---")
                st.markdown("### 🏆 AI Decision")

                for _, res in resolution_df.iterrows():
                    if res['New_Booking_Wins']:
                        st.markdown(
                            f'<div class="score-win">'
                            f'<h3>✅ YOUR BOOKING WINS</h3>'
                            f'<p>Score: {res["Your_Score"]}/25 vs {res["Existing_Score"]}/25</p>'
                            f'<p>{res["Resolution"]}</p>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="score-lose">'
                            f'<h3>❌ EXISTING BOOKING WINS</h3>'
                            f'<p>Score: {res["Existing_Score"]}/25 vs {res["Your_Score"]}/25</p>'
                            f'<p>{res["Resolution"]}</p>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                # Manager Override Section
                st.markdown("---")
                st.markdown("### 🔐 Manager Override")
                st.markdown("If this booking is critical, a Manager can override the AI decision regardless of score.")

                override_col1, override_col2 = st.columns(2)

                with override_col1:
                    manager_name = st.text_input("Manager Name (for approval)", key='mgr_name')
                    manager_reason = st.text_area("Override Reason", placeholder="e.g., Client deadline, safety requirement...", key='mgr_reason')

                with override_col2:
                    st.markdown("")
                    st.markdown("")
                    if st.button("✅ Manager Override — Approve My Booking", type="primary", use_container_width=True):
                        if manager_name and manager_reason:
                            st.success("✅ **MANAGER OVERRIDE APPROVED**")
                            st.markdown(f"**Approved by:** {manager_name}")
                            st.markdown(f"**Reason:** {manager_reason}")
                            st.markdown(f"Conflicting booking(s) will be rescheduled.")
                            st.balloons()
                        else:
                            st.error("⚠️ Please enter Manager Name and Override Reason.")

                    if st.button("❌ Accept AI Decision", use_container_width=True):
                        all_wins = resolution_df['New_Booking_Wins'].all()
                        if all_wins:
                            st.success("✅ **BOOKING CONFIRMED** — AI decision accepted.")
                        else:
                            st.info("📋 **BOOKING QUEUED** — You'll be notified when equipment becomes available.")
                            st.markdown("**💡 Suggestions:**")
                            st.markdown("- Try a different date")
                            st.markdown("- Select a different equipment unit")
                            st.markdown("- Increase priority level if task is urgent")

            else:
                # No conflict
                st.success("✅ **BOOKING APPROVED** — No conflicts detected!")
                st.markdown(f"Equipment **{book_id}** ({book_type}) is available for **{book_booking_date}**.")

                # Show AI score anyway
                eq_rows = df[df['Equipment_ID'] == book_id]
                eq_info = eq_rows.iloc[0] if len(eq_rows) > 0 else {}
                score, breakdown = calculate_ai_priority_score(new_booking, df, eq_info)

                st.markdown("---")
                display_score_breakdown("📗 Your Booking Score", score, breakdown)

                st.balloons()


# ============================================================
# PAGE: ANALYTICS
# ============================================================
elif page == "📈 Analytics":
    st.header("📈 Equipment Utilization Analytics")

    if 'Crane_Utilization_Pct' in df.columns:
        st.subheader("Equipment Utilization by Type")
        util_by_type = df.groupby('Equipment_Type')['Crane_Utilization_Pct'].mean().sort_values(ascending=False)
        st.bar_chart(util_by_type)

    st.markdown("---")

    if 'Has_Conflict' in df.columns:
        st.subheader("Conflicts by Equipment Type")
        conflict_by_type = df[df['Has_Conflict'] == 'Yes'].groupby('Equipment_Type').size().sort_values(ascending=False)
        if not conflict_by_type.empty:
            st.bar_chart(conflict_by_type)
        else:
            st.info("No conflicts recorded in the dataset.")

    st.markdown("---")

    st.subheader("Priority Distribution by Project")
    priority_project = pd.crosstab(df['Project'], df['Priority'])
    st.dataframe(priority_project, use_container_width=True)

    st.markdown("---")

    if 'Weather_Condition' in df.columns:
        st.subheader("Weather Impact on Operations")
        weather_status = pd.crosstab(df['Weather_Condition'], df['Status'])
        st.dataframe(weather_status, use_container_width=True)

    st.markdown("---")

    st.subheader("Booking Duration Distribution")
    duration_counts = df['Duration'].value_counts()
    st.bar_chart(duration_counts)


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(f"🏗️ Equipment Booking AI System | Shipyard Operations | Built with Streamlit | {datetime.now().strftime('%Y')}")

