import requests
import base64
import pandas as pd
import numpy as np
import jmespath
from datetime import timezone
import datetime as dt
from dateutil import parser
import time
from pandarallel import pandarallel
import pytz
from openAI.openAI import ChatGPT as chatgpt

ChatGPT = chatgpt()

pandarallel.initialize(progress_bar=True)


# Conectando com a API do TopDesk
class chamados:

    def __init__(self, topdesk_url, operador, chave):
        self._topdesk_url = topdesk_url
        self._operador = operador
        self._chave = base64.b64encode(
            (self._operador + ':' + chave).encode('utf-8')).decode('utf-8')
        self._header = {'Authorization': 'Basic {}'.format(self._chave)}

    # Retorna chamados abertos

    def conexao(self, incrementoBusca=''):
        if requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 200:
            return '200: Sucesso', requests.get(self._topdesk_url + '/incidents' + incrementoBusca,
                                                headers=self._header)
        elif requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 204:
            return '204: Sucesso, nenhum incidente (correspondente) encontrado', requests.get(
                self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header)
        elif requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 206:
            return '206: Sucesso, mas existem mais incidentes', requests.get(
                self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header)
        elif requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 400:
            return '400: Pedido Ruim', requests.get(self._topdesk_url + '/incidents' + incrementoBusca,
                                                    headers=self._header)
        elif requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 401:
            return '401: Não autorizado (Nenhum token valido de autenticação fornecido)', requests.get(
                self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header)
        elif requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 403:
            return '403: Sem permissão para acesso aos dados', requests.get(
                self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header)
        elif requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 404:
            return '404: Não encontrado', requests.get(self._topdesk_url + '/incidents' + incrementoBusca,
                                                       headers=self._header)
        elif requests.get(self._topdesk_url + '/incidents' + incrementoBusca, headers=self._header).status_code == 500:
            return '500: Erro do Servidor Interno', requests.get(self._topdesk_url + '/incidents' + incrementoBusca,
                                                                 headers=self._header)

    def buscaChamado(self, chamado):
        return self.conexao('/number/' + chamado)

    def chamadosSLACorrente(self):
        return requests.get(self._topdesk_url + '/incidents?page_size=10000&query=completed==False;('
                                                'operatorGroup.name=="TI - Service Desk",operatorGroup.name=="TI - '
                                                'Field Service",operatorGroup.name=="TI - Service Desk (N2)");('
                                                'callType.name==Requisição,callType.name==Incidente)',
                            headers=self._header)

    def chamados_agendados_com_usuario(self):
        return requests.get(self._topdesk_url + '/incidents?page_size=10000&query=completed==False;('
                            'operatorGroup.name=="TI - Service Desk",operatorGroup.name=="TI - '
                            'Field Service",operatorGroup.name=="TI - Service Desk (N2)");('
                            'callType.name==Requisição,callType.name==Incidente)',
                            headers=self._header)

    def chamadosSLACorrenteDataFrame(self):
        expression = """{
        NIVEL: status,
        NUMERO_CHAMADO: number,
        TIPO_CHAMADO: callType.name,
        SOLICITANTE: caller.dynamicName,
        CATEGORIA: category.name,
        SUBCATEGORIA: subcategory.name,
        DATA_ABERTURA: callDate,
        DATA_ALVO: targetDate,
        GRUPO_OPERADOR: operatorGroup.name,
        OPERADOR: operator.name,
        FORNECEDOR: supplier.name,
        STATUS: processingStatus.name,
        ACOES: action
        }
        """
        list_expression = []
        for i in self.chamadosSLACorrente().json():
            list_expression.append(jmespath.compile(expression).search(i))

        # Inserindo list no Data Frame
        df_chamados = pd.DataFrame(list_expression, columns=['NUMERO_CHAMADO', 'NIVEL', 'TIPO_CHAMADO',
                                                             'SOLICITANTE', 'CATEGORIA',
                                                             'SUBCATEGORIA', 'DATA_ABERTURA',
                                                             'DATA_ALVO', 'GRUPO_OPERADOR',
                                                             'OPERADOR', 'FORNECEDOR',
                                                             'STATUS', 'ACOES'])

        # Convertendo o fuso horário dos campos que contém datas
        df_chamados['DATA_ABERTURA'] = pd.to_datetime(
            df_chamados['DATA_ABERTURA']).dt.tz_convert('America/Sao_Paulo')
        df_chamados['DATA_ALVO'] = pd.to_datetime(
            df_chamados['DATA_ALVO']).dt.tz_convert('America/Sao_Paulo')

        # Alterando nomenclatura para os níveis de chamado
        df_chamados['NIVEL'].replace(
            'firstLine', 'Primeiro Nivel', inplace=True)
        df_chamados['NIVEL'].replace(
            'secondLine', 'Segundo Nivel', inplace=True)

        # Muda os valores None na coluna Fornecedores para NaN
        df_chamados['FORNECEDOR'] = df_chamados['FORNECEDOR'].fillna(
            value=np.nan)

        # Cria coluna que receberá o tempo restante para o chamado estourar
        df_chamados['TEMPO_RESTANTE'] = np.nan
        df_chamados = df_chamados[['NUMERO_CHAMADO', 'NIVEL', 'TIPO_CHAMADO', 'SOLICITANTE', 'CATEGORIA',
                                   'SUBCATEGORIA', 'DATA_ABERTURA', 'DATA_ALVO', 'TEMPO_RESTANTE', 'GRUPO_OPERADOR',
                                   'OPERADOR', 'FORNECEDOR', 'STATUS', 'ACOES']]

        dt_data_now = dt.datetime.fromtimestamp(time.time())
        for idx in df_chamados.iterrows():
            # print(idx[1]['NUMERO_CHAMADO'])
            dt_data_alvo = dt.datetime.fromtimestamp(
                idx[1]['DATA_ALVO'].timestamp())
            diff_seconds = (dt_data_alvo - dt_data_now).total_seconds()
            idx[1]['TEMPO_RESTANTE'] = int(diff_seconds / 3600)
            df_chamados.loc[df_chamados['NUMERO_CHAMADO'] == idx[1]['NUMERO_CHAMADO'], 'TEMPO_RESTANTE'] = int(
                diff_seconds / 3600)

        return df_chamados

    def filtroChamadosProxFim(self, horas=1000):
        df_chamados = self.chamadosSLACorrenteDataFrame()
        return df_chamados[(df_chamados['TEMPO_RESTANTE'] >= 0) & (df_chamados['TEMPO_RESTANTE'] < horas) &
                           ((df_chamados['STATUS'] != 'Pendente Fornecedor') & (df_chamados['STATUS'] != 'Pendente cliente') &
                            (df_chamados['STATUS'] != 'Pendente análise do problema') & (df_chamados['STATUS'] != 'Pendente análise do problema') &
                            (df_chamados['STATUS'] != 'Pendente análise') & (df_chamados['STATUS'] != 'Pendente autorização') &
                            (df_chamados['STATUS'] != 'Agendado com o Usuário'))].sort_values(by='TEMPO_RESTANTE')

    # Aqui ele busca a data da ultima interação de fato de um operador com o cliente
    def get_date_last_action(self, x):
        import requests
        import pandas as pd
        from autenticacao import Autenticacao_TopDesk as autenticacao
        Autenticacao = autenticacao()
        query_inicio = 'http://rioquente.topdesk.net'

        chave = base64.b64encode(
            (Autenticacao.user() + ':' + Autenticacao.key()).encode('utf-8')).decode('utf-8')
        header = {'Authorization': 'Basic {}'.format(chave)}

        def percorre_acoes(response):
            for i in range(len(response.json())):
                if (response.json()[i]['invisibleForCaller'] == False) and (response.json()[i]['operator'] != None):
                    # print(response.json()[i]['creationDate'])
                    return pd.to_datetime(response.json()[i]['creationDate']).tz_convert('America/Sao_Paulo')
                elif i < len(response.json()) - 1:
                    # print(i)
                    continue
                else:
                    # print(i)
                    return None

        # print(x.ACOES)
        response = requests.get(query_inicio+x.ACOES, headers=header)
        if response.status_code == 204:
            #print('Chamado {} data ultima interação {}!'.format(df.NUMERO_CHAMADO, pd.to_datetime('')))
            return pd.to_datetime('')
        elif (response.status_code == 200) or (response.status_code == 206):
            data = percorre_acoes(response)
            if data != None:
                #print('Chamado {} data ultima interação {}!'.format(df.NUMERO_CHAMADO, data))
                return data
            else:
                #print('Chamado {} data ultima interação {}!'.format(df.NUMERO_CHAMADO, pd.to_datetime('')))
                return pd.to_datetime('')

    # Aqui ele calcula os dias desde a ultima interação do operador

    def calcula_dias_acao(self, df):
        if type(df['DATA_ULTIMA_INTERACAO_OPERADOR']) == type(pd.to_datetime('')):
            return (dt.datetime.today() - dt.datetime.fromtimestamp(df['DATA_ABERTURA'].timestamp())).days
        else:
            return (dt.datetime.today() - dt.datetime.fromtimestamp(df['DATA_ULTIMA_INTERACAO_OPERADOR'].timestamp())).days

    # Aqui gera o Data Frame final com dias e data de ultima interação
    def DF_UltimasAcoes(self):
        df_tmp = self.chamadosSLACorrenteDataFrame()

        df_tmp['DATA_ABERTURA'] = pd.to_datetime(
            df_tmp['DATA_ABERTURA']).dt.tz_convert('America/Sao_Paulo')

        df_tmp['DATA_ALVO'] = pd.to_datetime(
            df_tmp['DATA_ALVO']).dt.tz_convert('America/Sao_Paulo')

        df_tmp['LINK'] = 'https://rioquente.topdesk.net/tas/secure/incident?action=lookup&lookup=naam&lookupValue=' + \
            df_tmp['NUMERO_CHAMADO']

        df_tmp['DATA_ULTIMA_INTERACAO_OPERADOR'] = df_tmp.parallel_apply(self.get_date_last_action, axis=1)  # type: ignore

        df_tmp['DIAS_ULTIMA_INTERACAO_OPERADOR'] = df_tmp.apply(lambda row: self.calcula_dias_acao(
            row[['DATA_ABERTURA', 'DATA_ULTIMA_INTERACAO_OPERADOR']]), axis=1)
        print(df_tmp)
        return df_tmp

    # Aqui obtemos o Data Frame com os agendamentos já com a coluna de data e hora

    def DF_Agendamentos(self):
        expression = """{
        NIVEL: status,
        NUMERO_CHAMADO: number,
        TIPO_CHAMADO: callType.name,
        SOLICITANTE: caller.dynamicName,
        CATEGORIA: category.name,
        SUBCATEGORIA: subcategory.name,
        DATA_ABERTURA: callDate,
        DATA_ALVO: targetDate,
        GRUPO_OPERADOR: operatorGroup.name,
        OPERADOR: operator.name,
        FORNECEDOR: supplier.name,
        STATUS: processingStatus.name,
        ACOES: action
        }
        """
        list_expression = []
        for i in self.chamados_agendados_com_usuario():
            list_expression.append(jmespath.compile(expression).search(i))

        df_chamados_agendados = pd.DataFrame(list_expression, columns=['NUMERO_CHAMADO', 'NIVEL', 'TIPO_CHAMADO',
                                                                       'SOLICITANTE', 'CATEGORIA',
                                                                       'SUBCATEGORIA', 'DATA_ABERTURA',
                                                                       'DATA_ALVO', 'GRUPO_OPERADOR',
                                                                       'OPERADOR', 'FORNECEDOR',
                                                                       'STATUS', 'ACOES'])

        df_chamados_agendados['DATA_AGENDAMENTO'] = df_chamados_agendados['ACOES'].apply(
            lambda x: self.percorre_acoes_agendamento(x))

    def percorre_acoes_agendamento(self, query):
        query_inicio = 'http://rioquente.topdesk.net'
        print(query)
        response = requests.get(query_inicio+query, headers=self._header)
        # print(response.json())
        if response.status_code == 200:
            for acao in range(len(response.json())):
                if (response.json()[acao]['invisibleForCaller'] == False) and (response.json()[acao]['operator'] != None):
                    print(response.json()[acao]['plainText'])
                    data = dt.datetime.strptime(
                        response.json()[acao]['creationDate'], '%Y-%m-%dT%H:%M:%S.%f%z')
                    fuso_horario_destino = pytz.timezone('America/Sao_Paulo')
                    pergunta = f'O texto foi criado em {str(data.astimezone(fuso_horario_destino))} (use esta data somente como referência para compreender o agendamento): considerando o texto, para qual data foi agendado? Quero a resposta resumida formato dd/mm/YYYY HH:MM:SS'
                    resposta = ChatGPT.get_response(
                        pergunta, response.json()[acao]['plainText'])
                    try:
                        data_hora = parser.parse(
                            resposta.choices[0].text, dayfirst=True)
                        if data_hora.astimezone(fuso_horario_destino) < data.astimezone(fuso_horario_destino):
                            data_hora = ''
                            print(f'\nHora vazia')
                        data_hora_str = str(data_hora)
                        print(f'A data e hora do agendamento foi: {data_hora_str}')
                    except Exception as e:
                        print(f'Deu o seguinte erro {e}')
                        continue
                elif acao < len(response.json()) - 1:
                    continue
                else:
                    data_hora_str = ''
                    break
        elif response.status_code == 204:
            data_hora_str = ''

        return data_hora_str
