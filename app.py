import os
import logging
import requests
import openai
from flask import Flask, render_template, request, jsonify

# --- OpenTelemetry Setup ---
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.azure.monitor import AzureMonitorTraceExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# --- Azure Monitor Resource Init ---
resource = Resource.create({
    "service.name": "app-itinnovate-snowagent",
})

# --- Tracer and Exporter ---
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

exporter = AzureMonitorTraceExporter.from_connection_string(
    os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(exporter)
)

# --- App Init ---
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# --- Required Environment Variables ---
WEBHOOK_URL = os.environ['WEBHOOK_URL']
AZURE_OPENAI_KEY = os.environ['AZURE_OPENAI_KEY']
AZURE_OPENAI_ENDPOINT = os.environ['AZURE_OPENAI_ENDPOINT']
AZURE_OPENAI_API_VERSION = os.environ['AZURE_OPENAI_API_VERSION']
AZURE_DEPLOYMENT_ID = os.environ['AZURE_DEPLOYMENT_ID']

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

    with tracer.start_as_current_span("send_message"):
        try:
            response = requests.post(
                WEBHOOK_URL,
                json={'message': user_message, 'sessionid': session_id},
                verify=False
            )
            response.raise_for_status()
            try:
                json_response = response.json()
                bot_reply = json_response.get('output', 'No reply from webhook.')
            except ValueError:
                bot_reply = "Webhook error: Empty or non-JSON response"
        except Exception as e:
            bot_reply = f"Webhook error: {str(e)}"
        return jsonify({'reply': bot_reply})

@app.route('/summarize_session', methods=['POST'])
def summarize_session():
    data = request.json
    messages = data.get('messages', [])

    if not messages:
        return jsonify({"summary": "No messages to summarize."}), 400

    prompt = "Summarize the following chat session in one short sentence for a sidebar label:\n" + "\n".join(messages)

    with tracer.start_as_current_span("summarize_session"):
        try:
            response = openai.chat.completions.create(
                model=AZURE_DEPLOYMENT_ID,
                messages=[{"role": "user", "content": prompt}]
            )
            summary = response.choices[0].message.content.strip()
            return jsonify({"summary": summary})
        except Exception as e:
            return jsonify({"summary": f"OpenAI error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
