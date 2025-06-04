FROM python:3.9-slim

WORKDIR /app

COPY requirements_model.txt .

RUN pip install --no-cache-dir -r requirements_model.txt

COPY model_api.py .
COPY credencialesPraw.env . 

ENV FLASK_APP=model_api.py
ENV HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
ENV FLASK_DEBUG=1          
ENV PYTHONUNBUFFERED=1  

EXPOSE 5001

CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
