import dash
from dash import html, dcc, Input, Output, State
from dash import dash_table as dt
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash_bootstrap_templates import ThemeSwitchAIO
import dash_loading_spinners as dls

from flask import Flask

from callTopDesk.callTopDesk import chamados
from autenticacao import Autenticacao as autenticacao

Autenticacao = autenticacao()

# ===================== App ===================== #
FONT_AWESOME = ["https://use.fontawesome.com/releases/v5.10.2/css/all.css"]
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

app = dash.Dash(__name__, external_stylesheets=[
                FONT_AWESOME, dbc.themes.BOOTSTRAP, dbc_css])
app.scripts.config.serve_locally = True
server = app.server

df = pd.DataFrame()

# =================== Styles ==================== #
template_theme1 = "minty"
template_theme2 = "vapor"
url_theme1 = dbc.themes.MINTY
url_theme2 = dbc.themes.VAPOR

tab_card = {"height": "100%"}

# Em Plotly as figuras podem ser customizadas através de dicionários
# Configurar legendas, efeitos de hover..
main_config = {
    "hovermode": "x unified",
    "legend": {
        "yanchor": "top",
        "y": 0.9,
        "xanchor": "left",
        "x": 0.1,
        "title": {"text": None},
        "font": {"color": "white"},
        "bgcolor": "rgba(0,0,0,0.5)"},
    "margin": {"l": 0, "r": 0, "t": 10, "b": 0}
}

# =================== Layout ==================== #

datatable_agendados = html.Div(
    dt.DataTable(
        id="tabela-agendamentos",
        filter_action="native",
    )
)

datatable_agendados_with_theme = html.Div(
    [
        html.H4("Teste Tabelas DataTable"),
        datatable_agendados
    ],
    className="dbc"
)

datatable_chamados_vencendo = html.Div(
    dt.DataTable(
        id="tabela-chamados-vencendo",
        filter_action="native",
        page_size=10,
        style_table={'height': '100%', 'width': '100%'}
    )
)

datatable_chamados_vencendo_with_theme = html.Div(
    [
        datatable_chamados_vencendo
    ],
    className="dbc"
)

datatable_chamados_respondidos = html.Div(
    dt.DataTable(
        id="tabela-chamados-respondidos",
        filter_action="native",
        page_size=10,
        style_table={'height': '50%', 'width': '100%'}
    )
)

datatable_chamados_respondidos_with_theme = html.Div(
    [
        datatable_chamados_respondidos
    ],
    className="dbc"
)

app.layout = dbc.Container(children=[
    # Layout de fato
    # Row 1
    dbc.Row([
        # Col 1 contendo o card com titulo e seletor de tema
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H3("Monitor")
                        ], sm=8),
                        dbc.Col([
                            html.I(className="fas fa-fire-extinguisher",
                                   style={"font-size": "400%"})
                        ], sm=4, align="center"),
                        dbc.Row([
                            dbc.Col([
                                ThemeSwitchAIO(aio_id="theme", themes=[
                                    url_theme1, url_theme2
                                ]),
                                html.H6("Monitor de Chamados")
                            ]),
                        ], style={"margin-top": "10px"}),
                    ]),
                ]),
            ], style=tab_card),
        ], sm=12, md=12, lg=2),

        # Col 2 - Card contendo o gráfico de chamado próximos do vencimento
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H4(id="h5-chamados-proximos",
                                    children=["Horas para vencimento"]),
                            # Esta config no gráfico tira as oções do Plotly de salvar gráfico, dar zoom e etc..
                            dcc.Graph(
                                id='graph-pie1', config={"displayModeBar": False, "showTips": False}),
                            dcc.Interval(id='interval1', interval=15000),
                            dbc.InputGroup([
                                html.Legend("Horas para o vencimento: "),
                                dbc.Input(id="input-horas", placeholder="Horas para vencimento", disabled=False,
                                          value=24, type="number", min=0, className="dbc"),
                            ]),
                        ]),
                        dbc.Col([
                            dbc.Container(datatable_chamados_vencendo_with_theme)
                        ]),
                    ])
                ])
            ], style=tab_card),
        ], sm=12, md=12, lg=5),

        # Col 3 - Card contendo gráfico de chamados respondidos
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H4('"Chamados Respondidos" (Por Operador): '),
                            dcc.Graph(
                                id="graph-pie2", config={"displayModeBar": False, "showTips": False}),
                            dcc.Interval(id="interval2", interval=15000),
                        ]),
                        dbc.Col([
                            dbc.Container(datatable_chamados_respondidos_with_theme)    
                        ]),
                    ]),
                ]),
            ], style=tab_card),
        ], sm=12, md=12, lg=5),
    ], class_name="main_row g-2 my-auto", style={'margin-top': '7px'}),  # Fim da Row 1

    # Row 2 - Abraça o gráfico de chamados sem interação do operador
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4(
                        "Chamados/Dias Sem Interação do Operador de Service Desk"),
                    dbc.Row([
                        dbc.Col([
                            dbc.InputGroup([
                                html.Legend("Selecione Operador: "),
                                dbc.Select(
                                    id='select-operadores',
                                    options=[
                                        {'label': 'Todos', 'value': 1},
                                    ],
                                    disabled=True,
                                    value='Todos',
                                ),
                            ]),
                        ]),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dls.Pacman(
                                [
                                    dcc.Graph(id="graph-chamados-acoes",
                                              config={
                                                  "displayModeBar": False,
                                                  "showTips": False},
                                              style={"margin-top": "30px"}),],
                                color="#D9F028",
                                width=100,
                                speed_multiplier=1,
                                show_initially=True,
                                id="loading-store",
                            ),
                        ]),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Form([
                                html.Div([

                                    dbc.Label("Intervalo de Dias",
                                              html_for="range-slider"),
                                    dcc.RangeSlider(id="range-slider",
                                                    min=None, max=None, step=30),
                                ]),
                                dcc.Interval(id="interval3", interval=1800000),
                            ], style={"margin-top": "10px"}),
                        ]),
                    ]),
                ]),
            ], style=tab_card),
        ], sm=12, md=12, lg=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Container(datatable_agendados_with_theme)
                        ]),
                    ]),
                ]),
            ], style=tab_card),
        ], sm=12, md=12, lg=6),

    ], className='main_row g-2 my-auto'),
    dcc.Store(id="store")
], fluid=True, style={"height": "100%"})

