
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
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
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .conflict-yes {
        background-color: #ffcccc;
        padding: 10px;
        border-radius: 5px;
    }
    .conflict-no {
        background-color: #ccffcc;
        padding: 10px;
        border-radius: 5px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Duration mapping
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


@st.cache_data
def load_data():
    """Load the equipment bookings dataset."""
    df = pd.read_excel('data/Equipment_Bookings_AI_Training.xlsx')
    return df


def calculate_end_date(booking_date, duration):
    """Calculate end date based on booking date and duration."""
    days = DURATION_MAP.get(duration, 1)
    if days >= 1:
        return booking_date + timedelta(days=int(days) - 1)
    return booking_date


def detect_conflicts(df, new_booking):
    """Detect conflicts between a new booking and existing bookings."""
    new_start = pd.to_datetime(new_booking['Booking_Date'])
    new_end = calculate_end_date(new_start, new_booking['Duration'])
    new_equipment = new_booking['Equipment_ID']
    new_shift = new_booking['Shift']
    
    # Filter for same equipment and shift
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
    
    # Check overlap
    conflicts = same_equipment[
        (same_equipment['Booking_Date_dt'] <= new_end) & 
        (same_equipment['End_Date_dt'] >= new_start)
    ]
    
    return conflicts, len(conflicts) > 0


def resolve_conflict(new_booking, conflicts):
    """Resolve conflict based on priority and FCFS rules."""
    new_priority = PRIORITY_SCORES.get(new_booking['Priority'], 2)
    new_request_date = pd.to_datetime(new_booking['Request_Date'])
    
    results = []
    
    for _, conflict in conflicts.iterrows():
        conflict_priority = PRIORITY_SCORES.get(conflict['Priority'], 2)
        conflict_request_date = pd.to_datetime(conflict['Request_Date'])
        
        if new_priority > conflict_priority:
            resolution = "Priority Override - New booking WINS"
            new_wins = True
        elif new_priority < conflict_priority:
            resolution = "Yielded to Higher Priority - Existing booking WINS"
            new_wins = False
        else:
            # Same priority - FCFS
            if new_request_date <= conflict_request_date:
                resolution = "First-Come-First-Served - New booking WINS"
                new_wins = True
            else:
                resolution = "First-Come-First-Served - Existing booking WINS"
                new_wins = False
        
        results.append({
            'Conflicting_Booking': conflict['Booking_ID'],
            'Conflict_Equipment': conflict['Equipment_ID'],
            'Conflict_Priority': conflict['Priority'],
            'Conflict_Request_Date': conflict['Request_Date'],
            'Conflict_Booking_Date': conflict['Booking_Date'],
            'Conflict_Duration': conflict['Duration'],
            'Resolution': resolution,
            'New_Booking_Wins': new_wins
        })
    
    return pd.DataFrame(results)


@st.cache_resource
def train_model(df):
    """Train ML model for conflict resolution prediction."""
    # Prepare features
    df_model = df.copy()
    df_model['Priority_Score'] = df_model['Priority'].map(PRIORITY_SCORES)
    df_model['Duration_Days'] = df_model['Duration'].map(DURATION_MAP)
    df_model['Request_Date_dt'] = pd.to_datetime(df_model['Request_Date'])
    df_model['Booking_Date_dt'] = pd.to_datetime(df_model['Booking_Date'])
    df_model['Lead_Time'] = (df_model['Booking_Date_dt'] - df_model['Request_Date_dt']).dt.days
    
    # Encode categorical variables
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
    
    # Target variable
    if 'Wins_Equipment' in df_model.columns:
        df_model['Target'] = (df_model['Wins_Equipment'] == 'Yes').astype(int)
    else:
        df_model['Target'] = 1  # Default
    
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
    st.image("https://img.icons8.com/color/96/crane.png", width=80)
    st.title("Navigation")
    st.markdown("---")
    
    page = st.radio(
        "Select Module",
        ["📊 Dashboard", "📋 Booking Manager", "⚠️ Conflict Detector", "🤖 AI Prediction", "📈 Analytics"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### System Info")
    st.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
    st.info("🔄 Model: Gradient Boosting")
    st.info("📦 Records: 1,230 bookings")

# Load data
try:
    df = load_data()
except:
    st.warning("⚠️ Data file not found. Please place 'Equipment_Bookings_AI_Training.xlsx' in the 'data/' folder.")
    st.stop()

# ============================================================
# PAGE: DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.header("📊 Operations Dashboard")
    
    # Key Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Bookings", len(df))
    with col2:
        conflict_count = len(df[df.get('Has_Conflict', pd.Series(['No']*len(df))) == 'Yes'])
        st.metric("Conflicts Detected", conflict_count)
    with col3:
        st.metric("Equipment Units", df['Equipment_ID'].nunique())
    with col4:
        st.metric("Active Projects", df['Project'].nunique())
    with col5:
        completion_rate = len(df[df['Status'] == 'Completed']) / len(df) * 100
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Bookings by Equipment Category")
        cat_counts = df['Equipment_Category'].value_counts()
        st.bar_chart(cat_counts)
    
    with col2:
        st.subheader("Bookings by Priority")
        priority_counts = df['Priority'].value_counts()
        st.bar_chart(priority_counts)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Status Distribution")
        status_counts = df['Status'].value_counts()
        st.bar_chart(status_counts)
    
    with col2:
        st.subheader("Bookings by Project")
        project_counts = df['Project'].value_counts()
        st.bar_chart(project_counts)
    
    # Conflict Resolution Summary
    if 'Conflict_Resolution' in df.columns:
        st.subheader("⚠️ Conflict Resolution Summary")
        resolution_counts = df['Conflict_Resolution'].value_counts()
        st.dataframe(resolution_counts.reset_index().rename(
            columns={'index': 'Resolution Method', 'Conflict_Resolution': 'Resolution Method', 'count': 'Count'}
        ), use_container_width=True)


# ============================================================
# PAGE: BOOKING MANAGER
# ============================================================
elif page == "📋 Booking Manager":
    st.header("📋 Booking Manager")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_category = st.multiselect("Equipment Category", df['Equipment_Category'].unique())
    with col2:
        filter_project = st.multiselect("Project", sorted(df['Project'].unique()))
    with col3:
        filter_priority = st.multiselect("Priority", ['Low', 'Medium', 'High', 'Urgent'])
    with col4:
        filter_status = st.multiselect("Status", df['Status'].unique())
    
    # Apply filters
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
    
    # Display columns
    display_cols = ['Booking_ID', 'Booking_Date', 'Equipment_Category', 'Equipment_Type', 
                    'Equipment_ID', 'Location', 'Project', 'Lift_Item', 'Duration', 
                    'Priority', 'Status']
    if 'Has_Conflict' in filtered_df.columns:
        display_cols.extend(['Has_Conflict', 'Conflict_Resolution', 'Wins_Equipment'])
    
    st.dataframe(filtered_df[display_cols], use_container_width=True, height=500)


# ============================================================
# PAGE: CONFLICT DETECTOR
# ============================================================
elif page == "⚠️ Conflict Detector":
    st.header("⚠️ Conflict Detection & Resolution")
    st.markdown("Submit a new booking request to check for scheduling conflicts.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 New Booking Request")
        
        new_request_date = st.date_input("Request Date", datetime.now())
        new_booking_date = st.date_input("Booking Date", datetime.now() + timedelta(days=3))
        
        equipment_categories = df['Equipment_Category'].unique().tolist()
        new_category = st.selectbox("Equipment Category", equipment_categories)
        
        # Filter equipment types based on category
        available_types = df[df['Equipment_Category'] == new_category]['Equipment_Type'].unique().tolist()
        new_type = st.selectbox("Equipment Type", available_types)
        
        # Filter equipment IDs based on type
        available_ids = df[df['Equipment_Type'] == new_type]['Equipment_ID'].unique().tolist()
        new_equipment_id = st.selectbox("Equipment Unit", available_ids)
        
        new_duration = st.selectbox("Duration", list(DURATION_MAP.keys()))
        new_shift = st.selectbox("Shift", ['Day Shift (0700-1900)', 'Night Shift (1900-0700)'])
        new_priority = st.selectbox("Priority", ['Low', 'Medium', 'High', 'Urgent'])
        new_project = st.selectbox("Project", sorted(df['Project'].unique().tolist()))
        
        # Location
        available_locations = df['Location'].unique().tolist()
        new_location = st.selectbox("Location", available_locations)
        
        new_lift_item = st.text_input("Lift Item", "Steel Block Section")
    
    with col2:
        st.subheader("🔍 Conflict Analysis")
        
        if st.button("🚀 Check for Conflicts", type="primary", use_container_width=True):
            new_booking = {
                'Request_Date': new_request_date,
                'Booking_Date': new_booking_date,
                'Equipment_Category': new_category,
                'Equipment_Type': new_type,
                'Equipment_ID': new_equipment_id,
                'Duration': new_duration,
                'Shift': new_shift,
                'Priority': new_priority,
                'Project': new_project,
                'Location': new_location,
                'Lift_Item': new_lift_item,
            }
            
            conflicts, has_conflict = detect_conflicts(df, new_booking)
            
            if has_conflict:
                st.error(f"⚠️ CONFLICT DETECTED! {len(conflicts)} overlapping booking(s) found.")
                
                # Show conflict details
                resolution_df = resolve_conflict(new_booking, conflicts)
                
                st.markdown("### Resolution Decision")
                
                for _, res in resolution_df.iterrows():
                    if res['New_Booking_Wins']:
                        st.success(f"✅ **{res['Resolution']}**")
                        st.markdown(f"Your booking overrides **{res['Conflicting_Booking']}** "
                                   f"(Priority: {res['Conflict_Priority']})")
                    else:
                        st.warning(f"❌ **{res['Resolution']}**")
                        st.markdown(f"Existing booking **{res['Conflicting_Booking']}** "
                                   f"(Priority: {res['Conflict_Priority']}) takes precedence.")
                
                st.markdown("### Conflicting Bookings Detail")
                st.dataframe(resolution_df, use_container_width=True)
                
            else:
                st.success("✅ NO CONFLICT! Equipment is available for the requested period.")
                st.balloons()
                
                st.markdown("### Booking Summary")
                summary_data = {
                    'Field': ['Equipment', 'Unit ID', 'Date', 'Duration', 'Shift', 'Priority', 'Project', 'Location'],
                    'Value': [new_type, new_equipment_id, str(new_booking_date), new_duration, 
                             new_shift, new_priority, new_project, new_location]
                }
                st.table(pd.DataFrame(summary_data))


# ============================================================
# PAGE: AI PREDICTION
# ============================================================
elif page == "🤖 AI Prediction":
    st.header("🤖 AI-Powered Conflict Prediction")
    st.markdown("Machine Learning model trained on historical booking data to predict conflict outcomes.")
    
    st.markdown("---")
    
    # Train model
    with st.spinner("Training AI model..."):
        model, encoders, accuracy, features, report = train_model(df)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Model Accuracy", f"{accuracy*100:.1f}%")
    with col2:
        st.metric("Training Records", len(df))
    with col3:
        st.metric("Features Used", len(features))
    
    st.markdown("---")
    
    # Classification Report
    st.subheader("📊 Model Performance Report")
    
    report_df = pd.DataFrame(report).transpose()
    st.dataframe(report_df.round(3), use_container_width=True)
    
    st.markdown("---")
    
    # Feature Importance
    st.subheader("🎯 Feature Importance")
    importance_df = pd.DataFrame({
        'Feature': features,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False)
    
    st.bar_chart(importance_df.set_index('Feature')['Importance'])
    
    st.markdown("---")
    
    # Prediction Interface
    st.subheader("🔮 Make a Prediction")
    st.markdown("Input booking parameters to predict whether it will win equipment allocation.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pred_priority = st.select_slider("Priority", options=['Low', 'Medium', 'High', 'Urgent'], value='Medium')
        pred_duration = st.selectbox("Duration", list(DURATION_MAP.keys()), key='pred_duration')
        pred_lead_time = st.slider("Lead Time (days)", 1, 14, 5)
        pred_wind = st.slider("Wind Speed (knots)", 0, 45, 10)
        pred_utilization = st.slider("Crane Utilization %", 20, 100, 60)
    
    with col2:
        pred_category = st.selectbox("Equipment Category", df['Equipment_Category'].unique(), key='pred_cat')
        pred_type = st.selectbox("Equipment Type", 
                                 df[df['Equipment_Category'] == pred_category]['Equipment_Type'].unique(), 
                                 key='pred_type')
        pred_shift = st.selectbox("Shift", ['Day Shift (0700-1900)', 'Night Shift (1900-0700)'], key='pred_shift')
        pred_project = st.selectbox("Project", sorted(df['Project'].unique()), key='pred_project')
        pred_weather = st.selectbox("Weather", df['Weather_Condition'].unique(), key='pred_weather')
    
    if st.button("🔮 Predict Outcome", type="primary", use_container_width=True):
        # Encode inputs
        try:
            input_data = pd.DataFrame([{
                'Priority_Score': PRIORITY_SCORES[pred_priority],
                'Duration_Days': DURATION_MAP[pred_duration],
                'Lead_Time': pred_lead_time,
                'Equipment_Category_Enc': encoders['equipment_cat'].transform([pred_category])[0],
                'Equipment_Type_Enc': encoders['equipment_type'].transform([pred_type])[0],
                'Shift_Enc': encoders['shift'].transform([pred_shift])[0],
                'Project_Enc': encoders['project'].transform([pred_project])[0],
                'Weather_Enc': encoders['weather'].transform([pred_weather])[0],
                'Wind_Speed_Knots': pred_wind,
                'Crane_Utilization_Pct': pred_utilization,
            }])
            
            prediction = model.predict(input_data)[0]
            probability = model.predict_proba(input_data)[0]
            
            st.markdown("### Prediction Result")
            
            if prediction == 1:
                st.success(f"✅ **WINS EQUIPMENT** (Confidence: {probability[1]*100:.1f}%)")
                st.progress(probability[1])
            else:
                st.error(f"❌ **DOES NOT WIN EQUIPMENT** (Confidence: {probability[0]*100:.1f}%)")
                st.progress(probability[0])
                
                st.markdown("**💡 Recommendation:** Consider increasing priority or adjusting the schedule.")
        except Exception as e:
            st.error(f"Prediction error: {str(e)}")


# ============================================================
# PAGE: ANALYTICS
# ============================================================
elif page == "📈 Analytics":
    st.header("📈 Equipment Utilization Analytics")
    
    # Equipment utilization
    st.subheader("Equipment Utilization by Type")
    util_by_type = df.groupby('Equipment_Type')['Crane_Utilization_Pct'].mean().sort_values(ascending=False)
    st.bar_chart(util_by_type)
    
    st.markdown("---")
    
    # Conflicts by equipment type
    if 'Has_Conflict' in df.columns:
        st.subheader("Conflicts by Equipment Type")
        conflict_by_type = df[df['Has_Conflict'] == 'Yes'].groupby('Equipment_Type').size().sort_values(ascending=False)
        if not conflict_by_type.empty:
            st.bar_chart(conflict_by_type)
        else:
            st.info("No conflicts recorded in the dataset.")
    
    st.markdown("---")
    
    # Priority distribution by project
    st.subheader("Priority Distribution by Project")
    priority_project = pd.crosstab(df['Project'], df['Priority'])
    st.dataframe(priority_project, use_container_width=True)
    
    st.markdown("---")
    
    # Weather impact
    st.subheader("Weather Impact on Operations")
    weather_status = pd.crosstab(df['Weather_Condition'], df['Status'])
    st.dataframe(weather_status, use_container_width=True)
    
    st.markdown("---")
    
    # Duration analysis
    st.subheader("Booking Duration Distribution")
    duration_counts = df['Duration'].value_counts()
    st.bar_chart(duration_counts)


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888;'>"
    "🏗️ Equipment Booking AI System | Shipyard Operations | "
    f"Built with Streamlit | {datetime.now().strftime('%Y')}"
    "</div>",
    unsafe_allow_html=True
)

