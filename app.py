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


# Add a radio button for selecting Receipts or Payments
transaction_type = st.radio("Select Transaction Type:", ('Receipts', 'Payments'))

# Add a checkbox to ask if the user wants to upload the previous year's analysis
add_previous_year = st.checkbox("Do you want to upload the previous year's analysis?")

# Initialize analysis_df to None in case no analysis file is uploaded
analysis_df = None

# If the user checks the box, show the file uploader for the previous year's analysis
if add_previous_year:
    uploaded_analysis = st.file_uploader("Upload previous year's analysis", type=['xlsx', 'xls'])
    
    # Load the previous year's analysis based on transaction type if a file is uploaded
    if uploaded_analysis:
        try:
            if transaction_type == 'Receipts':
                analysis_df = pd.read_excel(uploaded_analysis, sheet_name='ReceiptsAnalysis', header=None)
            elif transaction_type == 'Payments':
                analysis_df = pd.read_excel(uploaded_analysis, sheet_name='Payments Analysis', header=None)
            
            # Find the row where the first column contains "Date" and use that as the header
            header_row = analysis_df[analysis_df.iloc[:, 0].astype(str).str.contains("Date", case=False, na=False)].index
            if not header_row.empty:
                header_row = header_row[0]
                analysis_df.columns = analysis_df.iloc[header_row]
                analysis_df = analysis_df.drop(range(header_row + 1)).reset_index(drop=True)
            else:
                st.error("No header row containing 'Date' found in the analysis file.")
                analysis_df = None
        except Exception as e:
            st.error(f"Error loading previous year's analysis: {e}")
            analysis_df = None

