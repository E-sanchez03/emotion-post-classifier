from flask import Flask, request, render_template, session, redirect
import praw
from dotenv import load_dotenv
import os
import polars as pl
import pandas as pd
import dash
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import requests

# Cargar variables de entorno
load_dotenv("credencialesPraw.env")

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5001/classify")

# Inicializar Reddit API
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# Clasificación de comentarios
def annotate_comments(comment_list):
    texts = [comment.body for comment in comment_list if hasattr(comment, "body")]
    response = requests.post(MODEL_SERVICE_URL, json={"texts": texts})
    results = response.json().get("emotions", [])

    comments_dict = {}
    for comment, result in zip(comment_list, results):
        if hasattr(comment, "id"):
            comments_dict[comment.id] = result

    return comments_dict

# Procesamiento y agrupación de emociones
def get_results(url):
    # Obtener el post de Reddit
    submission = reddit.submission(url=url)

    # Obtener los comentarios
    submission.comments.replace_more(limit=10)
    comentarios = submission.comments.list()

    # Clasificar los comentarios
    comments_dict = annotate_comments(comentarios)

    # Crear DataFrame con los resultados
    df = pd.DataFrame({
        'Comentario': list(comments_dict.keys()),
        'Emoción': list(comments_dict.values())
    })

    # Agrupar por emoción y contar ocurrencias
    emociones = df.groupby('Emoción').size().reset_index(name='count')

    return emociones


# Flask
server = Flask(__name__)
server.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "pruebaClave")

# Dash
app = Dash(__name__, server=server, url_base_pathname='/dashboard/')

theme = {
    'background': '#c1c8d6',
    'card_background': '#e9eaf0',
    'text': '#2c3e50',
    'grid': '#ecf0f1'
}

app.layout = html.Div(
    style={'backgroundColor': theme['background'], 'padding': '20px', 'fontFamily': 'Arial, sans-serif'},
    children=[
        html.Div(
            style={
                'backgroundColor': theme['card_background'], 'padding': '20px',
                'borderRadius': '10px', 'boxShadow': '0 2px 5px rgba(0,0,0,0.1)',
                'marginBottom': '20px'
            },
            children=[
                dcc.Location(id='url-dashboard', refresh=False),
                html.H1(
                    'Emociones del Post',
                    style={'textAlign': 'center', 'color': theme['text'], 'marginBottom': '10px'}
                ),
                html.Div(
                    'A continuación se muestran diferentes gráficos acerca de las emociones de este post en función de diversas variables.',
                    style={'textAlign': 'center', 'color': theme['text'], 'marginBottom': '10px', 'fontSize': '16px'}
                ),
            ]
        ),
        html.Div([
            dcc.Graph(id='bar-pie-graph')
        ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20'}),
        html.Div(id='status-message')
    ]
)

@server.route('/')
def home():
    return render_template('template.html')  # Asegúrate de tener este archivo en /templates

# 🔁 Callback para actualizar el gráfico
@app.callback(
    Output('bar-pie-graph', 'figure'),
    Output('status-message', 'children'),
    Input('url-dashboard', 'pathname')
)
def update_graph(pathname):
    if pathname and pathname.strip().endswith('/dashboard/'):
        server.logger.info(f"update_graph - INICIO DEL CALLBACK para pathname: {pathname}")
        emociones_data_list = session.get('emociones_data', None)
        server.logger.info(f"update_graph - DATOS CRUDOS DE SESIÓN: {str(emociones_data_list)}")

        if emociones_data_list is not None and len(emociones_data_list) > 0:
            # ... (tus logs de verificación de tipos y claves del primer elemento) ...
            server.logger.info(f"update_graph - DATOS FINALES ANTES DE PX.PIE: {str(emociones_data_list)}") # Log CLAVE
            try:
                fig = px.pie(
                    emociones_data_list, 
                    names='Emoción',
                    values='count',
                    title='Distribución de Emociones' # Manténlo simple por ahora
                )
                
                # LOG CORREGIDO PARA LA FIGURA
                if fig.data and isinstance(fig.data, (list, tuple)) and len(fig.data) > 0:
                     trace = fig.data[0] # Obtener la primera traza (el pie chart)
                     server.logger.info(f"update_graph - FIGURA GENERADA - Labels: {trace.labels}")
                     server.logger.info(f"update_graph - FIGURA GENERADA - Values: {trace.values}") # Estos son los valores numéricos que usa Plotly
                     # También podrías loguear trace.hovertemplate si quieres verlo
                else:
                     server.logger.info("update_graph - FIGURA GENERADA - fig.data está vacío o no tiene el formato esperado")
                
                server.logger.info("update_graph - Gráfico (simplificado) generado exitosamente.")
                return fig, "" # Esta figura debería ser correcta
            except Exception as e:
                server.logger.error(f"update_graph - ERROR durante px.pie o al loguear fig: {e}", exc_info=True)
                return {}, f"Error al crear el gráfico: {str(e)}"

        elif emociones_data_list is not None and len(emociones_data_list) == 0:
            return {}, "No se encontraron comentarios o emociones para analizar."

        else:
            return {}, "No hay datos para mostrar. Por favor, procesa una URL desde la página principal."
    
    return dash.no_update, dash.no_update
# Ruta para procesar URL
@server.route('/procesar-url', methods=['POST'])
def procesar_url():
    url = request.form['url']
    emociones = get_results(url)

    # Guardar como lista de dicts en sesión
    session['emociones_data'] = emociones.to_dict(orient='records')


    # Redirigir directamente a la ruta
    return redirect('/dashboard/')

# Ejecutar servidor
if __name__ == '__main__':
    server.run(host='0.0.0.0', port=int(os.getenv("PORT", 8050)), debug=True)
