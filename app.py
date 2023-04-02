import pandas as pd
import numpy as np

import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State

import plotly.express as px

from flask import Flask

import dash_bootstrap_components as dbc

from callTopDesk.callTopDesk import chamados

from dash_bootstrap_templates import load_figure_template
load_figure_template("minty")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MINTY])
app.title = 'Monitor de Chamados'

# =================== Layout ================== #

# =========  Layout  =========== #
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
                    html.H6("Operadores(as)", style={"margin-top": "10px"}),
                    dbc.InputGroup([
                        dbc.Select(
                            options=[
                                {'label': 'Todos', 'value': 1}
                            ],
                            disabled=True,
                            value='Todos',
                        ),
                    ]),
                ], style={"margin-top": "10px"}),
            ], style={"margin": "20px", "padding": "5px", "height": "90vh"}),
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
            ]),
        ]),
    ])
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
            l=0, r=0, t=20, b=20), height=300, template="minty")
        return fig, '"Chamados com Vencimento Próximo" (Por Operador)'
    elif len(labels) != 0:
        fig = px.pie(names=labels, values=values)
        fig.update_traces(
            textposition='inside', textinfo='percent+value')
        fig.update_layout(margin=dict(
            l=0, r=0, t=20, b=20), height=300, template="minty")
        return fig, '"Chamados com vencimento nas próxmas {} horas" (Por Operador): '.format(horas)


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
            l=0, r=0, t=40, b=20), height=300, template="minty")
        return fig
    elif len(labels) != 0:
        fig = px.pie(names=labels, values=values)
        fig.update_traces(textposition='inside', textinfo='percent+value')
        fig.update_layout(margin=dict(
            l=0, r=0, t=40, b=20), height=300, template="minty")
        return fig


# ================= Run Server ================= #
if __name__ == '__main__':
    app.run_server(debug=True, port=8080, host='0.0.0.0')
