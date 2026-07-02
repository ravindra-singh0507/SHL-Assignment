# Architecture - SHL AI Hiring Assistant

## System Design

The SHL AI Hiring Assistant is a stateless, conversational API that recommends SHL assessments based on user requirements. It uses semantic search to find relevant assessments and Gemini 2.5 Flash to generate natural conversation responses.

## Component Overview

### 1. Catalog (`app/catalog.py`)
- **Purpose**: Load and manage the SHL assessment catalog
- **Key Classes**: 
  - `Assessment`: Represents a single assessment with metadata
  - `Catalog`: Container for all assessments
- **Features**:
  - Parses JSON catalog into Assessment objects
  - Maps assessment keys to test_type codes (K, P, A, S, B, C, D)
  - Provides lookup methods (by name, by ID)
  - Generates searchable text for embeddings

### 2. Retrieval (`app/retrieval.py`)
- **Purpose**: Vector search using FAISS and sentence-transformers
- **Key Classes**: 
  - `Retrieval`: Manages the FAISS vector index
- **Features**:
  - Embeds assessment text using sentence-transformers
  - Builds and saves FAISS index for fast similarity search
  - Retrieves top-K similar assessments for a query
  - Supports name-based search

### 3. LLM (`app/llm.py`)
- **Purpose**: Wrapper around Google Gemini 2.5 Flash API
- **Key Classes**: 
  - `LLM`: API client
- **Features**:
  - Generates responses with system and user prompts
  - Formats conversation history for context
  - Formats assessment data for context injection
  - Extracts JSON from model responses

### 4. Agent (`app/agent.py`)
- **Purpose**: Conversation logic and recommendation engine
- **Key Classes**: 
  - `Agent`: Orchestrates retrieval and generation
- **Features**:
  - Reconstructs conversation state from message history
  - Determines when to clarify vs. recommend
  - Builds search queries from conversation context
  - Parses and validates recommendations
  - Detects comparisons, out-of-domain requests

### 5. Prompts (`app/prompts.py`)
- **Purpose**: Instruction templates for the LLM
- **Key Prompts**:
  - `SYSTEM_PROMPT`: Core instructions and behavior guidelines
  - `RECOMMENDATION_PROMPT`: Instruct to recommend from retrieved items
  - `CLARIFICATION_PROMPT`: Ask clarifying questions
  - `COMPARISON_PROMPT`: Compare two assessments

### 6. Models (`app/models.py`)
- **Purpose**: Pydantic request/response schemas
- **Key Models**:
  - `ChatRequest`: User input format
  - `ChatResponse`: API response format
  - `Recommendation`: Individual recommendation
  - `HealthResponse`: Health check response

### 7. Routes (`app/routes.py`)
- **Purpose**: FastAPI endpoints
- **Endpoints**:
  - `GET /health`: Health check
  - `POST /chat`: Main chat endpoint
- **Features**:
  - Request validation with Pydantic
  - Response serialization
  - Error handling

### 8. Main (`app/main.py`)
- **Purpose**: FastAPI application factory and startup
- **Features**:
  - Initializes all components on startup
  - Loads catalog and builds vector index
  - Sets up CORS middleware
  - Includes router

## Data Flow

### Conversation Flow

```
User Message
    ↓
[Routes] - Parse and validate request
    ↓
[Agent] - Reconstruct state
    ↓
[Agent] - Determine action (clarify vs. recommend)
    ↓
IF clarifying:
    [LLM] - Generate clarification questions
    ↓
    Return response (no recommendations)

IF recommending:
    [Agent] - Build search query
    ↓
    [Retrieval] - Find similar assessments
    ↓
    [LLM] - Generate recommendations from retrieved set
    ↓
    [Agent] - Parse and validate recommendations
    ↓
    Return response with recommendations
```

### Vector Search Flow

