
# retail_sales_app_updated.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import requests
import pathlib
import json
from datetime import datetime, date
from io import BytesIO

# Set Streamlit page config
st.set_page_config(
    page_icon=':bar-chart:',
    menu_items={
        'About': "# Jon Carrasco \n mail@joncarrasco.com",
    },
)

# Hide footer
hide_menu_style = """
    <style>
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# Improved: Use with open() and cache the result
@st.cache_data
def get_colors():
    with open('./assets/mm_colors.json') as f:
        data = json.load(f)
    return data['mm_color']

@st.cache_data
def get_category():
    with open('./assets/retail_categories.json') as f:
        data = json.load(f)
    return data

# Improved: Error handling and user feedback
def get_MARTS_data(api_key='', date_from='2000', date_to=str(date.today().year)):
    if not api_key:
        st.warning("API key not provided. Data request may fail.")
    link = f'https://api.census.gov/data/timeseries/eits/marts?get=data_type_code,time_slot_id,seasonally_adj,category_code,cell_value,error_data&for=us:*&time=from+{date_from}+to+{date_to}&key={api_key}'
    st.info('Making the API request for MARTS...')
    response = requests.get(link)
    response.raise_for_status()
    data = response.json()
    st.success('Data request complete.')
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# Clean and pivot retail sales data
def clean_retail_sales_data(df, seasonally_adj='yes', category=None):
    st.info('Transforming and pivoting data...')
    if category is None:
        category = get_category()
    df['on_report'] = df['category_code'].replace(category['on_report'])
    df['short'] = df['category_code'].replace(category['short'])
    df['long'] = df['category_code'].replace(category['long'])
    x = df.loc[(df['data_type_code'] == 'SM') & (df['seasonally_adj'] == seasonally_adj)][['short', 'cell_value', 'time']]
    x['cell_value'] = x['cell_value'].astype(int)
    x['Date'] = pd.to_datetime(x['time'], format='%Y-%m').dt.date
    x = x.pivot(index='Date', columns='short')
    st.success('Data transformation complete.')
    return x['cell_value']

def gen_ohlc(MARTS, window='MM'):
    ohlc = pd.DataFrame()
    if window == 'MM':
        df_pct = MARTS.pct_change(1).tail(13)
    elif window == 'QQ':
        df_pct = MARTS.pct_change(3).tail(13)
    elif window == 'YY':
        df_pct = MARTS.pct_change(12).tail(13)
    ohlc['Level'] = MARTS.iloc[-1]
    ohlc['Open'] = df_pct.iloc[1]
    ohlc['High'] = df_pct.max()
    ohlc['Low'] = df_pct.min()
    ohlc['Close'] = df_pct.iloc[-1]
    return ohlc

@st.cache_data
def load_data():
    data = get_MARTS_data()
    return clean_retail_sales_data(data)

@st.cache_data
def to_excel(dfs):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for sheet_name, df in dfs.items():
            df.columns = [str(c)[:31].replace(":", "_") for c in df.columns]
            df.to_excel(writer, sheet_name=sheet_name, index=True, float_format="%.5f")
            worksheet = writer.sheets[sheet_name]
            for column in df:
                column_length = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column) + 1
                worksheet.set_column(col_idx, col_idx, column_length)
            worksheet.set_column(0, 0, 10)
    return buffer

# UI title
st.title("Retail Sales Data")
st.caption("An application to download and analyze MARTS data from the US Census.")

if 'download' not in st.session_state:
    st.session_state['download'] = False

if st.button('Download Data'):
    st.session_state['download'] = True

if st.session_state['download']:
    with st.spinner("Downloading and transforming data..."):
        MARTS = load_data()
        dfs = {
            'Retail Sales': MARTS,
            'M-M Pct Change': MARTS.pct_change(1),
            'M-M Change': MARTS.diff(1),
            'Q-Q Pct Change': MARTS.pct_change(3),
            'Q-Q Change': MARTS.diff(3),
            'Y-Y Pct Change': MARTS.pct_change(12),
            'Y-Y Change': MARTS.diff(12),
            'OHLC MM': gen_ohlc(MARTS, window='MM'),
            'OHLC QQ': gen_ohlc(MARTS, window='QQ'),
            'OHLC YY': gen_ohlc(MARTS, window='YY'),
        }

    table_selected = st.radio('Select Table', list(dfs))
    view_mode = st.radio('Data to view:', ['Most recent value.', 'All values.'])

    if view_mode == 'Most recent value.':
        st.write(dfs[table_selected].iloc[-1])
    else:
        st.dataframe(dfs[table_selected])

    st.download_button(
        label="Download Excel",
        data=to_excel(dfs),
        file_name="Retail_Sales_Data.xlsx",
        mime="application/vnd.ms-excel"
    )
