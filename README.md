# Projet ESP32 - Smartelia API

This project is a FastAPI-based application designed to interact with ESP32 devices and manage Smartelia settings. It features a modern, ergonomic web interface and a robust backend.

## Structure

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: Jinja2 Templates + Custom CSS (No build step required)
- **Database**: PostgreSQL
- **Infrastructure**: Docker & Docker Compose

## Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed.
- OR Python 3.11+ for local development.

## Quick Start (Docker)

The easiest way to run the project is using Docker.

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd projet_esp_32
    ```

2.  **Configure Environment:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` if necessary (e.g., to change secrets or database credentials).

3.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

4.  **Access the Application:**
    - **Dashboard**: [http://localhost:8000](http://localhost:8000)
    - **Settings**: [http://localhost:8000/settings](http://localhost:8000/settings)
    - **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Local Development (Without Docker)

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set Environment Variables:**
    Ensure your `.env` file is configured. You may need to run a local PostgreSQL instance and update `APP_DATABASE_URL`.

3.  **Run the Server:**
    ```bash
    python run.py
    ```

## Configuration

Configuration is managed via environment variables (see `.env.example`).
Key settings include:
- `APP_APP_NAME`: Name of the application.
- `APP_DATABASE_URL`: Database connection string.
- `APP_SECRET_KEY`: Secret key for security (must be 32+ chars).

## Project Layout

- `core/`: Core configuration and logging.
- `routers/`: API and Page routes.
- `templates/`: HTML templates (Jinja2).
- `static/`: Static assets (CSS, JS, Images).
- `docker/`: Docker related files.
