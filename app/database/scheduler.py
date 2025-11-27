from app.core.celery_config import celery_app
from app.core.async_config import AsyncSessionLocal
import os
from dotenv import load_dotenv
import requests
from app.log.logger import get_loggers

load_dotenv()
API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER = os.getenv("SENDGRID_SENDER")

logger = get_loggers("celery")


@celery_app.task(name="app.task.send_email", queue="email")
def send_email(subject: str, body: str, to_email: str):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "personalizations": [{"to": [{"email": to_email}], "subject": subject}],
        "from": {"email": SENDER},
        "content": [{"type": "text/plain", "value": body}],
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"respomse: {response.status_code},  body: {response.text}")
    except Exception as e:
        print(f"failure: {e}")
