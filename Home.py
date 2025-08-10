import streamlit as st

from pathlib import Path

st.sidebar.markdown('Dessenvolvido por [Brayan Maurico Rodríguez](https://sites.google.com/view/brayanmauricio)')

      
st.title("Bem-vindo ao Relatório de Produtividade da Equipe!")
st.markdown("---")

st.markdown(
    """
    Este dashboard foi criado para ajudar você a visualizar e analisar a produtividade da sua equipe 
    com base nos dados do Trello. Ele oferece uma visão clara do status das tarefas, 
    do tempo estimado de trabalho e da alocação de cada membro.
    """
)


st.header("Como usar o Dashboard")

st.markdown(
    """
    Utilize o menu na barra lateral para navegar entre as diferentes seções:
    
    - **Resumo Histórico:** Analise a performance geral da equipe, com métricas de tarefas concluídas, atrasadas e carga horária total.
    
    - **Tarefas do Dia:** Obtenha uma visão diária da alocação de tarefas e tempo estimado de trabalho por membro da equipe.
    """
)

st.subheader("Filtros")
st.markdown(
    """
    Na barra lateral, você encontrará a opção **"Incluir tarefas de rotina na análise"**. 
    Desmarque esta opção para excluir tarefas com a etiqueta 'rotina' da análise, 
    permitindo que você se concentre apenas em projetos e demandas pontuais.
    """
)

st.markdown("---")
st.info("Os dados são atualizados com base no arquivo `trello.json` na raiz do seu repositório. Para análises precisas, certifique-se de que o arquivo esteja sempre atualizado.")

st.divider()

st.markdown(

'''
Dash interativo, armazenado em  [GitHub](https://github.com/bramau9010) 
'''
)

