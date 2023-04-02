import requests
import base64
import pandas as pd
import numpy as np
import jmespath
from datetime import timezone
import datetime
import pytz
import time


# Conectando com a API do TopDesk
class chamados:

    def __init__(self, topdesk_url, operador, chave):
        self._topdesk_url = topdesk_url
        self._operador = operador
        self._chave = base64.b64encode((self._operador + ':' + chave).encode('utf-8')).decode('utf-8')
        self._header = {'Authorization': 'Basic {}'.format(self._chave)}

    # Retorna chamados abertos
    def mostra(self):
        print(self._chave)

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
        STATUS: processingStatus.name
        }
        """
        list_expression = []
        for i in self.chamadosSLACorrente().json():
            list_expression.append(jmespath.compile(expression).search(i))

        #Inserindo list no Data Frame
        df_chamados = pd.DataFrame(list_expression, columns=['NUMERO_CHAMADO','NIVEL','TIPO_CHAMADO',
                                                     'SOLICITANTE','CATEGORIA',
                                                     'SUBCATEGORIA','DATA_ABERTURA',
                                                    'DATA_ALVO','GRUPO_OPERADOR',
                                                    'OPERADOR','FORNECEDOR',
                                                    'STATUS'])

        #Convertendo o fuso horário dos campos que contém datas
        df_chamados['DATA_ABERTURA'] = pd.to_datetime(df_chamados['DATA_ABERTURA']).dt.tz_convert('America/Sao_Paulo')
        df_chamados['DATA_ALVO'] = pd.to_datetime(df_chamados['DATA_ALVO']).dt.tz_convert('America/Sao_Paulo')

        #Alterando nomenclatura para os níveis de chamado
        df_chamados['NIVEL'].replace('firstLine', 'Primeiro Nivel', inplace=True)
        df_chamados['NIVEL'].replace('secondLine', 'Segundo Nivel', inplace=True)

        #Muda os valores None na coluna Fornecedores para NaN
        df_chamados['FORNECEDOR'] = df_chamados['FORNECEDOR'].fillna(value=np.nan)

        #Cria coluna que receberá o tempo restante para o chamado estourar
        df_chamados['TEMPO_RESTANTE'] = np.nan
        df_chamados = df_chamados[['NUMERO_CHAMADO', 'NIVEL', 'TIPO_CHAMADO', 'SOLICITANTE', 'CATEGORIA',
                                   'SUBCATEGORIA', 'DATA_ABERTURA', 'DATA_ALVO', 'TEMPO_RESTANTE', 'GRUPO_OPERADOR',
                                   'OPERADOR', 'FORNECEDOR', 'STATUS']]

        dt_data_now = datetime.datetime.fromtimestamp(time.time())
        for idx in df_chamados.iterrows():
            # print(idx[1]['NUMERO_CHAMADO'])
            dt_data_alvo = datetime.datetime.fromtimestamp(idx[1]['DATA_ALVO'].timestamp())
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
                            (df_chamados['STATUS'] != 'Pendente análise') & (df_chamados['STATUS'] != 'Pendente autorização'))].sort_values(by='TEMPO_RESTANTE')

    def filtroChamadosAbertosCategoria(self, categoria=None):
        df_chamados = self.chamadosSLACorrenteDataFrame()
        if categoria == None:
            return df_chamados
        else:
            return df_chamados[df_chamados['CATEGORIA'] == categoria]