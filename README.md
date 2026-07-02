# SHL AI Hiring Assistant

A conversational AI assistant that recommends SHL Individual Test Solutions through natural conversation using FastAPI, Google Gemini 2.5 Flash, and semantic search with FAISS.

## Features

- **Conversational Interface**: Ask clarification questions when requests are vague
- **Smart Recommendations**: Recommend relevant SHL assessments from a comprehensive catalog
- **Refinement**: Update recommendations as requirements change
- **Comparison**: Compare two assessments using only catalog data
- **Refusal**: Politely decline out-of-domain requests
- **Grounded Responses**: All recommendations come only from the supplied catalog
- **Stateless API**: Reconstruct conversation state from message history

## Technology Stack

- **Python 3.11+**
- **FastAPI** - Web framework
- **Google Gemini 2.5 Flash** - LLM for conversational logic
- **sentence-transformers** - Semantic embeddings
- **FAISS** - Vector similarity search
- **Pydantic** - Request/response validation
- **python-dotenv** - Environment configuration

## Project Structure

```
shl-assignment/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── routes.py            # API endpoints (/health, /chat)
│   ├── catalog.py           # Load & manage SHL assessments
│   ├── retrieval.py         # FAISS vector search
│   ├── agent.py             # Conversation logic
│   ├── llm.py               # Gemini API wrapper
│   ├── prompts.py           # System prompts & templates
│   ├── models.py            # Pydantic schemas
│   └── utils.py             # Utility functions
├── data/
│   └── shl_product_catalog.json      # Catalog (auto-downloaded)
│   └── sample_conversations/         # Sample conversations for testing
├── vector_store/
│   └── faiss_index.pkl              # Vector index (built at startup)
├── tests/
│   ├── __init__.py
│   └── test_endpoints.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Installation

### 1. Clone or setup the project

```bash
cd shl-assignment
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 5. Download the catalog (if not already present)

The catalog is automatically downloaded on first startup. To manually download:

```bash
python -c "
from app.catalog import Catalog
catalog = Catalog('data/shl_product_catalog.json')
print(f'Loaded {catalog.size()} assessments')
"
```

## Running Locally

### Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

## Building the Vector Index

The vector index is built automatically on first startup. To rebuild:

```bash
python -c "
from app.catalog import Catalog
from app.retrieval import Retrieval

catalog = Catalog('data/shl_product_catalog.json')
retrieval = Retrieval(catalog)
retrieval.build_index()
retrieval.save_index()
print('Index built and saved')
"
```

## API Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

### POST /chat

Chat endpoint for conversational recommendations.

**Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "We need an assessment for senior leadership."
    }
  ]
}
```

**Response:**
```json
{
  "reply": "For senior leadership positions, I recommend...",
  "recommendations": [
    {
      "name": "Occupational Personality Questionnaire OPQ32r",
      "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
      "test_type": "P"
    }
  ],
  "end_of_conversation": false
}
```

## Examples

### Example 1: Initial Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "We need an assessment for senior leadership."
      }
    ]
  }'
```

### Example 2: Multi-turn Conversation

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "We need assessments for senior engineers"
      },
      {
        "role": "assistant",
        "content": "What technologies and skills are critical?"
      },
      {
        "role": "user",
        "content": "Java, Spring, AWS, and Docker"
      }
    ]
  }'
```

## Testing

### Run tests

```bash
pytest tests/ -v
```

### Test with sample conversations

```bash
python -c "
from pathlib import Path
import json
from app.catalog import Catalog
from app.retrieval import Retrieval
from app.llm import LLM
from app.agent import Agent

# Load components
catalog = Catalog('data/shl_product_catalog.json')
retrieval = Retrieval(catalog)
retrieval.load_index()
llm = LLM()
agent = Agent(catalog, retrieval, llm)

# Test with sample message
messages = [
    {'role': 'user', 'content': 'We need an assessment for senior leadership'}
]
reply, recs = agent.process_messages(messages)
print('Reply:', reply)
print('Recommendations:', len(recs) if recs else 0)
"
```

## Deployment on Render

### 1. Create a Render account

Visit https://render.com and create an account.

### 2. Connect GitHub repository

Connect your GitHub repository to Render.

### 3. Create a Web Service

- **Name**: shl-ai-hiring-assistant
- **Environment**: Python
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### 4. Set environment variables

In the Render dashboard:
- `GEMINI_API_KEY`: Your Google Gemini API key
- `CATALOG_PATH`: `data/shl_product_catalog.json`
- `INDEX_PATH`: `vector_store/faiss_index.pkl`

### 5. Deploy

Push to the connected branch, and Render will automatically deploy.

## Conversation Behaviors

### Clarification

When the request is vague, the assistant asks 1-2 focused questions:

```
User: "I need an assessment."
Assistant: "What role are you hiring for, and what seniority level?"
```

### Recommendation

Once enough context exists, the assistant provides 1-10 recommendations:

```
Assistant: "For senior leadership, I recommend:
1. OPQ32r - Measures 32 workplace behavior dimensions
2. OPQ Leadership Report - Leadership-specific insights"
```

### Refinement

If the user changes requirements, recommendations are updated:

```
User: "Actually, add a technical knowledge component."
Assistant: "Updated recommendation to include..."
```

### Comparison

If the user asks to compare assessments:

```
User: "Compare OPQ32r and DSI"
Assistant: "OPQ32r measures broad workplace behavior (25 min), while DSI focuses specifically on safety and dependability (10 min)..."
```

### Refusal

Out-of-domain requests are politely declined:

```
User: "What interview questions should I ask?"
Assistant: "I can only help with assessment selection. For interview guidance, I'd recommend..."
```

## Code Quality

- Type hints throughout
- Pydantic models for validation
- Clean separation of concerns
- Modular design
- Comprehensive error handling
- Logging throughout

## Limitations

- No conversation memory (stateless)
- Recommendations limited to SHL catalog
- Clarification questions only in English
- No real-time catalog updates

## Future Improvements

- Multi-language support
- Conversation history persistence (optional)
- Integration with SHL API for real-time updates
- Custom assessment combinations
- Role-specific templates
- Advanced filtering options

## Support

For issues or questions:
1. Check the sample conversations in `data/sample_conversations/`
2. Review API documentation at `/docs`
3. Check logs for error details

## License

SHL AI Hiring Assistant - AI Interview Take-home Assignment
