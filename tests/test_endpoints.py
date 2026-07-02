"""Tests for SHL AI Hiring Assistant API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client with proper lifespan management."""
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_no_extra_fields(self, client):
        response = client.get("/health")
        data = response.json()
        assert set(data.keys()) == {"status"}


class TestChatEndpoint:
    def test_empty_messages_returns_400(self, client):
        response = client.post("/chat", json={"messages": []})
        assert response.status_code == 400

    def test_invalid_request_body(self, client):
        response = client.post("/chat", json={})
        assert response.status_code == 422

    def test_response_schema(self, client):
        """Response must have exactly: reply, recommendations, end_of_conversation."""
        response = client.post("/chat", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "end_of_conversation" in data
        assert "recommendations" in data
        assert isinstance(data["reply"], str)
        assert isinstance(data["end_of_conversation"], bool)

    def test_recommendations_schema_when_present(self, client):
        """Each recommendation must have name, url, test_type."""
        response = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "We run a graduate management trainee scheme. We need a full battery - cognitive, personality, and situational judgement."}
            ]
        })
        data = response.json()
        if data["recommendations"]:
            for rec in data["recommendations"]:
                assert "name" in rec
                assert "url" in rec
                assert "test_type" in rec
                assert rec["url"].startswith("https://www.shl.com/")


class TestClarification:
    def test_vague_request_asks_clarification(self, client):
        """Vague first message should trigger clarification (no recommendations)."""
        response = client.post("/chat", json={
            "messages": [{"role": "user", "content": "We need a solution for senior leadership."}]
        })
        data = response.json()
        assert data["recommendations"] is None
        assert data["end_of_conversation"] is False
        assert len(data["reply"]) > 0


class TestRecommendation:
    def test_specific_request_gives_recommendations(self, client):
        """Detailed first message should give immediate recommendations."""
        response = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Hiring graduate financial analysts. We need numerical reasoning and a finance knowledge test."}
            ]
        })
        data = response.json()
        assert data["recommendations"] is not None
        assert len(data["recommendations"]) >= 1
        assert data["end_of_conversation"] is False

    def test_multi_turn_recommendation(self, client):
        """After clarification exchange, should give recommendations."""
        response = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "We need a solution for senior leadership."},
                {"role": "assistant", "content": "What kind of solution? Selection or development?"},
                {"role": "user", "content": "Selection - comparing candidates against a leadership benchmark."},
            ]
        })
        data = response.json()
        assert data["recommendations"] is not None
        assert len(data["recommendations"]) >= 1


class TestRefinement:
    def test_add_requirement(self, client):
        """User can add requirements and get updated recommendations."""
        response = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "I need assessments for a senior Java developer."},
                {"role": "assistant", "content": "Here are Java-related assessments."},
                {"role": "user", "content": "Also add AWS and Docker assessments."},
            ]
        })
        data = response.json()
        assert data["recommendations"] is not None
        assert len(data["recommendations"]) >= 1


class TestRefusal:
    def test_legal_question_refused(self, client):
        """Legal/compliance questions should be politely refused."""
        response = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Are we legally required under HIPAA to test all staff?"}
            ]
        })
        data = response.json()
        assert data["recommendations"] is None or data["recommendations"] == []
        assert data["end_of_conversation"] is False


class TestComparison:
    def test_comparison_request(self, client):
        """Comparison requests should return explanation without recommendations."""
        response = client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "What's the difference between the Dependability and Safety Instrument (DSI) and the Manufac. & Indust. - Safety & Dependability 8.0?"}
            ]
        })
        data = response.json()
        assert len(data["reply"]) > 50
        assert data["end_of_conversation"] is False
