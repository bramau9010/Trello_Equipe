import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from io import StringIO

from utilidades import leitura_dados


def resumo_historico(df):
    """
    Constrói a aba de Resumo Histórico de Produtividade.
    Recebe df já preparado (colunas de data convertidas, Tempo_Estimado_Horas criado).
    """

    hoje = pd.Timestamp.now(tz='America/Sao_Paulo').normalize()
    inicio_semana = hoje - pd.to_timedelta(hoje.dayofweek, unit='d')
    fim_semana = inicio_semana + pd.to_timedelta(6, unit='d')

    df['Vencendo_Esta_Semana'] = (
        (df['Data_Entrega'].dt.normalize() >= inicio_semana) &
        (df['Data_Entrega'].dt.normalize() <= fim_semana)
    )

    # Tarefa aberta e já vencida
    condicao_a = (df['Data_Conclusao'].isna()) & (df['Data_Entrega'].notna()) & (df['Data_Entrega'] < hoje)
    # Tarefa concluída depois do prazo
    condicao_b = (df['Status'] == "CONCLUÍDO") & (df['Data_Conclusao'] > df['Data_Entrega'])
    df['Atrasada'] = np.where(condicao_b | condicao_a, True, False)

    st.title("Relatório de Produtividade da Equipe")
    st.markdown("Use esta ferramenta para analisar a produtividade da equipe com base nos dados de tarefas.")

    incluir_rotinas = st.sidebar.checkbox('Incluir tarefas de rotina na análise', value=True, key='resumo_rotinas')
    if not incluir_rotinas:
        df = df[df['Is_Rotina'] == False].copy()
        st.sidebar.info("Excluindo tarefas de rotina da análise.")

    st.header("Resumo Geral da Produtividade")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Tarefas", len(df))
    col2.metric("Tarefas Concluídas", df['Status'].value_counts().get("CONCLUÍDO", 0))
    col3.metric("Vencendo esta Semana", int(df['Vencendo_Esta_Semana'].sum()))
    col4.metric("Total de Tarefas Atrasadas", int(df['Atrasada'].sum()))

    st.markdown("---")

    col_grafico1, col_grafico2 = st.columns(2)

    with col_grafico1:
        st.subheader("Volume Total de Tarefas por Membro")
        tarefas_por_membro = df['Membro'].value_counts()
        fig1 = px.bar(
            tarefas_por_membro,
            x=tarefas_por_membro.values,
            y=tarefas_por_membro.index,
            orientation='h',
            labels={'x': 'Quantidade de Tarefas', 'y': 'Membro'},
            text=tarefas_por_membro.values,
            color=tarefas_por_membro.values,
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig1.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig1, use_container_width=True)

    with col_grafico2:
        st.subheader("Tarefas Atrasadas por Membro")
        atrasos_por_membro = df[(df['Status'] != "CONCLUÍDO") & (df['Atrasada'] == True)]['Membro'].value_counts()
        if not atrasos_por_membro.empty:
            fig2 = px.bar(
                atrasos_por_membro,
                x=atrasos_por_membro.values,
                y=atrasos_por_membro.index,
                orientation='h',
                labels={'x': 'Quantidade de Tarefas Atrasadas', 'y': 'Membro'},
                text=atrasos_por_membro.values,
                color=atrasos_por_membro.values,
                color_continuous_scale=px.colors.sequential.Reds
            )
            fig2.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.success("🎉 Parabéns! Nenhuma tarefa atrasada no período analisado.")

    st.markdown("---")

    st.header("Análises Detalhadas")
    col_detalhe1, col_detalhe2 = st.columns(2)

    with col_detalhe1:
        st.subheader("Carga Horária Estimada por Membro (horas)")
        carga_horaria = df.groupby('Membro')['Tempo_Estimado_Horas'].sum().sort_values(ascending=False)
        if not carga_horaria.empty and carga_horaria.sum() > 0:
            fig3 = px.bar(
                carga_horaria,
                x=carga_horaria.values,
                y=carga_horaria.index,
                orientation='h',
                labels={'x': 'Total de Horas Estimadas', 'y': 'Membro'},
                text=carga_horaria.values,
                color=carga_horaria.values,
                color_continuous_scale=px.colors.sequential.Viridis
            )
            fig3.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
            fig3.update_traces(texttemplate='%{text:.2f}h', textposition='outside')
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Não há dados de tempo estimado para exibir.")

    with col_detalhe2:
        st.subheader("Distribuição de Tarefas por Status")
        tarefas_por_status = pd.pivot_table(
            df,
            values='ID_Tarefa',
            index='Membro',
            columns='Status',
            aggfunc='count',
            fill_value=0
        )
        st.dataframe(tarefas_por_status, use_container_width=True)

    if st.checkbox("Mostrar dados brutos processados", key='resumo_brutos'):
        st.subheader("Dados Processados")
        st.dataframe(df)


