"""FastAPI routes."""

from fastapi import APIRouter, HTTPException
from .models import ChatRequest, ChatResponse, HealthResponse, Recommendation
from .agent import Agent
from .utils import logger

router = APIRouter()

_agent: Agent = None


def set_agent(agent: Agent):
    """Set the global agent instance."""
    global _agent
    _agent = agent


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint for conversational recommendations."""
    if not _agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        reply, recommendations, end_of_conversation = _agent.process_messages(messages)

        # Build recommendation list
        rec_list = None
        if recommendations:
            rec_list = [
                Recommendation(
                    name=rec["name"],
                    url=rec["url"],
                    test_type=rec["test_type"],
                )
                for rec in recommendations
            ]

        return ChatResponse(
            reply=reply,
            recommendations=rec_list,
            end_of_conversation=end_of_conversation,
        )

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
