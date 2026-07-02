"""Pydantic models for request/response validation."""

from pydantic import BaseModel
from typing import Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: Optional[list[Recommendation]] = None
    end_of_conversation: bool


class HealthResponse(BaseModel):
    status: str
