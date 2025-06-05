from flask import Flask, request, jsonify
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import os
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Diccionario para cachear los pipelines de Hugging Face cargados
# Esto evita tener que recargar el modelo en cada solicitud.
loaded_pipelines = {}

# Definir los modelos disponibles y sus tareas (todos son text-classification para emociones)
# Podrías cargar esto desde una configuración si lo prefieres.
AVAILABLE_MODELS = {
    "j-hartmann/emotion-english-distilroberta-base": "text-classification",
    "michellejieli/emotion_text_classifier": "text-classification", # En HF Hub está como text-classification
    "Panda0116/emotion-classification-model": "text-classification",
    "hamzawaheed/emotion-classification-model": "text-classification",
    "uboza10300/emotion-classification-model": "text-classification",
    "Zoopa/emotion-classification-model": "text-classification",
    "bhadresh-savani/distilbert-base-uncased-emotion": "text-classification",
    "SamLowe/roberta-base-go_emotions": "text-classification",
    "joeddav/distilbert-base-uncased-go-emotions-student": "text-classification"
    # Puedes añadir más modelos aquí
}

def get_pipeline(model_name):
    """
    Carga y devuelve un pipeline de Hugging Face.
    Utiliza una caché para evitar recargar modelos.
    """
    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"Modelo '{model_name}' no está en la lista de modelos disponibles.")

    if model_name in loaded_pipelines:
        logger.info(f"Usando pipeline cacheado para el modelo: {model_name}")
        return loaded_pipelines[model_name]

    try:
        logger.info(f"Cargando modelo: {model_name}...")
        # Especificar la tarea puede no ser siempre necesario si el modelo la define bien,
        # pero es más explícito. Para modelos de emoción, 'text-classification' es lo usual.
        # Algunos modelos pueden requerir la carga explícita de tokenizer y model
        # si la inferencia de pipeline simple no funciona como se espera,
        # pero para la mayoría de los modelos de clasificación de texto, esto es suficiente.
        
        # Asegurarse de que el modelo puede manejar la tarea como "text-classification"
        # Si un modelo específico devuelve múltiples etiquetas o necesita un manejo especial,
        # se podría personalizar aquí.
        task = AVAILABLE_MODELS[model_name]
        
        # Para asegurar que obtenemos la etiqueta y el score, incluso si es solo la top_k=1
        # Esto es lo que la app cliente parece esperar: una lista de diccionarios.
        classifier = pipeline(task, model=model_name, tokenizer=model_name, top_k=1)
        
        loaded_pipelines[model_name] = classifier
        logger.info(f"Modelo '{model_name}' cargado y cacheado exitosamente.")
        return classifier
    except Exception as e:
        logger.error(f"Error al cargar el modelo '{model_name}': {e}")
        # Podrías querer eliminarlo de la caché si la carga falló parcialmente.
        if model_name in loaded_pipelines:
            del loaded_pipelines[model_name]
        raise RuntimeError(f"No se pudo cargar el modelo '{model_name}'. Error: {str(e)}")


@app.route('/classify', methods=['POST'])
def classify_texts():
    if not request.is_json:
        logger.warning("Solicitud recibida no es JSON.")
        return jsonify({"error": "Solicitud debe ser JSON"}), 400

    data = request.get_json()
    texts = data.get('texts')
    model_name = data.get('model_name')

    if not texts:
        logger.warning("No se proporcionaron textos en la solicitud.")
        return jsonify({"error": "No se proporcionaron 'texts' en el cuerpo de la solicitud."}), 400
    if not isinstance(texts, list):
        logger.warning("'texts' no es una lista.")
        return jsonify({"error": "'texts' debe ser una lista de strings."}), 400
    if not model_name:
        logger.warning("No se proporcionó 'model_name' en la solicitud.")
        return jsonify({"error": "No se proporcionó 'model_name' en el cuerpo de la solicitud."}), 400

    logger.info(f"Solicitud de clasificación recibida para el modelo: {model_name} con {len(texts)} textos.")

    try:
        classifier = get_pipeline(model_name)
    except ValueError as e: # Modelo no disponible
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 404
    except RuntimeError as e: # Error al cargar el modelo
        logger.error(f"Error interno del servidor: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e: # Otros errores inesperados al obtener el pipeline
        logger.error(f"Error inesperado al obtener el pipeline para '{model_name}': {e}")
        return jsonify({"error": f"Error inesperado al configurar el modelo: {str(e)}"}), 500

    try:
        # El pipeline devuelve una lista de listas de diccionarios si top_k > 1 o top_k=None.
        # Si top_k=1 (como lo configuré), devuelve una lista de listas, donde cada sublista tiene un solo diccionario.
        # Ejemplo: [[{'label': 'joy', 'score': 0.99}], [{'label': 'sadness', 'score': 0.95}]]
        # La aplicación Flask principal espera una lista de estos diccionarios (o la etiqueta principal).
        # Si tu aplicación cliente espera directamente una lista de etiquetas, necesitarías procesar esto.
        # results = classifier(texts, padding=True, truncation=True) # Padding y truncation son buenas prácticas
        
        # Procesar textos en lotes si son muchos para evitar problemas de memoria (opcional, depende del uso)
        # batch_size = 16 
        # results = []
        # for i in range(0, len(texts), batch_size):
        #    batch_texts = texts[i:i + batch_size]
        #    results.extend(classifier(batch_texts, padding=True, truncation=True))
        
        # Procesamiento simple
        results = classifier(texts, padding=True, truncation=True)

        # La aplicación Flask principal parece esperar una lista de diccionarios [{label: '...', score: ...}]
        # o al menos poder acceder a result[0]['label'].
        # Si `classifier` ya devuelve [{...}], [{...}], ... entonces está bien.
        # Si devuelve [[{...}]], [[{...}]], ... (que es común con top_k=1), necesitamos extraer el primer elemento.
        
        # Aseguramos que la salida sea una lista de diccionarios (o el objeto que el pipeline retorna por elemento)
        # Si results = [[{'label': 'joy', 'score': 0.99}], [{'label': 'sad', 'score': 0.8}]]
        # y quieres que sea [{'label': 'joy', 'score': 0.99}, {'label': 'sad', 'score': 0.8}]
        # Esto depende de cómo el pipeline específico con top_k=1 formatea su salida.
        # Para `text-classification` con `top_k=1`, normalmente devuelve una lista de listas, 
        # cada sublista conteniendo un único diccionario.
        # Ejemplo: [[{'label': 'joy', 'score': 0.998}]].
        # La aplicación principal usaba: emocion_data[0]['label']
        # Esto implica que cada elemento de la lista 'emotions' es una lista que contiene un diccionario.
        
        # Por lo tanto, 'results' ya debería tener el formato:
        # [[{'label': 'joy', 'score': 0.99887...}], [{'label': 'anger', 'score': 0.99820...}]]
        # que es lo que la aplicación principal espera en `comments_dict.values()`
        # para luego hacer `emocion_data[0]['label']`.

        logger.info(f"Clasificación completada para el modelo: {model_name}.")
        return jsonify({"emotions": results})

    except Exception as e:
        logger.error(f"Error durante la clasificación con el modelo '{model_name}': {e}")
        return jsonify({"error": f"Error durante la clasificación: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    # Para producción, considera usar un servidor WSGI como Gunicorn o uWSGI
    # Ejemplo: gunicorn -w 4 -b 0.0.0.0:5001 model_api:app
    logger.info(f"Servicio de modelos iniciando en el puerto {port}")
    app.run(debug=True, host='0.0.0.0', port=port) # debug=False para producción