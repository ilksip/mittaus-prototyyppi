import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os, json
import requests
def get_default_thresholds(conn):
    query = text("SELECT sensor_type, trigger_value, trigger_when_below, alert_message FROM Default_Thresholds")
    return conn.execute(query).mappings().all()

st.set_page_config(page_title="Jäte Dashboard", layout="wide")
st.title("Dashboard")

API_BASE_URL = "http://api:5000/api" #points to docker container "api"

# SQLAlchemy Engine
@st.cache_resource
def get_engine():
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("POSTGRES_DB")
    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(url)

st.subheader("Current Fill levels")
try:
    engine = get_engine()
    query = text("""
        SELECT 
            sub.device_name,
            sub.calculated_fill AS fill_level
        FROM (
            SELECT DISTINCT ON (d.device_id)
                d.device_name,
                (d.bin_height - ((t.sensor_values->>'fill_level')::float - d.height_buffer)) / d.bin_height  * 100 AS calculated_fill
            FROM Devices d
            JOIN Telemetry t ON d.device_id = t.device_id
            ORDER BY d.device_id, t.created_at DESC
        ) AS sub
        ORDER BY fill_level DESC
        LIMIT 10
    """)

    df = pd.read_sql_query(query, engine)
    if not df.empty:
        fig = px.bar(
            df, 
            x="device_name", 
            y="fill_level",
            labels={"device_name": "Device", "fill_level": "Fill %"},
            range_y=[0, 100],
            color="fill_level",
            color_continuous_scale="RdYlGn_r"
        )

        fig.update_layout(
            bargap=0.6, 
            width=500, 
            showlegend=False
        )

        st.plotly_chart(fig, width="content")
        top_bin = df.iloc[0]
        st.info(f"{top_bin['device_name']} is {top_bin['fill_level']:.1f}% full.")
    else:
        st.warning("No data found.")

except Exception as e:
    st.error(f"Failed to generate chart: {e}")

st.divider()
st.subheader("Device Configuration")

try:
    engine = get_engine()
    
    # 1. Fetch current devices
    query = text("SELECT device_id, device_name, bin_height, height_buffer, alerts_enabled FROM Devices")
    devices_df = pd.read_sql_query(query, engine)

    # 2. Use st.data_editor for inline editing
    edited_devices = st.data_editor(
        devices_df,
        column_config={
            "device_id": st.column_config.TextColumn("Device ID", disabled=True),
            "firmware_version": st.column_config.TextColumn("Firmware", disabled=True, width="small"),
            "device_name": st.column_config.TextColumn("Device Name"),
            "bin_height": st.column_config.NumberColumn("Bin Height (cm)", min_value=1),
            "height_buffer": st.column_config.NumberColumn("Buffer (cm)"),
            "alerts_enabled": st.column_config.CheckboxColumn("Mail alerts enabled")
        },
        #num_rows="dynamic",
        width="stretch",
        key="device_editor"
    )

    if st.button("Sync changes to database"):
        with engine.begin() as conn:
            for _, row in edited_devices.iterrows():
                if pd.notnull(row.get('device_id')): # Update existing
                    conn.execute(
                        text("UPDATE Devices SET device_name = :name, bin_height = :height, alerts_enabled = :alerts, height_buffer = :buffer WHERE device_id = :id"),
                        {"name": row["device_name"], "height": row["bin_height"], "id": row["device_id"], "alerts": row["alerts_enabled"], "buffer": row["height_buffer"]}
                        )
                else: # Adding new devices via dashboard, never reached, broken, needs rework
                    if row["device_name"] and row["bin_height"]:
                        result = conn.execute(text("INSERT INTO Devices (device_name, bin_height) VALUES (:dn, :b) RETURNING device_id"),
                                     {"dn": row['device_name'], "b": row['bin_height']})
                        fresh_uuid = result.scalar()

                        defaults = get_default_thresholds(conn)

                        for t in defaults:
                            conn.execute(text("INSERT INTO Alert_Thresholds (device_id, trigger_value, sensor_type, trigger_when_below, alert_message) VALUES (:did, :value, :type, :below, :msg)"),
                            {"did":fresh_uuid, "value":t["trigger_value"],"type":t["sensor_type"],"below":t["trigger_when_below"],"msg":t["alert_message"]})
  
        st.success("Configuration updated!")
        st.rerun()

except Exception as e:
    st.error(f"Error loading devices: {e}")

st.divider()
st.subheader("User Management")

USERS_API = f"{API_BASE_URL}/users"

response = requests.get(USERS_API)
data = response.json()
if not data:
    # Create an empty DataFrame with the specific columns your API expects
    users_df = pd.DataFrame(columns=["user_id", "name", "email"])
else:
    users_df = pd.DataFrame(data)

st.data_editor(
    users_df,
    column_config={
        "user_id": st.column_config.NumberColumn("ID", disabled=True),
        "name": st.column_config.TextColumn("Full Name", required=True),
        "email": st.column_config.TextColumn("Email Address", required=True),
    },
    num_rows="dynamic",
    key="user_editor_state" 
)

if st.button("Save Changes"):
    state = st.session_state["user_editor_state"]
    
    # delete
    for index in state["deleted_rows"]:
        user_id = users_df.iloc[index]["user_id"]
        requests.delete(f"{USERS_API}/{user_id}")

    # add
    for row in state["added_rows"]:
        if row.get("name") and row.get("email"):
            requests.post(USERS_API, json=row)

    # update
    for index, changes in state["edited_rows"].items():
        # Get original record
        user_id = users_df.iloc[int(index)]["user_id"]
        original_row = users_df.iloc[int(index)].to_dict()
        # Merge changes into original row
        updated_row = {**original_row, **changes}
        requests.put(f"{USERS_API}/{user_id}", json=updated_row)

    st.success("Changes applied successfully!")
    st.rerun()


