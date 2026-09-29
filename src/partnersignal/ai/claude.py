"""Claude engine: the same two tasks as the local engine, answered by the Anthropic API.

Structured outputs (`messages.parse` with a Pydantic model) guarantee the response matches
the schema the UI renders. The prompts restrict the model to evidence in the notes and
tell it that every draft is reviewed by a person before anything is sent.
"""

from __future__ import annotations

import json

import anthropic

from ..catalog import BANT_LEVELS, PRACTICES, SERVICES
from .local import OutreachContext
from .schemas import DiscoveryExtraction, OutreachDraft

CATALOG = "\n".join(f"- {s.key} ({PRACTICES[s.practice]}): {s.name}. {s.summary}" for s in SERVICES)

DISCOVERY_SYSTEM = f"""You help a professional-services associate at an IT distributor turn raw notes
from a call with a reseller partner into a structured qualification record.

Rules:
- Use only what the notes say. Every quote must be copied verbatim from the notes. If something was
  not discussed, mark it "unknown" with an empty quote and list it under missing_information.
- BANT levels: {json.dumps(BANT_LEVELS)}. "confirmed" budget means money is approved, not just mentioned.
  "decision_maker" means the person who approves the spend is named or engaged.
- Recommend at most three practices, strongest first, choosing service keys from this catalog:
{CATALOG}
- Follow-up questions should be open, specific to these notes, and help close the missing BANT gaps.
- next_step is one concrete action for the associate, not the customer.
- The associate reviews your output before anything is saved. Do not invent names, numbers or dates."""

OUTREACH_SYSTEM = f"""You draft short outreach e-mails from a professional-services associate at an IT
distributor to a reseller partner contact. The associate edits and sends the e-mail themselves.

Write like a thoughtful early-career business developer: plain language, specific to the context
given, under 140 words in the body, one clear ask, no hype, no invented facts, no pricing promises.
Sign off with the sender's first name. In `personalization`, list each line that depends on the
record and say which field it came from. In `review_checklist`, list what the sender must verify.
Services you may reference:
{CATALOG}"""


class ClaudeEngine:
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key, timeout=90.0, max_retries=1)
        self.model = model

    def extract_discovery(self, notes: str, partner_context: str) -> DiscoveryExtraction:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=DISCOVERY_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": f"<partner>\n{partner_context}\n</partner>\n\n<call_notes>\n{notes}\n</call_notes>",
                }
            ],
            output_format=DiscoveryExtraction,
        )
        return _parsed(response, DiscoveryExtraction)

    def draft_outreach(self, ctx: OutreachContext) -> OutreachDraft:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=OUTREACH_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(ctx.__dict__, indent=2)}],
            output_format=OutreachDraft,
        )
        return _parsed(response, OutreachDraft)


class EngineUnavailable(RuntimeError):
    pass


def _parsed(response, model_type):
    if response.stop_reason == "refusal":
        raise EngineUnavailable("the model declined this request")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise EngineUnavailable("the model response was incomplete")
    if not isinstance(response.parsed_output, model_type):
        raise EngineUnavailable("unexpected response shape")
    return response.parsed_output
