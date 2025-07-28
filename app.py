import os
import requests
import openai
import logging
from flask import Flask, render_template, request, jsonify

# --- App Insights Imports ---
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.ext.requests.trace import trace_integration
from opencensus.trace.tracer import Tracer
from opencensus.ext.flask.flask_middleware import FlaskMiddleware

app = Flask(__name__)

# --- App Insights Setup ---
trace_integration()
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler())  # Picks up APPLICATIONINSIGHTS_CONNECTION_STRING from env
logger.setLevel(logging.INFO)

middleware = FlaskMiddleware(
    app,
    exporter=AzureExporter(),
    sampler=ProbabilitySampler(1.0),
)

logger.info("App started and Application Insights logging is enabled.")

# --- Required Environment Variables ---
try:
    WEBHOOK_URL = os.environ['WEBHOOK_URL']
    AZURE_OPENAI_KEY = os.environ['AZURE_OPENAI_KEY']
    AZURE_OPENAI_ENDPOINT = os.environ['AZURE_OPENAI_ENDPOINT']
    AZURE_OPENAI_API_VERSION = os.environ['AZURE_OPENAI_API_VERSION']
    AZURE_DEPLOYMENT_ID = os.environ['AZURE_DEPLOYMENT_ID']
except KeyError as e:
    logger.error(f"Missing environment variable: {e.args[0]}")
    raise RuntimeError(f"Missing required environment variable: {e.args[0]}")

# --- Azure OpenAI Config ---
openai.api_type = "azure"
openai.api_key = AZURE_OPENAI_KEY
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = AZURE_OPENAI_API_VERSION

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    if isinstance(data, list) and len(data) > 0:
        data = data[0]

    user_message = data.get('message')
    session_id = data.get('sessionid')

    logger.info(f"New message from session {session_id}: {user_message}")

    try:
        response = requests.post(
            WEBHOOK_URL,
            json={'message': user_message, 'sessionid': session_id},
            verify=False
        )
        response.raise_for_status()
        logger.info("Webhook response received successfully.")
        try:
            json_response = response.json()
            bot_reply = json_response.get('output', 'No reply from webhook.')
        except ValueError:
            bot_reply = "Webhook error: Empty or non-JSON response"
            logger.warning("Non-JSON response from webhook")
    except Exception as e:
        bot_reply = f"Webhook error: {str(e)}"
        logger.error(f"Webhook call failed: {str(e)}")

    return jsonify({'reply': bot_reply})

@app.route('/summarize_session', methods=['POST'])
def summarize_session():
    data = request.json
    messages = data.get('messages', [])

    if not messages:
        logger.warning("Summarize request received with no messages.")
        return jsonify({"summary": "No messages to summarize."}), 400

    prompt = "Summarize the following chat session in one short sentence for a sidebar label:\n" + "\n".join(messages)

    try:
        response = openai.chat.completions.create(
            model=AZURE_DEPLOYMENT_ID,
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        logger.info("Summary successfully generated for session.")
        return jsonify({"summary": summary})
    except Exception as e:
        logger.error(f"OpenAI summarization failed: {str(e)}")
        return jsonify({"summary": f"OpenAI error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
