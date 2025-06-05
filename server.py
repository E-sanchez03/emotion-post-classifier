from flask import Flask, request, render_template, render_template_string
import praw
import prawcore
from dotenv import load_dotenv
import os
import polars as pl
import requests
import json

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

# Lista de modelos válidos (opcional, pero bueno para validación si es necesario aquí)
# Si el servicio de modelos ya valida, esto podría no ser estrictamente necesario aquí.
# Sin embargo, es bueno tenerlo para una validación temprana.
VALID_MODELS = [
    "j-hartmann/emotion-english-distilroberta-base",
    "michellejieli/emotion_text_classifier",
    "Panda0116/emotion-classification-model",
    "hamzawaheed/emotion-classification-model",
    "uboza10300/emotion-classification-model",
    "Zoopa/emotion-classification-model",
    "bhadresh-savani/distilbert-base-uncased-emotion",
    "SamLowe/roberta-base-go_emotions",
    "joeddav/distilbert-base-uncased-go-emotions-student"
]

# PASO 3: Modificar annotate_comments para aceptar selected_model y pasarlo al servicio
def annotate_comments(comment_list, selected_model):
    if not comment_list:
        return {}, "No hay comentarios para anotar."

    texts = [comment.body for comment in comment_list if hasattr(comment, "body") and comment.body.strip()]
    
    if not texts:
        return {}, "No se encontraron cuerpos de comentario válidos para procesar."

    valid_comments_for_annotation = [comment for comment in comment_list if hasattr(comment, "body") and comment.body.strip()]

    # Payload para el servicio de modelos, incluyendo el modelo seleccionado
    payload = {
        "texts": texts,
        "model_name": selected_model # <- AÑADIDO model_name al payload
    }

    try:
        # response = requests.post(MODEL_SERVICE_URL, json={"texts": texts}) # <- LÍNEA ANTIGUA
        response = requests.post(MODEL_SERVICE_URL, json=payload) # <- LÍNEA NUEVA con payload
        response.raise_for_status()
        
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            return {}, f"Error: El servicio del modelo no devolvió un JSON válido. Respuesta: {response.text[:200]}"

        results = response_data.get("emotions")
        if results is None:
            # Podrías también querer verificar si hay un error específico del modelo en response_data
            error_from_service = response_data.get("error")
            if error_from_service:
                 return {}, f"Error del servicio de modelo: {error_from_service}. Respuesta: {response_data}"
            return {}, f"Error: La respuesta del servicio del modelo no contiene la clave 'emotions'. Respuesta: {response_data}"
        
        if len(results) != len(valid_comments_for_annotation):
            return {}, f"Error: Discrepancia en el número de resultados ({len(results)}) y comentarios enviados ({len(valid_comments_for_annotation)})."

        return {comment.id: result for comment, result in zip(valid_comments_for_annotation, results) if hasattr(comment, "id")}, None

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

