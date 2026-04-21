import os
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st


GDPR_COUNTRIES = [
    "AUSTRIA", "BELGIUM", "BULGARIA", "CROATIA", "CYPRUS", "CZECH REPUBLIC",
    "DENMARK", "ESTONIA", "Finland", "FRANCE", "GERMANY", "GREECE", "HUNGARY",
    "IRELAND", "ITALY", "LATVIA", "LITHUANIA", "LUXEMBOURG", "MALTA",
    "NETHERLANDS", "POLAND", "PORTUGAL", "ROMANIA", "SLOVAKIA", "SLOVENIA",
    "SPAIN", "SWEDEN", "UNITED KINGDOM"
]
GDPR_COUNTRIES_LOWER = [country.lower() for country in GDPR_COUNTRIES]


def processor(uploaded_file):
    df = pd.read_csv(uploaded_file)
    file_name = uploaded_file.name

    todays_date = datetime.now()
    try:
        todays_formatted_date = todays_date.strftime('%-m/%-d/%y')
    except ValueError:
        todays_formatted_date = f"{todays_date.month}/{todays_date.day}/{str(todays_date.year)[-2:]}"

    df['Verification Date'] = todays_formatted_date
    df.columns = df.columns.astype(str).str.strip()

    if "PW" in file_name:
        brandname = "PW"

        df.loc[:, 'PPW- LEGACY Last Engaged Date PW'] = todays_formatted_date
        df["Contract Mfg/Pkg Value Id"] = (
            df["Contract Mfg/Pkg Value Id"]
            .fillna('')
            .astype(str)
            .str.split(';')
            .apply(lambda x: [int(i) for i in x if i.isdigit()])
        )

        columns_to_check = ['PW Editorial', 'PW 3rd Party', 'PW Subscription', 'PW Webinar', "PW Special Report", "PW Survey", "PW Daily NL"]
        special_columns_to_check = ["CP 3rd Party", 'CM+P Newsletter']
        all_columns_to_check = columns_to_check + special_columns_to_check
        for column in columns_to_check:
            df[column] = df[column].astype(str).str.strip()

        rows_to_delete = (
            (df[all_columns_to_check].isin(["IN", 'OUT']).all(axis=1))
            | (df["PW Subscription"] == "OUT")
            | (df['Country'].str.lower().str.strip() == 'canada')
            | (df['Email Address'].str.endswith('.ca'))
        )
        df = df[~rows_to_delete]

        for column in all_columns_to_check:
            df[column] = df[column].replace(['IN', 'OUT'], ['+', '-'])

        df.sort_values(by="Customer Id", inplace=True)

        vals = [3548, 3552, 3551]

        for index, row in df.iterrows():
            country = str(row['Country']).lower().strip()
            contract_vals_check = any(val in row["Contract Mfg/Pkg Value Id"] for val in vals) if isinstance(row["Contract Mfg/Pkg Value Id"], list) else False

            if ((country in GDPR_COUNTRIES_LOWER) or (row["group_key"] == "EU")):
                if (row["PPW- GDPR Opt-In"] != "Y"):
                    for x in ['PW 3rd Party', 'PW Webinar', "PW Special Report", "PW Survey", "CP 3rd Party"]:
                        if df.at[index, x] not in ['+', '-']:
                            df.at[index, x] = "-"

                elif (row["PPW- GDPR Opt-In"] == "Y"):
                    if row["VCT Description"] == 3 or contract_vals_check:
                        if df.at[index, "CP 3rd Party"] not in ['+', '-']:
                            df.at[index, "CP 3rd Party"] = "IN"
                    else:
                        if df.at[index, "CP 3rd Party"] not in ['+', '-']:
                            df.at[index, "CP 3rd Party"] = "-"

                    for x in ['PW 3rd Party', 'PW Webinar', 'PW Special Report', 'PW Survey']:
                        if df.at[index, x] not in ['+', '-']:
                            df.at[index, x] = "IN"

            if row["VCT Description"] == 3 or contract_vals_check:
                if df.at[index, "CM+P Newsletter"] not in ['+', '-']:
                    df.at[index, "CM+P Newsletter"] = "IN"
            else:
                if row["VCT Description"] == 3 or contract_vals_check:
                    for x in ["CP 3rd Party", "CM+P Newsletter"]:
                        if df.at[index, x] not in ['+', '-']:
                            df.at[index, x] = "IN"
                else:
                    for x in ["CP 3rd Party", "CM+P Newsletter"]:
                        if df.at[index, x] not in ['+', '-']:
                            df.at[index, x] = "-"

            for column in all_columns_to_check:
                if df.at[index, column] not in ['+', '-']:
                    df.at[index, column] = "IN"

        df[all_columns_to_check] = df[all_columns_to_check].replace(['+', '-'], ['', ''])
        df.fillna('', inplace=True)
        df.drop(["PPW- GDPR Opt-In", "Contract Mfg/Pkg Value Id", "VCT Description"], axis=1, inplace=True)

        mask = df[all_columns_to_check].apply(lambda x: (x == '').all(), axis=1)
        df = df.drop(df[mask].index)

    elif "PFW" in file_name:
        brandname = "PFW"

        df.loc[:, 'PPFW LEGACY Last Engaged Date PFW'] = todays_formatted_date

        columns_to_check = ['PFW Editorial', 'PFW 3rd Party', 'PFW Subscription', 'PFW Webinar', "PFW Special Report", "PFW Survey", "PFW Newsletter"]
        for column in columns_to_check:
            df[column] = df[column].astype(str).str.strip()

        rows_to_delete = (
            (df[columns_to_check].isin(["IN", 'OUT']).all(axis=1))
            | (df["PFW Subscription"] == "OUT")
            | (df['Country'].str.lower().str.strip() == 'canada')
            | (df['Email Address'].str.endswith('.ca'))
        )
        df = df[~rows_to_delete]

        for column in columns_to_check:
            df[column] = df[column].replace(['IN', 'OUT'], ['+', '-'])

        for index, row in df.iterrows():
            country = str(row['Country']).lower().strip()
            if ((country in GDPR_COUNTRIES_LOWER) or (row["group_key"] == "EU")):
                gdpr_sensitive_columns = ['PFW 3rd Party', 'PFW Webinar', 'PFW Special Report', 'PFW Survey']
                if (row["PPFW- GDPR Opt-In"] != "Y"):
                    for column in gdpr_sensitive_columns:
                        if df.at[index, column] not in ['+', '-']:
                            df.at[index, column] = "-"
                elif (row["PPFW- GDPR Opt-In"] == "Y"):
                    for column in gdpr_sensitive_columns:
                        if df.at[index, column] not in ['+', '-']:
                            df.at[index, column] = "IN"

            for column in columns_to_check:
                if df.at[index, column] not in ['+', '-']:
                    df.at[index, column] = "IN"

        df[columns_to_check] = df[columns_to_check].replace(['+', '-'], ['', ''])
        df.fillna('', inplace=True)
        df.drop("PPFW- GDPR Opt-In", axis=1, inplace=True)

        mask = df[columns_to_check].apply(lambda x: (x == '').all(), axis=1)
        df = df.drop(df[mask].index)

    elif "HCP" in file_name:
        brandname = "HCP"

        df.loc[:, 'PHCP- LEGACY Last Engaged Date HCP'] = todays_formatted_date

        columns_to_check = ['HCP Editorial', 'HCP 3rd Party', 'HCP Subscription', 'HCP Webinar', "HCP Survey", "HCP Newsletter"]
        for column in columns_to_check:
            df[column] = df[column].astype(str).str.strip()

        rows_to_delete = (
            (df[columns_to_check].isin(["IN", 'OUT']).all(axis=1))
            | (df["HCP Subscription"] == "OUT")
            | (df['Country'].str.lower().str.strip() == 'canada')
            | (df['Email Address'].str.endswith('.ca'))
        )
        df = df[~rows_to_delete]

        for column in columns_to_check:
            df[column] = df[column].replace(['IN', 'OUT'], ['+', '-'])

        for index, row in df.iterrows():
            country = str(row['Country']).lower().strip()
            if ((country in GDPR_COUNTRIES_LOWER) or (row["group_key"] == "EU")):
                gdpr_sensitive_columns = ['HCP 3rd Party', 'HCP Webinar', 'HCP Survey']
                if (row["PHCP- GDPR Opt-In"] != "Y"):
                    for column in gdpr_sensitive_columns:
                        if df.at[index, column] not in ['+', '-']:
                            df.at[index, column] = "-"
                elif (row["PHCP- GDPR Opt-In"] == "Y"):
                    for column in gdpr_sensitive_columns:
                        if df.at[index, column] not in ['+', '-']:
                            df.at[index, column] = "IN"

            for column in columns_to_check:
                if df.at[index, column] not in ['+', '-']:
                    df.at[index, column] = "IN"

        df[columns_to_check] = df[columns_to_check].replace(['+', '-'], ['', ''])
        df.fillna('', inplace=True)
        df.drop("PHCP- GDPR Opt-In", axis=1, inplace=True)

        mask = df[columns_to_check].apply(lambda x: (x == '').all(), axis=1)
        df = df.drop(df[mask].index)

    elif "OEM" in file_name:
        brandname = "OEM"

        df.loc[:, 'POEM- LEGACY Last Engaged Date PP OEM'] = todays_formatted_date

        columns_to_check = ['OEM Editorial', 'OEM 3rd Party', 'OEM Subscription', "OEM Survey", "OEM Special Report", "OEM Newsletter"]
        for column in columns_to_check:
            df[column] = df[column].astype(str).str.strip()

        rows_to_delete = (
            (df[columns_to_check].isin(["IN", 'OUT']).all(axis=1))
            | (df["OEM Subscription"] == "OUT")
            | (df['Country'].str.lower().str.strip() == 'canada')
            | (df['Email Address'].str.endswith('.ca'))
        )
        df = df[~rows_to_delete]

        for column in columns_to_check:
            df[column] = df[column].replace(['IN', 'OUT'], ['+', '-'])

        for index, row in df.iterrows():
            country = str(row['Country']).lower().strip()
            if ((country in GDPR_COUNTRIES_LOWER) or (row["group_key"] == "EU")):
                gdpr_sensitive_columns = ['OEM 3rd Party', 'OEM Special Report', 'OEM Survey']
                if (row["POEM- GDPR Opt-In"] != "Y"):
                    for column in gdpr_sensitive_columns:
                        if df.at[index, column] not in ['+', '-']:
                            df.at[index, column] = "-"
                elif (row["POEM- GDPR Opt-In"] == "Y"):
                    for column in gdpr_sensitive_columns:
                        if df.at[index, column] not in ['+', '-']:
                            df.at[index, column] = "IN"

            for column in columns_to_check:
                if df.at[index, column] not in ['+', '-']:
                    df.at[index, column] = "IN"

        df[columns_to_check] = df[columns_to_check].replace(['+', '-'], ['', ''])
        df.fillna('', inplace=True)
        df.drop("POEM- GDPR Opt-In", axis=1, inplace=True)

        mask = df[columns_to_check].apply(lambda x: (x == '').all(), axis=1)
        df = df.drop(df[mask].index)

    elif "Mundo" in file_name or "MUNDO" in file_name:
        brandname = "Mundo"

        df.loc[:, 'WATSON- Last Engaged Date LA'] = todays_formatted_date

        columns_to_check = ['Mundo EXPO PACK NL', 'Mundo Editorial', 'Mundo 3rd Party', "Mundo Webinar"]
        for column in columns_to_check:
            df[column] = df[column].astype(str).str.strip()

        rows_to_delete = (
            (df[columns_to_check].isin(["IN", 'OUT']).all(axis=1))
            | (df["Mundo Editorial"] == "OUT")
            | (df['Country'].str.lower().str.strip() == 'canada')
            | (df['Email Address'].str.endswith('.ca'))
        )
        df = df[~rows_to_delete]

        for column in columns_to_check:
            df[column] = df[column].replace(['IN', 'OUT'], ['+', '-'])

        for index, row in df.iterrows():
            country = str(row['Country']).lower().strip()
            if country in GDPR_COUNTRIES_LOWER:
                for column in ["Mundo 3rd Party", "Mundo Webinar"]:
                    if df.at[index, column] not in ['+', '-']:
                        df.at[index, column] = "-"

            for column in columns_to_check:
                if df.at[index, column] not in ['+', '-']:
                    df.at[index, column] = "IN"

        df[columns_to_check] = df[columns_to_check].replace(['+', '-'], ['', ''])
        df.fillna('', inplace=True)

        mask = df[columns_to_check].apply(lambda x: (x == '').all(), axis=1)
        df = df.drop(df[mask].index)

    else:
        raise TypeError("The file name does not contain any of our brand assets!")

    df["Promo Code"] = f"{brandname}_Onboarding"
    df.drop("Country", axis=1, inplace=True)

    if brandname != "Mundo":
        df.drop("group_key", axis=1, inplace=True)

    file_save_date = todays_date.strftime('%Y%m%d')
    output_file = f"{brandname}_Onboarding_Output_{file_save_date}.csv"

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return output_file, csv_bytes


