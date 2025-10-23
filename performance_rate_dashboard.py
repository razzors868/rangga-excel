import streamlit as st
import pandas as pd
from dashboard_utils import load_data, display_altair_chart, setup_filters
import numpy as np # Import numpy for handling division by zero safely

def performance_rate_dashboard(excel_file_path):
    st.title("Performance Rate Dashboard")

    excel_file = excel_file_path
    
    # Define required columns and data types for 'Performance Rate'
    required_cols = ['Group', 'Collected principal amount', 'Collected assign amount', 'Date V2', 'WFH/Onsite', 'Classification', 'Inh/Vendor', 'Team leader', 'Supervisor']
    dtype_spec = {
        'Group': str,
        'Collected principal amount': float,
        'Collected assign amount': float,
        'Date V2': object, # Will be converted to datetime by load_data
        'WFH/Onsite': str,
        'Classification': str,
        'Inh/Vendor': str,
        'Team leader': str,
        'Supervisor': str
    }

    df = load_data(excel_file, sheet_name='Rawdata', required_cols=required_cols, dtype_spec=dtype_spec)

    if df.empty:
        st.warning("No data to display for Performance Rate. Please ensure the Excel file exists and contains the 'Rawdata' sheet with valid data.")
        return

    # Setup filters and get filtered data and aggregation period
    filtered_df, aggregation_period = setup_filters(df)

    if not filtered_df.empty:
        temp_df_for_calc = filtered_df.copy()
        temp_df_for_calc['Collected principal amount'] = pd.to_numeric(temp_df_for_calc['Collected principal amount'], errors='coerce').fillna(0)
        temp_df_for_calc['Collected assign amount'] = pd.to_numeric(temp_df_for_calc['Collected assign amount'], errors='coerce').fillna(0)
        
        # Determine grouping key based on aggregation period
        if aggregation_period == 'Weekly':
            temp_df_for_calc['Period'] = temp_df_for_calc['Date V2'].dt.to_period('W').dt.start_time
        elif aggregation_period == 'Monthly':
            temp_df_for_calc['Period'] = temp_df_for_calc['Date V2'].dt.to_period('M').dt.start_time
        else: # Daily
            temp_df_for_calc['Period'] = temp_df_for_calc['Date V2']

        # Group by 'Group' and 'Period' and calculate sums
        grouped_sums = temp_df_for_calc.groupby(['Group', 'Period']).agg(
            total_principal=('Collected principal amount', 'sum'),
            total_assign=('Collected assign amount', 'sum')
        ).reset_index()

        # Calculate Performance Rate (handle division by zero)
        grouped_sums['Performance Rate'] = np.where(
            grouped_sums['total_assign'] == 0,
            0, # Or np.nan if you prefer to show missing values for 0/0
            grouped_sums['total_principal'] / grouped_sums['total_assign']
        )

        # Pivot the table to have periods as columns
        pivot_table_result = grouped_sums.pivot_table(index='Group', columns='Period', values='Performance Rate')

        # Format column headers based on aggregation period
        if aggregation_period == 'Weekly':
            pivot_table_result.columns = pivot_table_result.columns.strftime('W%U-%y') # Example: W40-25
        elif aggregation_period == 'Monthly':
            pivot_table_result.columns = pivot_table_result.columns.strftime('%b-%y') # Example: Oct-25
        else: # Daily
            pivot_table_result.columns = pivot_table_result.columns.strftime('%d/%b/%y')
        
        if not pivot_table_result.empty:
            st.subheader(f"Average Performance Rate by Group ({aggregation_period} Aggregation)")
            st.dataframe(pivot_table_result.style.format("{:.2%}")) # Format as percentage
        else:
            st.info("No data matches the selected filters for the specified aggregation.")
    else:
        st.info("No data available after applying filters.")

    # Dynamic Chart Selection
    st.subheader("Trend Charts")
    
    # For charts, we need to generate data based on the same sum-of-ratio logic
    # The generate_chart_data from dashboard_utils.py expects a value_column to aggregate by mean.
    # We will pass the grouped_sums dataframe directly to a custom chart generation logic
    # or adapt generate_chart_data if possible. For now, let's replicate the sum aggregation for charts.

    # Re-use grouped_sums for chart data if it exists, otherwise create it.
    chart_data_base = grouped_sums.copy()
    chart_data_base.rename(columns={'Period': 'Date'}, inplace=True)
    chart_data_base['Date'] = pd.to_datetime(chart_data_base['Date'])


    available_chart_columns = [col for col in df.columns if df[col].dtype == 'object' or df[col].dtype == 'category']
    available_chart_columns = [col for col in available_chart_columns if col not in ['Date V2', 'Collected principal amount', 'Collected assign amount']] # Exclude raw columns

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
                        st.markdown(f"##### Performance Rate by {chart_col_name}")
                        # For charts, we need to group by chart_col_name and Date, then sum principal and assign, then divide
                        chart_data_for_display = temp_df_for_calc.groupby([chart_col_name, 'Period']).agg(
                            total_principal=('Collected principal amount', 'sum'),
                            total_assign=('Collected assign amount', 'sum')
                        ).reset_index()

                        chart_data_for_display['Performance Rate'] = np.where(
                            chart_data_for_display['total_assign'] == 0,
                            0,
                            chart_data_for_display['total_principal'] / chart_data_for_display['total_assign']
                        )
                        chart_data_for_display.rename(columns={'Period': 'Date'}, inplace=True)
                        chart_data_for_display['Date'] = pd.to_datetime(chart_data_for_display['Date'])
                        
                        display_altair_chart(chart_data_for_display, chart_col_name, 'Performance Rate')
    else:
        st.info("Please select columns to display dynamic charts.")

if __name__ == "__main__":
    performance_rate_dashboard()