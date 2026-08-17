"""
llm_extract.py
Sends the uploaded bill file(s) (PDF and/or images) + claimant info to an
LLM (Google Gemini today, Anthropic Claude optionally) and returns the
structured claim JSON described in prompts.py.

Both providers are wired up already - switch via the PROVIDER secret.
See README.md "Switching / adding providers" section.
"""

from __future__ import annotations
import base64
import json
import re
from typing import Optional

from .prompts import EXTRACTION_SYSTEM_PROMPT, build_user_prompt


class ExtractionError(Exception):
    pass


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*|^```\s*|```$", "", text, flags=re.MULTILINE)
    return text.strip()


def _parse_json(text: str) -> dict:
    cleaned = _strip_json_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise ExtractionError(f"Model did not return valid JSON: {e}\n---\n{cleaned[:800]}")


# ----------------------------------------------------------------------
# Gemini
# ----------------------------------------------------------------------
def extract_with_gemini(files: list[dict], claimant_info: dict,
                         special_instructions: str, api_key: str,
                         model_name: str = "gemini-2.5-pro") -> dict:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name, system_instruction=EXTRACTION_SYSTEM_PROMPT)

    user_prompt = build_user_prompt(claimant_info, special_instructions)
    parts = [user_prompt] + [{"mime_type": f["mime_type"], "data": f["bytes"]} for f in files]

    response = model.generate_content(
        parts,
        generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
    )
    if not response.candidates:
        raise ExtractionError("Gemini returned no candidates (bill may have been blocked by safety filters).")
    return _parse_json(response.text)


# ----------------------------------------------------------------------
# Claude (optional - wired up for when you add an Anthropic key)
# ----------------------------------------------------------------------
def extract_with_claude(files: list[dict], claimant_info: dict,
                         special_instructions: str, api_key: str,
                         model_name: str = "claude-sonnet-4-6") -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(claimant_info, special_instructions)

    content = []
    for f in files:
        b64 = base64.standard_b64encode(f["bytes"]).decode("utf-8")
        if f["mime_type"] == "application/pdf":
            content.append({"type": "document", "source": {"type": "base64",
                                                             "media_type": "application/pdf", "data": b64}})
        else:
            content.append({"type": "image", "source": {"type": "base64",
                                                          "media_type": f["mime_type"], "data": b64}})
    content.append({"type": "text", "text": user_prompt})

    message = client.messages.create(
        model=model_name,
        max_tokens=8000,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    return _parse_json(text)


# ----------------------------------------------------------------------
# Dispatcher
# ----------------------------------------------------------------------
def extract_claim(files: list[dict], claimant_info: dict, special_instructions: str,
                   provider: str, api_key: str, model_name: Optional[str] = None) -> dict:
    if not api_key:
        raise ExtractionError(f"No API key configured for provider '{provider}'.")
    if not files:
        raise ExtractionError("No files provided for extraction.")

    if provider == "gemini":
        return extract_with_gemini(files, claimant_info, special_instructions,
                                    api_key, model_name or "gemini-2.5-pro")
    elif provider == "claude":
        return extract_with_claude(files, claimant_info, special_instructions,
                                    api_key, model_name or "claude-sonnet-4-6")
    else:
        raise ExtractionError(f"Unknown provider: {provider}")
