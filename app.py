import streamlit as st
import pandas as pd
import pandas as pd
from pathlib import Path
from datetime import timedelta
import os
import io

st.title("AIB Bank Statement Cleaner")
st.write("Note that files are arranged alphabetically. If necessary, rename them according to their chronological order")
st.write('e.g. "1 Jan-May", "2 Jun-Dec"')

# Initialize session state variables if they do not exist
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'analysis_df' not in st.session_state:
    st.session_state.analysis_df = None

# Add a radio button for selecting Receipts or Payments at the beginning
transaction_type = st.radio("Select Transaction Type:", ('Receipts', 'Payments'))

# File uploader for bank statements
uploaded_files = st.file_uploader("Upload files", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

# Store uploaded files in session state
if uploaded_files:
    st.session_state.uploaded_files = uploaded_files

# Add a button to clear all uploaded data
if st.button("Clear All Uploaded Data"):
    # Clear session state for uploaded files and analysis
    st.session_state.uploaded_files = []
    st.session_state.analysis_df = None
    st.session_state.cleaned_df = None  # This will hold cleaned DataFrame to avoid referencing errors
    st.success("All uploaded data has been cleared.")

# Process the uploaded files only if there are any
bank_df_list = []

# Read the uploaded files
if st.session_state.uploaded_files:
    for file in st.session_state.uploaded_files:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        bank_df_list.append(df)

    # Combine all bank statements into one DataFrame
    if bank_df_list:
        bank_df = pd.concat(bank_df_list, ignore_index=True)

        # Display the initial DataFrame
        st.write("This is what the first spreadsheet looks like before cleaning:")
        st.write(bank_df)

        if transaction_type == 'Receipts':
            # Cleaning the dataframe for Receipts
            bank_credit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Credit'].isna())]
            bank_credit_df = bank_credit_df[bank_credit_df['Date'] != 'Date']
            bank_credit_df['Date'] = pd.to_datetime(bank_credit_df['Date'], errors='coerce')
            bank_credit_df['Date'].fillna(method='ffill', inplace=True)
            bank_credit_df = bank_credit_df[~(bank_credit_df['Credit'].isna())]
            bank_credit_df = bank_credit_df.drop(['Debit', 'Balance'], axis=1)
            bank_credit_df['Credit'] = bank_credit_df['Credit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
            bank_credit_df['Credit'] = bank_credit_df['Credit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)
            bank_credit_df['Credit'] = pd.to_numeric(bank_credit_df['Credit'].astype(str).str.strip(), errors='coerce')
            bank_credit_df = bank_credit_df.dropna(subset=['Credit'])
            bank_credit_df.reset_index(drop=True, inplace=True)

            # Display the cleaned DataFrame for Receipts
            st.write("This is how the combined spreadsheet appears after cleaning:")
            st.write(bank_credit_df)

            # Create a CSV from the cleaned DataFrame
            csv = bank_credit_df.to_csv(index=False)
            buffer = io.BytesIO(csv.encode('utf-8'))

            # Add a download button
            st.download_button(
                label="Download Cleaned Receipts Data",
                data=buffer,
                file_name='cleaned_receipts.csv',
                mime='text/csv'
            )

        elif transaction_type == 'Payments':
            # Cleaning the dataframe for Payments
            bank_debit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Debit'].isna())]
            bank_debit_df = bank_debit_df[bank_debit_df['Date'] != 'Date']
            bank_debit_df['Date'] = pd.to_datetime(bank_debit_df['Date'], errors='coerce')
            bank_debit_df['Date'].fillna(method='ffill', inplace=True)
            bank_debit_df = bank_debit_df[~(bank_debit_df['Debit'].isna())]
            bank_debit_df = bank_debit_df.drop(['Credit', 'Balance'], axis=1)
            bank_debit_df['Debit'] = bank_debit_df['Debit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
            bank_debit_df['Debit'] = bank_debit_df['Debit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)
            bank_debit_df['Debit'] = pd.to_numeric(bank_debit_df['Debit'], errors='coerce')
            bank_debit_df = bank_debit_df.dropna(subset=['Debit'])
            bank_debit_df.reset_index(drop=True, inplace=True)

            # Display the cleaned DataFrame for Payments
            st.write("This is how the combined spreadsheet appears after cleaning:")
            st.write(bank_debit_df)

            # Create a CSV from the cleaned DataFrame
            csv = bank_debit_df.to_csv(index=False)
            buffer = io.BytesIO(csv.encode('utf-8'))

            # Add a download button
            st.download_button(
                label="Download Cleaned Spreadsheet",
                data=buffer,
                file_name='cleaned_payments.csv',
                mime='text/csv'
            )
