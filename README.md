# Telex AI Fitness Tip API

## Overview
This is an AI-powered fitness tip generation API built with Python and FastAPI. It leverages the OpenAI API to generate daily health tips, caches them locally, and serves them through a simple JSON endpoint.

## Features
- **FastAPI**: Serves as the high-performance web framework for building the API.
- **OpenAI API**: Used for the intelligent generation of health and fitness tips.
- **APScheduler**: Manages the daily, automated job of fetching and caching a new tip.
- **Local JSON Cache**: Persists a history of generated tips to a file, preventing redundant API calls and ensuring a tip is available for the day.

## Getting Started
### Installation
1.  **Clone the repository**
    ```bash
    git clone https://github.com/Wilsonide/health-ai.git
    cd health-ai
    ```

2.  **Create an environment file**
    Create a file named `.env` in the project root and add your environment variables.
    ```bash
    touch .env
    ```

3.  **Install dependencies**
    This project uses `uv` for package management.
    ```bash
    uv sync
    ```

4.  **Run the application**
    ```bash
    uv run uvicorn main:app --host 0.0.0.0 --port 8000
    ```
    The API will be available at `http://localhost:8000`.

### Environment Variables
The following environment variables are required. Add them to your `.env` file.

- `OPENAI_API_KEY`: Your API key for the OpenAI service.
  - **Example**: `OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"`
- `MODEL_NAME`: (Optional) The OpenAI model to use.
  - **Example**: `MODEL_NAME="gpt-4o-mini"`
- `CACHE_FILE`: (Optional) The name of the file used for caching tips.
  - **Example**: `CACHE_FILE="cache.json"`
- `HISTORY_SIZE`: (Optional) The number of past tips to store in the cache history.
  - **Example**: `HISTORY_SIZE="7"`
- `DAILY_TIP_HOUR_UTC`: (Optional) The hour (in UTC) to schedule the daily tip generation job.
  - **Example**: `DAILY_TIP_HOUR_UTC="7"`

## API Documentation
### Base URL
`http://localhost:8000`

### Endpoints
#### GET /
Provides basic information about the running API service.

**Request**:
No payload required.

**Response**:
```json
{
    "name": "Telex AI Fitness Tip Agent",
    "short_description": "Provides daily fitness tips via A2A JSON-RPC protocol.",
    "description": "An A2A agent that generates and sends AI-powered daily fitness tips using JSON-RPC 2.0. Designed for use with Telex workflows.",
    "author": "Wilson Icheku",
    "version": "1.0.0",
    "status": "running",
    "message": "Telex Fitness Agent (REST, OpenAI) is active!"
}
```

**Errors**:
- None expected for this endpoint.

---

#### POST /message
The main endpoint to retrieve fitness tips. It accepts different commands within the `text` field.

**Request**:
The payload should be a JSON object with a `text` key.
- To get the daily tip: `{"text": ""}` or any other string.
- To get the tip history: `{"text": "history"}`
- To force a new tip generation: `{"text": "refresh"}` or `{"text": "force"}`

```json
{
  "text": "history"
}
```

**Response**:
- **Daily Tip (Success)**: Returns the tip as a plain text string.
  ```
  "Incorporate a 10-minute walk into your day, whether during lunch or after dinner—it's a simple way to boost your mood and energy!"
  ```

- **History (Success)**: Returns a JSON array of historical tip objects.
  ```json
  [
    {
      "date": "2025-11-01",
      "tip": "Take a brisk 10-minute walk today to boost your mood and energy—it's a simple way to get your body moving and clear your mind!"
    },
    {
      "date": "2025-11-01",
      "tip": "Incorporate a 10-minute walk into your daily routine; it's a great way to boost energy and improve mood!"
    }
  ]
  ```

**Errors**:
- `500 Internal Server Error`: Returned for general processing failures.
  ```json
  {
      "status": "error",
      "message": "Something went wrong. Please try again later.",
      "error": "<description_of_the_error>"
  }
  ```
- `502 Bad Gateway`: Returned if the OpenAI API call fails or if the generated tip fails validation.
  ```json
  {
    "detail": "OpenAI error: <description>"
  }
  ```