<<<<<<< HEAD
from flask import Flask, request, render_template
=======
from flask import Flask, request, render_template, session, redirect
>>>>>>> 4fdb5eb37ffe81572edba59d5d364117beaf79fd
import praw
import prawcore
from dotenv import load_dotenv
import os
import polars as pl
<<<<<<< HEAD
=======
import pandas as pd
import dash
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
>>>>>>> 4fdb5eb37ffe81572edba59d5d364117beaf79fd
import requests
# import plotly.express as px # Ya no se necesita Plotly
# import plotly # Ya no se necesita Plotly
import json

# ... (el resto de tus importaciones y código inicial de PRAW, etc. se mantiene igual)
# Cargar variables de entorno
load_dotenv("credencialesPraw.env")

app = Flask(__name__)

# Conexión a Reddit
try:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
        read_only=True
    )
    reddit.user.me() 
    print("Conexión a Reddit exitosa.")
except Exception as e:
    print(f"Error al inicializar PRAW o conectar a Reddit: {e}")
    reddit = None

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5001/classify")

<<<<<<< HEAD
def annotate_comments(comment_list):
    if not comment_list:
        return {}, "No hay comentarios para anotar."

    texts = [comment.body for comment in comment_list if hasattr(comment, "body") and comment.body.strip()]
    
    if not texts:
        return {}, "No se encontraron cuerpos de comentario válidos para procesar."

    valid_comments_for_annotation = [comment for comment in comment_list if hasattr(comment, "body") and comment.body.strip()]

    try:
        response = requests.post(MODEL_SERVICE_URL, json={"texts": texts}, timeout=30)
        response.raise_for_status()
        
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            return {}, f"Error: El servicio del modelo no devolvió un JSON válido. Respuesta: {response.text[:200]}"

        results = response_data.get("emotions")
        if results is None:
            return {}, f"Error: La respuesta del servicio del modelo no contiene la clave 'emotions'. Respuesta: {response_data}"
        
        if len(results) != len(valid_comments_for_annotation):
            return {}, f"Error: Discrepancia en el número de resultados ({len(results)}) y comentarios enviados ({len(valid_comments_for_annotation)})."

        return {comment.id: result for comment, result in zip(valid_comments_for_annotation, results) if hasattr(comment, "id")}, None

    except requests.exceptions.Timeout:
        return {}, f"Error: Timeout al contactar el servicio del modelo en {MODEL_SERVICE_URL}."
    except requests.exceptions.ConnectionError:
        return {}, f"Error: No se pudo conectar al servicio del modelo en {MODEL_SERVICE_URL}. ¿Está en ejecución?"
    except requests.exceptions.HTTPError as e:
        return {}, f"Error HTTP del servicio del modelo: {e}. Respuesta: {response.text[:200]}"
    except requests.exceptions.RequestException as e:
        return {}, f"Error al contactar el servicio del modelo: {e}"

def get_results(url):
    if not reddit:
        return [], [], "Error: La conexión con Reddit no está disponible."

    try:
        submission = reddit.submission(url=url)
        if submission is None or not hasattr(submission, 'title'):
             return [], [], f"No se pudo encontrar una publicación de Reddit válida en la URL: {url}"
        
        submission.comments.replace_more(limit=10)
        comments = submission.comments.list()
    except prawcore.exceptions.Redirect:
        return [], [], f"URL de Reddit inválida o redirigida: {url}"
    except prawcore.exceptions.NotFound:
        return [], [], f"No se encontró la publicación de Reddit en la URL: {url}"
    except prawcore.exceptions.PrawcoreException as e:
        return [], [], f"Error al obtener comentarios de Reddit: {e}"
    except Exception as e:
        return [], [], f"Error inesperado al procesar la URL de Reddit: {e}"

    if not comments:
        return [], [], "No se encontraron comentarios en la publicación."
=======
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
>>>>>>> 4fdb5eb37ffe81572edba59d5d364117beaf79fd

    comments_dict, error_msg_annotation = annotate_comments(comments)

<<<<<<< HEAD
    if error_msg_annotation:
        return [], [], error_msg_annotation

    if not comments_dict:
        return [], [], "No se pudieron anotar emociones para los comentarios encontrados."

    df = pl.DataFrame({
        "ID_Comentario": list(comments_dict.keys()),
        "Emoción": list(comments_dict.values())
    })
    
    if df.is_empty():
        return [], [], "No hay datos de emociones para mostrar después del procesamiento."

    emociones_agg = df.group_by("Emoción").agg(pl.count().alias("count"))
    
    if emociones_agg.is_empty():
        return [], [], "No se encontraron emociones agregadas."
        
    emociones_dict = emociones_agg.to_dict(as_series=False)
    return emociones_dict.get("Emoción", []), emociones_dict.get("count", []), None

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        url = request.form.get("url")
        if not url:
            return render_template("resultado.html", error="Por favor, introduce una URL.")

        emociones, counts, error_msg = get_results(url)

        if error_msg:
            return render_template("resultado.html", error=error_msg)
        
        if not emociones or not counts:
            return render_template("resultado.html", error="No se encontraron emociones o comentarios válidos para mostrar.")

        # Preparar datos para Chart.js
        chart_data = {
            "labels": emociones,
            "datasets": [{
                "label": "Cantidad de Comentarios por Emoción",
                "data": counts,
                # Puedes definir colores aquí o dejar que Chart.js use los suyos
                "backgroundColor": [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)',
                    'rgba(199, 199, 199, 0.2)' # Añade más si tienes más emociones
                ],
                "borderColor": [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(199, 199, 199, 1)'
                ],
                "borderWidth": 1
            }]
        }
        # Convertir el diccionario a una cadena JSON
        # No se necesita un codificador especial como con Plotly
        chart_data_json = json.dumps(chart_data)

        return render_template("resultado.html", chart_data_json=chart_data_json)
            
    return render_template("template.html")

if __name__ == "__main__":
    if not reddit:
        print("ADVERTENCIA: El servidor se está ejecutando pero no se pudo conectar a Reddit al inicio.")
    app.run(debug=True, port=5000)
=======
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
>>>>>>> 4fdb5eb37ffe81572edba59d5d364117beaf79fd