# Alert Recipients
st.divider()
st.subheader("Device Alert Assignments")

try:
    # 1. Get list of devices and users for the dropdowns
    devices = pd.read_sql_query("SELECT device_id, device_name FROM Devices", engine)
    all_users = pd.read_sql_query("SELECT user_id, name, email FROM Users", engine)

    if not devices.empty and not all_users.empty:
        # Create labels for the multiselect: "Name (email)"
        all_users['label'] = all_users['name'] + " (" + all_users['email'] + ")"
        
        # Select device to manage
        selected_device_name = st.selectbox("Select a Device to configure alerts:", devices['device_name'])
        selected_device_id = devices[devices['device_name'] == selected_device_name]['device_id'].values[0]

        # 2. Get current recipients for THIS device
        current_recipients_query = text("""
            SELECT user_id FROM Alert_Recipients WHERE device_id = :d_id
        """)
        current_ids = pd.read_sql_query(current_recipients_query, engine, params={"d_id": selected_device_id})['user_id'].tolist()

        # 3. Display Multiselect
        # Default values are the users currently in the bridge table
        selected_user_labels = st.multiselect(
            "Users to notify for this device:",
            options=all_users['label'].tolist(),
            default=all_users[all_users['user_id'].isin(current_ids)]['label'].tolist()
        )

        if st.button("Update Alert Recipients"):
            # Get the IDs for the selected labels
            new_user_ids = all_users[all_users['label'].isin(selected_user_labels)]['user_id'].tolist()
            
            with engine.begin() as conn:
                # Sync logic: Clear existing and re-insert
                conn.execute(text("DELETE FROM Alert_Recipients WHERE device_id = :d_id"), {"d_id": selected_device_id})
                for uid in new_user_ids:
                    conn.execute(text("INSERT INTO Alert_Recipients (device_id, user_id) VALUES (:d_id, :u_id)"),
                                 {"d_id": selected_device_id, "u_id": uid})
            st.success(f"Recipients updated for {selected_device_name}!")
    else:
        st.info("Add both Devices and Users first to enable alert linking.")

except Exception as e:
    st.error(f"Linking error: {e}")

# LINE GRAPH



def get_devices():
    response = requests.get(f"{API_BASE_URL}/devices")
    return response.json() if response.status_code == 200 else []

def get_telemetry(device_id):
    response = requests.get(f"{API_BASE_URL}/devices/{device_id}/telemetry")
    return response.json() if response.status_code == 200 else []

def fetch_and_store_telemetry(device_id, params):
    response = requests.get(f"{API_BASE_URL}/devices/{device_id}/telemetry", params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            # Process into DataFrame immediately
            df = pd.DataFrame(data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            sensors_df = pd.json_normalize(df['sensor_values'])
            full_df = pd.concat([df.drop(columns=['sensor_values']), sensors_df], axis=1)
            
            # Store in session state
            st.session_state['telemetry_df'] = full_df
            st.session_state['sensor_cols'] = sensors_df.columns.tolist()
        else:
            st.session_state['telemetry_df'] = None
            st.warning("No telemetry found.")
    else:
        st.error("Failed to fetch data from API.")

st.title("Device Telemetry Monitor")

# 1. Device Selection
response = requests.get(f"{API_BASE_URL}/devices")
devices = response.json() if response.status_code == 200 else []

if not devices:
    st.info("No devices found. Add a device to start.")
else:
    # Create the mapping only if devices exist
    device_map = {d['device_name']: d for d in devices}
    selected_name = st.selectbox("Select Device", options=list(device_map.keys()))

    if selected_name:
        selected_device = device_map[selected_name]
        
        num_points = st.number_input("Number of points", min_value=10, max_value=1000, value=100)

        tm_params = {"limit": num_points} 
        if st.button("Fetch Telemetry"):
            fetch_and_store_telemetry(selected_device['device_id'], tm_params)

        if 'telemetry_df' in st.session_state and st.session_state['telemetry_df'] is not None:
            df = st.session_state['telemetry_df']
            sensors = st.session_state['sensor_cols']

            try:
                default_ix = sensors.index('fill_level')
            except ValueError:
                default_ix = 0 
                
            col1, col2 = st.columns([1, 4])
            with col1:
                selected_sensor = st.radio("Select Metric", options=sensors, index=default_ix)
            
            plot_df = df[['created_at', selected_sensor]].copy()
            
            if selected_sensor == 'fill_level':

                bh = selected_device['bin_height']
                buf = selected_device['height_buffer']
                
                plot_df['Fill %'] = plot_df['fill_level'].apply(
                    lambda x: max(0, min(100, ((bh - (x - buf)) / bh) * 100))
                )
                y_axis = 'Fill %'
            else:
                y_axis = selected_sensor

            with col2:
                if not plot_df.empty:
                    start_time = plot_df['created_at'].min().strftime('%m-%d %H:%M')
                    end_time = plot_df['created_at'].max().strftime('%m-%d %H:%M')
                    st.caption(f"Range: {start_time} to {end_time}")
                    st.line_chart(plot_df.set_index('created_at')[y_axis])
                else:
                    st.warning("No telemetry data found for this device.")