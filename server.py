# Importar librerías
from flask import Flask, request, render_template
import praw
import prawcore
from dotenv import load_dotenv
import os
import polars as pl
import requests
import json
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv("credencialesPraw.env")

# Inicializar la aplicación de Flask
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
    logger.info("Conexión a Reddit exitosa.")
except Exception as e:
    logger.info(f"Error al inicializar PRAW o conectar a Reddit: {e}")
    reddit = None

# URL a la que acceder para realizar la solicitud POST 
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5001/classify")

# Función para obtener un diccionario con cada comentario y su emoción más probable
def annotate_comments(comment_list, selected_model):
    if not comment_list:
        return {}, "No hay comentarios para anotar."

    # Obtención del cuerpo de los comentarios, sin metadatos
    texts = [comment.body for comment in comment_list if hasattr(comment, "body") and comment.body.strip()]
    
    if not texts:
        return {}, "No se encontraron cuerpos de comentario válidos para procesar."

    # Payload para el servicio de modelos, incluyendo el modelo seleccionado y los comentarios
    payload = {
        "texts": texts,
        "model_name": selected_model
    }

    try:
        # Enviamos la solicutd POST con el payload
        response = requests.post(MODEL_SERVICE_URL, json=payload)
        response.raise_for_status()
        
        try:
            # Obtener los resultados
            response_data = response.json()
        except json.JSONDecodeError:
            return {}, f"Error: El servicio del modelo no devolvió un JSON válido. Respuesta: {response.text[:200]}"
        # Quedarnos con el objeto emotions del JSON
        results = response_data.get("emotions")
        # Errores posibles si no hay resultados
        if results is None:
            error_from_service = response_data.get("error")
            if error_from_service:
                 return {}, f"Error del servicio de modelo: {error_from_service}. Respuesta: {response_data}"
            return {}, f"Error: La respuesta del servicio del modelo no contiene la clave 'emotions'. Respuesta: {response_data}"
        
        # Devolver un dicciónario con cada id de comentario y su resultado
        return {comment.id: result for comment, result in zip(comment_list, results) if hasattr(comment, "id")}, None

    # Obtención de errores provenientes de la solicitud POST
    except requests.exceptions.Timeout:
        return {}, f"Error: Timeout al contactar el servicio del modelo en {MODEL_SERVICE_URL}."
    except requests.exceptions.ConnectionError:
        return {}, f"Error: No se pudo conectar al servicio del modelo en {MODEL_SERVICE_URL}. ¿Está en ejecución?"
    except requests.exceptions.HTTPError as e:
        # Intentar obtener un mensaje de error más detallado del cuerpo de la respuesta si es JSON
        try:
            error_detail = e.response.json()
            detail_msg = error_detail.get("detail") or error_detail.get("error") or str(error_detail)
        except json.JSONDecodeError:
            detail_msg = e.response.text[:200]
        return {}, f"Error HTTP del servicio del modelo: {e}. Detalle: {detail_msg}"
    except requests.exceptions.RequestException as e:
        return {}, f"Error al contactar el servicio del modelo: {e}"


# Función
def get_results(url, selected_model): 
    
    try:
        # Obtener el post de Reddit solicitado
        submission = reddit.submission(url=url)
        if submission is None or not hasattr(submission, 'title'):
            return [], [], f"No se pudo encontrar una publicación de Reddit válida en la URL: {url}"
        
        # Reemplzar los comentarios de tipo 'More Comments'. COnfigurado a 10 por tema de eficiencia ( No obtiene todos los comentarios posibles )
        submission.comments.replace_more(limit=10) 
        comments = submission.comments.list()  # Obtener la lista de comentarios
        
    # Excepciones que pueden ocurrir al usar Reddit
    except prawcore.exceptions.Redirect:
        return [], [], f"URL de Reddit inválida o redirigida: {url}"
    except prawcore.exceptions.NotFound:
        return [], [], f"No se encontró la publicación de Reddit en la URL: {url}"
    except prawcore.exceptions.PrawcoreException as e:
        return [], [], f"Error al obtener comentarios de Reddit: {e}"
    except Exception as e: # Captura más genérica para errores inesperados
        return [], [], f"Error inesperado al procesar la URL de Reddit: {e}"

    if not comments:
        return [], [], "No se encontraron comentarios en la publicación."

    # Obtener el dicionario con las emociones
    comments_dict, error_msg_annotation = annotate_comments(comments, selected_model)

    if error_msg_annotation:
        return [], [], error_msg_annotation

    if not comments_dict:
        return [], [], "No se pudieron anotar emociones para los comentarios encontrados."

    # Obtener la emoción de cada comentario
    emociones_procesadas = []
    for emocion_data in comments_dict.values():
        emociones_procesadas.append(emocion_data[0]['label'])

    # Formar un DataFrame de Polars para usar funciones de agregación
    df = pl.DataFrame({
        "ID_Comentario": list(comments_dict.keys()),
        "Emoción": emociones_procesadas 
    })
    
    if df.is_empty():
        return [], [], "No hay datos de emociones para mostrar después del procesamiento."

    # Obtenemos un DF agrupado por cada emoción y su conteo
    emociones_agg = df.group_by("Emoción").agg(pl.count().alias("count")).sort("count", descending=True)
    
    if emociones_agg.is_empty():
        return [], [], "No se encontraron emociones agregadas."
        
    emociones_dict = emociones_agg.to_dict(as_series=False)
    return emociones_dict.get("Emoción", []), emociones_dict.get("count", []), None

# Página principal dinámica
@app.route("/", methods=["GET", "POST"])
def home():
    # Si se ha solicitado un análisis se pedirá un POST
    if request.method == "POST":
        url = request.form.get("url")  # URL pasada por el usuario
        selected_model = request.form.get("model_choice") # Modelo del formulario

        # Obtenemos las emociones con sus valores de agregación
        emociones, counts, error_msg = get_results(url, selected_model)

        if error_msg:
            return render_template("resultado.html", error=error_msg, submitted_url=url, submitted_model=selected_model)
        
        if not emociones or not counts:
            return render_template("resultado.html", error="No se encontraron emociones o comentarios válidos para mostrar.", submitted_url=url, submitted_model=selected_model)

        # Formamos un gráfico usando Chart.js
        chart_data = {
            "labels": emociones,
            "datasets": [{
                "label": "Cantidad de Comentarios por Emoción",
                "data": counts,
                # Colores generados por GPT que generan una visualización agradable a la vista
                "backgroundColor": [
                    'rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)', 'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)',
                    'rgba(199, 199, 199, 0.2)', 'rgba(100, 100, 255, 0.2)', 
                    'rgba(255, 100, 100, 0.2)', 'rgba(100, 255, 100, 0.2)'
                ],
                "borderColor": [
                    'rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)', 'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)',
                    'rgba(199, 199, 199, 1)', 'rgba(100, 100, 255, 1)',
                    'rgba(255, 100, 100, 1)', 'rgba(100, 255, 100, 1)'
                ],
                "borderWidth": 1
            }]
        }
        chart_data_json = json.dumps(chart_data)
        # Pasamos los datos al html donde se encuentra el Script de JS
        return render_template("resultado.html", chart_data_json=chart_data_json, submitted_url=url, submitted_model=selected_model)
    
    # Mostramos la página de incio si el método es de tipo GET
    else:     
        return render_template("template.html") 

if __name__ == "__main__":
    if not reddit:
        logger.info("ADVERTENCIA: El servidor se está ejecutando pero no se pudo conectar a Reddit al inicio.")
    app.run(debug=True, host='0.0.0.0', port=8050) 