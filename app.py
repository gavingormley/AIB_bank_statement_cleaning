import streamlit as st
import pandas as pd
import re

# Function to fix numbers with issues in formatting
def fix_numbers(num_str):
    # Fix decimal place issues for pattern 1
    pattern1 = r'[:;·,](\d{2}$)'  # Matches :, ;, ·, or , followed by two digits

    # Fix numbers for pattern 2
    pattern2 = r'(\d{1,3})[:;·,](\d{3})'  # Matches three digits, a comma, and another three digits

    # First, apply pattern 1
    num_str = re.sub(pattern1, r'.\1', num_str)

    # Then, apply pattern 2 (removing the comma)
    num_str = re.sub(pattern2, r'\1\2', num_str)

    return num_str

# Initialize Session State for uploaded files and analysis
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'previous_year_analysis' not in st.session_state:
    st.session_state.previous_year_analysis = None

st.title("AIB Bank Statement Cleaner")
st.write("**Note:** Files are arranged alphabetically. If necessary, rename them according to their chronological order (e.g., '1 Jan-May', '2 Jun-Dec').")

# Section for Selecting Transaction Type
st.header("Select Transaction Type")
transaction_type = st.selectbox("Select Transaction Type:", ('Receipts', 'Payments'), key='transaction_type_selector')

# Section for Uploading Previous Year's Analysis
st.header("Previous Year's Analysis (Optional)")
add_previous_year = st.checkbox("Do you want to upload the previous year's analysis?")

if add_previous_year:
    uploaded_analysis = st.file_uploader("Upload previous year's analysis", type=['xlsx', 'xls'], key='analysis_uploader')
    
    if uploaded_analysis:
        def process_previous_analysis(uploaded_analysis, transaction_type):
            try:
                sheet_name = 'ReceiptsAnalysis' if transaction_type == 'Receipts' else 'Payments Analysis'
                
                temp_df = pd.read_excel(uploaded_analysis, sheet_name=sheet_name, header=None)
                header_row_indices = temp_df[temp_df.iloc[:, 0].astype(str).str.contains("Date", case=False, na=False)].index.tolist()
                if not header_row_indices:
                    st.error("No header row containing 'Date' found in the analysis file.")
                    return None
                header_row = header_row_indices[0]
                
                temp_df.columns = temp_df.iloc[header_row]
                temp_df = temp_df.drop(range(header_row + 1)).reset_index(drop=True)
                
                required_columns = ['Details', 'Analysis']
                for col in required_columns:
                    if col not in temp_df.columns:
                        st.error(f"'{col}' column not found in the analysis file.")
                        return None
                
                analysis_df = temp_df[required_columns].copy()
                analysis_df['Match'] = analysis_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)
                
                analysis_mapping = (
                    analysis_df.groupby('Match')['Analysis']
                    .agg(lambda x: x.value_counts().index[0])
                    .reset_index()
                )
                
                return analysis_mapping
            except Exception as e:
                st.error(f"Error processing previous year's analysis: {e}")
                return None

        analysis_df_processed = process_previous_analysis(uploaded_analysis, transaction_type)
        if analysis_df_processed is not None:
            st.session_state.previous_year_analysis = analysis_df_processed
            st.success("Previous year's analysis loaded successfully.")
        else:
            st.session_state.previous_year_analysis = None

# Section for Uploading Current Year's Bank Statements
st.header("Upload Current Year's Bank Statements")
uploaded_files = st.file_uploader("Upload current year's files", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, key='current_files_uploader')

if uploaded_files:
    st.session_state.uploaded_files.extend(uploaded_files)
    st.write("**Uploaded Files:**")
    for file in st.session_state.uploaded_files:
        st.write(f"- {file.name}")

if st.button("Clear Uploaded Files"):
    st.session_state.uploaded_files.clear()
    st.session_state.previous_year_analysis = None
    st.success("Uploaded files and previous year's analysis cleared.")

