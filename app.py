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
uploaded_files = st.file_uploader("Upload current year's files", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

# Add a radio button for selecting Receipts or Payments
transaction_type = st.radio("Select Transaction Type:", ('Receipts', 'Payments'))

# Add a checkbox to ask if the user wants to upload the previous year's analysis
add_previous_year = st.checkbox("Do you want to upload the previous year's analysis?")

# If the user checks the box, show the file uploader for the previous year's analysis
uploaded_analysis = None
if add_previous_year:
    uploaded_analysis = st.file_uploader("Upload previous year's analysis", type=['xlsx', 'xls'])

bank_df_list = []
analysis_df = None

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

        # If previous year's analysis is uploaded
        if add_previous_year and uploaded_analysis:
            # Load the previous year's analysis based on transaction type
            if transaction_type == 'Receipts':
                analysis_df = pd.read_excel(uploaded_analysis, sheet_name='ReceiptsAnalysis', header=None)
            elif transaction_type == 'Payments':
                analysis_df = pd.read_excel(uploaded_analysis, sheet_name='Payments Analysis', header=None)

            # Find the row where the first column contains "Date" and use that as the header
            header_row = analysis_df[analysis_df.iloc[:, 0].str.contains("Date", na=False)].index[0]
            analysis_df.columns = analysis_df.iloc[header_row]
            analysis_df = analysis_df.drop(range(header_row + 1))

            # Reset index for the analysis DataFrame
            analysis_df.reset_index(drop=True, inplace=True)

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
            bank_credit_df['Credit'] = pd.to_numeric(bank_credit_df['Credit'], errors='coerce')
            bank_credit_df = bank_credit_df.dropna(subset=['Credit'])
            bank_credit_df.reset_index(drop=True, inplace=True)

            # Create a matching column by stripping whitespace and converting to lowercase
            bank_credit_df['Match'] = bank_credit_df['Details'].str.lower().str.replace(r'\s+', '', regex=True)
            if analysis_df is not None:
                analysis_df['Match'] = analysis_df['Details'].str.lower().str.replace(r'\s+', '', regex=True)
                # Merge based on 'Match' column
                bank_credit_df = pd.merge(bank_credit_df, analysis_df, on='Match', how='left', suffixes=('', '_previous'))

            # Drop 'Match' column from final DataFrame
            bank_credit_df.drop(columns=['Match'], inplace=True)

            st.write("This is how the combined spreadsheet appears after cleaning:")
            st.write(bank_credit_df)

            # Create a CSV from the cleaned DataFrame
            csv = bank_credit_df.to_csv(index=False)
            buffer = io.BytesIO(csv.encode('utf-8'))

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

            # Create a matching column by stripping whitespace and converting to lowercase
            bank_debit_df['Match'] = bank_debit_df['Details'].str.lower().str.replace(r'\s+', '', regex=True)
            if analysis_df is not None:
                analysis_df['Match'] = analysis_df['Details'].str.lower().str.replace(r'\s+', '', regex=True)
                # Merge based on 'Match' column
                bank_debit_df = pd.merge(bank_debit_df, analysis_df, on='Match', how='left', suffixes=('', '_previous'))

            # Drop 'Match' column from final DataFrame
            bank_debit_df.drop(columns=['Match'], inplace=True)

            st.write("This is how the combined spreadsheet appears after cleaning:")
            st.write(bank_debit_df)

            # Create a CSV from the cleaned DataFrame
            csv = bank_debit_df.to_csv(index=False)
            buffer = io.BytesIO(csv.encode('utf-8'))

            st.download_button(
                label="Download Cleaned Payments Data",
                data=buffer,
                file_name='cleaned_payments.csv',
                mime='text/csv'
            )
