# Social-Media-API

A social media backend API built with **FastAPI**, featuring JWT authentication, blog posts, comments, reactions, shares,profiles messaging, WebSocket support, Celery tasks, and Redis caching.

---

## Features

- **Authentication & User Management**
  - JWT-based login and registration
  - Registeration with email validation and profile picture upload
- **Posts & Interactions**
  - Create, read, update, delete posts
  - Comments, reactions (like/unlike), and shares
- **Messaging System**
  - Send/receive messages
  - Real-time updates via WebSockets
  - **Profile System**
  - view your profile and other users profiles
- **Background Tasks**
  - Celery for notifications and asynchronous processing
- **Caching**
  - Redis caching for public profiles, feeds, and message history
- **Database**
  - PostgreSQL (via SQLAlchemy & databases)  
  - Optional Alembic migrations

---
## Installation

1. **Clone the repository**

```bash
git clone https://github.com/USERNAME/REPO_NAME.git
cd REPO_NAME
Create a virtual environment

2. **Create a virtual environment**
bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
Install dependencies

3. **Install dependencies**
bash
pip install -r requirements.txt
Environment variables

Create a .env file in the project root:
4. **Environment variables**

Create a .env file in the project root:
env
DATABASE_URL=postgresql://user:password@localhost/dbname
JWT_SECRET_KEY=your_secret_key
REDIS_URL=redis://localhost:6379/0
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_SENDER=your_sender_email