# ============================================================== Callbacks ================================================================ #


@app.callback(
    Output('graph-pie1', 'figure'),
    Output('h5-chamados-proximos', 'children'),
    [
        Input('interval1', 'n_intervals'),
        Input('input-horas', 'value'),
        Input(ThemeSwitchAIO.ids.switch("theme"), "value")
    ]
)
def render_graphs_chamados_prox_fim(n_intervals, horas, toggle):
    template = template_theme1 if toggle else template_theme2

    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       Autenticacao.user(), Autenticacao.key())
    df_chamados_ProxFim = topDesk.filtroChamadosProxFim(horas)

    labels = list(df_chamados_ProxFim['OPERADOR'].value_counts().index)
    values = list(df_chamados_ProxFim['OPERADOR'].value_counts().values)

    if len(labels) == 0:
        df = topDesk.chamadosSLACorrenteDataFrame()
        labels = list(df['OPERADOR'].value_counts().index)
        print(labels)
        fig = px.pie(names=[], values=None)
        fig.update_layout(margin=dict(
            l=0, r=0, t=20, b=20), height=300, template=template)
        return fig, '"Chamados com Vencimento Próximo" (Por Operador)'
    elif len(labels) != 0:
        fig = px.pie(names=labels, values=values)
        fig.update_traces(
            textposition='inside', textinfo='percent+value')
        fig.update_layout(margin=dict(
            l=0, r=0, t=20, b=20), height=300, template=template)
        return fig, '"Chamados com vencimento nas próximas {} horas" (Por Operador): '.format(horas)
    
# Callback chamados próximo de vencer
@app.callback(
    dash.dependencies.Output('tabela-chamados-vencendo', 'data'),
    dash.dependencies.Output('tabela-chamados-vencendo', 'columns'),
    dash.dependencies.Input('interval1', 'n_intervals'),
    Input('input-horas', 'value'),
)
def input_datatable_chamados_vencendo(n_intervals, horas):

    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       Autenticacao.user(), Autenticacao.key())
    df_chamados_ProxFim = topDesk.filtroChamadosProxFim(horas)

    columns = [{"name": i, "id": i, "presentation": "markdown"} if i == "CHAMADO (LINK)" else {
        "name": i, "id": i} for i in df_chamados_ProxFim[["CHAMADO (LINK)", "OPERADOR"]].columns]

    return df_chamados_ProxFim.to_dict('records'), columns


# Callback - Renderiza o gráfico de chamados respondidos


@app.callback(
    Output('graph-pie2', 'figure'),
    [Input('interval2', 'n_intervals'),
     Input(ThemeSwitchAIO.ids.switch("theme"), "value")]
)
def render_graphs_chamados_respondidos(n_intervals, toggle):
    template = template_theme1 if toggle else template_theme2

    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       Autenticacao.user(), Autenticacao.key())
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
            l=0, r=0, t=40, b=20), height=300, template=template)
        return fig
    elif len(labels) != 0:
        fig = px.pie(names=labels, values=values)
        fig.update_traces(textposition='inside', textinfo='percent+value')
        fig.update_layout(margin=dict(
            l=0, r=0, t=40, b=20), height=300, template=template)
        return fig

 # Callback tabela de chamados respondidos


