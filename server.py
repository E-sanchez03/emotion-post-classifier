from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from transformers import pipeline
import praw
from dotenv import load_dotenv
import os
import polars as pl
from huggingface_hub import login
import dash
from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px

# Cargar variables de entorno
load_dotenv("credencialesPraw.env")
# Login a HuggingFace
login(os.getenv("HUGGINGFACE_TOKEN"))

# Inicializar modelo
emotion_model_path = "j-hartmann/emotion-english-distilroberta-base"  # Reemplazo por uno público
emotion_classifier = pipeline(
    "text-classification", model=emotion_model_path, return_all_scores=True, padding=True, truncation=True, device=0
)

# Inicializar Reddit API
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# Función para clasificar los comentarios
def annotate_comments(comment_list, classifier=emotion_classifier):
    texts = [comment.body for comment in comment_list if hasattr(comment, "body")]
    results = classifier(texts)
    comments_dict = {}
    for comment, result in zip(comment_list, results):
        if hasattr(comment, "id"):
            top = max(result, key=lambda x: x['score'])
            comments_dict[comment.id] = top['label']
    return comments_dict

# Función para obtener las emociones
def get_results(url):
    submission = reddit.submission(url=url)

    submission.comments.replace_more(limit=0)
    comentarios = submission.comments.list()

    comments_dict = annotate_comments(comentarios)
    df = pl.DataFrame({'Comentario': list(comments_dict.keys()), 'Emoción': list(comments_dict.values())})
    emociones = df.group_by('Emoción').count()
    return emociones


# Inciación del servidor en Flask
server = Flask(__name__)
server.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "pruebaClave")

# Iniciación de Dash sobre el servidor Flask
app = Dash(__name__, server=server, url_base_pathname='/dashboard/')


theme = {
    'background': '#c1c8d6',
    'card_background': '#e9eaf0',
    'text': '#2c3e50',
    'grid': '#ecf0f1'
}

app.layout = html.Div(
    # Titulo y descripción
    style={'backgroundColor': theme['background'], 'padding': '20px', 'fontFamily': 'Arial, sans-serif'},
    children=[
        html.Div(
            style={'backgroundColor': theme['card_background'], 'padding': '20px',
                   'borderRadius': '10px', 'boxShadow': '0 2px 5px rgba(0,0,0,0.1)',
                   'marginBottom': '20px'},
            children=[
                dcc.Location(id='url-dashboard', refresh=False),
                html.H1(
                    'Emociones del Post',
                    style={'textAlign': 'center','color': theme['text'],'marginBottom': '10px'}
                ),
                html.Div(
                    'A continuación se muestran diferentes gráficos acerca de las emociones de este post en función de diversas variables.',
                    style={'textAlign': 'center','color': theme['text'],
                           'marginBottom': '10px','fontSize': '16px'}
                ),
            ]
        ),

        html.Div([
                        dcc.Graph(
                            id='bar-pie-graph',
                            hoverData={'points': [{'customdata': 'Andalucía'}]}
                        )
                    ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20'}),

        html.Div(id='status-message')
    ]
)

@server.route('/')
def home():
    return render_template('template.html')  # Asegúrate de que template.html existe





@app.callback(
        Output('bar-pie-graph', 'figure'),
        Output('status-message', 'children'),
        Input('url-dashboard', 'pathname')
)
def update_graph(pathname):
    if pathname == '/dashboard/':
        # Recuperar datos de la sesión de Flask
        emociones_data_list = session.get('emociones_data', None)

        if emociones_data_list is not None and len(emociones_data_list) > 0:
            # Opcional: Limpiar los datos de la sesión después de usarlos
            # session.pop('emociones_data', None)
            
            # Crear el gráfico de tarta. px.pie puede tomar una lista de diccionarios.
            # Los diccionarios deben ser como: [{'Emoción': 'joy', 'count': 10}, {'Emoción': 'sad', 'count': 5}]
            fig = px.pie(
                emociones_data_list, 
                names='Emoción', 
                values='count', 
                title='Distribución de Emociones'
            )
            return fig, "" # Figura y ningún mensaje de estado
        elif emociones_data_list is not None and len(emociones_data_list) == 0:
            return {}, "No se encontraron comentarios o emociones para analizar."
        else:
            # Si no hay datos en la sesión (por ejemplo, el usuario fue a /dashboard/ directamente)
            return {}, "No hay datos para mostrar. Por favor, procesa una URL desde la página principal."
    
    # Si no es la ruta /dashboard/ (poco probable con esta configuración), no actualices nada
    return dash.no_update, dash.no_update



@server.route('/procesar-url', methods=['POST'])
def procesar_url():
    url = request.form['url']
    emociones = get_results(url)
    session['emociones_data'] = emociones.to_dicts()
    
    # Redirigir a la página del dashboard de Dash
    return redirect(url_for('/dashboard/'))

