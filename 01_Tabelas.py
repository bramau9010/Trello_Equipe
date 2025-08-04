import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pathlib import Path
from datetime import datetime
from utilidades import leitura_dados
# set page to be wider
st.set_page_config(layout="wide")
leitura_dados()

df_mestre=st.session_state['dados']['df_trello']

df_mestre2=df_mestre[[i for i in df_mestre.columns if 'ID_' not in i]].copy()


st.dataframe(df_mestre2, use_container_width=True)