def tarefas_do_dia(df):
    """
    Constrói a aba de Tarefas do Dia e Alocação da Equipe.
    """

    st.title("📅 Tarefas do Dia e Alocação da Equipe")
    st.markdown("Uma visão detalhada das tarefas planejadas para hoje e a alocação de tempo de cada membro da equipe.")

    incluir_rotinas = st.sidebar.checkbox('Incluir tarefas de rotina na análise', value=True, key='dia_rotinas')
    if not incluir_rotinas:
        df = df[df['Is_Rotina'] == False].copy()
        st.sidebar.info("Excluindo tarefas de rotina da análise.")

    df_hoje = df[df['Status'].isin(['A FAZER', 'FAZENDO'])].copy()

    if df_hoje.empty:
        st.success("🎉 A equipe está com as tarefas do dia em dia!")
        st.info("Nenhuma tarefa em andamento ou pendente para hoje. Hora de planejar as próximas!")
        return

    st.header("Resumo da Jornada de Trabalho")

    col1, col2 = st.columns(2)
    total_tarefas = len(df_hoje)
    total_horas_estimadas = df_hoje['Tempo_Estimado_Horas'].sum()

    col1.metric("Total de Tarefas Ativas", total_tarefas)
    col2.metric("Total de Horas Estimadas", f"{total_horas_estimadas:.2f}h")

    st.markdown("---")

    st.header("Detalhamento das Tarefas de Hoje")
    st.markdown("Aqui você encontra a lista completa de tarefas de cada membro, com detalhes importantes para o acompanhamento diário.")

    for membro in df_hoje['Membro'].unique():
        with st.expander(f"✨ Tarefas de **{membro}**"):
            df_membro = df_hoje[df_hoje['Membro'] == membro].copy()

            tabela_membro = df_membro[[
                'Tarefa', 'Status', 'Data_Entrega', 'Tempo_Estimado_Horas', 'Etiquetas'
            ]].rename(columns={
                'Data_Entrega': 'Data Limite',
                'Tempo_Estimado_Horas': 'Horas Estimadas',
                'Etiquetas': 'Etiqueta'
            })

            tabela_membro['Data Limite'] = tabela_membro['Data Limite'].dt.strftime('%d/%m/%Y')
            st.dataframe(tabela_membro.set_index('Tarefa'), use_container_width=True)


def main():
    """
    Prepara os dados e gerencia a navegação entre as abas.
    """

    df = st.session_state['dados']['df_trello'].copy()

    hoje = pd.Timestamp.now(tz='America/Sao_Paulo').normalize()
    inicio_semana = hoje - pd.to_timedelta(hoje.dayofweek, unit='d')
    fim_semana = inicio_semana + pd.to_timedelta(6, unit='d')

    df['Data_Entrega'] = pd.to_datetime(df['Data_Entrega'], errors='coerce')
    df['Data_Conclusao'] = pd.to_datetime(df['Data_Conclusao'], errors='coerce')

    df['Vencendo_Esta_Semana'] = (
        (df['Data_Entrega'].dt.normalize() >= inicio_semana) &
        (df['Data_Entrega'].dt.normalize() <= fim_semana)
    )

    condicao_a = (df['Data_Conclusao'].isna()) & (df['Data_Entrega'].notna()) & (df['Data_Entrega'] < hoje)
    condicao_b = (df['Status'] == "CONCLUÍDO") & (df['Data_Conclusao'] > df['Data_Entrega'])
    df['Atrasada'] = np.where(condicao_b | condicao_a, True, False)

    df['Tempo_Estimado_Min'] = pd.to_numeric(df['Tempo_Estimado_Min'], errors='coerce')
    df['Tempo_Estimado_Horas'] = df['Tempo_Estimado_Min'] / 60

    if df.empty:
        st.error("Não foi possível carregar os dados do Trello. Verifique o arquivo JSON.")
        return

    pagina_selecionada = st.sidebar.radio("Selecione a página", ["Resumo Histórico", "Tarefas do Dia"])

    if pagina_selecionada == "Resumo Histórico":
        resumo_historico(df)
    elif pagina_selecionada == "Tarefas do Dia":
        tarefas_do_dia(df)


if __name__ == '__main__':
    st.set_page_config(layout="wide", page_title="Relatório de Produtividade")
    leitura_dados()
    main()