# File uploader for bank statements
uploaded_files = st.file_uploader("Upload current year's files", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

bank_df_list = []

# Process the bank statement files after they've been uploaded
if uploaded_files:
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            bank_df_list.append(df)
        except Exception as e:
            st.warning(f"Failed to read {file.name}: {e}")

    # Combine all bank statements into one DataFrame
    if bank_df_list:
        try:
            bank_df = pd.concat(bank_df_list, ignore_index=True)
            st.write("This is what the first spreadsheet looks like before cleaning:")
            st.write(bank_df)
        except Exception as e:
            st.error(f"Error combining bank statements: {e}")
            bank_df = None

    # Proceed only if bank_df is successfully created
    if 'bank_df' in locals() and bank_df is not None:
        try:
            if transaction_type == 'Receipts':
                # Cleaning the dataframe for Receipts
                bank_credit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Credit'].isna())]
                bank_credit_df = bank_credit_df[bank_credit_df['Date'].astype(str).str.lower() != 'date']
                bank_credit_df['Date'] = pd.to_datetime(bank_credit_df['Date'], errors='coerce')
                bank_credit_df['Date'].fillna(method='ffill', inplace=True)
                bank_credit_df = bank_credit_df[~bank_credit_df['Credit'].isna()]
                bank_credit_df = bank_credit_df.drop(['Debit', 'Balance'], axis=1, errors='ignore')

                # Ensure 'Details' column exists
                if 'Details' not in bank_credit_df.columns:
                    st.error("'Details' column not found in Receipts data.")
                    bank_credit_df = None
                else:
                    bank_credit_df['Credit'] = bank_credit_df['Credit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
                    bank_credit_df['Credit'] = bank_credit_df['Credit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)
                    bank_credit_df['Credit'] = pd.to_numeric(bank_credit_df['Credit'], errors='coerce')
                    bank_credit_df = bank_credit_df.dropna(subset=['Credit'])
                    bank_credit_df.reset_index(drop=True, inplace=True)

                    # Create a matching column by stripping whitespace and converting to lowercase
                    bank_credit_df['Match'] = bank_credit_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)

                    # Merge with previous year's analysis if uploaded
                    if analysis_df is not None:
                        if 'Details' not in analysis_df.columns:
                            st.error("'Details' column not found in previous year's analysis.")
                        else:
                            analysis_df['Match'] = analysis_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)
                            # Merge based on 'Match' column
                            bank_credit_df = pd.merge(bank_credit_df, analysis_df, on='Match', how='left', suffixes=('', '_previous'))
                    
                    # Drop 'Match' column from final DataFrame
                    bank_credit_df.drop(columns=['Match'], inplace=True, errors='ignore')

            elif transaction_type == 'Payments':
                # Cleaning the dataframe for Payments
                bank_debit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Debit'].isna())]
                bank_debit_df = bank_debit_df[bank_debit_df['Date'].astype(str).str.lower() != 'date']
                bank_debit_df['Date'] = pd.to_datetime(bank_debit_df['Date'], errors='coerce')
                bank_debit_df['Date'].fillna(method='ffill', inplace=True)
                bank_debit_df = bank_debit_df[~bank_debit_df['Debit'].isna()]
                bank_debit_df = bank_debit_df.drop(['Credit', 'Balance'], axis=1, errors='ignore')

                # Ensure 'Details' column exists
                if 'Details' not in bank_debit_df.columns:
                    st.error("'Details' column not found in Payments data.")
                    bank_debit_df = None
                else:
                    bank_debit_df['Debit'] = bank_debit_df['Debit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
                    bank_debit_df['Debit'] = bank_debit_df['Debit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)
                    bank_debit_df['Debit'] = pd.to_numeric(bank_debit_df['Debit'], errors='coerce')
                    bank_debit_df = bank_debit_df.dropna(subset=['Debit'])
                    bank_debit_df.reset_index(drop=True, inplace=True)

                    # Create a matching column by stripping whitespace and converting to lowercase
                    bank_debit_df['Match'] = bank_debit_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)

                    # Merge with previous year's analysis if uploaded
                    if analysis_df is not None:
                        if 'Details' not in analysis_df.columns:
                            st.error("'Details' column not found in previous year's analysis.")
                        else:
                            analysis_df['Match'] = analysis_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)
                            # Merge based on 'Match' column
                            bank_debit_df = pd.merge(bank_debit_df, analysis_df, on='Match', how='left', suffixes=('', '_previous'))
                    
                    # Drop 'Match' column from final DataFrame
                    bank_debit_df.drop(columns=['Match'], inplace=True, errors='ignore')

            # Select the appropriate DataFrame to display
            cleaned_df = bank_credit_df if transaction_type == 'Receipts' else bank_debit_df

            if cleaned_df is not None:
                # Inspect the data types of the DataFrame
                st.write("Inspecting the data types of the cleaned DataFrame:")
                st.write(cleaned_df.dtypes)

                # Convert any problematic columns to strings
                for col in cleaned_df.columns:
                    if cleaned_df[col].apply(lambda x: isinstance(x, (list, dict, set))).any():
                        cleaned_df[col] = cleaned_df[col].astype(str)

                # Optionally, display a sample of the DataFrame
                st.write("This is how the combined spreadsheet appears after cleaning:")
                try:
                    st.write(cleaned_df)
                except Exception as e:
                    st.error(f"Error displaying DataFrame: {e}")
                
                # Create a CSV from the cleaned DataFrame
                try:
                    csv = cleaned_df.to_csv(index=False)
                    buffer = io.BytesIO(csv.encode('utf-8'))

                    # Define the download button label and filename based on transaction type
                    download_label = "Download Cleaned Receipts Data" if transaction_type == 'Receipts' else "Download Cleaned Payments Data"
                    file_name = 'cleaned_receipts.csv' if transaction_type == 'Receipts' else 'cleaned_payments.csv'

                    st.download_button(
                        label=download_label,
                        data=buffer,
                        file_name=file_name,
                        mime='text/csv'
                    )
                except Exception as e:
                    st.error(f"Error creating download CSV: {e}")

        except Exception as e:
            st.error(f"Error during cleaning process: {e}")
