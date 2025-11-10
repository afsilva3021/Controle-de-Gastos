import sqlite3
import pandas as pd
from contextlib import contextmanager
import os
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Cria o diretório se não existir
            base_dir = Path(__file__).parent.parent
            self.db_path = base_dir / 'financas.db'
        else:
            self.db_path = Path(db_path)
        
        # Garante que o diretório existe
        self.db_path.parent.mkdir(exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # CORREÇÃO: usar = em vez de -
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        """Inicializa o banco de dados com tabelas e dados padrão"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Tabela de transações
            c.execute('''
                CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    categoria TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa')),
                    data DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de categorias
            c.execute('''
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa'))
                )
            ''')
            
            # Categorias padrão
            categorias_padrao = [
                ('Salário', 'receita'),
                ('Freelance', 'receita'),
                ('Investimentos', 'receita'),
                ('Presente', 'receita'),
                ('Outros', 'receita'),
                ('Alimentação', 'despesa'),
                ('Transporte', 'despesa'),
                ('Moradia', 'despesa'),
                ('Saúde', 'despesa'),
                ('Educação', 'despesa'),
                ('Lazer', 'despesa'),
                ('Compras', 'despesa'),
                ('Outros', 'despesa')
            ]
            
            # Inserir categorias padrão
            for categoria, tipo in categorias_padrao:
                try:
                    c.execute(
                        "INSERT OR IGNORE INTO categorias (nome, tipo) VALUES (?, ?)",
                        (categoria, tipo)
                    )
                except sqlite3.IntegrityError:
                    pass
            
            conn.commit()
    
    def execute_query(self, query, params=()):
        """Executa uma query e retorna o cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
    
    def fetch_all(self, query, params=()):
        """Executa uma query e retorna um DataFrame"""
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def add_transacao(self, descricao, valor, categoria, tipo, data):
        """Adiciona uma nova transação"""
        query = """
        INSERT INTO transacoes (descricao, valor, categoria, tipo, data)
        VALUES (?, ?, ?, ?, ?)
        """
        self.execute_query(query, (descricao, abs(valor), categoria, tipo, data))
    
    def get_transacoes(self, mes=None, ano=None):
        """Obtém transações com filtro opcional de mês/ano"""
        query = "SELECT * FROM transacoes"
        params = []
        
        if mes and ano:
            query += " WHERE strftime('%m', data) = ? AND strftime('%Y', data) = ?"
            params = [f"{mes:02d}", str(ano)]
        
        query += " ORDER BY data DESC"
        return self.fetch_all(query, params)
    
    def get_resumo(self, mes, ano):
        """Obtém resumo por categoria"""
        query = """
        SELECT 
            tipo,
            categoria,
            SUM(valor) as total
        FROM transacoes 
        WHERE strftime('%m', data) = ? AND strftime('%Y', data) = ?
        GROUP BY tipo, categoria
        """
        return self.fetch_all(query, (f"{mes:02d}", str(ano)))
    
    def get_categorias(self, tipo=None):
        """Obtém lista de categorias"""
        query = "SELECT nome FROM categorias"
        params = []
        
        if tipo:
            query += " WHERE tipo = ?"
            params = [tipo]
        
        query += " ORDER BY nome"
        df = self.fetch_all(query, params)
        return df['nome'].tolist()
    
    def add_categoria(self, nome, tipo):
        """Adiciona uma nova categoria"""
        query = "INSERT INTO categorias (nome, tipo) VALUES (?, ?)"
        try:
            self.execute_query(query, (nome, tipo))
            return True
        except sqlite3.IntegrityError:
            return False