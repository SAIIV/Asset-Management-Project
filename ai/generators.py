"""AI gateway: the TextGenerator adapter (Design Document 3.3 and 10.3, decision AD-2).

    get_generator().generate(task, facts, schema, time_limit) -> dict matching schema

Used by the features that need a language model (AI #5 report summary; photo
and PDF classification later). Which provider runs is chosen by one setting,
AI_TEXT_PROVIDER in .env. The provider is still being decided, so the only
version so far is "off", which always reports the service as unavailable and
lets every caller show its "AI down" state. A provider class (OpenAI, Claude or
a local model) is added here once it is chosen; callers do not change.
"""

from django.conf import settings


class AIUnavailable(Exception):
    """The text-generation service cannot be used right now."""


class TextGenerator:
    name = ""

    def generate(self, task, facts, schema, time_limit):
        """Return JSON (a dict) that matches schema. facts are data, never instructions."""
        raise NotImplementedError


class DisabledGenerator(TextGenerator):
    name = "off"

    def generate(self, task, facts, schema, time_limit):
        raise AIUnavailable("no text-generation provider is configured (AI_TEXT_PROVIDER=off)")


GENERATORS = {"off": DisabledGenerator}


def get_generator():
    provider = str(getattr(settings, "AI_TEXT_PROVIDER", "off")).lower()
    if provider not in GENERATORS:
        raise AIUnavailable(f"unknown AI_TEXT_PROVIDER '{provider}'")
    return GENERATORS[provider]()