if st.button("Process Statements", key='process_button', help="Click to process the uploaded bank statements."):
    if st.session_state.uploaded_files:
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
        if bank_df_list:
            try:
                bank_df = pd.concat(bank_df_list, ignore_index=True)
                st.write("**Preview of Combined Bank Statements Before Cleaning:**")
                st.dataframe(bank_df)
            except Exception as e:
                st.error(f"Error combining bank statements: {e}")
                st.stop()

            def clean_data(bank_df, transaction_type, analysis_mapping=None):
                try:
                    if transaction_type == 'Receipts':
                        bank_credit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Credit'].isna())]
                        bank_credit_df = bank_credit_df[bank_credit_df['Date'].astype(str).str.lower() != 'date']
                        bank_credit_df['Date'] = pd.to_datetime(bank_credit_df['Date'], errors='coerce')
                        bank_credit_df['Date'].fillna(method='ffill', inplace=True)
                        bank_credit_df = bank_credit_df[~bank_credit_df['Credit'].isna()]
                        bank_credit_df = bank_credit_df.drop(['Debit', 'Balance'], axis=1, errors='ignore')

                        if 'Details' not in bank_credit_df.columns:
                            st.error("'Details' column not found in Receipts data.")
                            return None

                        bank_credit_df['Credit'] = bank_credit_df['Credit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
                        bank_credit_df['Credit'] = bank_credit_df['Credit'].apply(fix_numbers)
                        bank_credit_df['Credit'] = pd.to_numeric(bank_credit_df['Credit'], errors='coerce')
                        bank_credit_df = bank_credit_df.dropna(subset=['Credit'])
                        bank_credit_df.reset_index(drop=True, inplace=True)

                        bank_credit_df['Match'] = bank_credit_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)

                        if analysis_mapping is not None:
                            bank_credit_df = bank_credit_df.merge(
                                analysis_mapping, left_on='Match', right_on='Match', how='left'
                            )

                        bank_credit_df.drop(columns=['Match'], inplace=True)
                        return bank_credit_df

                    elif transaction_type == 'Payments':
                        bank_debit_df = bank_df[~(bank_df['Date'].isna() & bank_df['Debit'].isna())]
                        bank_debit_df = bank_debit_df[bank_debit_df['Date'].astype(str).str.lower() != 'date']
                        bank_debit_df['Date'] = pd.to_datetime(bank_debit_df['Date'], errors='coerce')
                        bank_debit_df['Date'].fillna(method='ffill', inplace=True)
                        bank_debit_df = bank_debit_df[~bank_debit_df['Debit'].isna()]
                        bank_debit_df = bank_debit_df.drop(['Credit', 'Balance'], axis=1, errors='ignore')

                        if 'Details' not in bank_debit_df.columns:
                            st.error("'Details' column not found in Payments data.")
                            return None

                        bank_debit_df['Debit'] = bank_debit_df['Debit'].astype(str).str.replace(r'[^0-9,\.]', '', regex=True)
                        bank_debit_df['Debit'] = bank_debit_df['Debit'].apply(fix_numbers)
                        bank_debit_df['Debit'] = pd.to_numeric(bank_debit_df['Debit'], errors='coerce')
                        bank_debit_df = bank_debit_df.dropna(subset=['Debit'])
                        bank_debit_df.reset_index(drop=True, inplace=True)

                        bank_debit_df['Match'] = bank_debit_df['Details'].astype(str).str.lower().str.replace(r'\s+', '', regex=True)

                        if analysis_mapping is not None:
                            bank_debit_df = bank_debit_df.merge(
                                analysis_mapping, left_on='Match', right_on='Match', how='left'
                            )

                        bank_debit_df.drop(columns=['Match'], inplace=True)
                        return bank_debit_df

                except Exception as e:
                    st.error(f"Error during data cleaning: {e}")
                    return None

            cleaned_data = clean_data(bank_df, transaction_type, st.session_state.previous_year_analysis)

            if cleaned_data is not None:
                st.write("**Preview of Cleaned Data:**")
                st.dataframe(cleaned_data)

    else:
        st.warning("Please upload bank statements before processing.")
