import pandas as pd
import numpy as np
import asyncio
import webbrowser

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate


import plotly.express as px

from flask import Flask

import dash_bootstrap_components as dbc
import dash_loading_spinners as dls

from callTopDesk.callTopDesk import chamados

from dash_bootstrap_templates import load_figure_template
load_figure_template("minty")
load_figure_template("darkly")
load_figure_template("vapor")

# app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MINTY])

server = Flask(__name__)
app = dash.Dash(server=server, suppress_callback_exceptions=True, external_stylesheets=[  # type: ignore
                dbc.themes.VAPOR])  # type: ignore
app.title = 'Monitor de Chamados'
server = app.server


# =================== Layout ================== #

# =================== Layout ================== #
app.layout = dbc.Container(children=[
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H2("Monitor"), style={"text-align": "center"}
                ),
                dbc.CardBody([
                    html.H6("Horas para vencimento"),
                    dbc.InputGroup([
                        dbc.Input(id='input-horas', placeholder='Horas para vencimento', disabled=False,
                                  value=24, type='number', min=0),
                    ]),
                    html.H6("Operadores(as)", style={
                        "margin-top": "10px"}),
                    dbc.InputGroup([

                        dbc.Select(
                            id='select-operadores',
                            options=[
                                {'label': 'Todos', 'value': 1},
                            ],
                            disabled=True,
                            value='Todos',
                        ),
                    ]),
                ], style={"margin-top": "10px"}),
            ], style={"margin": "20px", "padding": "5px", "height": "100%"}),
        ], lg=2, sm=12),
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    html.H5(id='h5-chamados-proximos'),
                    dcc.Graph(id='graph-pie1'),
                    dcc.Interval(id='interval1', interval=15000),
                ], lg=5, sm=12, style={"margin-top": "20px"}),
                dbc.Col([
                    html.H5('"Chamados Respondidos" (Por Operador): '),
                    dcc.Graph(id='graph-pie2'),
                    dcc.Interval(id='interval2', interval=15000),
                ], lg=5, sm=12, style={"margin-top": "20px"}),
            ]),
            dbc.Row([
                dbc.Col([
                    html.H5(
                        'Chamados/Dias Sem Interação do Operador de Service Desk'),
                    dls.Pacman(
                        [
                            dcc.Graph(id="graph-chamados-acoes")],
                        color="#D9F028",
                        width=100,
                        speed_multiplier=1,
                        show_initially=True,
                        id="loading-store",
                    ),
                    html.Pre(id='data_click'),
                    dbc.Form([
                        html.Div([

                            dbc.Label("Intervalo de Dias",
                                      html_for="range-slider"),
                            dcc.RangeSlider(id="range-slider",
                                            min=None, max=None, step=30),
                        ]),
                        dcc.Interval(id="interval3", interval=1800000),
                    ], style={"margin-top": "10px"}),

                ], lg=10, sm=12, style={"margin-top": "20px"}),
            ]),
        ]),
    ]),
    dcc.Store(id="store")
], style={"padding": "0px"}, fluid=True)
# =================== CallBacks ================ #


@app.callback(
    Output('graph-pie1', 'figure'),
    Output('h5-chamados-proximos', 'children'),
    [
        Input('interval1', 'n_intervals'),
        Input('input-horas', 'value')
    ]
)
def render_graphs_chamados_prox_fim(n_intervals, horas):
    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       'thiago.leite', '7ejdu-gyzmx-cuoyp-qkb5w-o4dam')
    df_chamados_ProxFim = topDesk.filtroChamadosProxFim(horas)

    labels = list(df_chamados_ProxFim['OPERADOR'].value_counts().index)
    values = list(df_chamados_ProxFim['OPERADOR'].value_counts().values)

    if len(labels) == 0:
        df = topDesk.chamadosSLACorrenteDataFrame()
        labels = list(df['OPERADOR'].value_counts().index)
        print(labels)
        fig = px.pie(names=[], values=None)
        fig.update_layout(margin=dict(
            l=0, r=0, t=20, b=20), height=300, template="vapor")
        return fig, '"Chamados com Vencimento Próximo" (Por Operador)'
    elif len(labels) != 0:
        fig = px.pie(names=labels, values=values)
        fig.update_traces(
            textposition='inside', textinfo='percent+value')
        fig.update_layout(margin=dict(
            l=0, r=0, t=20, b=20), height=300, template="vapor")
        return fig, '"Chamados com vencimento nas próxmas {} horas" (Por Operador): '.format(horas)

# Renderiza o gráfico de chamados respondidos


