# Huggle Bundler

The **Huggle Bundler** is a specialized standalone service for the Huggle platform, designed to intelligently bundle seller products. It leverages AI logic models for smart product grouping and generative AI for creating appealing bundle images.

## 🏗 Architecture

The system is built as a **FastAPI** service that interacts with a **PostgreSQL** database. It integrates with external and local AI services to provide its core functionality.

### Core Components

1.  **Bundling API (`bundling_api/`)**:
    -   **Framework**: FastAPI (Python).
    -   **Database**: PostgreSQL (via SQLAlchemy & Alembic), designed to work with Neon.
    -   **Endpoints**: REST API for recommending and saving bundles.

2.  **AI Logic Engine**:
    -   **Service**: `app.services.ai`
    -   **Function**: Generates bundle names ("Catchy" yet honest) and descriptions.
    -   **Providers**:
        -   **OpenRouter** (DeepSeek models).
        -   **Groq** (Llama 3 models) for low-latency generation.
    -   **Strategy**: Prioritizes products expiring soon to reduce waste.

3.  **Generative AI for Images**:
    -   **Service**: `app.services.image_generator`
    -   **Technology**: Local **Diffusers** (Stable Diffusion) or Mock mode.
    -   **Flow**:
        -   Analyzes product categories (Electronics, Food, etc.) to determine composition, lighting, and style.
        -   Generates a prompt compatible with CLIP token limits.
        -   Uses a local async worker pattern (`start_async_image_server.py`) to handle GPU-intensive generation.
    -   **Storage**: Uploads generated images to Cloudflare R2 or serves them locally.

## 🚀 Getting Started

### Prerequisites

-   **Python 3.11+**
-   **PostgreSQL** database (or a Neon connection string).
-   **GPU** (Optional, but recommended for local image generation).

### Installation

1.  **Clone the repository** and navigate to the root.

2.  **Set up the Virtual Environment**:
    ```bash
    cd bundling_api
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Configuration**:
    Copy the example environment file and configure it:
    ```bash
    cp .env.example .env
    ```
    Update `.env` with your credentials:
    -   `DATABASE_URL`: Your Postgres connection string.
    -   `AI_PROVIDER`: `openrouter` or `groq`.
    -   `OPENROUTER_API_KEY` / `GROQ_API_KEY`: Keys for LLM services.
    -   `R2_*`: Cloudflare R2 credentials for image storage.

5.  **Database Migration**:
    Initialize the database schema for bundles:
    ```bash
    alembic upgrade head
    ```

### Running the Service

You can run the API server and the image generation worker separately.

#### 1. Start the Main API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at `http://localhost:8000`.

#### 2. Start the Async Image Server (Optional)
If you want to enable local image generation:
```bash
python start_async_image_server.py
```
*Note: This requires a GPU and installed torch/diffusers dependencies.*

## 📚 API Overview

-   **POST /bundles/recommend**: Get rule-based bundle suggestions.
-   **POST /bundles/recommend/ai**: Get AI-enhanced suggestions (uses LLM for naming/descriptions).
-   **POST /bundles/save**: Save a selected bundle to the database.
-   **GET /bundles**: List saved bundles for a seller.

## 📁 Project Structure

-   `bundling_api/`: Main application source.
    -   `app/`: FastAPI application code.
        -   `services/`: Core logic (AI, Recommender, Image Gen).
        -   `routers/`: API route definitions.
        -   `models/` & `schemas/`: DB and Pydantic models.
    -   `migrations/`: Alembic migration scripts.
    -   `scripts/`: Utility scripts for testing and maintenance.
-   `bin/` & `lib/`: (Local virtual environment files).

## 🛠 Development

to run tests:
```bash
pytest
```

For more detailed documentation, checking `bundling_api/README.md`.
