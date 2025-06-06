# Importar librerías
from flask import Flask, request, jsonify
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import os
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar la app con Flask
app = Flask(__name__)

# Diccionario para cachear los pipelines de Hugging Face cargados
# Esto evita tener que recargar el modelo en cada solicitud.
loaded_pipelines = {}

# Definir los modelos disponibles y sus tareas 
# Opcional: Precargar los modelos pesados
AVAILABLE_MODELS = {
    "j-hartmann/emotion-english-distilroberta-base": "text-classification",
    "michellejieli/emotion_text_classifier": "text-classification", 
    "Panda0116/emotion-classification-model": "text-classification",
    "hamzawaheed/emotion-classification-model": "text-classification",
    "uboza10300/emotion-classification-model": "text-classification",
    "Zoopa/emotion-classification-model": "text-classification",
    "bhadresh-savani/distilbert-base-uncased-emotion": "text-classification",
    "SamLowe/roberta-base-go_emotions": "text-classification",
    "joeddav/distilbert-base-uncased-go-emotions-student": "text-classification"
    # Puedes añadir más modelos aquí
}

# Cargar el pipeline de HugginFace
def get_pipeline(model_name):
    # Comprobar que el modelo está disponible
    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"Modelo '{model_name}' no está en la lista de modelos disponibles.")

    # Comprobar si se encuentra en caché
    if model_name in loaded_pipelines:
        logger.info(f"Usando pipeline cacheado para el modelo: {model_name}")
        return loaded_pipelines[model_name]

    try:
        logger.info(f"Cargando modelo: {model_name}...")
        task = AVAILABLE_MODELS[model_name]
        
        # Cargar el pipeline devolviendo el top_k = 1, el score mayor
        classifier = pipeline(task, model=model_name, tokenizer=model_name, top_k=1)
        
        # Guardar en caché el pipeline
        loaded_pipelines[model_name] = classifier
        logger.info(f"Modelo '{model_name}' cargado y cacheado exitosamente.")
        return classifier
    
    except Exception as e:
        logger.error(f"Error al cargar el modelo '{model_name}': {e}")
        # Lo eliminamos de caché por si se ha cargado parcialmente
        if model_name in loaded_pipelines:
            del loaded_pipelines[model_name]
        raise RuntimeError(f"No se pudo cargar el modelo '{model_name}'. Error: {str(e)}")


# Definimos la ruta classify a la que se puede acceder mediante el método POST
@app.route('/classify', methods=['POST'])
def classify_texts():
    # Comprobación de obtener los textos en el formato pedido
    if not request.is_json:
        logger.warning("Solicitud recibida no es JSON.")
        return jsonify({"error": "Solicitud debe ser JSON"}), 400

    # Obtenemos todos los comentarios y el nombre del modelo 
    data = request.get_json()
    texts = data.get('texts')
    model_name = data.get('model_name')

    # Comprobación de errores
    if not texts:
        logger.warning("No se proporcionaron textos en la solicitud.")
        return jsonify({"error": "No se proporcionaron 'texts' en el cuerpo de la solicitud."}), 400
    if not isinstance(texts, list):
        logger.warning("'texts' no es una lista.")
        return jsonify({"error": "'texts' debe ser una lista de strings."}), 400
    if not model_name:
        logger.warning("No se proporcionó 'model_name' en la solicitud.")
        return jsonify({"error": "No se proporcionó 'model_name' en el cuerpo de la solicitud."}), 400

    # Información de que se ha recibido la información correcta
    logger.info(f"Solicitud de clasificación recibida para el modelo: {model_name} con {len(texts)} textos.")

    try:
        # Llamamos a la función para obtener el pipeline adecuado al modelo seleccionado
        classifier = get_pipeline(model_name)
        
        
    # Comprobación de errores
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
        # Obtenemos los resultados para cada comentario
        results = classifier(texts, padding=True, truncation=True)

        logger.info(f"Clasificación completada para el modelo: {model_name}.")
        return jsonify({"emotions": results})

    except Exception as e:
        logger.error(f"Error durante la clasificación con el modelo '{model_name}': {e}")
        return jsonify({"error": f"Error durante la clasificación: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"Servicio de modelos iniciando en el puerto {port}")
    app.run(debug=True, host='0.0.0.0', port=port) # debug=False para producción