```
Catalog Load
    ↓
[Assessment Objects] - Each with searchable_text
    ↓
[Retrieval] - Embed texts with sentence-transformers
    ↓
[FAISS Index] - Store embeddings
    ↓
Save to disk
    ↓
On future requests:
    Query → Embed → Search FAISS → Return top-K
```

## Key Design Decisions

### 1. Statelessness
- Every request contains full conversation history
- No server-side session storage
- Enables horizontal scaling and cloud deployment
- Agent reconstructs context from messages each time

### 2. Retrieved Context Injection
- Before asking Gemini for recommendations, we retrieve relevant assessments
- We only send retrieved assessments to the LLM
- This prevents hallucination of non-existent assessments
- Clean separation between retrieval and generation

### 3. Test Type Mapping
- Catalog uses "keys" array with long strings ("Knowledge & Skills", "Personality & Behavior", etc.)
- We map these to single-letter codes in `assessment.test_type` property
- Multiple types are comma-separated ("K,P" for Knowledge & Personality)
- Makes recommendations compact and matches sample conversation format

### 4. Searchable Text
- Each assessment has `searchable_text` combining name, description, keys, job levels, languages
- This creates rich context for embedding without needing complex metadata handling
- Enables semantic search across all relevant dimensions

### 5. Conversation Heuristics
- First turn (2 messages) requires explicit recommendation keywords
- After several turns, we assume enough context for recommendations
- Looks for action keywords: recommend, suggest, need, hiring, assessment, etc.
- Avoids premature recommendations on vague queries

### 6. Response Validation
- All recommendations are validated against catalog before returning
- Checks that assessment exists in catalog
- Ensures no hallucinated assessments are returned
- Limits to 1-10 recommendations

## Performance Considerations

### Vector Index
- FAISS IndexFlatL2 for exact similarity (suitable for 377 assessments)
- Could upgrade to IVF for larger catalogs (>100K items)
- Index is built once and cached on disk
- Load time: ~100ms, Search time: <10ms

### Embedding Model
- sentence-transformers/all-MiniLM-L6-v2
- 384-dimensional embeddings
- 33MB model size, loads once at startup
- Inference time: ~10-50ms depending on text length

### LLM Calls
- One API call per user message (to Gemini)
- Temperature 0.3 for recommendations (deterministic)
- Temperature 0.5 for clarifications (natural variation)
- Max tokens: 2000 per response

## Scalability

### Current Limits
- Works well for ~300-1000 assessments (current: 377)
- LLM response generation is the bottleneck (~1-2 seconds)
- Vector search is very fast (<10ms)

### Scaling Options
- Use IVF-based FAISS index for larger catalogs
- Implement response caching for common queries
- Use LLM batching for higher throughput
- Add Redis for distributed caching

## Security Considerations

1. **Input Validation**: All requests validated with Pydantic
2. **API Keys**: GEMINI_API_KEY stored in environment variables
3. **CORS**: Configured to accept all origins (adjust for production)
4. **Error Handling**: Graceful error messages, no sensitive data leaks
5. **Prompt Injection**: Detected and refused

## Error Handling

- Missing catalog: Startup fails with clear error
- Invalid JSON: Handled during load with UTF-8 encoding fixes
- Missing API key: Runtime error on LLM initialization
- Empty messages: 400 Bad Request
- LLM timeouts: 500 Internal Server Error with message

## Testing

- Unit tests for catalog loading and retrieval
- Integration tests for API endpoints
- Sample conversation validation
- Test fixtures based on provided sample conversations

## Monitoring & Debugging

1. **Logging**: Configured in utils.py, outputs to console
2. **Health endpoint**: For uptime monitoring
3. **LLM response inspection**: See full response in API tests
4. **Catalog stats**: Easy access via `catalog.size()`

## Future Enhancements

1. Multi-language support for prompts
2. User preference learning (track recommendations)
3. A/B testing framework for different prompts
4. Conversation history persistence (optional)
5. Advanced filtering (by language, duration, job level)
6. Custom assessment combinations
7. Integration with SHL API for real-time catalog updates
8. WebSocket support for streaming responses
