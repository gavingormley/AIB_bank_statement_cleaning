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

# File uploader for bank statements
uploaded_files = st.file_uploader("Upload files", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

# Add a radio button for selecting Receipts or Payments
transaction_type = st.radio("Select Transaction Type:", ('Receipts', 'Payments'))

bank_df_list = []

# Read the uploaded files
if uploaded_files:
    for file in uploaded_files:
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
            # Keep only credit rows (or rows with date)
            bank_credit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Credit'].isna())]

            # Remove rows where cells = column names
            bank_credit_df = bank_credit_df[bank_credit_df['Date'] != 'Date']

            # Convert Date column to datetime
            bank_credit_df['Date'] = pd.to_datetime(bank_credit_df['Date'], errors='coerce')

            # Forward fill missing or NaT values with the previous valid date
            bank_credit_df['Date'].fillna(method='ffill', inplace=True)

            # Keep only credit rows
            bank_credit_df = bank_credit_df[~(bank_credit_df['Credit'].isna())]

            # Drop unneeded rows
            bank_credit_df = bank_credit_df.drop(['Debit', 'Balance'], axis=1)

            # Remove non-numeric characters but keep commas and periods
            bank_credit_df['Credit'] = bank_credit_df['Credit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)

            # Handle the potential mixed formats
            bank_credit_df['Credit'] = bank_credit_df['Credit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)

            # Convert the cleaned column to numeric
            bank_credit_df['Credit'] = bank_credit_df['Credit'].astype(str).str.strip() 
            bank_credit_df['Credit'] = pd.to_numeric(bank_credit_df['Credit'], errors='coerce')

            # Remove all rows where 'Credit' is NaN
            bank_credit_df = bank_credit_df.dropna(subset=['Credit'])

            # Reset the index after cleaning
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
            # Keep only debit rows (or rows with date)
            bank_debit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Debit'].isna())]

            # Remove rows where cells = column names
            bank_debit_df = bank_debit_df[bank_debit_df['Date'] != 'Date']

            # Convert Date column to datetime
            bank_debit_df['Date'] = pd.to_datetime(bank_debit_df['Date'], errors='coerce')

            # Forward fill missing or NaT values with the previous valid date
            bank_debit_df['Date'].fillna(method='ffill', inplace=True)

            # Keep only debit rows
            bank_debit_df = bank_debit_df[~(bank_debit_df['Debit'].isna())]

            # Drop unneeded columns
            bank_debit_df = bank_debit_df.drop(['Credit', 'Balance'], axis=1)

            # Remove non-numeric characters but keep commas and periods
            bank_debit_df['Debit'] = bank_debit_df['Debit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)

            # Handle the potential mixed formats
            bank_debit_df['Debit'] = bank_debit_df['Debit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)

            # Convert the cleaned column to numeric
            bank_debit_df['Debit'] = pd.to_numeric(bank_debit_df['Debit'], errors='coerce')

            # Remove all rows where 'Debit' is NaN
            bank_debit_df = bank_debit_df.dropna(subset=['Debit'])

            # Reset the index after cleaning
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
