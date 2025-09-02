from pathlib import Path
import pandas as pd
import streamlit as st
from datetime import datetime

import json

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

def leitura_dados():
    if not 'dados' in st.session_state:

        '''
        Esta primeirra parte carrega o histórico de atingimento de metas, ele procura na mpasta caminho, a qual deve ser atualizada a cada
        fechamento de mês, os arquivos que terminam com 'V5 - ajuste das dinamicas.xlsx' ou 'V5 - ajuste das dinamicas.xlsm'. Ajustar para que isto siga sendo assim

        '''



        # --- CONFIGURAÇÃO DO LOGGING ---
        # Configura o logger para exibir mensagens informativas, incluindo data e hora.
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logger = logging.getLogger(__name__)

        # --- CONSTANTES DE CONFIGURAÇÃO ---
        # Palavras-chave para identificar as listas de forma flexível (use minúsculas)
        KEYWORDS_TODO = ['fazer', 'to-do', 'backlog']
        KEYWORDS_DOING = ['fazendo', 'doing', 'em andamento', 'in progress']
        KEYWORDS_DONE = ['concluído', 'done', 'feito']

        # Nome exato do campo customizado e valor padrão
        CUSTOM_FIELD_NAME = 'Tempo de execução em minutos'
        DEFAULT_EXECUTION_TIME_MIN = 30

        class TrelloDataFrameBuilder:
            """
            Classe para carregar, processar e estruturar dados de um export JSON do Trello
            em um DataFrame do Pandas, pronto para análise.
            """

            def __init__(self, json_path: str):
                """
                Inicializa o construtor do DataFrame.

                Args:
                    json_path (str): O caminho para o arquivo JSON do Trello.
                """
                self.json_path = json_path
                self.data: Optional[Dict[str, Any]] = None
                self._id_to_member: Dict[str, Dict] = {}
                self._id_to_label: Dict[str, str] = {}
                self._id_to_list: Dict[str, Dict] = {}
                self._custom_field_id: Optional[str] = None

            def _load_data(self) -> bool:
                """
                Método privado para carregar os dados do arquivo JSON.

                Returns:
                    bool: True se os dados foram carregados com sucesso, False caso contrário.
                """
                logger.info(f"Carregando dados de: {self.json_path}")
                try:
                    with open(self.json_path, "r", encoding="utf-8") as file:
                        self.data = json.load(file)
                    return True
                except FileNotFoundError:
                    logger.error(f"Arquivo JSON não encontrado em '{self.json_path}'.")
                    return False
                except json.JSONDecodeError:
                    logger.error(f"O arquivo JSON '{self.json_path}' está malformado ou corrompido.")
                    return False

            def _map_entities(self):
                """Método privado para mapear entidades do Trello (membros, etiquetas, listas)."""
                if not self.data:
                    logger.warning("Não há dados para mapear. Carregue os dados primeiro.")
                    return

                self._id_to_member = {m["id"]: {"name": m["fullName"]} for m in self.data.get("members", [])}
                self._id_to_label = {lbl["id"]: lbl["name"] for lbl in self.data.get("labels", [])}

                for lst in self.data.get("lists", []):
                    name_lower = lst["name"].lower().strip()
                    status = None
                    if any(keyword in name_lower for keyword in KEYWORDS_TODO):
                        status = "A FAZER"
                    elif any(keyword in name_lower for keyword in KEYWORDS_DOING):
                        status = "FAZENDO"
                    elif any(keyword in name_lower for keyword in KEYWORDS_DONE):
                        status = "CONCLUÍDO"
                    
                    if status:
                        self._id_to_list[lst["id"]] = {"name": lst["name"], "status": status}
                
                self._custom_field_id = next((f["id"] for f in self.data.get("customFields", []) if f.get("name") == CUSTOM_FIELD_NAME), None)
                
                logger.info(f"Mapeamento concluído. Listas identificadas: {list(l['status'] for l in self._id_to_list.values())}")


            def build_master_dataframe(self) -> pd.DataFrame:
                """
                Orquestra o processo de criação do DataFrame mestre.

                Carrega os dados, mapeia as entidades, processa cada card aplicando as regras de
                negócio e retorna um DataFrame final com o schema definido.

                Returns:
                    pd.DataFrame: Um DataFrame Pandas estruturado e pronto para análise.
                """
                if not self._load_data():
                    return pd.DataFrame() # Retorna DF vazio se o carregamento falhar

                self._map_entities()
                
                logger.info("Iniciando processamento dos cards para construção do DataFrame...")
                processed_tasks: List[Dict] = []
                for card in self.data.get("cards", []):
                    if card.get("closed") or card.get("idList") not in self._id_to_list:
                        continue

                    list_info = self._id_to_list[card["idList"]]
                    
                    label_ids = card.get("idLabels", [])
                    labels = [self._id_to_label.get(lid, "") for lid in label_ids]
                    is_routine = any('rotina' in lbl.lower() for lbl in labels)

                    # --- Aplicação das Regras de Negócio ---
                    execution_time = pd.NA
                    due_date = pd.to_datetime(card.get("due"), errors='coerce', utc=True)
                    
                    if is_routine:
                        execution_time = DEFAULT_EXECUTION_TIME_MIN
                        if self._custom_field_id and 'customFieldItems' in card:
                            for item in card["customFieldItems"]:
                                if item.get("idCustomField") == self._custom_field_id and 'value' in item:
                                    time_val = item['value'].get('number')
                                    if time_val and str(time_val).isdigit():
                                        execution_time = int(time_val)
                                    break
                    elif pd.isna(due_date):
                        last_activity_date = pd.to_datetime(card.get("dateLastActivity"), errors='coerce', utc=True)
                        if pd.notna(last_activity_date):
                            due_date = last_activity_date + timedelta(days=1)
                    
                    conclusion_date = pd.to_datetime(card.get("dateLastActivity"), errors='coerce', utc=True) if list_info["status"] == "CONCLUÍDO" else pd.NaT

                    member_ids = card.get("idMembers", [])
                    if not member_ids:
                        member_ids.append("UNASSIGNED")
                        self._id_to_member["UNASSIGNED"] = {"name": "Não Atribuído"}

                    for member_id in member_ids:
                        member_info = self._id_to_member.get(member_id)
                        if not member_info: continue

                        processed_tasks.append({
                            'ID_Tarefa': card.get("id"),
                            'Tarefa': card.get("name", "Sem Título"),
                            'ID_Membro': member_id,
                            'Membro': str(member_info["name"]).strip().split()[0].upper(),
                            'ID_Lista': card.get("idList"),
                            'Status': list_info["status"],
                            'Data_Entrega': due_date,
                            'Data_Conclusao': conclusion_date,
                            'Etiquetas': ", ".join(filter(None, labels)),
                            'Is_Rotina': is_routine,
                            'Tempo_Estimado_Min': execution_time
                        })

                if not processed_tasks:
                    logger.warning("Nenhum card foi processado. Verifique o conteúdo do JSON.")
                    return pd.DataFrame()

                df = pd.DataFrame(processed_tasks)
                
                # --- Definição do Schema e Tipos de Dados ---
                schema = {
                    "ID_Tarefa": "string", "Tarefa": "string", "ID_Membro": "string", "Membro": "string",
                    "ID_Lista": "string", "Status": "category", "Etiquetas": "string",
                    "Is_Rotina": "boolean", "Tempo_Estimado_Min": "Int64"
                }
                df = df.astype(schema)
                df['Data_Entrega'] = df['Data_Entrega'].dt.tz_convert('America/Sao_Paulo')
                df['Data_Conclusao'] = df['Data_Conclusao'].dt.tz_convert('America/Sao_Paulo')
                
                final_columns_order = [
                    'ID_Tarefa', 'Tarefa', 'ID_Membro', 'Membro', 'ID_Lista', 'Status',
                    'Data_Entrega', 'Data_Conclusao', 'Etiquetas', 'Is_Rotina', 'Tempo_Estimado_Min'
                ]
                
                logger.info(f"DataFrame mestre construído com sucesso, contendo {len(df)} registros.")
                return df[final_columns_order]


        # --- Bloco Principal de Execução ---
        
        # --- Configuração ---
        TRELLO_JSON_PATH = "trello.json"  # Coloque o caminho para o seu arquivo aqui
        
        # 1. Instanciar a classe
        builder = TrelloDataFrameBuilder(json_path=TRELLO_JSON_PATH)
        
        # 2. Chamar o método principal para construir o DataFrame
        df_mestre = builder.build_master_dataframe()
        df_mestre = df_mestre[df_mestre['Membro']!='NÃO']
        

        # 3. Exibir resultados para verificação
        if not df_mestre.empty:

            pass
        
        else:
            st.error("Não foi possível carregar os dados do Trello. Verifique o arquivo JSON.")
            

            

        dados={
            'df_trello':df_mestre
        }
        st.session_state['dados']=dados

        

        