@app.callback(
    Output('graph-pie2', 'figure'),
    [Input('interval2', 'n_intervals')]
)
def render_graphs_chamados_respondidos(n_intervals):
    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       'thiago.leite', '7ejdu-gyzmx-cuoyp-qkb5w-o4dam')
    df_chamados = topDesk.chamadosSLACorrenteDataFrame()
    df = df_chamados[df_chamados['STATUS'] == 'Respondido pelo usuário']

    labels = list(df['OPERADOR'].value_counts().index)
    values = list(df['OPERADOR'].value_counts().values)

    print(labels)
    if len(labels) == 0:
        df = topDesk.chamadosSLACorrenteDataFrame()
        labels = list(df['OPERADOR'].value_counts().index)
        print(labels)
        fig = px.pie(names=[], values=None)
        fig.update_layout(margin=dict(
            l=0, r=0, t=40, b=20), height=300, template="vapor")
        return fig
    elif len(labels) != 0:
        fig = px.pie(names=labels, values=values)
        fig.update_traces(textposition='inside', textinfo='percent+value')
        fig.update_layout(margin=dict(
            l=0, r=0, t=40, b=20), height=300, template="vapor")
        return fig


# Aqui geramos o DF e guardamos no store que será armazenado no cash do navegador do usuário


@app.callback(
    Output('store', 'data'),
    Output('select-operadores', 'options'),
    Output('select-operadores', 'disabled'),
    Output("loading-store", 'show_initially'),
    Input('interval3', 'n_intervals'),
)
def get_DF_UltimasAcoes(n_intervals):
    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       'thiago.leite', '7ejdu-gyzmx-cuoyp-qkb5w-o4dam')

    df_chamados = topDesk.DF_UltimasAcoes()

    df_filtro = df_chamados.sort_values(
        by='DIAS_ULTIMA_INTERACAO_OPERADOR', ascending=False).reset_index(drop=True)
    df_filtro = df_filtro[df_filtro['DIAS_ULTIMA_INTERACAO_OPERADOR'] > 1]

    lista_operadores = list(df_filtro['OPERADOR'].unique())
    lista_operadores.sort()
    lista_operadores.append('Todos')

    return df_filtro.to_dict(), lista_operadores, False, False

# Insere valor no slider range


@app.callback(
    Output('range-slider', 'min'),
    Output('range-slider', 'max'),
    Output('range-slider', 'value'),
    Input('store', 'data')
)
def input_values_range(data):
    df_ultimasAcoes = pd.DataFrame(data)
    return df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].min(), df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].max(), [df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].min(), df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].max()]  # type: ignore

# Renderiza o gráfico de chamados por dias sem interação dos operadores


@app.callback(
    Output('graph-chamados-acoes', 'figure'),
    [Input('store', 'data'), Input('interval3', 'n_intervals'),
     Input('range-slider', 'value'), Input('select-operadores', 'value')],

)
def render_graphs_chamados_p_dias_sem_interacao(data, n_intervals, value_range, value_select):
    df_ultimasAcoes = pd.DataFrame(data)
    min = int(value_range[0])
    max = int(value_range[1])
    print(value_select)
    if value_select == 'Todos':
        df_ultimasAcoes = df_ultimasAcoes[(df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'] >= min) & (
            df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'] <= max)]
        # print(df_ultimasAcoes)
        print('Minimo {}\nMaximo {}\nMIN {}\nMAX {}'.format(
            value_range, type(value_range), type(min), type(max)))
    else:
        df_ultimasAcoes = df_ultimasAcoes[(df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'] >= min) & (
            df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'] <= max) & (df_ultimasAcoes['OPERADOR'] == value_select)]

    # Posso testar com histogram no lugar de bar, porém tem que tirar o text
    fig = px.bar(df_ultimasAcoes, x='NUMERO_CHAMADO', y='DIAS_ULTIMA_INTERACAO_OPERADOR',
                 text='OPERADOR',
                 hover_data=['OPERADOR', 'STATUS', 'LINK'],
                 color='GRUPO_OPERADOR')
    fig.update_layout(template="vapor")

    return fig


# Callback que abre o link do chamado em uma nova tab
@app.callback(Output('data_click', 'children'), Input('graph-chamados-acoes', 'clickData'))
def event_clickData(clickData):
    if clickData:
        webbrowser.open_new_tab(clickData['points'][0]['customdata'][2])
    else:
        raise PreventUpdate


# ================= Run Server ================= #
if __name__ == '__main__':
    app.run_server(debug=False, port=8080, host='0.0.0.0')
