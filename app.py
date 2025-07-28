from flask import Flask, request, jsonify, session
import os
import requests
from flask_cors import CORS
from azure.monitor.opentelemetry import configure_azure_monitor

# Enable App Insights if the connection string exists
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a_very_secret_key")

# Azure OpenAI config
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")  # fallback

@app.route("/")
def index():
    return jsonify({"message": "Chat API is running."})

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    user_input = data.get("message", "")

    if "chat_history" not in session:
        session["chat_history"] = []

    session["chat_history"].append({"role": "user", "content": user_input})

    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }
    payload = {
        "messages": session["chat_history"],
        "temperature": 0.7
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        reply = res.json()["choices"][0]["message"]["content"]
        session["chat_history"].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/summarize_session", methods=["GET"])
def summarize_session():
    if "chat_history" not in session or not session["chat_history"]:
        return jsonify({"summary": "No session history to summarize."})

    session["chat_history"].append({"role": "user", "content": "Summarize this session"})
    return send_message()

@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"message": "Session reset."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
