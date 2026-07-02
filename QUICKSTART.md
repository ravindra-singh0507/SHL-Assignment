# Quick Start Guide - SHL AI Hiring Assistant

## Prerequisites

- Python 3.11 or higher
- pip package manager
- Git (optional, for cloning)
- Google Gemini API key

## Step 1: Clone/Setup Project

```bash
cd shl-assignment
```

## Step 2: Create Virtual Environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including:
- fastapi, uvicorn
- google-generativeai
- sentence-transformers
- faiss-cpu
- pydantic, python-dotenv

## Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your GEMINI_API_KEY:

```
GEMINI_API_KEY=your_actual_api_key_here
CATALOG_PATH=data/shl_product_catalog.json
INDEX_PATH=vector_store/faiss_index.pkl
HOST=0.0.0.0
PORT=8000
```

## Step 5: Build Vector Index (Optional - Done Automatically)

```bash
python setup.py build-index
```

Or manually:

```bash
python -c "
from app.catalog import Catalog
from app.retrieval import Retrieval
catalog = Catalog('data/shl_product_catalog.json')
retrieval = Retrieval(catalog)
retrieval.build_index()
retrieval.save_index()
print('Index built!')
"
```

## Step 6: Start the Server

```bash
python setup.py run
```

Or directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

## Step 7: Access the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Example API Calls

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok"
}
```

### Chat Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "We need an assessment for senior engineers specializing in Java and Spring"
      }
    ]
  }'
```

### Multi-turn Conversation

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
        "content": "What technologies are critical for this role?"
      },
      {
        "role": "user",
        "content": "Java, Spring, SQL, and AWS"
      }
    ]
  }'
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_catalog.py -v

# Run with coverage
python -m pytest tests/ --cov=app
```

## Troubleshooting

### ModuleNotFoundError: No module named 'google.generativeai'

```bash
pip install google-generativeai
```

### ModuleNotFoundError: No module named 'sentence_transformers'

```bash
pip install sentence-transformers
```

### GEMINI_API_KEY not found

Ensure `.env` file exists and contains:
```
GEMINI_API_KEY=your_key_here
```

### Vector index not found

The index is built automatically on first startup. If issues persist:

```bash
rm vector_store/faiss_index.pkl  # Remove old index
python setup.py build-index       # Rebuild
```

### Port 8000 already in use

```bash
# Use a different port
uvicorn app.main:app --port 8001
```

## Development Workflow

1. **Make changes** to Python files in `app/`
2. **Start server with `--reload`** flag to auto-restart on changes
3. **Test with curl or Swagger UI**
4. **Run tests** with `pytest`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check `data/sample_conversations/` for example conversations
- Review `app/prompts.py` for system prompt tuning
- Modify `app/agent.py` for conversation logic changes

## Deployment

To deploy on Render:

1. Push code to GitHub
2. Connect repository to Render
3. Set environment variables in Render dashboard
4. Deploy using the `render.yaml` configuration

See [README.md](README.md) for detailed deployment instructions.
