import os
from flask import Flask, request, jsonify
import requests

# Optional App Insights (non-blocking)
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor()
    except ImportError:
        print("[INFO] Azure Monitor exporter not installed. Skipping App Insights setup.")

app = Flask(__name__)

# Load environment variables
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT_ID = os.getenv("AZURE_DEPLOYMENT_ID")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "Missing 'message' in request"}), 400

    headers = {
        "Content-Type": "application/json",
        "api-key": OPENAI_API_KEY
    }

    body = {
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.7,
        "top_p": 0.95,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "max_tokens": 800,
        "stop": None
    }

    try:
        response = requests.post(
            f"{OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_ID}/chat/completions?api-version={API_VERSION}",
            headers=headers,
            json=body
        )
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        return jsonify({"response": answer})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/summarize_session", methods=["POST"])
def summarize_session():
    data = request.get_json()
    messages = data.get("messages", [])

    if not isinstance(messages, list):
        return jsonify({"error": "'messages' should be a list"}), 400

    summary_prompt = "Summarize this chat:\n\n" + "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in messages
    )

    headers = {
        "Content-Type": "application/json",
        "api-key": OPENAI_API_KEY
    }

    body = {
        "messages": [{"role": "user", "content": summary_prompt}],
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 300
    }

    try:
        response = requests.post(
            f"{OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_ID}/chat/completions?api-version={API_VERSION}",
            headers=headers,
            json=body
        )
        response.raise_for_status()
        summary = response.json()["choices"][0]["message"]["content"]
        return jsonify({"summary": summary})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