@app.callback(
    dash.dependencies.Output('tabela-chamados-respondidos', 'data'),
    dash.dependencies.Output('tabela-chamados-respondidos', 'columns'),
    dash.dependencies.Input('interval1', 'n_intervals')
)
def input_datatable_chamados_respondidos(n_intervals):

    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       Autenticacao.user(), Autenticacao.key())
    df_chamados = topDesk.chamadosSLACorrenteDataFrame()
    df = df_chamados[df_chamados['STATUS'] == 'Respondido pelo usuário']

    columns = [{"name": i, "id": i, "presentation": "markdown"} if i == "CHAMADO (LINK)" else {
        "name": i, "id": i} for i in df[["CHAMADO (LINK)", "OPERADOR"]].columns]

    return df.to_dict('records'), columns


# CallBack - Aqui geramos o DF e guardamos no store que será armazenado no cash do navegador do usuário


@app.callback(
    Output('store', 'data'),
    Output('select-operadores', 'options'),
    Output('select-operadores', 'disabled'),
    Output("loading-store", 'show_initially'),
    Input('interval3', 'n_intervals'),
)
def get_DF_UltimasAcoes(n_intervals):
    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       Autenticacao.user(), Autenticacao.key())

    df_chamados = topDesk.DF_UltimasAcoes()

    df_filtro = df_chamados.sort_values(
        by='DIAS_ULTIMA_INTERACAO_OPERADOR', ascending=False).reset_index(drop=True)
    df_filtro = df_filtro[df_filtro['DIAS_ULTIMA_INTERACAO_OPERADOR'] > 1]

    lista_operadores = list(df_filtro['OPERADOR'].unique())
    lista_operadores.sort()
    lista_operadores.append('Todos')

    return df_filtro.to_dict(), lista_operadores, False, False

# Callback: Insere valor no slider range


@app.callback(
    Output('range-slider', 'min'),
    Output('range-slider', 'max'),
    Output('range-slider', 'value'),
    Input('store', 'data')
)
def input_values_range(data):
    df_ultimasAcoes = pd.DataFrame(data)
    return df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].min(), df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].max(), [df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].min(), df_ultimasAcoes['DIAS_ULTIMA_INTERACAO_OPERADOR'].max()]  # type: ignore


# Callback - Renderiza o gráfico de chamados por dias sem interação dos operadores

@app.callback(
    Output('graph-chamados-acoes', 'figure'),
    [Input('store', 'data'), Input('interval3', 'n_intervals'),
     Input('range-slider', 'value'), Input('select-operadores', 'value'),
     Input(ThemeSwitchAIO.ids.switch("theme"), "value")],

)
def render_graphs_chamados_p_dias_sem_interacao(data, n_intervals, value_range, value_select, toggle):
    template = template_theme1 if toggle else template_theme2

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
                 hover_data=['OPERADOR', 'STATUS'],
                 color='GRUPO_OPERADOR', template=template)
    # fig.update_layout(template=template)

    return fig

# Callback Agendamentos


@app.callback(
    dash.dependencies.Output('tabela-agendamentos', 'data'),
    dash.dependencies.Output('tabela-agendamentos', 'columns'),
    dash.dependencies.Input('interval2', 'n_intervals')
)
def agendamento_card(toggle):
    # template = template_theme1 if toggle else template_theme2
    df = pd.DataFrame(
        {
            "Chamado": ["I2305-000", "I2305-0785", "I2305-8000"],
            "Operador": ["Fernando Henrique Machado", "Thiago Francisco de Souza Leite", "Dielson Freitas"],
            "Hora Agendamento": ["15:30", "15:45", "15:50"],
            "Link": ['[Google](https://www.google.com)', '[Youtube](https://www.youtube.com/watch?v=LU5-ZmF7Itc&ab_channel=Caz%C3%A9TV)', '[Facebook](https://www.facebook.com)']
        })

    topDesk = chamados('https://rioquente.topdesk.net/tas/api',
                       Autenticacao.user(), Autenticacao.key())
    df_chamados = topDesk.chamadosSLACorrenteDataFrame()
    df = df_chamados[df_chamados['STATUS'] == 'Respondido pelo usuário']

    columns = [{"name": i, "id": i, "presentation": "markdown"} if i == "CHAMADO (LINK)" else {
        "name": i, "id": i} for i in df[["CHAMADO (LINK)", "OPERADOR", "SOLICITANTE"]].columns]
    return df.to_dict('records'), columns


# ================= Run Server ================== #
if __name__ == '__main__':
    app.run_server(debug=False, port=8080, host='0.0.0.0')
