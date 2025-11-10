import os
from pathlib import Path

# Configurações da aplicação
class Config:
    APP_NAME = "Controle de Gastos Pessoais"
    VERSION = "1.0.0"
    
    # Database
    DB_NAME = "financas.db"
    DB_PATH = Path(__file__).parent / DB_NAME
    
    # Configurações do Streamlit
    STREAMLIT_CONFIG = {
        "page_title": "Controle de Gastos",
        "page_icon": "💰",
        "layout": "wide",
        "initial_sidebar_state": "expanded"
    }

config = Config()