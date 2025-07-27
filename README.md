# Flask Chatbot with Nginx and Docker

This project is a simple chatbot web app built with Flask, served via Nginx in Docker. All messages are sent to an n8n webhook.

## Features
- HTML chatbot UI
- Flask backend
- Nginx reverse proxy
- Dockerized setup
- Forwards all messages to n8n webhook

## Setup
1. Ensure Docker and Docker Compose are installed.
2. Build and start the services:
   ```zsh
   docker-compose up --build
   ```
3. Access the chatbot at [http://localhost:8080](http://localhost:8080)

## Configuration
- The n8n webhook URL is set in `docker-compose.yml` as `N8N_WEBHOOK_URL`.
- Nginx proxies requests to the Flask app.

## File Structure
- `app.py`: Flask application
- `templates/index.html`: Chatbot UI
- `requirements.txt`: Python dependencies
- `Dockerfile`: Flask app container
- `nginx.conf`: Nginx configuration
- `docker-compose.yml`: Multi-container setup

## Customization
- Update the n8n webhook URL in `docker-compose.yml` if needed.
- Modify `index.html` for UI changes.

---
For questions or issues, please open an issue in this repository.
