#!/usr/bin/env python3
"""
Script de execução do Controle de Gastos
"""

import subprocess
import sys
import os

def main():
    """Função principal para executar a aplicação"""
    print("🚀 Iniciando Controle de Gastos...")
    print("📊 A aplicação estará disponível em: http://localhost:8501")
    print("⏹️  Pressione Ctrl+C para parar a aplicação")
    
    try:
        # Executar Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py"
        ])
    except KeyboardInterrupt:
        print("\n👋 Aplicação encerrada!")
    except Exception as e:
        print(f"❌ Erro ao executar a aplicação: {e}")

if __name__ == "__main__":
    main()