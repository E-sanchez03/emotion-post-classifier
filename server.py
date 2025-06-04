from flask import Flask, request, render_template
import praw
import prawcore
from dotenv import load_dotenv
import os
import polars as pl
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

    comments_dict, error_msg_annotation = annotate_comments(comments)

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
    else:     
        app.logger.info('Holas')  
        return render_template("template.html")

if __name__ == "__main__":
    if not reddit:
        print("ADVERTENCIA: El servidor se está ejecutando pero no se pudo conectar a Reddit al inicio.")
    app.run(debug=True, host='0.0.0.0', port=8050)
