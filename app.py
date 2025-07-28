from flask import Flask, request, jsonify, session
import openai
import os
from flask_cors import CORS
from azure.monitor.opentelemetry import configure_azure_monitor

# Enable Application Insights if the connection string is set
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor()

app = Flask(__name__)
CORS(app)

# Secret key for Flask session management
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a_very_secret_key")

# OpenAI API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/")
def index():
    return jsonify({"message": "Chat API is running."})

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    user_message = data.get("message", "")
    
    if "chat_history" not in session:
        session["chat_history"] = []

    session["chat_history"].append({"role": "user", "content": user_message})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=session["chat_history"]
        )
        reply = response["choices"][0]["message"]["content"]
        session["chat_history"].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/summarize_session", methods=["GET"])
def summarize_session():
    if "chat_history" not in session or not session["chat_history"]:
        return jsonify({"summary": "No session history to summarize."})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=session["chat_history"] + [{"role": "user", "content": "Summarize this session"}]
        )
        summary = response["choices"][0]["message"]["content"]
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    return jsonify({"message": "Session reset."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
