FROM python:3.9-slim

WORKDIR /app

COPY requirements_server.txt .

RUN pip install --no-cache-dir -r requirements_server.txt

COPY server.py .
COPY credencialesPraw.env . 
COPY templates templates/ 

ENV FLASK_APP=server.py
ENV MODEL_SERVICE_URL=${MODEL_SERVICE_URL}
ENV FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
ENV REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
ENV REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
ENV REDDIT_USER_AGENT=${REDDIT_USER_AGENT}

EXPOSE 8050

CMD ["python", "server.py"]