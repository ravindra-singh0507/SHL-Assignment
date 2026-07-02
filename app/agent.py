"""Agent for managing conversation and recommendations."""

import json
import re
from .catalog import Catalog, Assessment
from .retrieval import Retrieval
from .llm import LLM
from .models import Recommendation
from . import prompts
from .utils import logger


class Agent:
    def __init__(self, catalog: Catalog, retrieval: Retrieval, llm: LLM):
        self.catalog = catalog
        self.retrieval = retrieval
        self.llm = llm

    def process_messages(self, messages: list[dict]) -> tuple[str, list[Recommendation], bool]:
        """Process conversation and return (reply, recommendations, end_of_conversation)."""
        if not messages:
            return "Hello! I can help you find the right SHL assessments. What role are you hiring for?", [], False

        last_user_msg = self._get_last_user_message(messages)
        conversation = self.llm.format_conversation(messages)

        # Detect out-of-domain requests
        if self._is_out_of_domain(last_user_msg, conversation):
            reply = self._handle_refusal(last_user_msg)
            return reply, [], False

        # Detect comparison requests
        comparison_names = self._detect_comparison(last_user_msg, messages)
        if comparison_names:
            reply = self._handle_comparison(conversation, comparison_names)
            return reply, [], False

        # Determine intent: clarify vs recommend
        intent = self._classify_intent(messages)

        if intent == "clarify":
            reply = self._handle_clarification(conversation)
            return reply, [], False

        # intent is "recommend" — search and generate recommendations
        search_query = self._build_search_query(messages)
        retrieved = self.retrieval.search(search_query, k=15)

        if not retrieved:
            return "I couldn't find matching assessments. Could you provide more details about the role or skills needed?", [], False

        reply, recommendations = self._handle_recommendation(conversation, last_user_msg, retrieved)

        # Determine end_of_conversation
        end = self._is_end_of_conversation(messages, reply)

        return reply, recommendations, end

    def _get_last_user_message(self, messages: list[dict]) -> str:
        """Get the last user message."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _classify_intent(self, messages: list[dict]) -> str:
        """Classify conversation intent: clarify or recommend."""
        last_msg = self._get_last_user_message(messages)
        msg_lower = last_msg.lower()

        # Single-message case
        if len(messages) == 1:
            has_role = self._has_role_context(msg_lower)
            has_skills = self._has_skill_or_assessment_detail(msg_lower)
            has_action = self._has_action_intent(msg_lower)

            # Recommend if: specific role + specific skills/tech
            if has_role and has_skills:
                return "recommend"
            # Recommend if: explicit assessment action + role
            if has_role and has_action:
                return "recommend"
            # Recommend if: explicit action + enough detail (long message)
            if has_action and len(last_msg.split()) >= 10:
                return "recommend"
            return "clarify"

        # Multi-turn: if user is responding to assistant's questions, recommend
        if len(messages) >= 3:
            action_signals = [
                "add", "include", "also", "drop", "remove", "replace",
                "actually", "instead", "update", "change", "keep",
                "yes", "go ahead", "confirmed", "that works", "perfect",
                "us", "english", "backend", "frontend", "senior ic",
            ]
            if any(signal in msg_lower for signal in action_signals):
                return "recommend"
            return "recommend"

        # Two messages (user + assistant asked + user replied): recommend
        if len(messages) == 2:
            return "recommend" if len(last_msg.split()) > 3 else "clarify"

        return "clarify"

    def _has_role_context(self, msg: str) -> bool:
        """Check if message specifies a clear, specific job role."""
        # These are specific job titles/roles (not vague categories)
        role_indicators = [
            "engineer", "developer", "analyst", "manager", "admin", "operator",
            "graduate", "trainee", "executive", "agent", "assistant",
            "nurse", "doctor", "teacher", "accountant", "consultant",
            "contact centre", "contact center", "plant operator",
            "intern", " sde", "swe ", "devops", "data scientist", "designer",
            "architect", "financial analyst", "hire ", "hiring for",
        ]
        return any(r in msg for r in role_indicators)

    def _has_skill_or_assessment_detail(self, msg: str) -> bool:
        """Check if message specifies skills or assessment types."""
        indicators = [
            # Assessment types
            "cognitive", "personality", "numerical", "verbal", "situational",
            "knowledge test", "reasoning", "full battery", "battery",
            "assessment battery", "screen", "re-skill", "aptitude", "simulation",
            # Technical skills
            "excel", "word", "java", "python", "sql", "spring", "react",
            "angular", "javascript", "typescript", "aws", "docker", "kubernetes",
            "full stack", "full-stack", "frontend", "backend", "devops",
            "machine learning", "data science", "networking",
            # Soft skills / domains
            "safety", "customer service", "communication",
            "problem solving", "critical thinking",
        ]
        return any(d in msg for d in indicators)

    def _has_action_intent(self, msg: str) -> bool:
        """Check if message explicitly requests assessment recommendations."""
        action_phrases = [
            "hiring for", "recruit for",
            "recommend", "suggest", "what should",
            "what assessment", "what test", "which assessment",
            "looking for assessment", "need assessment", "need a test",
            "screen", "evaluate candidates", "assess candidates",
        ]
        return any(p in msg for p in action_phrases)

    def _is_out_of_domain(self, last_msg: str, conversation: str) -> bool:
        """Detect out-of-domain requests."""
        ood_patterns = [
            r"interview question",
            r"legal\s+(advice|requirement|compliance|obligation)",
            r"(are we|am i)\s+(legally|required)",
            r"pay scale|salary|compensation",
            r"(ignore|forget).*(instruction|prompt|system)",
            r"write me (a|an)\s+(email|letter|code|essay)",
            r"what is the meaning of life",
            r"tell me a joke",
        ]
        msg_lower = last_msg.lower()
        return any(re.search(p, msg_lower) for p in ood_patterns)

    def _detect_comparison(self, last_msg: str, messages: list[dict]) -> list[str]:
        """Detect comparison requests and extract assessment names."""
        msg_lower = last_msg.lower()

        comparison_triggers = ["compare", "difference between", "vs", "versus",
                               "different from", "what's the difference"]
        if not any(t in msg_lower for t in comparison_triggers):
            return []

        # Find assessment names mentioned in the message
        mentioned = []
        for assessment in self.catalog.get_all():
            name_lower = assessment.name.lower()
            # Check for partial name matches (e.g., "DSI" for "Dependability and Safety Instrument (DSI)")
            if name_lower in msg_lower:
                mentioned.append(assessment.name)
            # Check for common abbreviations/short names
            elif self._name_fragment_in_text(assessment.name, msg_lower):
                mentioned.append(assessment.name)

        # If we didn't find names in current message, check previous recommendations context
        if len(mentioned) < 2:
            # Look for names from recent conversation context
            for msg in messages:
                content = msg.get("content", "").lower()
                for assessment in self.catalog.get_all():
                    if assessment.name.lower() in content and assessment.name not in mentioned:
                        if assessment.name.lower() in msg_lower or any(
                            word in msg_lower for word in assessment.name.lower().split()[:2]
                        ):
                            mentioned.append(assessment.name)

        return mentioned if len(mentioned) >= 2 else mentioned

    def _name_fragment_in_text(self, name: str, text: str) -> bool:
        """Check if a meaningful fragment of an assessment name appears in text."""
        # Handle parenthetical abbreviations like "(DSI)"
        paren_match = re.search(r'\(([A-Z]{2,})\)', name)
        if paren_match and paren_match.group(1).lower() in text:
            return True
        # Handle key words from name (at least 2 significant words)
        words = [w for w in name.lower().split() if len(w) > 3 and w not in ("new)", "(new)", "the", "and")]
        matches = sum(1 for w in words if w in text)
        return matches >= 2 and len(words) >= 2

    def _handle_refusal(self, last_msg: str) -> str:
        """Generate a polite refusal."""
        try:
            prompt = prompts.REFUSAL_PROMPT.format(request=last_msg)
            return self.llm.generate(prompts.SYSTEM_PROMPT, prompt, temperature=0.3)
        except Exception:
            return ("I can only help with SHL assessment selection and recommendations. "
                    "For legal, compliance, or other questions, please consult the appropriate team. "
                    "Is there anything I can help you with regarding SHL assessments?")

    def _handle_comparison(self, conversation: str, names: list[str]) -> str:
        """Handle assessment comparison requests."""
        assessments = []
        for name in names:
            a = self.catalog.get_by_name(name)
            if a:
                assessments.append(a)

        if not assessments:
            # Try retrieval as fallback
            assessments = self.retrieval.search(" ".join(names), k=5)

        assessment_data = self.llm.format_assessments(assessments)
        prompt = prompts.COMPARISON_PROMPT.format(
            conversation=conversation,
            assessment_data=assessment_data,
        )
        try:
            return self.llm.generate(prompts.SYSTEM_PROMPT, prompt, temperature=0.3)
        except Exception as e:
            logger.error(f"Comparison generation failed: {e}")
            return "I encountered an error comparing those assessments. Could you try rephrasing?"

    def _handle_clarification(self, conversation: str) -> str:
        """Generate clarification questions."""
        prompt = prompts.CLARIFICATION_PROMPT.format(conversation=conversation)
        try:
            return self.llm.generate(prompts.SYSTEM_PROMPT, prompt, temperature=0.5)
        except Exception as e:
            logger.error(f"Clarification generation failed: {e}")
            return "Could you tell me more about the role you're hiring for and what skills are important?"

    def _handle_recommendation(
        self, conversation: str, last_msg: str, retrieved: list[Assessment]
    ) -> tuple[str, list[dict]]:
        """Generate recommendations from retrieved assessments."""
        assessment_context = self.llm.format_assessments(retrieved)

        prompt = prompts.RECOMMENDATION_PROMPT.format(
            conversation=conversation,
            retrieved_assessments=assessment_context,
            requirements=last_msg,
        )

        try:
            response = self.llm.generate(prompts.SYSTEM_PROMPT, prompt, temperature=0.3)
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            # Fallback: return top retrieved assessments
            recs = [{"name": a.name, "url": a.url, "test_type": a.test_type} for a in retrieved[:5]]
            return "Based on your requirements, here are my recommendations:", recs

        # Parse recommendations from the structured response
        recommendations = self._parse_recommendations(response, retrieved)
        return response, recommendations

    def _parse_recommendations(self, response: str, retrieved: list[Assessment]) -> list[dict]:
        """Extract recommendations from LLM response by matching assessment names."""
        recommendations = []
        seen = set()

        response_lower = response.lower()

        # Check which retrieved assessments are mentioned in the response
        for assessment in retrieved:
            name_lower = assessment.name.lower()
            if name_lower in response_lower:
                if assessment.name not in seen:
                    recommendations.append({
                        "name": assessment.name,
                        "url": assessment.url,
                        "test_type": assessment.test_type,
                    })
                    seen.add(assessment.name)
                    if len(recommendations) >= 10:
                        break

        # If no matches found via name matching, try partial matching
        if not recommendations:
            for assessment in retrieved:
                # Check for key distinctive words from the name
                name_words = [w for w in assessment.name.lower().split()
                              if len(w) > 3 and w not in ("new)", "(new)", "the", "and", "for")]
                match_count = sum(1 for w in name_words if w in response_lower)
                if match_count >= 2 or (len(name_words) <= 2 and match_count >= 1):
                    if assessment.name not in seen:
                        recommendations.append({
                            "name": assessment.name,
                            "url": assessment.url,
                            "test_type": assessment.test_type,
                        })
                        seen.add(assessment.name)
                        if len(recommendations) >= 10:
                            break

        # Final fallback: return top retrieved assessments (better than nothing)
        if not recommendations:
            for assessment in retrieved[:5]:
                recommendations.append({
                    "name": assessment.name,
                    "url": assessment.url,
                    "test_type": assessment.test_type,
                })

        return recommendations

    def _build_search_query(self, messages: list[dict]) -> str:
        """Build a focused search query from conversation context."""
        # Gather all user messages for context
        user_parts = []
        for msg in messages:
            if msg.get("role") == "user":
                user_parts.append(msg.get("content", ""))

        # Use last 3 user messages max for relevance
        recent = user_parts[-3:]
        return " ".join(recent)

    def _is_end_of_conversation(self, messages: list[dict], reply: str) -> bool:
        """Determine if the conversation should end."""
        if len(messages) < 3:
            return False

        last_msg = self._get_last_user_message(messages).lower().strip()

        # Strong confirmation signals
        end_phrases = [
            "confirmed", "locking it in", "lock it in",
            "that's what we need", "final list", "final battery",
            "that covers it", "keep the shortlist",
        ]
        if any(phrase in last_msg for phrase in end_phrases):
            return True

        # Weaker signals — only if conversation is long enough and has recommendations
        if len(messages) >= 5:
            weak_signals = ["perfect", "that works", "thanks", "thank you", "sounds good"]
            if any(signal in last_msg for signal in weak_signals):
                # Check if the previous assistant message had recommendations
                for msg in reversed(messages[:-1]):
                    if msg.get("role") == "assistant":
                        return True
                    break

        # Hard limit
        if len(messages) >= 14:
            return True

        return False
