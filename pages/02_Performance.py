import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import StringIO
from utilidades import leitura_dados
# set page to be wider
st.set_page_config(layout="wide", page_title="Relatório de Produtividade")
leitura_dados()





def main():
    """
    Função principal que constrói a aplicação Streamlit.
    """
        
    df=st.session_state['dados']['df_trello']


    hoje = pd.Timestamp.now(tz='America/Sao_Paulo').normalize()
    
    inicio_semana = hoje - pd.to_timedelta(hoje.dayofweek, unit='d')
    
    fim_semana = inicio_semana + pd.to_timedelta(6, unit='d')

    # Tratando as colunas  Data_entrega e Data_Conclusao como date  'yyyy-mm-dd'
    df['Data_Entrega'] = pd.to_datetime(df['Data_Entrega'], format='%Y-%m-%d', errors='coerce')
    df['Data_Conclusao'] = pd.to_datetime(df['Data_Conclusao'], format='%Y-%m-%d', errors='coerce')
    

    # Coluna "Vencendo_Esta_Semana"
    df['Vencendo_Esta_Semana'] = (df['Data_Entrega'].dt.normalize() >= inicio_semana) & (df['Data_Entrega'].dt.normalize() <= fim_semana)

    # Coluna "Atrasada"
    condicao_a = (df['Data_Conclusao'].isna()) & (df['Data_Entrega'].notna()) & (df['Data_Entrega']< hoje)
    condicao_b = (df['Status'] != "CONCLUÍDO") & (df['Data_Entrega'] > df['Data_Conclusao'])
    df['Atrasada'] = np.where(condicao_b | condicao_a, True, False)
    # convert   df['Atrasada'].value_counts()  to dataframe 
    
    

    

    # Coluna "Tempo_Estimado_Horas"
    df['Tempo_Estimado_Min'] = pd.to_numeric(df['Tempo_Estimado_Min'], errors='coerce')
    df['Tempo_Estimado_Horas'] = df['Tempo_Estimado_Min'] / 60


    st.title("Relatório de Produtividade da Equipe")
    st.markdown("Use esta ferramenta para analisar a produtividade da equipe com base nos dados de tarefas.")

    
    # Filtro de rotina na sidebar
    incluir_rotinas = st.sidebar.checkbox('Incluir tarefas de rotina na análise', value=True)
    if not incluir_rotinas:
        df = df[df['Is_Rotina'] == False].copy()
        st.sidebar.info("Excluindo tarefas de rotina da análise.")

    # --- 3. ANÁLISE DESCRITIVA E VISUALIZAÇÃO ---
    st.header("Resumo Geral da Produtividade")

    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Tarefas", len(df))
    col2.metric("Tarefas Concluídas", df['Status'].value_counts().get("CONCLUÍDO", 0))
    col3.metric("Vencendo esta Semana", int(df['Vencendo_Esta_Semana'].sum()))
    col4.metric("Total de Tarefas Atrasadas", int(df['Atrasada'].sum()))

    st.markdown("---")

    # Dividir a tela em duas colunas para os gráficos e tabelas
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
        fig1.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig1, use_container_width=True)

    with col_grafico2:
        st.subheader("Tarefas Atrasadas por Membro")
        atrasos_por_membro = df[(df['Status']!="CONCLUÍDO")&(df['Atrasada'] == True)]['Membro'].value_counts()
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
            fig2.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.success("ߎ預arabéns! Nenhuma tarefa atrasada no período analisado.")
    st.markdown("---")
    # Opcional: Exibir os dados brutos filtrados
    if st.checkbox("Mostrar Tarefafas atrasadas"):
        # st.subheader("Dados Processados")
        df_atrasadas = df[(df['Status']!="CONCLUÍDO")&(df['Atrasada'] == True)][['Membro','Tarefa','Status']]
        st.dataframe(df_atrasadas, use_container_width=True)
        

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
            fig3.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
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

    # Opcional: Exibir os dados brutos filtrados
    if st.checkbox("Mostrar dados brutos processados"):
        st.subheader("Dados Processados")
        st.dataframe(df)



main()
