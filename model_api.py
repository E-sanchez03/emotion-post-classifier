from flask import Flask, request, jsonify
from transformers import pipeline
import os
from dotenv import load_dotenv
from huggingface_hub import login
import logging

# Cargamos las variables de entorno
load_dotenv("credencialesPraw.env")

# Nos logeamos en hugginface
login(os.getenv("HUGGINGFACE_TOKEN"))

# Iniciamos la aplicación de la API del modelo
api = Flask(__name__)

classifier_path = "j-hartmann/emotion-english-distilroberta-base"
pipe = pipeline(
    "text-classification", model=classifier_path, return_all_scores=True, padding=True, truncation=True, device=0
)
api.logger.setLevel(logging.DEBUG) 
api.logger.info("Flask en modo debug, el logger debería funcionar en consola.")

@api.route("/classify", methods=['POST'])
def classify_emotions():

    data = request.get_json()
    texts = data.get("texts")

    results = pipe(texts)
    top_emotions = []
    for result_set in results:
        top = max(result_set, key=lambda x: x['score'])
        top_emotions.append(top['label'])
            
    return jsonify({"emotions": top_emotions})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001)) # Puerto para el servicio del modelo
    api.run(host='0.0.0.0', port=port, debug=True)