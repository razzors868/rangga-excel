import streamlit as st
import os
import pandas as pd
import time
from pathlib import Path

st.set_page_config(layout="wide")

hide_streamlit_style = """
            <style>
            [data-testid="stToolbar"] {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

from talking_duration_dashboard import talking_duration_dashboard
from sms_dashboard import sms_dashboard
from dialling_quantity_dashboard import dialling_quantity_dashboard
from epoch_whatsapp_dashboard import epoch_whatsapp_dashboard
from performance_rate_dashboard import performance_rate_dashboard

# Define the directory for uploaded files
UPLOAD_DIR = "files"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True) # Ensure the directory exists

def get_excel_files():
    """Returns a list of Excel files in the UPLOAD_DIR."""
    return sorted([f.name for f in Path(UPLOAD_DIR).iterdir() if f.suffix in ['.xlsx', '.xls']])

def main():
    st.sidebar.title("Dashboard Navigation")

    st.sidebar.subheader("Excel File Management")
    
    # File Uploader
    uploaded_file = st.sidebar.file_uploader("Upload an Excel file", type=["xlsx", "xls"])
    if uploaded_file is not None:
        file_path = Path(UPLOAD_DIR) / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"File '{uploaded_file.name}' uploaded successfully!")
        st.session_state.excel_file_selector = uploaded_file.name # Automatically select the uploaded file
        if st.sidebar.button("Refresh File List", key="refresh_file_list"):
            st.rerun()

    # List, Search, and Delete Files
    excel_files = get_excel_files()
    if not excel_files:
        st.sidebar.info("No Excel files uploaded yet.")
        st.session_state.excel_file_selector = None
    else:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Available Excel Files")
        search_query = st.sidebar.text_input("Search files", key="file_search")

        filtered_files = [f for f in excel_files if search_query.lower() in f.lower()]
        
        if not filtered_files:
            st.sidebar.info("No files match your search query.")
            st.session_state.excel_file_selector = None
        else:
            # Determine the currently selected file or default to the first
            current_selected_file = st.session_state.get('excel_file_selector', None)
            if current_selected_file not in filtered_files and filtered_files:
                current_selected_file = filtered_files[0] # Default to first if current is not in filtered

            selected_file_name = st.sidebar.radio(
                "Select a file to use:",
                filtered_files,
                index=filtered_files.index(current_selected_file) if current_selected_file in filtered_files else 0,
                key="excel_file_selector"
            )
            
            # Display delete button only for the selected file, with confirmation
            st.sidebar.markdown("---")
            if selected_file_name:
                col1, col2 = st.sidebar.columns([0.8, 0.2])
                with col1:
                    st.sidebar.write(f"Selected: **{selected_file_name}**")
                with col2:
                    if col2.button("🗑️", key=f"delete_selected_file", help=f"Delete {selected_file_name}"):
                        st.session_state['file_to_delete'] = selected_file_name
                        st.rerun()

            # Confirmation dialog for deletion
            if 'file_to_delete' in st.session_state and st.session_state['file_to_delete']:
                file_to_delete = st.session_state['file_to_delete']
                st.sidebar.warning(f"Apakah anda ingin menghapus file '{file_to_delete}'?")
                col_yes, col_no = st.sidebar.columns(2)
                with col_yes:
                    if st.button("Yes, delete", key="confirm_delete_yes"):
                        try:
                            os.remove(Path(UPLOAD_DIR) / file_to_delete)
                            st.sidebar.success(f"File '{file_to_delete}' deleted.")
                            if 'excel_file_selector' in st.session_state and st.session_state.excel_file_selector == file_to_delete:
                                del st.session_state.excel_file_selector
                        except OSError as e:
                            st.sidebar.error(f"Error deleting file: {e}")
                        finally:
                            del st.session_state['file_to_delete']
                            st.rerun()
                with col_no:
                    if st.button("No, cancel", key="confirm_delete_no"):
                        del st.session_state['file_to_delete']
                        st.rerun()
    st.sidebar.markdown("---")

    # Only show dashboard navigation if an Excel file is selected
    if st.session_state.get('excel_file_selector'):
        st.sidebar.subheader("Dashboard Views")
        dashboards = {
            "Talking Duration": talking_duration_dashboard,
            "SMS": sms_dashboard,
            "Dialing Quantity": dialling_quantity_dashboard,
            "Epoch Whatsapp": epoch_whatsapp_dashboard,
            "Performance Rate": performance_rate_dashboard
        }

        selected_dashboard = st.sidebar.radio("Go to", list(dashboards.keys()))

        st.title(f"{selected_dashboard} Overview")
        # Pass the selected Excel file path to the dashboard function
        dashboards[selected_dashboard](Path(UPLOAD_DIR) / st.session_state.excel_file_selector)
    else:
        st.title("Welcome to the Dashboard Application")
        st.info("Please upload or select an Excel file from the sidebar to proceed.")


if __name__ == "__main__":
    main()