import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go


# Datasets
df_reg = pd.read_excel('Formulario_de_Registro_Actividades_dummy.xlsx')
df_eval = pd.read_excel('Formulario_Evaluacion_Dummy.xlsx')
df_cier = pd.read_excel('Informe_de_Cierre_de_Actividad_dummy.xlsx')

df1 = df_reg
df2 = df_eval
df3 = df_cier

# Integración y cálculo de indicadores
cols_survey1 = ['ID', 'Nobre de la actividad', 'Tipo de actividad', 'Fecha tentativa de la actividad', 'Número estimado de participantes']
cols_survey2 = ['ID', '¿Cómo califica en general la actividad en la que participó?']
cols_survey3 = [
    'ID', 'Porcentaje de participación\xa0 esperada vs real (solo número)', 'Se cumplieron con los objetivos propuestos',
    'Nivel de satisfacción general de los participantes', 'Total participantes (solo número)',
    'Participantes según su perfil (si el perfil no participó marque 0%).Estudiantes',
    'Participantes según su perfil (si el perfil no participó marque 0%).Docentes',
    'Participantes según su perfil (si el perfil no participó marque 0%).Egresados',
    'Participantes según su perfil (si el perfil no participó marque 0%).Empleados',
    'Participantes según su perfil (si el perfil no participó marque 0%).Empresarios/sector productivo',
    'Participantes según su perfil (si el perfil no participó marque 0%).Público general',
    'Número de productos, prototipos o resultados tangibles desarrollados (si aplica):',
    'Califique el nivel de coordinación y organización'
]

df_merge_1_2 = pd.merge(df1[cols_survey1], df2[cols_survey2], on='ID', how='inner')
df_all = pd.merge(df_merge_1_2, df3[cols_survey3], on='ID', how='inner')

df_all['Satisfacción numérica'] = df_all['¿Cómo califica en general la actividad en la que participó?'].map({'Excelente':4, 'Bueno':3, 'Regular':2, 'Malo':1})
#df_all['Nivel coordinación numérico'] = df_all['Califique el nivel de coordinación y organización'].map({'Excelente':3, 'Bueno':2, 'Regular':1})
df_all['Nivel coordinación numérico'] = df_all['Califique el nivel de coordinación y organización']
df_all['Objetivos cumplidos (bin)'] = df_all['Se cumplieron con los objetivos propuestos'].map({'Sí':1, 'No':0, 'Parcialmente':0.5})
#df_all['Satisfacción general numérica'] = df_all['Nivel de satisfacción general de los participantes'].map({'Alta':3, 'Media':2, 'Baja':1})
df_all['Satisfacción general numérica'] = df_all['Nivel de satisfacción general de los participantes']

indicadores = df_all.groupby('Tipo de actividad').agg(
    Total_Actividades=('ID', 'count'),
    Promedio_Satisfacción_Encuesta2=('Satisfacción numérica', 'mean'),
    Promedio_Satisfacción_Encuesta3=('Satisfacción general numérica', 'mean'),
    Porcentaje_Objetivos_Cumplidos=('Objetivos cumplidos (bin)', 'mean'),
    Promedio_Participación_Esperada_vs_Real=('Porcentaje de participación\xa0 esperada vs real (solo número)', 'mean'),
    Promedio_Participantes=('Número estimado de participantes', 'mean'),
    Total_Participantes_Reporte3=('Total participantes (solo número)', 'sum'),
    Promedio_Nivel_Coordinacion=('Nivel coordinación numérico', 'mean'),
    Total_Resultados_Tangibles=('Número de productos, prototipos o resultados tangibles desarrollados (si aplica):', 'sum')
).reset_index()

#import ace_tools_open as tools
#tools.display_dataframe_to_user(name="Indicadores clave por tipo de actividad", dataframe=indicadores)

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Dashboard Indicadores de Actividades ITM"),

    dcc.Dropdown(
        id='tipo-actividad-dropdown',
        options=[{'label': t, 'value': t} for t in indicadores['Tipo de actividad']],
        value=indicadores['Tipo de actividad'].tolist(),
        multi=True
    ),

    dcc.Graph(id='total-actividades-bar'),
    dcc.Graph(id='satisfaccion-bar'),
    dcc.Graph(id='objetivos-line'),
    html.H2("Resumen de indicadores"),
    html.Div(id='tabla-indicadores')
])


@app.callback(
    [Output('total-actividades-bar', 'figure'),
     Output('satisfaccion-bar', 'figure'),
     Output('objetivos-line', 'figure'),
     Output('tabla-indicadores', 'children')],
    [Input('tipo-actividad-dropdown', 'value')]
)
def update_dashboard(selected_tipos):
    if not selected_tipos:
        selected_tipos = indicadores['Tipo de actividad'].tolist()

    dff = indicadores[indicadores['Tipo de actividad'].isin(selected_tipos)]

    # Gráfico total actividades
    fig_total = go.Figure(data=[
        go.Bar(x=dff['Tipo de actividad'], y=dff['Total_Actividades'], name='Total Actividades')
    ])
    fig_total.update_layout(title='Total de actividades por tipo')

    # Gráfico de satisfacción
    fig_satisf = go.Figure(data=[
        go.Bar(x=dff['Tipo de actividad'], y=dff['Promedio_Satisfacción_Encuesta2'], name='Satisfacción del participante'),
        go.Bar(x=dff['Tipo de actividad'], y=dff['Promedio_Satisfacción_Encuesta3'], name='Percepción de satisfacción ITM')
    ])
    fig_satisf.update_layout(title='Promedio de satisfacción por tipo')

    # Gráfico línea objetivos y participación
    fig_objetivos = go.Figure()
    fig_objetivos.add_trace(go.Scatter(x=dff['Tipo de actividad'], y=dff['Porcentaje_Objetivos_Cumplidos']*100,
                                      mode='lines+markers', name='% Objetivos cumplidos'))
    fig_objetivos.add_trace(go.Scatter(x=dff['Tipo de actividad'], y=dff['Promedio_Participación_Esperada_vs_Real'],
                                      mode='lines+markers', name='% Participación esperada vs real'))
    fig_objetivos.update_layout(title='Objetivos cumplidos y participación')

    # Tabla resumen
    tabla = html.Table([
        html.Thead([
            html.Tr([html.Th(col) for col in dff.columns])
        ]),
        html.Tbody([
            html.Tr([html.Td(round(val,2) if isinstance(val, float) else val) for val in dff.iloc[i]]) for i in range(len(dff))
        ])
    ])

    return fig_total, fig_satisf, fig_objetivos, tabla


if __name__ == '__main__':
    app.run(debug=True)