from flask import Flask, request, jsonify
from transformers import pipeline
import os
from dotenv import load_dotenv
from huggingface_hub import login
<<<<<<< HEAD
import torch # Para la detección de GPU
=======
import logging
>>>>>>> 4fdb5eb37ffe81572edba59d5d364117beaf79fd

# Cargar variables de entorno desde archivo .env
load_dotenv("credencialesPraw.env")

# Login en Hugging Face (necesario para cargar modelos privados o usar tokens)
huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
if huggingface_token:
    try:
        login(huggingface_token)
        print("Login en Hugging Face exitoso.")
    except Exception as e:
        print(f"Error durante el login en Hugging Face: {e}")
        # Podrías decidir si continuar o salir si el login es crítico

# Crear la aplicación Flask
api = Flask(__name__)

<<<<<<< HEAD
# Inicializar pipeline de clasificación emocional
classifier_path = "j-hartmann/emotion-english-distilroberta-base" # Modelo en inglés
pipe = None # Inicializar como None

try:
    # Determinar dispositivo (GPU si está disponible, si no CPU)
    if torch.cuda.is_available():
        device_num = 0 # Usar la primera GPU
        print(f"GPU detectada. Usando dispositivo: cuda:{device_num}")
    else:
        device_num = -1 # Usar CPU
        print("GPU no detectada. Usando CPU.")

    pipe = pipeline(
        "text-classification",
        model=classifier_path,
        return_all_scores=True, # Necesario para obtener todas las puntuaciones y luego el máximo
        padding=True,
        truncation=True,
        device=device_num 
    )
    print(f"Pipeline de clasificación cargado exitosamente en {'GPU' if device_num != -1 else 'CPU'}.")
except Exception as e:
    print(f"Error CRÍTICO al cargar el modelo de Transformers o inicializar el pipeline: {e}")
    print("La API de modelo podría no funcionar correctamente.")
    # En un entorno de producción, podrías querer que la aplicación falle aquí
    # o tenga un estado de 'no saludable'.
=======
classifier_path = "j-hartmann/emotion-english-distilroberta-base"
pipe = pipeline(
    "text-classification", model=classifier_path, return_all_scores=True, padding=True, truncation=True, device=0
)
api.logger.setLevel(logging.DEBUG) 
api.logger.info("Flask en modo debug, el logger debería funcionar en consola.")
>>>>>>> 4fdb5eb37ffe81572edba59d5d364117beaf79fd

@api.route("/classify", methods=['POST'])
def classify_emotions():
    if pipe is None:
        return jsonify({"error": "El modelo de clasificación no está disponible debido a un error de inicialización."}), 503 # Service Unavailable

    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibió payload JSON."}), 400
        
    texts = data.get("texts")

    if not texts or not isinstance(texts, list):
        return jsonify({"error": "No se proporcionó una lista de textos válida en la clave 'texts'."}), 400
    
    # Filtrar strings vacíos o None en la lista de textos, ya que el pipeline puede fallar con ellos
    valid_texts = [text for text in texts if isinstance(text, str) and text.strip()]
    if not valid_texts:
        return jsonify({"error": "La lista de textos está vacía o no contiene strings válidos."}), 400

    try:
        results = pipe(valid_texts) # Solo procesar textos válidos
        
        # Mapear los resultados de vuelta a la longitud original de 'texts' si es necesario
        # o decidir cómo manejar los textos inválidos (aquí simplemente se ignoran para la predicción).
        # Por simplicidad, devolvemos emociones solo para los textos válidos.
        # Si el cliente espera una emoción (o null/error) por CADA texto original,
        # se necesitaría una lógica de mapeo más compleja.

        top_emotions = [
            max(result_set, key=lambda x: x['score'])['label']
            for result_set in results # results aquí ya corresponde a valid_texts
        ]
        return jsonify({"emotions": top_emotions})
    except Exception as e:
        # Esto podría capturar errores durante la inferencia del pipeline
        print(f"Error durante la clasificación con el pipeline: {e}")
        return jsonify({"error": "Ocurrió un error interno durante la clasificación de emociones."}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    # `debug=True` es útil para desarrollo, pero considera desactivarlo en producción.
    # `use_reloader=False` puede ser útil si tienes problemas con el modelo cargándose dos veces
    # debido al recargador de Flask en modo debug, especialmente con recursos GPU.
    # Sin embargo, perderías la recarga automática al cambiar código.
    api.run(host='0.0.0.0', port=port, debug=True) #, use_reloader=False si hay problemas con GPU y debug