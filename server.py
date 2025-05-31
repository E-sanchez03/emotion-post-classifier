from flask import Flask, request, render_template, jsonify
from transformers import pipeline
import praw
from dotenv import load_dotenv
import os
import polars as pl
from huggingface_hub import login
load_dotenv("credencialesPraw.env")
login(os.getenv("HUGGINGFACE_TOKEN"))
# Cargar variables de entorno


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

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('template.html')  # Asegúrate de que template.html existe

@app.route('/procesar-url', methods=['POST'])
def procesar_url():
    url = request.form['url']
    emociones = get_results(url)
    # Convertir el resultado de Polars a dict para JSON
    return jsonify(emociones.to_dicts())

def annotate_comments(comment_list, classifier=emotion_classifier):
    texts = [comment.body for comment in comment_list if hasattr(comment, "body")]
    results = classifier(texts)
    comments_dict = {}
    for comment, result in zip(comment_list, results):
        if hasattr(comment, "id"):
            top = max(result, key=lambda x: x['score'])
            comments_dict[comment.id] = top['label']
    return comments_dict

def get_results(url):
    submission = reddit.submission(url=url)

    submission.comments.replace_more(limit=0)
    comentarios = submission.comments.list()

    comments_dict = annotate_comments(comentarios)
    df = pl.DataFrame({'Comentario': list(comments_dict.keys()), 'Emoción': list(comments_dict.values())})
    emociones = df.group_by('Emoción').count()
    return emociones
