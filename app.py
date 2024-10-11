import streamlit as st
import pandas as pd
import pandas as pd
from pathlib import Path
from datetime import timedelta
import os
import io

# Add a button to clear all uploaded data
if st.button("Clear All Uploaded Data"):
    # Clear session state for uploaded files and analysis
    st.session_state.uploaded_files = []
    st.session_state.analysis_df = None
    st.success("All uploaded data has been cleared.")

# Initialize Session State for uploaded files and analysis
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'analysis_df' not in st.session_state:
    st.session_state.analysis_df = None

st.title("AIB Bank Statement Cleaner")
st.write("**Note:** Files are arranged alphabetically. If necessary, rename them according to their chronological order (e.g., '1 Jan-May', '2 Jun-Dec').")

# Section for Uploading Previous Year's Analysis
st.header("Previous Year's Analysis (Optional)")
add_previous_year = st.checkbox("Do you want to upload the previous year's analysis?")

if add_previous_year:
    uploaded_analysis = st.file_uploader("Upload previous year's analysis", type=['xlsx', 'xls'], key='analysis_uploader')
    
    if uploaded_analysis:
        def process_previous_analysis(uploaded_analysis, transaction_type):
            try:
                sheet_name = 'ReceiptsAnalysis' if transaction_type == 'Receipts' else 'Payments Analysis'
                
                # Read the specified sheet without assuming headers
                temp_df = pd.read_excel(uploaded_analysis, sheet_name=sheet_name, header=None)
                
                # Find the header row where the first column contains "Date" (case-insensitive)
                header_row_indices = temp_df[temp_df.iloc[:, 0].astype(str).str.contains("Date", case=False, na=False)].index.tolist()
                if not header_row_indices:
                    st.error("No header row containing 'Date' found in the analysis file.")
                    return None
                header_row = header_row_indices[0]
                
                # Set the header
                temp_df.columns = temp_df.iloc[header_row]
                temp_df = temp_df.drop(range(header_row + 1)).reset_index(drop=True)
                
                # Ensure only 'Details' and 'Analysis' columns are present
                required_columns = ['Details', 'Analysis']
                for col in required_columns:
                    if col not in temp_df.columns:
                        st.error(f"'{col}' column not found in the analysis file.")
                        return None
                
                # Select only 'Details' and 'Analysis' columns
                analysis_df = temp_df[required_columns].copy()
                
                # Create the 'Match' column by stripping whitespace and converting to lowercase
                analysis_df['Match'] = analysis_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)
                
                return analysis_df
            except Exception as e:
                st.error(f"Error processing previous year's analysis: {e}")
                return None

        # Get the selected transaction type for analysis processing
        transaction_type_analysis = st.selectbox("Select Transaction Type for Analysis:", ('Receipts', 'Payments'), key='analysis_transaction_type')
        
        analysis_df_processed = process_previous_analysis(uploaded_analysis, transaction_type_analysis)
        if analysis_df_processed is not None:
            st.session_state.analysis_df = analysis_df_processed
            st.success("Previous year's analysis loaded successfully.")
        else:
            st.session_state.analysis_df = None

# Section for Uploading Current Year's Bank Statements
st.header("Upload Current Year's Bank Statements")
uploaded_files = st.file_uploader("Upload current year's files", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, key='current_files_uploader')

if uploaded_files:
    # Store uploaded files in session state if not already stored
    if not st.session_state.uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        st.success("Files uploaded successfully. They will be available for processing.")
    else:
        # If new files are uploaded, replace the existing ones
        if st.session_state.uploaded_files != uploaded_files:
            st.session_state.uploaded_files = uploaded_files
            st.success("Uploaded files have been updated.")
    
    # Display the names of the uploaded files
    st.write("**Uploaded Files:**")
    for file in st.session_state.uploaded_files:
        st.write(f"- {file.name}")
    
    # Section for Selecting Transaction Type and Processing
    st.header("Process Transactions")
    transaction_type = st.selectbox("Select Transaction Type to Process:", ('Receipts', 'Payments'), key='transaction_type_selector')
    
    # Button to Trigger Processing
    if st.button("Process Selected Transaction Type"):
        def process_bank_files(uploaded_files):
            bank_df_list = []
            for file in uploaded_files:
                try:
                    if file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file)
                    bank_df_list.append(df)
                except Exception as e:
                    st.warning(f"Failed to read {file.name}: {e}")
            return bank_df_list

        bank_df_list = process_bank_files(st.session_state.uploaded_files)

        # Combine all bank statements into one DataFrame
        if bank_df_list:
            try:
                bank_df = pd.concat(bank_df_list, ignore_index=True)
                st.write("**Preview of Combined Bank Statements Before Cleaning:**")
                st.dataframe(bank_df.head())  # Display only the first few rows for brevity
            except Exception as e:
                st.error(f"Error combining bank statements: {e}")
                st.stop()

            # Cleaning Function
            def clean_data(bank_df, transaction_type, analysis_df=None):
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
                            return None
                        
                        # Clean 'Credit' column
                        bank_credit_df['Credit'] = bank_credit_df['Credit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
                        bank_credit_df['Credit'] = bank_credit_df['Credit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)
                        bank_credit_df['Credit'] = pd.to_numeric(bank_credit_df['Credit'], errors='coerce')
                        bank_credit_df = bank_credit_df.dropna(subset=['Credit'])
                        bank_credit_df.reset_index(drop=True, inplace=True)

                        # Create a matching column by stripping whitespace and converting to lowercase
                        bank_credit_df['Match'] = bank_credit_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)

                        # Merge with previous year's analysis if available
                        if analysis_df is not None:
                            bank_credit_df = pd.merge(
                                bank_credit_df,
                                analysis_df[['Match', 'Analysis']],
                                on='Match',
                                how='left'
                            )

                        # Drop 'Match' column from final DataFrame
                        bank_credit_df.drop(columns=['Match'], inplace=True, errors='ignore')

                        return bank_credit_df

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
                            return None
                        
                        # Clean 'Debit' column
                        bank_debit_df['Debit'] = bank_debit_df['Debit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
                        bank_debit_df['Debit'] = bank_debit_df['Debit'].str.replace(r'(\d+),(\d+)', r'\1.\2', regex=True)
                        bank_debit_df['Debit'] = pd.to_numeric(bank_debit_df['Debit'], errors='coerce')
                        bank_debit_df = bank_debit_df.dropna(subset=['Debit'])
                        bank_debit_df.reset_index(drop=True, inplace=True)

                        # Create a matching column by stripping whitespace and converting to lowercase
                        bank_debit_df['Match'] = bank_debit_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)

                        # Merge with previous year's analysis if available
                        if analysis_df is not None:
                            bank_debit_df = pd.merge(
                                bank_debit_df,
                                analysis_df[['Match', 'Analysis']],
                                on='Match',
                                how='left'
                            )

                        # Drop 'Match' column from final DataFrame
                        bank_debit_df.drop(columns=['Match'], inplace=True, errors='ignore')

                        return bank_debit_df

                except Exception as e:
                    st.error(f"Error during cleaning process: {e}")
                    return None

            # Clean the data based on the selected transaction type
            cleaned_df = clean_data(bank_df, transaction_type, st.session_state.analysis_df)

            if cleaned_df is not None:
                st.write("**This is how the combined spreadsheet appears after cleaning:**")
                try:
                    st.dataframe(cleaned_df)
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
                    st.error(f"Error generating download link: {e}")
            else:
                st.error("No data available after cleaning.")
