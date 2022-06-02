# streamlit run retail_sales_app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import xlsxwriter
from io import BytesIO
import requests
import math
import pathlib
from datetime import datetime, date

def get_colors():
    import json
    f = open('./assets/mm_colors.json')
    data = json.load(f)
    f.close()
    return data['mm_color']

def get_category():
    import json
    f = open('./assets/retail_categories.json')
    data = json.load(f)
    f.close()
    return data

def get_MARTS_data(api_key='', date_from='2000', date_to=str(date.today().year)):
    link = f'https://api.census.gov/data/timeseries/eits/marts?get=data_type_code,time_slot_id,seasonally_adj,category_code,cell_value,error_data&for=us:*&time=from+{date_from}+to+{date_to}&key={api_key}'
    print('Making the API request for MARTS...')
    response=requests.get(link)
    data=response.json()
    print('> Done!\n')
    df=pd.DataFrame(data[1:], columns=data[0])
    return df

def clean_retail_sales_data(df, seasonally_adj='yes', on_report=True, category=get_category()):
    print('Transform and Pivot Data.')
    df['on_report'] = df['category_code'].replace(category['on_report'])
    df['short'] = df['category_code'].replace(category['short'])
    df['long'] = df['category_code'].replace(category['long'])
    if on_report:
        x = df.loc[(df['data_type_code'] == 'SM') & (df['seasonally_adj']==seasonally_adj) & (df['on_report'] == 'yes')][['short','cell_value','time']]
    else:
        x = df.loc[(df['data_type_code'] == 'SM') & (df['seasonally_adj']==seasonally_adj)][['short','cell_value','time']]
    x['cell_value'] = x['cell_value'].astype(int)
    x['Date'] = pd.to_datetime(x['time'],format='%Y-%m').dt.date
    # x['year'] = pd.DatetimeIndex(x['time']).year
    # x['month'] = pd.DatetimeIndex(x['time']).month
    x = x.pivot(index='Date',columns='short')
    print('> Done!\n')
    return x['cell_value']

@st.cache
def load_data():
    data = get_MARTS_data()
    return clean_retail_sales_data(data)

@st.cache(allow_output_mutation=True)
def to_excel(dfs):
     import io
     buffer = io.BytesIO()
     with pd.ExcelWriter(buffer) as writer:
        for sheet_name, df in dfs.items():  # loop through `dict` of dataframes
            df.to_excel(writer, sheet_name=sheet_name,index=True,float_format="%.5f")  # send df to writer
            worksheet = writer.sheets[sheet_name]  # pull worksheet object
            for column in df:
                column_length = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column) + 1
                writer.sheets[sheet_name].set_column(col_idx, col_idx, column_length)
            writer.sheets[sheet_name].set_column(0, 0, 10) # write the index column
     return buffer

st.set_page_config(
     page_icon= ':bar-chart:',
     menu_items={
          # 'Get Help': 'mailto:jon.carrsco@madisonmarquette.com',
          'About': "# Madison Marquette \n Jon Carrasco \n jon.carrasco@madisonmarquette.com"},)

hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

'## Retail Sales Data '
'An application to download and analyze MARTS data from the US Census.'

if 'download' not in st.session_state:
    st.session_state['download'] = False

if 'preview_table' not in st.session_state:
    st.session_state['preview_table'] = False


if not st.session_state['download']:
    st.session_state['download'] = st.button('Download Data')

if st.session_state['download']:
    MARTS = load_data()
    dfs = {}
    dfs['Retail Sales'] = MARTS
    dfs['M-M Pct Change'] = MARTS.pct_change(1)
    dfs['M-M Change'] = MARTS.diff(1)
    dfs['Y-Y Pct Change'] = MARTS.pct_change(12)
    dfs['Y-Y Change'] = MARTS.diff(12)
    st.session_state['table'] = st.radio('Select Table', list(dfs))
    st.session_state['table_view'] = st.radio('Data to view.',['Most recent value.','All values.'])
    if st.session_state['table_view'] == 'Most recent value.':
        dfs[st.session_state['table']].iloc[-1]
    elif st.session_state['table_view'] == 'All values.':
        dfs[st.session_state['table']]
    st.download_button(
    label="Download Excel",
    data=to_excel(dfs),
    file_name="Retail Sales Data.xlsx",
    mime="application/vnd.ms-excel"
    )
