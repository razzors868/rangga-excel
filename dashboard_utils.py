import streamlit as st
import pandas as pd
import altair as alt

# Global variable for the Excel file path (now a placeholder, actual path passed dynamically)
EXCEL_FILE_PATH = 'placeholder.xlsx'

@st.cache_data
def load_data(file_path, sheet_name='Rawdata', required_cols=None, dtype_spec=None):
    """
    Reads a specified sheet from an Excel file and loads it into a pandas DataFrame.
    Handles common data type conversions and error checking.
    """
    # Define a comprehensive list of columns that might be needed across all dashboards
    # and their expected dtypes. This makes load_data more robust.
    all_possible_cols = {
        'Name': str,
        'Employee ID': str,
        'Group': str,
        'Team leader': str,
        'Supervisor': str,
        'Collected assign amount': float,
        'Collected principal amount': float,
        'Actual amount collected': float,
        'Collection rate today': float,
        'Collection rate for new case today': float,
        'Dialing Quantity': float,
        'Dialing quantity connected': float,
        'Talk Duration': float,
        'SMS Quantity': float,
        'Epoch Whatsapp': float, # Corrected from 'Epoch Wha'
        'Date V2': object, # To be converted to datetime
        'WFH/Onsite': str,
        'Classification': str,
        'Inh/Vendor': str,
        'Talk Duration V2': float # Including both Talk Duration and Talk Duration V2, as it might exist in some datasets
    }

    # If specific required_cols are provided, filter the all_possible_cols
    if required_cols:
        cols_to_use = {col: all_possible_cols[col] for col in required_cols if col in all_possible_cols}
    else:
        cols_to_use = all_possible_cols # Use all if not specified

    # Merge with any provided dtype_spec, prioritizing provided spec
    final_dtype_spec = {**cols_to_use, **(dtype_spec if dtype_spec else {})}

    try:
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            usecols=list(final_dtype_spec.keys()),
            dtype=final_dtype_spec
        )
        
        # Ensure 'Date V2' is parsed as datetime objects if present
        if 'Date V2' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Date V2']):
            df['Date V2'] = pd.to_datetime(df['Date V2'], errors='coerce')
        
        # Drop rows where essential columns are NaN
        # Assuming 'Group' and 'Date V2' are crucial for most dashboards
        subset_cols = [col for col in ['Group', 'Date V2'] if col in df.columns]
        df.dropna(subset=subset_cols, inplace=True)
        
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found.")
        return pd.DataFrame()
    except ValueError as ve:
        st.error(f"An error occurred during Excel parsing: {ve}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return pd.DataFrame()

def apply_filters_and_aggregate(df, aggregation_period, value_column):
    if df.empty:
        return pd.DataFrame()

    # Ensure the value_column is numeric
    df[value_column] = pd.to_numeric(df[value_column], errors='coerce')
    df.dropna(subset=[value_column], inplace=True)

    # Determine grouping key based on aggregation period
    if aggregation_period == 'Weekly':
        df['Period'] = df['Date V2'].dt.to_period('W').dt.start_time
    elif aggregation_period == 'Monthly':
        df['Period'] = df['Date V2'].dt.to_period('M').dt.start_time
    else: # Daily
        df['Period'] = df['Date V2']

    # Group by 'Group' and 'Period' and calculate the mean of the value_column
    grouped_data = df.groupby(['Group', 'Period'])[value_column].mean().reset_index()

    # Pivot the table to have periods as columns
    pivot_table = grouped_data.pivot_table(index='Group', columns='Period', values=value_column)

    # Format column headers based on aggregation period
    if aggregation_period == 'Weekly':
        pivot_table.columns = pivot_table.columns.strftime('W%U-%y') # Example: W40-25
    elif aggregation_period == 'Monthly':
        pivot_table.columns = pivot_table.columns.strftime('%b-%y') # Example: Oct-25
    else: # Daily
        pivot_table.columns = pivot_table.columns.strftime('%d/%b/%y')

    return pivot_table


def generate_chart_data(df, aggregation_period, chart_group_col, value_column):
    if df.empty:
        return pd.DataFrame()

    temp_df = df.copy()
    temp_df[value_column] = pd.to_numeric(temp_df[value_column], errors='coerce')
    temp_df.dropna(subset=[value_column], inplace=True)

    # Determine grouping key based on aggregation period
    if aggregation_period == 'Weekly':
        temp_df['Period'] = temp_df['Date V2'].dt.to_period('W').dt.start_time
    elif aggregation_period == 'Monthly':
        temp_df['Period'] = temp_df['Date V2'].dt.to_period('M').dt.start_time
    else: # Daily
        temp_df['Period'] = temp_df['Date V2']

    # Group by the chart_group_col and 'Period' and calculate the mean of the value_column
    grouped_data = temp_df.groupby([chart_group_col, 'Period'])[value_column].mean().reset_index()

    # Rename columns for Altair
    grouped_data.rename(columns={'Period': 'Date', value_column: f'Avg {value_column}'}, inplace=True)
    
    # Ensure 'Date' is datetime for consistent plotting
    grouped_data['Date'] = pd.to_datetime(grouped_data['Date'])

    return grouped_data

def display_altair_chart(chart_data, chart_group_col, value_column_display_name):
    if chart_data.empty:
        st.info(f"No data for {chart_group_col} chart.")
        return


    # Create a base chart
    base = alt.Chart(chart_data).encode(
        x=alt.X('Date:T', axis=alt.Axis(title='Date', format='%d/%b/%y')),
        y=alt.Y(f'Performance Rate:Q', title='Performance Rate', axis=alt.Axis(format='.1%')) if value_column_display_name == 'Performance Rate' else alt.Y(f'Avg {value_column_display_name}:Q', title=f'Avg {value_column_display_name}'),
        color=alt.Color(f'{chart_group_col}:N', title=chart_group_col)
    ).properties(
        title=f'{value_column_display_name} by {chart_group_col}'
    )

    # Add lines
    lines = base.mark_line(point=True).encode(
        tooltip=[
            alt.Tooltip('Date:T', format='%d/%b/%y'),
            alt.Tooltip('Performance Rate:Q', format='.2%', title='Performance Rate') if value_column_display_name == 'Performance Rate' else alt.Tooltip(f'Avg {value_column_display_name}:Q', format='.2f'),
            alt.Tooltip(f'{chart_group_col}:N')
        ]
    )

    # Add text labels for the values
    text_fill_color = 'white'

    text = base.mark_text(
        align='center',
        baseline='bottom',
        dy=-10, # Nudge text upwards
        fontSize=13, # Increase font size for better visibility
    ).encode(
        text=alt.Text('Performance Rate:Q', format='.2%') if value_column_display_name == 'Performance Rate' else alt.Text(f'Avg {value_column_display_name}:Q', format='.2f'),
        color=alt.value(text_fill_color) # Dynamically adjust text fill color
    )
    
    chart = (lines + text).interactive()
    st.altair_chart(chart, use_container_width=True)

def setup_filters(df):
    st.header("Filters and Aggregation")

    # --- Aggregation Period Selector ---
    aggregation_period = st.radio(
        "Select Aggregation Period",
        ('Daily', 'Weekly', 'Monthly')
    )

    # --- Date Range Filter ---
    st.subheader("Date Range Filter")
    min_date = df['Date V2'].min().date()
    max_date = df['Date V2'].max().date()

    # Default to October 2025 as per user's earlier request, if data exists for it
    default_start_date = pd.Timestamp('2025-10-01').date()
    default_end_date = pd.Timestamp('2025-10-31').date()

    # Ensure default dates are within the actual data range
    if default_start_date < min_date:
        default_start_date = min_date
    if default_end_date > max_date:
        default_end_date = max_date
    if default_start_date > max_date: # Handle case where default start is after all data
        default_start_date = min_date
    if default_end_date < min_date: # Handle case where default end is before all data
        default_end_date = max_date


    selected_start_date = st.date_input(
        "Start Date",
        value=default_start_date,
        min_value=min_date,
        max_value=max_date
    )
    selected_end_date = st.date_input(
        "End Date",
        value=default_end_date,
        min_value=min_date,
        max_value=max_date
    )

    # Convert selected dates to datetime for filtering
    selected_start_datetime = pd.to_datetime(selected_start_date)
    selected_end_datetime = pd.to_datetime(selected_end_date)

    temp_filtered_df = df[
        (df['Date V2'] >= selected_start_datetime) &
        (df['Date V2'] <= selected_end_datetime)
    ].copy()

    # --- Initialize session state for filters ---
    filter_columns = ['Group', 'WFH/Onsite', 'Classification', 'Inh/Vendor', 'Team leader', 'Supervisor']
    for col in filter_columns:
        if f'selected_{col}' not in st.session_state:
            st.session_state[f'selected_{col}'] = [] # Initialize as empty list, meaning all options are implicitly selected (show all)

    st.subheader("Data Filters") # This subheader is now for the other filters

    # Add custom CSS for button styling
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: #f0f2f6;
            color: #262730;
            border-radius: 5px;
            border: 1px solid #d3d3d3;
            padding: 5px 10px;
            margin: 2px;
            cursor: pointer;
        }
        div.stButton > button:first-child:hover {
            border-color: #007bff;
            color: #007bff;
        }
        div.stButton > button.selected {
            background-color: #007bff;
            color: white;
            border-color: #007bff;
        }
        div.stButton > button:disabled {
            background-color: #e0e0e0;
            color: #a0a0a0;
            cursor: not-allowed;
            border-color: #e0e0e0;
        }
        </style>
    """, unsafe_allow_html=True)

    # Add custom CSS for scrollable expanders
    st.markdown("""
        <style>
        /* Target the div that contains the buttons within the custom scrollable-expander */
        .scrollable-expander div[data-testid="stVerticalBlock"] > div {
            max-height: 200px; /* Adjust height as needed */
            overflow-y: auto;
            border: 1px solid #333; /* Optional: for visual debugging of scrollable area */
            padding: 5px; /* Optional: for better spacing */
        }
        </style>
    """, unsafe_allow_html=True)

    # Arrange filters in columns
    num_filter_cols = 3 # You can change this to 2 or 3
    filter_cols_iterator = iter(filter_columns)
    
    while True:
        cols = st.columns(num_filter_cols)
        current_batch = []
        try:
            for _ in range(num_filter_cols):
                current_batch.append(next(filter_cols_iterator))
        except StopIteration:
            pass

        if not current_batch:
            break

        for i, filter_col in enumerate(current_batch):
            with cols[i]:
                with st.expander(filter_col, expanded=True):
                    # Wrap the buttons in a custom div for CSS targeting
                    with st.container(height=200, border=True): # Use st.container for scrollable area
                        all_options = df[filter_col].unique().tolist()
                        all_options.sort()

                        available_options_for_this_filter = temp_filtered_df[filter_col].unique().tolist()
                        available_options_for_this_filter.sort()

                        st.session_state[f'selected_{filter_col}'] = [
                            opt for opt in st.session_state[f'selected_{filter_col}'] if opt in available_options_for_this_filter
                        ]
                        
                        for option in all_options:
                            is_available = option in available_options_for_this_filter
                            is_visually_selected = option in st.session_state[f'selected_{filter_col}']
                            
                            button_label = f"✅ {option}" if is_visually_selected else option
                            if st.button(
                                button_label,
                                key=f"{filter_col}_button_{option}",
                                disabled=not is_available,
                                help=f"{option} ({'Available' if is_available else 'Unavailable'})",
                            ):
                                if option in st.session_state[f'selected_{filter_col}']:
                                    st.session_state[f'selected_{filter_col}'].remove(option)
                                else:
                                    st.session_state[f'selected_{filter_col}'].append(option)
                                st.rerun()

        # Apply filter to temp_filtered_df based on current selections ("select to include").
        # This needs to be done after all buttons for a column are processed, but before the next column's available options are determined.
        for filter_col in current_batch:
            if st.session_state[f'selected_{filter_col}']:
                temp_filtered_df = temp_filtered_df[temp_filtered_df[filter_col].isin(st.session_state[f'selected_{filter_col}'])]
    
    return temp_filtered_df, aggregation_period