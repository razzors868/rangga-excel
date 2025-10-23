import streamlit as st
import pandas as pd
from dashboard_utils import load_data, apply_filters_and_aggregate, generate_chart_data, display_altair_chart, setup_filters

def talking_duration_dashboard(excel_file_path):
    st.title("Talking Duration Dashboard")

    excel_file = excel_file_path
    
    # Define required columns and data types for 'Talk Duration V2'
    required_cols = ['Group', 'Talk Duration V2', 'Date V2', 'WFH/Onsite', 'Classification', 'Inh/Vendor', 'Team leader', 'Supervisor']
    dtype_spec = {
        'Group': str,
        'Talk Duration V2': float,
        'Date V2': object, # Will be converted to datetime by load_data
        'WFH/Onsite': str,
        'Classification': str,
        'Inh/Vendor': str,
        'Team leader': str,
        'Supervisor': str
    }

    df = load_data(excel_file, sheet_name='Rawdata', required_cols=required_cols, dtype_spec=dtype_spec)

    if df.empty:
        st.warning("No data to display for Talking Duration. Please ensure the Excel file exists and contains the 'Rawdata' sheet with valid data.")
        return

    # Setup filters and get filtered data and aggregation period
    filtered_df, aggregation_period = setup_filters(df)

    # Apply filters and aggregate
    if not filtered_df.empty:
        pivot_table_result = apply_filters_and_aggregate(
            filtered_df,
            aggregation_period,
            'Talk Duration V2'
        )
        if not pivot_table_result.empty:
            st.subheader(f"Average Talk Duration V2 by Group ({aggregation_period} Aggregation)")
            st.dataframe(pivot_table_result)
        else:
            st.info("No data matches the selected filters for the specified aggregation.")
    else:
        st.info("No data available after applying filters.")

    # Dynamic Chart Selection
    st.subheader("Trend Charts")
    available_chart_columns = [col for col in df.columns if df[col].dtype == 'object' or df[col].dtype == 'category']
    available_chart_columns = [col for col in available_chart_columns if col not in ['Date V2', 'Talk Duration V2']] # Exclude Date V2 and Talk Duration V2

    selected_chart_columns = st.multiselect(
        "Select columns to generate charts",
        options=available_chart_columns,
        default=['Inh/Vendor', 'Classification'] if 'Inh/Vendor' in available_chart_columns and 'Classification' in available_chart_columns else (available_chart_columns[:2] if available_chart_columns else [])
    )

    if selected_chart_columns:
        # Create columns for charts dynamically, max 2 charts per row
        num_charts = len(selected_chart_columns)
        for i in range(0, num_charts, 2):
            chart_cols = st.columns(2)
            for j in range(2):
                if (i + j) < num_charts:
                    chart_col_name = selected_chart_columns[i + j]
                    with chart_cols[j]:
                        st.markdown(f"##### AVG Talking Duration by {chart_col_name}")
                        chart_data = generate_chart_data(filtered_df, aggregation_period, chart_col_name, 'Talk Duration V2')
                        display_altair_chart(chart_data, chart_col_name, 'Talk Duration V2')
    else:
        st.info("Please select columns to display dynamic charts.")

if __name__ == "__main__":
    talking_duration_dashboard()