def process_uploaded_files(uploaded_files):
    output_files = []
    errors = []

    for uploaded_file in uploaded_files:
        if uploaded_file is None:
            continue
        try:
            output_file, csv_bytes = processor(uploaded_file)
            output_files.append((output_file, csv_bytes))
        except Exception as exc:
            errors.append(f"{uploaded_file.name}: {exc}")

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for output_file, csv_bytes in output_files:
            zipf.writestr(output_file, csv_bytes)
        if errors:
            zipf.writestr("ERRORS.txt", "\n".join(errors))

    memory_file.seek(0)
    return memory_file.getvalue(), output_files, errors


st.set_page_config(page_title="Email Onboarding Opt In Processor", layout="centered")

st.title("Email Onboarding Opt In Processor")
st.write("Upload one or more CSV files. The app processes each file and returns a ZIP of the outputs.")

with st.expander("What this app does", expanded=True):
    st.markdown(
        """
- Detects the brand from the filename (`PW`, `PFW`, `HCP`, `OEM`, or `Mundo`)
- Applies the same onboarding/GDPR logic from your Flask app
- Creates one processed CSV per uploaded file
- Bundles all outputs into a single ZIP download
        """
    )

uploaded_files = st.file_uploader(
    "Upload CSV files",
    type=["csv"],
    accept_multiple_files=True,
)

if st.button("Process files", type="primary"):
    if not uploaded_files:
        st.error("Please upload at least one CSV file.")
    else:
        with st.spinner("Processing files..."):
            zip_bytes, output_files, errors = process_uploaded_files(uploaded_files)

        if output_files:
            st.success(f"Processed {len(output_files)} file(s).")
            st.download_button(
                label="Download ZIP",
                data=zip_bytes,
                file_name="processed_onboarding_files.zip",
                mime="application/zip",
            )

            with st.expander("Processed files"):
                for name, _ in output_files:
                    st.write(f"- {name}")

        if errors:
            st.warning("Some files could not be processed. They are also included in ERRORS.txt inside the ZIP.")
            for err in errors:
                st.write(f"- {err}")
