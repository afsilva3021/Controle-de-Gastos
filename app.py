import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta
import os
from pathlib import Path

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
        
        # Categorias padrão - CORRIGIDO
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
        
        # Inserir categorias padrão - CORRIGIDO
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



# Funções utilitárias
def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def inicializar_session_state():
    """Inicializa variáveis de sessão"""
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseManager()
    
    # Inicializar estado para controlar a atualização das categorias
    if 'tipo_transacao' not in st.session_state:
        st.session_state.tipo_transacao = 'receita'

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
        ["📊 Dashboard", "💸 Nova Transação", "📋 Extrato", "📈 Relatórios", "✏️ Editar/Excluir" "⚙️ Categorias" ]
    )
    
    # Página: Dashboard
    if menu == "📊 Dashboard":
        render_dashboard(db, mes_selecionado, ano_selecionado)
    
    # Página: Nova Transação
    elif menu == "💸 Nova Transação":
        render_nova_transacao(db)
    
    # Página: Extrato
    elif menu == "📋 Extrato":
        render_extrato(db, mes_selecionado, ano_selecionado)
    
    # Página: Relatórios
    elif menu == "📈 Relatórios":
        render_relatorios(db, mes_selecionado, ano_selecionado)
    
    # Página: Categorias
    elif menu == "⚙️ Categorias":
        render_categorias(db)
    
    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **💡 Dicas:**
        - Registre todas as transações
        - Categorize corretamente
        - Revise seu extrato semanalmente
        
        *v1.0.0* 🔒
        """
    )

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
            # Gráfico de pizza - Despesas por categoria
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
            # Gráfico de barras - Receitas vs Despesas
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
        
        # NOVO: EXTRATO COM SALDO ACUMULADO
        st.subheader("📋 Extrato com Saldo Acumulado")
        
        # Gerar extrato com saldo
        extrato = gerar_extrato_com_saldo(transacoes)
        
        if not extrato.empty:
            # Exibir como tabela formatada
            st.table(extrato)
        else:
            st.info("Nenhuma transação para exibir no extrato")
        
        st.markdown("---")

        # Top 5 receitas (CORRIGIDO o nome)
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



def render_nova_transacao(db):
    """Renderiza a página de nova transação - SOLUÇÃO DEFINITIVA"""
    st.title("💸 Nova Transação")
    
    # Estado para controlar o tipo
    if 'current_tipo' not in st.session_state:
        st.session_state.current_tipo = 'receita'
    
    # Atualizar o tipo baseado na seleção do usuário
    new_tipo = st.radio(
        "Tipo de Transação", 
        ["receita", "despesa"], 
        horizontal=True,
        index=0 if st.session_state.current_tipo == 'receita' else 1,
        key="tipo_selector"
    )
    
    # Atualizar estado se mudou
    if new_tipo != st.session_state.current_tipo:
        st.session_state.current_tipo = new_tipo
        st.rerun()  # 🔄 FORÇA ATUALIZAÇÃO IMEDIATA
    
    # Buscar categorias para o tipo atual
    categorias = db.get_categorias(st.session_state.current_tipo)
    
    # Mostrar informações de debug
    st.info(f"📋 **Categorias de {st.session_state.current_tipo}:** {', '.join(categorias) if categorias else 'Nenhuma'}")
    
    # Formulário
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
                    # Reset para o estado padrão após salvar
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
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            filtro_tipo = st.selectbox("Filtrar por tipo", ["Todos", "receita", "despesa"])
        with col2:
            categorias_todas = db.get_categorias()
            filtro_categoria = st.selectbox("Filtrar por categoria", ["Todas"] + categorias_todas)
        
        # Aplicar filtros
        transacoes_filtradas = transacoes.copy()
        if filtro_tipo != "Todos":
            transacoes_filtradas = transacoes_filtradas[transacoes_filtradas['tipo'] == filtro_tipo]
        if filtro_categoria != "Todas":
            transacoes_filtradas = transacoes_filtradas[transacoes_filtradas['categoria'] == filtro_categoria]
        
        # Formatar para exibição
        transacoes_display = transacoes_filtradas.copy()
        transacoes_display['valor_formatado'] = transacoes_display['valor'].apply(formatar_moeda)
        transacoes_display['tipo_emoji'] = transacoes_display['tipo'].map({'receita': '💰', 'despesa': '💸'})
        transacoes_display['data'] = pd.to_datetime(transacoes_display['data']).dt.strftime('%d/%m/%Y')
        
        # Exibir tabela
        colunas_exibir = ['data', 'tipo_emoji', 'descricao', 'categoria', 'valor_formatado']
        st.dataframe(
            transacoes_display[colunas_exibir],
            column_config={
                'data': 'Data',
                'tipo_emoji': 'Tipo',
                'descricao': 'Descrição',
                'categoria': 'Categoria',
                'valor_formatado': 'Valor'
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Estatísticas
        receitas_filtro = transacoes_filtradas[transacoes_filtradas['tipo'] == 'receita']['valor'].sum()
        despesas_filtro = transacoes_filtradas[transacoes_filtradas['tipo'] == 'despesa']['valor'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Receitas Filtradas", formatar_moeda(receitas_filtro))
        with col2:
            st.metric("💸 Despesas Filtradas", formatar_moeda(despesas_filtro))
                
    else:
        st.info("📋 Nenhuma transação encontrada para o período selecionado.")

def render_relatorios(db, mes, ano):
    """Renderiza a página de relatórios"""
    st.title("📈 Relatórios Avançados")
    
    # Obter dados dos últimos 6 meses
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
        # Gráfico de evolução
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
        
        # Análise de tendência
        st.subheader("📊 Análise de Tendência")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            variacao_receitas = ((df_mensal['receitas'].iloc[-1] - df_mensal['receitas'].iloc[0]) / 
                               df_mensal['receitas'].iloc[0] * 100) if df_mensal['receitas'].iloc[0] > 0 else 0
            st.metric("📈 Variação Receitas", f"{variacao_receitas:+.1f}%")
        
        with col2:
            variacao_despesas = ((df_mensal['despesas'].iloc[-1] - df_mensal['despesas'].iloc[0]) / 
                               df_mensal['despesas'].iloc[0] * 100) if df_mensal['despesas'].iloc[0] > 0 else 0
            st.metric("📉 Variação Despesas", f"{variacao_despesas:+.1f}%")
        
        with col3:
            variacao_saldo = ((df_mensal['saldo'].iloc[-1] - df_mensal['saldo'].iloc[0]) / 
                            abs(df_mensal['saldo'].iloc[0]) * 100) if df_mensal['saldo'].iloc[0] != 0 else 0
            st.metric("⚖️ Variação Saldo", f"{variacao_saldo:+.1f}%")
    else:
        st.info("📈 Dados insuficientes para gerar relatórios.")

def buscar_transacoes_filtradas(db, periodo, filtro_tipo, filtro_categoria):
    """Busca transações baseado nos filtros aplicados"""
    hoje = datetime.now()
    
    if periodo == "Este mês":
        mes = hoje.month
        ano = hoje.year
        transacoes = db.get_transacoes(mes, ano)
    elif periodo == "Mês anterior":
        mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        transacoes = db.get_transacoes(mes_anterior.month, mes_anterior.year)
    elif periodo == "Últimos 3 meses":
        # Buscar dos últimos 3 meses
        data_inicio = hoje - relativedelta(months=3)
        transacoes_todas = db.get_transacoes()
        if not transacoes_todas.empty:
            transacoes_todas['data'] = pd.to_datetime(transacoes_todas['data'])
            transacoes = transacoes_todas[transacoes_todas['data'] >= data_inicio]
        else:
            transacoes = pd.DataFrame()
    elif periodo == "Personalizado":
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data início", hoje.replace(day=1))
        with col2:
            data_fim = st.date_input("Data fim", hoje)
        
        if st.button("Aplicar filtro personalizado"):
            transacoes_todas = db.get_transacoes()
            if not transacoes_todas.empty:
                transacoes_todas['data'] = pd.to_datetime(transacoes_todas['data'])
                transacoes = transacoes_todas[
                    (transacoes_todas['data'] >= pd.to_datetime(data_inicio)) & 
                    (transacoes_todas['data'] <= pd.to_datetime(data_fim))
                ]
            else:
                transacoes = pd.DataFrame()
    else:  # Todos
        transacoes = db.get_transacoes()
    
    # Aplicar filtros adicionais
    if not transacoes.empty:
        if filtro_tipo != "Todos":
            transacoes = transacoes[transacoes['tipo'] == filtro_tipo]
        if filtro_categoria != "Todas":
            transacoes = transacoes[transacoes['categoria'] == filtro_categoria]
    
    return transacoes

def exibir_transacao_editavel(db, transacao, index):
    """Exibe uma transação com opções de editar e excluir"""
    with st.container():
        st.markdown("---")
        
        col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 1, 1])
        
        with col1:
            st.write(f"**{transacao['descricao']}**")
        
        with col2:
            tipo_emoji = "💰" if transacao['tipo'] == 'receita' else "💸"
            st.write(f"{tipo_emoji} {transacao['tipo']}")
        
        with col3:
            st.write(f"`{transacao['categoria']}`")
        
        with col4:
            valor_formatado = formatar_moeda(transacao['valor'])
            if transacao['tipo'] == 'receita':
                st.success(valor_formatado)
            else:
                st.error(valor_formatado)
        
        with col5:
            data_formatada = pd.to_datetime(transacao['data']).strftime('%d/%m/%Y')
            st.write(data_formatada)
        
        with col6:
            # Botão de editar
            if st.button("✏️", key=f"edit_{index}", help="Editar transação"):
                st.session_state[f'editing_{transacao["id"]}'] = True
            
            # Botão de excluir
            if st.button("🗑️", key=f"delete_{index}", help="Excluir transação"):
                st.session_state[f'deleting_{transacao["id"]}'] = True
        
        # Modal de edição
        if st.session_state.get(f'editing_{transacao["id"]}', False):
            editar_transacao(db, transacao)
        
        # Modal de exclusão
        if st.session_state.get(f'deleting_{transacao["id"]}', False):
            excluir_transacao(db, transacao)


def render_categorias(db):
    """Renderiza a página de categorias"""
    st.title("⚙️ Gerenciar Categorias")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Categorias de Receita")
        receitas_cat = db.get_categorias('receita')
        if receitas_cat:
            for cat in receitas_cat:
                st.write(f"• {cat}")
        else:
            st.info("Nenhuma categoria de receita")
    
    with col2:
        st.subheader("📤 Categorias de Despesa")
        despesas_cat = db.get_categorias('despesa')
        if despesas_cat:
            for cat in despesas_cat:
                st.write(f"• {cat}")
        else:
            st.info("Nenhuma categoria de despesa")
    
    # Adicionar nova categoria
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

if __name__ == "__main__":
    main()