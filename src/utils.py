import streamlit as st
import pandas as pd  # ADICIONAR ESTA LINHA
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta

def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_data(data):
    """Formata data para formato brasileiro"""
    if isinstance(data, str):
        return data
    return data.strftime("%d/%m/%Y")

def obter_meses():
    """Retorna lista de meses para seleção"""
    return [(i, calendar.month_name[i]) for i in range(1, 13)]

def obter_anos():
    """Retorna lista de anos para seleção"""
    ano_atual = datetime.now().year
    return list(range(ano_atual - 2, ano_atual + 1))

def calcular_periodo(mes, ano):
    """Calcula data inicial e final do período"""
    data_inicio = datetime(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    data_fim = datetime(ano, mes, ultimo_dia)
    return data_inicio, data_fim

def inicializar_session_state():
    """Inicializa variáveis de sessão"""
    if 'db' not in st.session_state:
        from src.database import DatabaseManager
        st.session_state.db = DatabaseManager()
        st.session_state.db.init_db()