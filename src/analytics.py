import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Analytics:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def gerar_grafico_pizza_despesas(self, df_resumo):
        """Gera gráfico de pizza para despesas por categoria"""
        if df_resumo.empty:
            return None
            
        despesas_cat = df_resumo[df_resumo['tipo'] == 'despesa']
        
        if despesas_cat.empty or despesas_cat['total'].sum() == 0:
            return None
        
        fig = px.pie(
            despesas_cat, 
            values='total', 
            names='categoria',
            title="📊 Despesas por Categoria",
            color_discrete_sequence=px.colors.sequential.Reds_r
        )
        return fig
    
    def gerar_grafico_comparacao(self, receitas, despesas):
        """Gera gráfico de barras para receitas vs despesas"""
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=['Receitas', 'Despesas'],
            y=[receitas, despesas],
            marker_color=['#2ecc71', '#e74c3c'],
            text=[f'R$ {receitas:,.2f}', f'R$ {despesas:,.2f}'],
            textposition='auto',
        ))
        fig.update_layout(
            title="📈 Receitas vs Despesas",
            showlegend=False,
            yaxis_title="Valor (R$)"
        )
        return fig
    
    def gerar_grafico_evolucao(self, mes, ano, meses_anteriores=5):
        """Gera gráfico de evolução dos últimos meses"""
        data_inicio = datetime(ano, mes, 1) - relativedelta(months=meses_anteriores-1)
        
        dados_mensais = []
        for i in range(meses_anteriores):
            data_ref = data_inicio + relativedelta(months=i)
            transacoes = self.db.get_transacoes(data_ref.month, data_ref.year)
            
            if not transacoes.empty:
                receitas = transacoes[transacoes['tipo'] == 'receita']['valor'].sum()
                despesas = transacoes[transacoes['tipo'] == 'despesa']['valor'].sum()
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
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_mensal['mes_nome'],
            y=df_mensal['receitas'],
            name='Receitas',
            line=dict(color='#2ecc71', width=3),
            mode='lines+markers'
        ))
        fig.add_trace(go.Scatter(
            x=df_mensal['mes_nome'],
            y=df_mensal['despesas'],
            name='Despesas',
            line=dict(color='#e74c3c', width=3),
            mode='lines+markers'
        ))
        fig.update_layout(
            title="📈 Evolução Mensal",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            hovermode='x unified'
        )
        return fig, df_mensal