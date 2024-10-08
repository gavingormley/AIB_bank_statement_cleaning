import streamlit as st
import pandas as pd
import pandas as pd
from pathlib import Path
from datetime import timedelta
import os
import io

# Title of the application
st.title("Bank Statement Uploader")

# File uploader for bank statements
uploaded_files = st.file_uploader("Upload Bank Statements", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

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

        # Display the combined DataFrame
        st.write("This is what the first spreadsheet looks like before cleaning:")
        st.write(bank_df)

        # ### Cleaning the DataFrame
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
        # Replace commas (only for decimals) with periods
        bank_credit_df['Credit'] = bank_credit_df['Credit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)

        # Convert the cleaned column to numeric
        bank_credit_df['Credit'] = bank_credit_df['Credit'].astype(str).str.strip() 
        bank_credit_df['Credit'] = pd.to_numeric(bank_credit_df['Credit'], errors='coerce')

        # Remove all rows where 'Credit' is NaN
        bank_credit_df = bank_credit_df.dropna(subset=['Credit'])

        # Display the cleaned DataFrame
        st.write("This is how the combined spreadsheet appears after cleaning:")
        st.write(bank_credit_df)

        # Create a CSV from the cleaned DataFrame
        csv = bank_credit_df.to_csv(index=False)

        # Convert the CSV to a bytes object
        buffer = io.StringIO(csv)
        buffer.seek(0)

        # Add a download button
        st.download_button(
            label="Download Cleaned Data",
            data=buffer,
            file_name='cleaned_bank_statements.csv',
            mime='text/csv'
        )
