import json
import re
from pydantic import ValidationError
from .llm import complete_json
from .schemas import Mandate

SYSTEM = """Convert the user's shopping request into JSON matching this schema:
{"item": str, "max_total": number|null, "currency": str, "min_rating": number|null,
 "max_delivery_days": int|null, "blocked_merchants": [str], "auto_approve_under": number}
Rules:
- Output ONLY JSON, no prose, no markdown fences.
- If the user did not state a budget, set max_total to null. NEVER guess or invent a number.
- Never invent limits the user did not state.
- auto_approve_under is 0 unless the user explicitly states an auto-buy amount."""

def _strip_fences(raw: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())

def _numbers_in(text: str) -> set[float]:
    return {float(n) for n in re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))}

def check_grounded(m: Mandate, text: str) -> None:
    """Paisa wali values user ke text mein maujood honi chahiye."""
    nums = _numbers_in(text)
    if m.max_total not in nums:
        raise ValueError(
            "Budget not clearly stated in your request. Please include a maximum amount."
        )
    if m.auto_approve_under and m.auto_approve_under not in nums:
        raise ValueError("Auto-buy amount not found in your request.")

def parse_mandate(text: str, retries: int = 1) -> Mandate:
    prompt = text
    last_err = None
    mandate = None
    for _ in range(retries + 1):
        try:
            raw = complete_json(SYSTEM, prompt)
        except Exception:
            raise RuntimeError("The AI service is busy. Please try again in a minute.")
        try:
            mandate = Mandate.model_validate(json.loads(_strip_fences(raw)))
            break
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = e
            prompt = f"{text}\n\nYour previous output was invalid ({e}). Return only valid JSON."

    if mandate is None:
        if "max_total" in str(last_err):
            raise ValueError(
                "Budget not clearly stated in your request. Please include a maximum amount."
            )
        raise ValueError("Could not understand your request. Please rephrase it.")

    check_grounded(mandate, text)   # LLM par bharosa nahi, code se verify
    return mandate