# PASO 2: Modificar get_results para aceptar selected_model
def get_results(url, selected_model): # <- AÑADIDO selected_model como parámetro
    if not reddit:
        return [], [], "Error: La conexión con Reddit no está disponible."

    try:
        submission = reddit.submission(url=url)
        if submission is None or not hasattr(submission, 'title'):
            return [], [], f"No se pudo encontrar una publicación de Reddit válida en la URL: {url}"
        
        submission.comments.replace_more(limit=10) # Considera hacer este límite configurable o mayor
        comments = submission.comments.list()
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

    # Pasar selected_model a annotate_comments
    comments_dict, error_msg_annotation = annotate_comments(comments, selected_model)

    if error_msg_annotation:
        return [], [], error_msg_annotation

    if not comments_dict:
        return [], [], "No se pudieron anotar emociones para los comentarios encontrados."
    
    # Asegurarse de que comments_dict.values() contenga diccionarios (o la estructura esperada)
    # Si la emoción es una sola etiqueta (string), está bien. Si es un dict (ej. {'label': 'joy', 'score': 0.9}),
    # necesitarás extraer la etiqueta principal. Asumiendo que ya es la etiqueta string.
    # Ejemplo de cómo manejar si 'Emoción' fuera una lista de dicts:
    # emotion_labels = [e[0]['label'] if isinstance(e, list) and e and isinstance(e[0], dict) else str(e) for e in comments_dict.values()]
    # df = pl.DataFrame({
    #     "ID_Comentario": list(comments_dict.keys()),
    #     "Emoción": emotion_labels 
    # })

    # Asumiendo que comments_dict.values() directamente da las etiquetas de emoción
    emociones_procesadas = []
    for emocion_data in comments_dict.values():
        if isinstance(emocion_data, list) and emocion_data: # Si el modelo devuelve una lista de [{label: '', score: ''}]
            emociones_procesadas.append(emocion_data[0]['label'])
        elif isinstance(emocion_data, dict): # Si devuelve un solo dict {label: '', score: ''}
             emociones_procesadas.append(emocion_data.get('label', 'desconocida'))
        else: # Si devuelve directamente el string de la emoción (caso ideal para el código actual)
            emociones_procesadas.append(str(emocion_data))


    df = pl.DataFrame({
        "ID_Comentario": list(comments_dict.keys()),
        "Emoción": emociones_procesadas # Usar las emociones procesadas
    })
    
    if df.is_empty():
        return [], [], "No hay datos de emociones para mostrar después del procesamiento."

    emociones_agg = df.group_by("Emoción").agg(pl.count().alias("count")).sort("count", descending=True)
    
    if emociones_agg.is_empty():
        return [], [], "No se encontraron emociones agregadas."
        
    emociones_dict = emociones_agg.to_dict(as_series=False)
    return emociones_dict.get("Emoción", []), emociones_dict.get("count", []), None

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        url = request.form.get("url")
        # PASO 1: Recuperar model_choice del formulario
        selected_model = request.form.get("model_choice")

        if not url:
            return render_template("resultado.html", error="Por favor, introduce una URL.")
        
        if not selected_model:
            return render_template("resultado.html", error="Por favor, selecciona un modelo de análisis.")

        # (Opcional) Validar si el modelo seleccionado es uno de los conocidos
        if selected_model not in VALID_MODELS:
             return render_template("resultado.html", error=f"El modelo '{selected_model}' no es válido.")

        # Pasar selected_model a get_results
        emociones, counts, error_msg = get_results(url, selected_model)

        if error_msg:
            return render_template("resultado.html", error=error_msg, submitted_url=url, submitted_model=selected_model)
        
        if not emociones or not counts:
            return render_template("resultado.html", error="No se encontraron emociones o comentarios válidos para mostrar.", submitted_url=url, submitted_model=selected_model)

        chart_data = {
            "labels": emociones,
            "datasets": [{
                "label": "Cantidad de Comentarios por Emoción",
                "data": counts,
                "backgroundColor": [
                    'rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)', 'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)',
                    'rgba(199, 199, 199, 0.2)', 'rgba(100, 100, 255, 0.2)', # Añadí más colores
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

        return render_template("resultado.html", chart_data_json=chart_data_json, submitted_url=url, submitted_model=selected_model)
    else:     
        # Asumiendo que tu template.html es el formulario inicial
        # Puedes pasar la lista de modelos al template si quieres generarlos dinámicamente allí
        # en lugar de tenerlos hardcodeados en el HTML.
        # Por ahora, asumo que template.html tiene el selector ya definido.
        return render_template("template.html") # Asegúrate de que este es el nombre correcto de tu formulario

if __name__ == "__main__":
    if not reddit:
        print("ADVERTENCIA: El servidor se está ejecutando pero no se pudo conectar a Reddit al inicio.")
    app.run(debug=True, host='0.0.0.0', port=8050) # Puerto 8050 como en tu original