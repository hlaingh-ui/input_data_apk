"""
Streamlit Statistics App
Single-file Streamlit app that lets users:
 1. Choose how many variables they want.
 2. Define variable names and types (short text, long text, number, date).
 3. Enter data row-by-row using generated input widgets.
 4. Upload a CSV (validated against the schema) to bulk add rows.
 5. See the collected data in a table and download it as CSV.

How to run:
 1. Make sure you have Python 3.8+ installed.
 2. Install dependencies:
      pip install streamlit pandas
 3. Run the app:
      streamlit run streamlit_statistics_app.py

Notes:
 - This app uses st.session_state to persist schema and rows while the app runs.
 - If you want to persist between restarts, you'll need to save to a file/db.

"""

import streamlit as st
import pandas as pd
from io import StringIO
import datetime

# ----------------------------- Helpers -----------------------------

def init_state():
    if 'schema' not in st.session_state:
        st.session_state.schema = []  # list of {'name':..., 'type':...}
    if 'rows' not in st.session_state:
        st.session_state.rows = []  # list of dict rows
    if 'num_vars' not in st.session_state:
        st.session_state.num_vars = 3
    if 'temp_fields' not in st.session_state:
        st.session_state.temp_fields = {}


def schema_to_dataframe():
    if not st.session_state.schema:
        return pd.DataFrame()
    cols = [s['name'] for s in st.session_state.schema]
    return pd.DataFrame(st.session_state.rows, columns=cols)


def validate_and_cast(row_dict):
    """Validate a single row (dict) using schema, cast types if needed.
    Returns (ok: bool, row_or_error: dict/str)
    """
    out = {}
    for field in st.session_state.schema:
        name = field['name']
        ftype = field['type']
        val = row_dict.get(name, None)
        # empty-string handling: treat as None
        if isinstance(val, str) and val.strip() == '':
            val = None
        if val is None:
            out[name] = None
            continue
        try:
            if ftype == 'number':
                # allow integer or float
                out[name] = float(val)
            elif ftype == 'date':
                if isinstance(val, datetime.date):
                    out[name] = val
                else:
                    out[name] = pd.to_datetime(val).date()
            else:  # short text or long text
                out[name] = str(val)
        except Exception as e:
            return False, f"Error casting field '{name}' to {ftype}: {e}"
    return True, out


# ----------------------------- UI -----------------------------

init_state()

st.set_page_config(page_title='Statistics data-entry app', layout='wide')
st.title('📊 Simple Statistics App (Streamlit)')
st.write('Create a simple schema, enter rows, preview table, and download CSV.')

# Optional metadata at top
with st.expander('Developer / App metadata (optional)', expanded=False):
    dev_link = st.text_input('Developer CV or project link (optional)', '')

st.markdown('---')

# Step 1: choose number of variables
col1, col2 = st.columns([1,3])
with col1:
    n = st.number_input('How many variables?', min_value=1, max_value=50, value=st.session_state.num_vars, step=1)
    if n != st.session_state.num_vars:
        st.session_state.num_vars = int(n)

with col2:
    st.info('After setting the number, click **Create fields** to generate inputs for variable names and types.')

if st.button('Create fields'):
    # initialize temp fields
    st.session_state.temp_fields = {}
    for i in range(st.session_state.num_vars):
        st.session_state.temp_fields[f'name_{i}'] = ''
        st.session_state.temp_fields[f'type_{i}'] = 'short text'
    st.rerun()

