# Telex AI API

## Overview
This project is a Python-based API built with FastAPI that serves daily health and fitness tips. It leverages the OpenAI API to generate content and uses an internal scheduler (APScheduler) for daily content refreshes.

## Features
- **FastAPI**: Provides a high-performance, asynchronous web framework for the API.
- **JSON-RPC 2.0**: Implements a single endpoint (`/rpc`) for all API interactions, following the JSON-RPC specification.
- **OpenAI Integration**: Connects to the OpenAI API (e.g., GPT-4o Mini) to generate unique, actionable fitness tips.
- **APScheduler**: Manages a background cron job to automatically generate a new tip each day.
- **Local Caching**: Stores generated tips in a local JSON file to prevent redundant API calls and ensure consistent daily content.

## Getting Started
### Installation
Follow these steps to set up and run the project locally.

1.  **Clone the repository**
    ```bash
    git clone https://github.com/your-username/telex-ai.git
    cd telex-ai
    ```

2.  **Install dependencies**
    The project uses `uv` for package management.
    ```bash
    uv sync
    ```

3.  **Set up environment variables**
    Create a `.env` file in the root directory and add the necessary variables.
    ```bash
    touch .env
    ```
    See the section below for the required variables.

4.  **Run the server**
    ```bash
    uv run uvicorn main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

### Environment Variables
These variables must be defined in a `.env` file at the project root.

| Variable                 | Description                                    | Example                               |
| ------------------------ | ---------------------------------------------- | ------------------------------------- |
| `OPENAI_API_KEY`         | **Required.** Your API key for OpenAI.         | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx`     |
| `MODEL_NAME`             | The OpenAI model to use.                       | `gpt-4o-mini`                         |
| `CACHE_FILE`             | Path to the local cache file.                  | `cache.json`                          |
| `HISTORY_SIZE`           | Number of past tips to retain in the cache.    | `7`                                   |
| `DAILY_TIP_HOUR_UTC`     | The UTC hour for the daily scheduled job.      | `7`                                   |
| `MIN_OPENAI_CALL_INTERVAL` | Minimum seconds between calls to OpenAI API. | `3`                                   |
| `MAX_TIP_LENGTH_CHARS`   | Maximum character length for a tip.            | `280`                                 |

## API Documentation
### Base URL
`http://127.0.0.1:8000`

### Endpoints
The API uses a single JSON-RPC 2.0 endpoint to handle all methods.

#### POST /rpc
This endpoint accepts all method calls. The specific action is determined by the `method` field in the JSON payload.

**Request**:
A standard JSON-RPC 2.0 request object.
```json
{
  "jsonrpc": "2.0",
  "method": "[METHOD_NAME]",
  "params": {},
  "id": 1
}
```

---

#### Method: `get_daily_tip`
Retrieves the fitness tip for the current day from the cache. If no tip is cached, it generates a new one, caches it, and then returns it.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "get_daily_tip",
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tip": "Take a brisk 10-minute walk today; it's a simple way to boost your mood and energy levels while getting your body moving!"
  },
  "error": null
}
```

---

#### Method: `get_history`
Returns a list of all previously generated and cached tips.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "get_history",
  "id": 2
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "history": [
      {
        "date": "2025-10-30",
        "tip": "Take a brisk 10-minute walk today; it's a simple way to boost your mood and energy levels while getting your body moving!"
      }
    ]
  },
  "error": null
}
```

---

#### Method: `force_refresh`
Forces the generation of a new tip from the OpenAI API, overwriting the cached tip for the current day if one exists.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "force_refresh",
  "id": 3
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "tip": "Incorporate 15 minutes of stretching into your morning routine to improve flexibility and reduce the risk of injury."
  },
  "error": null
}
```
---
**Errors**:
The API uses standard JSON-RPC 2.0 error codes within the response body, as well as standard HTTP status codes for critical failures.

- `-32700 Parse error`: Invalid JSON was received by the server.
- `-32600 Invalid Request`: The JSON sent is not a valid Request object.
- `-32601 Method not found`: The method does not exist / is not available.
- `-32602 Invalid params`: The `params` field was present, but this agent does not accept parameters.
- `-32000 Server error`: Generic error for failures during tip generation or history retrieval.
- `502 Bad Gateway`: Indicates a failure to communicate with or validate a response from the OpenAI API.

[![Readme was generated by Dokugen](https://img.shields.io/badge/Readme%20was%20generated%20by-Dokugen-brightgreen)](https://www.npmjs.com/package/dokugen)