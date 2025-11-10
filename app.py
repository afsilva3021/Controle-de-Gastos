import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta
import os

# Configuração da página
st.set_page_config(
    page_title="Controle de Gastos",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Classe de gerenciamento do banco de dados
class DatabaseManager:
    def __init__(self, db_path='financas.db'):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
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
            except:
                pass
        
        conn.commit()
        conn.close()
    
    def add_transacao(self, descricao, valor, categoria, tipo, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO transacoes (descricao, valor, categoria, tipo, data) VALUES (?, ?, ?, ?, ?)",
            (descricao, abs(valor), categoria, tipo, data)
        )
        conn.commit()
        conn.close()
    
    def get_transacoes(self, mes=None, ano=None):
        conn = self.get_connection()
        
        query = "SELECT * FROM transacoes"
        params = []
        
        if mes and ano:
            query += " WHERE strftime('%m', data) = ? AND strftime('%Y', data) = ?"
            params = [f"{mes:02d}", str(ano)]
        
        query += " ORDER BY data DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def get_resumo(self, mes, ano):
        conn = self.get_connection()
        
        query = """
        SELECT 
            tipo,
            categoria,
            SUM(valor) as total
        FROM transacoes 
        WHERE strftime('%m', data) = ? AND strftime('%Y', data) = ?
        GROUP BY tipo, categoria
        """
        
        df = pd.read_sql_query(query, conn, params=(f"{mes:02d}", str(ano)))
        conn.close()
        return df
    
    def get_categorias(self, tipo=None):
        conn = self.get_connection()
        
        query = "SELECT nome FROM categorias"
        params = []
        
        if tipo:
            query += " WHERE tipo = ?"
            params = [tipo]
        
        query += " ORDER BY nome"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df['nome'].tolist()
    
    def add_categoria(self, nome, tipo):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO categorias (nome, tipo) VALUES (?, ?)", (nome, tipo))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False

    def atualizar_transacao(self, transacao_id, descricao, valor, categoria, data):
        """Atualiza uma transação existente"""
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            c.execute(
                """
                UPDATE transacoes 
                SET descricao = ?, valor = ?, categoria = ?, data = ?
                WHERE id = ?
                """,
                (descricao, valor, categoria, data, transacao_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()

    def excluir_transacao_db(self, transacao_id):
        """Exclui uma transação do banco"""
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            c.execute("DELETE FROM transacoes WHERE id = ?", (transacao_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()

# Funções utilitárias
def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def gerar_extrato_com_saldo(transacoes):
    """Gera um DataFrame com saldo acumulado no formato desejado"""
    if transacoes.empty:
        return pd.DataFrame()
    
    # Criar cópia e ordenar por data
    df = transacoes.copy()
    df['data'] = pd.to_datetime(df['data'])
    df = df.sort_values('data')
    
    # Formatar data (ex: 01/nov)
    df['DATA'] = df['data'].dt.strftime('%d/%b').str.lower()
    
    # Formatar movimentação
    df['MOVIMENTAÇÃO'] = df['descricao']
    
    # Ajustar valor (negativo para despesas)
    df['VALOR_BRUTO'] = df.apply(
        lambda x: -x['valor'] if x['tipo'] == 'despesa' else x['valor'], 
        axis=1
    )
    
    # Calcular saldo acumulado
    df['SALDO'] = df['VALOR_BRUTO'].cumsum()
    
    # Formatar VALOR para exibição (com separadores)
    df['VALOR'] = df['VALOR_BRUTO'].apply(
        lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    )
    
    # Formatar SALDO para exibição
    df['SALDO_FMT'] = df['SALDO'].apply(
        lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    )
    
    # Selecionar e ordenar colunas
    extrato = df[['DATA', 'MOVIMENTAÇÃO', 'VALOR', 'SALDO_FMT']]
    extrato.columns = ['DATA', 'MOVIMENTAÇÃO', 'VALOR', 'SALDO']
    
    return extrato

def inicializar_session_state():
    """Inicializa variáveis de sessão"""
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseManager()
    
    if 'tipo_transacao' not in st.session_state:
        st.session_state.tipo_transacao = 'receita'

# Funções de renderização das páginas
def render_dashboard(db, mes, ano):
    """Renderiza a página do dashboard"""
    st.title("📊 Dashboard Financeiro")
    
    transacoes = db.get_transacoes(mes, ano)
    resumo = db.get_resumo(mes, ano)
    
    if not transacoes.empty:
        # Métricas principais
        receitas = transacoes[transacoes['tipo'] == 'receita']['valor'].sum()
        despesas = transacoes[transacoes['tipo'] == 'despesa']['valor'].sum()
        saldo = receitas - despesas
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Receitas", formatar_moeda(receitas))
        
        with col2:
            st.metric("💸 Despesas", formatar_moeda(despesas))
        
        with col3:
            st.metric("⚖️ Saldo", formatar_moeda(saldo))
        
        with col4:
            margem = (saldo / receitas * 100) if receitas > 0 else 0
            st.metric("📈 Margem", f"{margem:.1f}%")
        
        st.markdown("---")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            despesas_cat = resumo[resumo['tipo'] == 'despesa']
            if not despesas_cat.empty and despesas_cat['total'].sum() > 0:
                fig_despesas = px.pie(
                    despesas_cat, 
                    values='total', 
                    names='categoria',
                    title="📊 Despesas por Categoria",
                    color_discrete_sequence=px.colors.sequential.Reds_r
                )
                st.plotly_chart(fig_despesas, use_container_width=True)
            else:
                st.info("📊 Sem despesas para exibir no gráfico")
        
        with col2:
            fig_comparacao = go.Figure()
            fig_comparacao.add_trace(go.Bar(
                x=['Receitas', 'Despesas'],
                y=[receitas, despesas],
                marker_color=['#2ecc71', '#e74c3c'],
                text=[formatar_moeda(receitas), formatar_moeda(despesas)],
                textposition='auto',
            ))
            fig_comparacao.update_layout(
                title="📈 Receitas vs Despesas",
                showlegend=False,
                yaxis_title="Valor (R$)"
            )
            st.plotly_chart(fig_comparacao, use_container_width=True)
        
        st.markdown("---")
        
        # EXTRATO COM SALDO ACUMULADO
        st.subheader("📋 Extrato com Saldo Acumulado")
        extrato = gerar_extrato_com_saldo(transacoes)
        
        if not extrato.empty:
            st.table(extrato)
        
        st.markdown("---")

        # Top 5 receitas
        st.subheader("💰 Top 5 Maiores Receitas")
        receitas_df = transacoes[transacoes['tipo'] == 'receita']
        if not receitas_df.empty:
            top_receitas = receitas_df.nlargest(5, 'valor')
            for _, receita in top_receitas.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{receita['descricao']}**")
                with col2:
                    st.write(f"`{receita['categoria']}`")
                with col3:
                    st.success(formatar_moeda(receita['valor']))
        else:
            st.info("🎉 Nenhuma receita registrada este mês!")
        
        st.markdown("---")

        # Top 5 despesas
        st.subheader("💸 Top 5 Maiores Despesas")
        despesas_df = transacoes[transacoes['tipo'] == 'despesa']
        if not despesas_df.empty:
            top_despesas = despesas_df.nlargest(5, 'valor')
            for _, despesa in top_despesas.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{despesa['descricao']}**")
                with col2:
                    st.write(f"`{despesa['categoria']}`")
                with col3:
                    st.error(formatar_moeda(despesa['valor']))
        else:
            st.info("🎉 Nenhuma despesa registrada este mês!")
            
    else:
        st.info("📊 Nenhuma transação encontrada para o período selecionado.")

def render_nova_transacao(db):
    """Renderiza a página de nova transação"""
    st.title("💸 Nova Transação")
    
    if 'current_tipo' not in st.session_state:
        st.session_state.current_tipo = 'receita'
    
    new_tipo = st.radio(
        "Tipo de Transação", 
        ["receita", "despesa"], 
        horizontal=True,
        index=0 if st.session_state.current_tipo == 'receita' else 1,
        key="tipo_selector"
    )
    
    if new_tipo != st.session_state.current_tipo:
        st.session_state.current_tipo = new_tipo
        st.rerun()
    
    categorias = db.get_categorias(st.session_state.current_tipo)
    
    with st.form("nova_transacao_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            descricao = st.text_input("Descrição*", placeholder="Ex: Salário mensal, Almoço...")
            valor = st.number_input("Valor (R$)*", min_value=0.01, step=0.01, format="%.2f")
        
        with col2:
            if categorias:
                categoria = st.selectbox("Categoria*", categorias)
            else:
                st.warning("⚠️ Nenhuma categoria disponível")
                categoria = st.text_input("Digite uma categoria*", placeholder="Ex: Alimentação, Transporte...")
            
            data = st.date_input("Data", datetime.now())
        
        submitted = st.form_submit_button("💾 Salvar Transação")
        
        if submitted:
            if descricao and valor > 0 and categoria:
                try:
                    db.add_transacao(descricao, valor, categoria, st.session_state.current_tipo, data)
                    st.success("✅ Transação salva com sucesso!")
                    st.session_state.current_tipo = 'receita'
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar transação: {e}")
            else:
                st.error("❌ Preencha todos os campos obrigatórios!")

def render_extrato(db, mes, ano):
    """Renderiza a página de extrato"""
    st.title("📋 Extrato Financeiro")
    
    transacoes = db.get_transacoes(mes, ano)
    
    if not transacoes.empty:
        extrato = gerar_extrato_com_saldo(transacoes)
        
        st.subheader("📊 Extrato com Saldo Acumulado")
        st.table(extrato)
        
        # Estatísticas
        st.subheader("📈 Resumo do Período")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_receitas = transacoes[transacoes['tipo'] == 'receita']['valor'].sum()
            st.metric("💰 Total Receitas", formatar_moeda(total_receitas))
        
        with col2:
            total_despesas = transacoes[transacoes['tipo'] == 'despesa']['valor'].sum()
            st.metric("💸 Total Despesas", formatar_moeda(total_despesas))
        
        with col3:
            saldo_final = total_receitas - total_despesas
            st.metric("⚖️ Saldo Final", formatar_moeda(saldo_final))
                
    else:
        st.info("📋 Nenhuma transação encontrada para o período selecionado.")

def render_relatorios(db, mes, ano):
    """Renderiza a página de relatórios"""
    st.title("📈 Relatórios Avançados")
    
    data_inicio = datetime(ano, mes, 1) - relativedelta(months=5)
    
    dados_mensais = []
    for i in range(6):
        data_ref = data_inicio + relativedelta(months=i)
        transacoes_mes = db.get_transacoes(data_ref.month, data_ref.year)
        
        if not transacoes_mes.empty:
            receitas = transacoes_mes[transacoes_mes['tipo'] == 'receita']['valor'].sum()
            despesas = transacoes_mes[transacoes_mes['tipo'] == 'despesa']['valor'].sum()
        else:
            receitas = despesas = 0
            
        dados_mensais.append({
            'mes_ano': data_ref.strftime('%Y-%m'),
            'mes_nome': data_ref.strftime('%b/%Y'),
            'receitas': receitas,
            'despesas': despesas,
            'saldo': receitas - despesas
        })
    
    df_mensal = pd.DataFrame(dados_mensais)
    
    if not df_mensal.empty:
        fig_evolucao = go.Figure()
        fig_evolucao.add_trace(go.Scatter(
            x=df_mensal['mes_nome'],
            y=df_mensal['receitas'],
            name='Receitas',
            line=dict(color='#2ecc71', width=3),
            mode='lines+markers'
        ))
        fig_evolucao.add_trace(go.Scatter(
            x=df_mensal['mes_nome'],
            y=df_mensal['despesas'],
            name='Despesas',
            line=dict(color='#e74c3c', width=3),
            mode='lines+markers'
        ))
        fig_evolucao.update_layout(
            title="📈 Evolução Mensal - Últimos 6 Meses",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            hovermode='x unified'
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)
    else:
        st.info("📈 Dados insuficientes para gerar relatórios.")

def render_categorias(db):
    """Renderiza a página de categorias"""
    st.title("⚙️ Gerenciar Categorias")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Categorias de Receita")
        receitas_cat = db.get_categorias('receita')
        for cat in receitas_cat:
            st.write(f"• {cat}")
    
    with col2:
        st.subheader("📤 Categorias de Despesa")
        despesas_cat = db.get_categorias('despesa')
        for cat in despesas_cat:
            st.write(f"• {cat}")
    
    st.markdown("---")
    st.subheader("➕ Adicionar Nova Categoria")
    
    with st.form("nova_categoria", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nova_cat_nome = st.text_input("Nome da Categoria", placeholder="Ex: Viagem, Academia...")
        
        with col2:
            nova_cat_tipo = st.selectbox("Tipo", ["receita", "despesa"])
        
        submitted = st.form_submit_button("Adicionar Categoria")
        
        if submitted and nova_cat_nome:
            success = db.add_categoria(nova_cat_nome, nova_cat_tipo)
            if success:
                st.success("✅ Categoria adicionada com sucesso!")
                st.rerun()
            else:
                st.error("❌ Esta categoria já existe!")

def render_editar_excluir(db):
    """Renderiza a página para editar e excluir transações"""
    st.title("✏️ Editar/Excluir Transações")
    
    st.subheader("Últimas Transações")
    transacoes = db.get_transacoes()
    
    if not transacoes.empty:
        # Ordenar por data (mais recentes primeiro)
        transacoes['data'] = pd.to_datetime(transacoes['data'])
        transacoes = transacoes.sort_values('data', ascending=False)
        
        for _, transacao in transacoes.head(15).iterrows():
            with st.expander(f"{transacao['descricao']} - {formatar_moeda(transacao['valor'])}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Tipo:** {transacao['tipo']}")
                    st.write(f"**Categoria:** {transacao['categoria']}")
                    st.write(f"**Data:** {pd.to_datetime(transacao['data']).strftime('%d/%m/%Y')}")
                
                with col2:
                    with st.form(key=f"edit_{transacao['id']}"):
                        nova_descricao = st.text_input("Descrição", value=transacao['descricao'])
                        novo_valor = st.number_input("Valor", value=float(transacao['valor']), format="%.2f")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.form_submit_button("💾 Atualizar"):
                                if db.atualizar_transacao(transacao['id'], nova_descricao, novo_valor, transacao['categoria'], transacao['data']):
                                    st.success("✅ Transação atualizada!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao atualizar")
                        
                        with col_btn2:
                            if st.form_submit_button("🗑️ Excluir"):
                                if db.excluir_transacao_db(transacao['id']):
                                    st.error("🗑️ Transação excluída!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao excluir")
    else:
        st.info("Nenhuma transação encontrada.")

# Inicializar aplicação
def main():
    # Inicializar banco de dados
    inicializar_session_state()
    db = st.session_state.db
    
    # Sidebar - Filtros de data
    st.sidebar.title("💰 Controle de Gastos")
    st.sidebar.markdown("---")
    
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    with st.sidebar:
        col1, col2 = st.columns(2)
        with col1:
            mes_selecionado = st.selectbox(
                "Mês",
                range(1, 13),
                index=mes_atual-1,
                format_func=lambda x: calendar.month_name[x]
            )
        with col2:
            ano_selecionado = st.selectbox(
                "Ano",
                range(ano_atual-2, ano_atual+1),
                index=2
            )
    
    # Menu principal
    menu = st.sidebar.radio(
        "Navegação",
        ["📊 Dashboard", "💸 Nova Transação", "📋 Extrato", "📈 Relatórios", "⚙️ Categorias", "✏️ Editar/Excluir"]
    )
    
    # Páginas
    if menu == "📊 Dashboard":
        render_dashboard(db, mes_selecionado, ano_selecionado)
    elif menu == "💸 Nova Transação":
        render_nova_transacao(db)
    elif menu == "📋 Extrato":
        render_extrato(db, mes_selecionado, ano_selecionado)
    elif menu == "📈 Relatórios":
        render_relatorios(db, mes_selecionado, ano_selecionado)
    elif menu == "⚙️ Categorias":
        render_categorias(db)
    elif menu == "✏️ Editar/Excluir":
        render_editar_excluir(db)
    
    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **💡 Dicas:**
        - Registre todas as transações
        - Categorize corretamente
        - Revise seu extrato semanalmente
        
        *v2.0.0* 🔒
        """
    )

if __name__ == "__main__":
    main()