# Reddit Post Emotion Classifier

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Powered-blue.svg)](https://www.docker.com/)

A web tool to analyze and visualize the emotion distribution in the comments of any Reddit post. This project allows for a quick measurement of public opinion and the overall sentiment of a community on a specific topic.

## ✨ Key Features

* **Simple Web Interface:** Allows any user to analyze a post by simply pasting its URL.
* **Reddit Integration:** Uses the official Reddit API via PRAW to efficiently fetch comments.
* **Microservice Architecture:** The system is designed with two main services: a web server (`server.py`) that handles user requests and Reddit communication, and an inference API (`model_api.py`) that handles the Natural Language Processing.
* **Dynamic Model Selection:** Offers a choice of multiple emotion classification models from the Hugging Face Hub. The user can select which model to use for each analysis.
* **Model Caching for Optimal Performance:** The model API caches Hugging Face pipelines after their first load, avoiding the need to reload them on every request and significantly improving response times.
* **Efficient Data Processing:** Uses the **Polars** library for high-performance aggregation and manipulation of the analysis results.
* **Results Visualization:** Displays a clear and concise summary of the emotion distribution through an interactive chart generated with Chart.js.

## 🛠️ Tech Stack

The project is built with the following technologies and libraries:

* **Backend & API:**
    * **Flask:** As the web micro-framework for both the main server and the model API.
* **Machine Learning / NLP:**
    * **Hugging Face `transformers`:** To load and utilize state-of-the-art text classification models.
    * **Hugging Face `pipeline`:** To simplify the model inference process.
* **Data Analysis & Manipulation:**
    * **Polars:** For high-performance data manipulation.
* **External API Integration:**
    * **PRAW (Python Reddit API Wrapper):** To interact with the Reddit API.
    * **Requests:** For internal communication between the web server and the model API.
* **Frontend:**
    * **HTML / Jinja2:** For rendering web pages.
    * **JavaScript / Chart.js:** For creating interactive data visualizations.
* **Deployment:**
    * **Docker / Docker Compose:** For containerization and service orchestration.

## 🚀 Demo

A quick GIF showcasing the process: entering a Reddit URL, seeing the analysis, and viewing the results chart.

![Demo del Clasificador de Emociones](https://github.com/E-sanchez03/emotion-post-classifier/blob/main/assets/demo.gif?raw=true)

## ⚙️ Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

You need to have Git and Docker installed on your machine.
* [Git](https://git-scm.com/downloads)
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Installation & Running

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/E-sanchez03/emotion-post-classifier.git](https://github.com/E-sanchez03/emotion-post-classifier.git)
    cd emotion-post-classifier
    ```

2.  **Create the credentials file:**
    Create a file named `credencialesPraw.env` in the root of the project and add your Reddit API credentials. You can get these by creating a "script" app on Reddit's developer portal.
    ```env
    # credencialesPraw.env
    REDDIT_CLIENT_ID="your_client_id"
    REDDIT_CLIENT_SECRET="your_client_secret"
    REDDIT_USER_AGENT="your_user_agent (e.g., MyRedditSentimentApp/0.1 by u/YourUsername)"
    ```

3.  **Build and run the application with Docker Compose:**
    This command will build the Docker images for both the server and the model API and start the containers.
    ```sh
    docker-compose up --build
    ```

4.  **Access the application:**
    Open your web browser and navigate to:
    [http://localhost:8050](http://localhost:8050)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Eugenio Sánchez Carreño**

* **LinkedIn:** [Eugenio Sánchez Carreño](https://www.linkedin.com/in/eugenio-s%C3%A1nchez-carre%C3%B1o/)
* **GitHub:** [E-sanchez03](https://github.com/E-sanchez03)