# Show variable creation UI if temp_fields exists or schema empty
show_fields = True if st.session_state.schema == [] or st.session_state.temp_fields else True
if show_fields:
    st.subheader('Define variables (name and type)')
    placeholder = st.container()
    with placeholder:
        fields_changed = False
        for i in range(st.session_state.num_vars):
            cols = st.columns([3,2])
            name_key = f'name_{i}'
            type_key = f'type_{i}'
            current_name = st.session_state.temp_fields.get(name_key, '')
            current_type = st.session_state.temp_fields.get(type_key, 'short text')
            new_name = cols[0].text_input(f'Variable #{i+1} name', value=current_name, key=name_key)
            new_type = cols[1].selectbox('Type', options=['short text','long text','number','date'], index=['short text','long text','number','date'].index(current_type), key=type_key)
            # update temp_fields
            if st.session_state.temp_fields.get(name_key) != new_name or st.session_state.temp_fields.get(type_key) != new_type:
                st.session_state.temp_fields[name_key] = new_name
                st.session_state.temp_fields[type_key] = new_type
                fields_changed = True

    if st.button('Save schema'):
        # collect names/types, validate
        new_schema = []
        seen = set()
        ok = True
        msg = ''
        for i in range(st.session_state.num_vars):
            nm = st.session_state.temp_fields.get(f'name_{i}', '').strip()
            tp = st.session_state.temp_fields.get(f'type_{i}', 'short text')
            if nm == '':
                ok = False
                msg = f'Variable name #{i+1} is empty.'
                break
            if nm in seen:
                ok = False
                msg = f"Duplicate variable name: '{nm}'."
                break
            seen.add(nm)
            new_schema.append({'name': nm, 'type': tp})
        if not ok:
            st.error(msg)
        else:
            st.session_state.schema = new_schema
            # create empty rows list and reset temp fields
            st.session_state.rows = []
            st.session_state.temp_fields = {}
            st.success('Schema saved — now enter data below.')
            st.rerun()

# Show current schema
if st.session_state.schema:
    st.subheader('Current schema')
    schema_df = pd.DataFrame(st.session_state.schema)
    st.table(schema_df)

    # Buttons: reset schema
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button('Reset schema and data'):
            st.session_state.schema = []
            st.session_state.rows = []
            st.rerun()
    with c2:
        if st.button('Clear data (keep schema)'):
            st.session_state.rows = []
            st.rerun()
    with c3:
        st.write('')

    st.markdown('---')

    # Step 2: Data entry form
    st.subheader('Enter a new row')
    with st.form('add_row_form'):
        new_row = {}
        for field in st.session_state.schema:
            nm = field['name']
            tp = field['type']
            if tp == 'short text':
                new_row[nm] = st.text_input(nm, key=f'input_{nm}')
            elif tp == 'long text':
                new_row[nm] = st.text_area(nm, key=f'input_{nm}')
            elif tp == 'number':
                # allow empty input: we'll store as None if blank
                val = st.text_input(nm + ' (number)', key=f'input_{nm}')
                new_row[nm] = val
            elif tp == 'date':
                new_row[nm] = st.date_input(nm + ' (date)', key=f'input_{nm}', value=None)
        submitted = st.form_submit_button('Add row')
        if submitted:
            ok, result = validate_and_cast(new_row)
            if not ok:
                st.error(result)
            else:
                st.session_state.rows.append(result)
                st.success('Row added.')
                st.rerun()

    # Step 3: Bulk upload via CSV
    st.subheader('Bulk add: upload CSV (columns must match schema names)')
    uploaded = st.file_uploader('Upload CSV file', type=['csv'])
    if uploaded is not None:
        try:
            df_new = pd.read_csv(uploaded)
            expected_cols = [s['name'] for s in st.session_state.schema]
            missing = [c for c in expected_cols if c not in df_new.columns]
            extra = [c for c in df_new.columns if c not in expected_cols]
            if missing:
                st.error(f'Missing columns in uploaded CSV: {missing}')
            else:
                # take only expected cols in schema order
                df_new = df_new[expected_cols]
                # validate and cast each row
                bad_rows = []
                added = 0
                for _, r in df_new.iterrows():
                    rowdict = r.to_dict()
                    ok, res = validate_and_cast(rowdict)
                    if not ok:
                        bad_rows.append(str(res))
                    else:
                        st.session_state.rows.append(res)
                        added += 1
                if bad_rows:
                    st.warning(f"Some rows failed to import (showing up to 5 errors): {bad_rows[:5]}")
                st.success(f'Imported {added} rows from CSV.')
                st.rerun()
        except Exception as e:
            st.error(f'Error reading CSV: {e}')

    # Show table and download
    st.subheader('Data table')
    df = schema_to_dataframe()
    if df.empty:
        st.info('No rows yet — add some using the form above or upload a CSV.')
    else:
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button('Download CSV', data=csv, file_name='data.csv', mime='text/csv')

else:
    st.info('Define a schema to get started (choose number of variables and click Create fields).')

# Footer
st.markdown('---')
st.write('Built with ❤️ — Streamlit + pandas')


# End of file
