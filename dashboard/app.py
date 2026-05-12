import streamlit as st
import pandas as pd
import requests

def get_users():
    response = requests.get(f"{API_BASE_URL}/users")
    return response.json() if response.status_code == 200 else []

def get_devices():
    response = requests.get(f"{API_BASE_URL}/devices")
    return response.json() if response.status_code == 200 else []

def get_telemetry(device_id):
    response = requests.get(f"{API_BASE_URL}/devices/{device_id}/telemetry")
    return response.json() if response.status_code == 200 else []


API_BASE_URL = "http://api:5000/api" #points to docker container "api"
DEVICES_URL = f"{API_BASE_URL}/devices"
USERS_URL = f"{API_BASE_URL}/users"

st.set_page_config(page_title="Jäte Dashboard", layout="wide")
st.title("Dashboard")
st.subheader("Device Configuration")

try:
    device_data = get_devices()
    d_cols = ["device_id", "device_name", "bin_height", "height_buffer", "alerts_enabled"]

    if not device_data:
        devices_df = pd.DataFrame(columns=d_cols)
    else:
        devices_df = pd.DataFrame(device_data)[d_cols]

    edited_devices = st.data_editor(
        devices_df,
        column_config={
            "device_id": st.column_config.TextColumn("Device ID", disabled=True),
            "device_name": st.column_config.TextColumn("Device Name"),
            "bin_height": st.column_config.NumberColumn("Bin Height (cm)", min_value=1),
            "height_buffer": st.column_config.NumberColumn("Buffer (cm)"),
            "alerts_enabled": st.column_config.CheckboxColumn("Mail alerts enabled")
        },
        num_rows="dynamic",
        width="stretch",
        key="device_editor_state"
    )
    
    if st.button("Save Changes"):
        state = st.session_state["device_editor_state"]
        
        # delete
        for index in state["deleted_rows"]:
            device_id = devices_df.iloc[index]["device_id"]
            requests.delete(f"{DEVICES_URL}/{device_id}")
        # add add later? kind of pointless
        # update
        for index, changes in state["edited_rows"].items():
            # Get original record
            device_id = devices_df.iloc[int(index)]["device_id"]
            original_row = devices_df.iloc[int(index)].to_dict()
            updated_row = {**original_row, **changes}
            requests.put(f"{DEVICES_URL}/{device_id}", json=updated_row)

        st.success("Changes applied successfully!")
        st.rerun()

except Exception as e:
    st.error(f"Error loading devices: {e}")

st.divider()
st.subheader("User Management")

data = get_users()
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

if st.button("Sync users"):
    state = st.session_state["user_editor_state"]
    
    # delete
    for index in state["deleted_rows"]:
        user_id = users_df.iloc[index]["user_id"]
        requests.delete(f"{USERS_URL}/{user_id}")

    # add
    for row in state["added_rows"]:
        if row.get("name") and row.get("email"):
            requests.post(USERS_URL, json=row)

    # update
    for index, changes in state["edited_rows"].items():
        # Get original record
        user_id = users_df.iloc[int(index)]["user_id"]
        original_row = users_df.iloc[int(index)].to_dict()
        # Merge changes into original row
        updated_row = {**original_row, **changes}
        requests.put(f"{USERS_URL}/{user_id}", json=updated_row)

    st.success("Changes applied successfully!")
    st.rerun()

# Alert Recipients
st.divider()
st.subheader("Device Alert Assignments")

st.subheader("Alert Notifications")

# 1. Fetch data from API
devices_list = requests.get(DEVICES_URL).json()
users_list = requests.get(USERS_URL).json()

if devices_list and users_list:
    # Prepare DataFrames for easy filtering
    df_devices = pd.DataFrame(devices_list)
    df_users = pd.DataFrame(users_list)
    
    # Create searchable labels
    df_users['label'] = df_users['name'] + " (" + df_users['email'] + ")"
    
    # UI: Device Selection
    selected_device_name = st.selectbox(
        "Select a Device to configure alerts:", 
        options=df_devices['device_name']
    )
    selected_device_id = df_devices[df_devices['device_name'] == selected_device_name]['device_id'].values[0]

    # 2. Fetch CURRENT recipients for this specific device from API
    current_ids_resp = requests.get(f"{DEVICES_URL}/{selected_device_id}/recipients")
    current_ids = current_ids_resp.json() if current_ids_resp.status_code == 200 else []

    # 3. UI: Multiselect for Users
    selected_user_labels = st.multiselect(
        "Users to notify for this device:",
        options=df_users['label'].tolist(),
        # Match current IDs to their labels for the default view
        default=df_users[df_users['user_id'].isin(current_ids)]['label'].tolist()
    )

    # 4. Update Button
    if st.button("Update Alert Recipients"):
        # Map labels back to IDs
        chosen_ids = df_users[df_users['label'].isin(selected_user_labels)]['user_id'].tolist()
        
        # Send sync request to API
        sync_resp = requests.post(
            f"{API_BASE_URL}/devices/{selected_device_id}/recipients",
            json={"user_ids": chosen_ids}
        )
        
        if sync_resp.status_code == 200:
            st.success(f"Recipients updated for {selected_device_name}!")
        else:
            st.error("Failed to update recipients.")
else:
    st.info("Ensure you have created at least one Device and one User first.")

# LINE GRAPH

def fetch_and_store_telemetry(device_id, params):
    response = requests.get(f"{DEVICES_URL}/{device_id}/telemetry", params=params)
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

devices = get_devices()

if not devices:
    st.info("No devices found. Add a device to start.")
else:
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