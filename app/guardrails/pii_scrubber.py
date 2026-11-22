"""Regex-first redaction, with optional local Presidio recognizers (no NLP download).

The returned map describes placeholder TYPES only. It cannot recover originals.
"""

import ipaddress
import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ScrubbedText:
    text: str
    redaction_map: dict[str, str]


PATTERNS = [
    ("PRIVATE_KEY", r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----"),
    ("AWS_KEY", r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    (
        "SECRET",
        r"(?i)\b(?:password|passwd|pwd|secret|aws_secret_access_key|api[_-]?key|token)"
        r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
    ),
    ("BEARER", r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    ("EMAIL", r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ("IPV6", r"(?<![\w:])(?:[A-Fa-f0-9]{0,4}:){2,}[A-Fa-f0-9:.]*(?:%[\w]+)?"),
    ("IPV4", r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"),
]


@lru_cache(maxsize=1)
def presidio_analyzer():
    # No spaCy model is required: NLP is deliberately disabled for these patterns.
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpArtifacts, NlpEngine

    class PatternOnlyEngine(NlpEngine):
        def load(self):
            pass

        def is_loaded(self):
            return True

        def process_text(self, text, language):
            return NlpArtifacts([], [], [], [], None, language)

        def process_batch(self, texts, language, **kwargs):
            for text in texts:
                yield text, self.process_text(text, language)

        def is_stopword(self, word, language):
            return False

        def is_punct(self, word, language):
            return False

        def get_supported_entities(self):
            return []

        def get_supported_languages(self):
            return ["en"]

    registry = RecognizerRegistry()
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            patterns=[Pattern("phone", r"(?<!\w)(?:\+1[ -]?)?\(?\d{3}\)?[ -]\d{3}[ -]\d{4}\b", 0.8)],
        )
    )
    return AnalyzerEngine(nlp_engine=PatternOnlyEngine(), registry=registry)


def scrub(text: str, use_presidio: bool = True) -> ScrubbedText:
    redactions = {}

    def replace(kind, match):
        value = match.group()
        if kind in {"IPV4", "IPV6"}:
            try:
                ipaddress.ip_address(value.split("%")[0])
            except ValueError:
                return value
        placeholder = f"[REDACTED_{kind}_{len(redactions) + 1}]"
        redactions[placeholder] = kind
        return placeholder

    for kind, pattern in PATTERNS:
        text = re.sub(pattern, lambda match, kind=kind: replace(kind, match), text)
    if use_presidio:
        results = presidio_analyzer().analyze(text=text, language="en", entities=["PHONE_NUMBER"])
        for result in sorted(results, key=lambda item: item.start, reverse=True):
            placeholder = f"[REDACTED_PHONE_{len(redactions) + 1}]"
            redactions[placeholder] = "PHONE_NUMBER"
            text = text[: result.start] + placeholder + text[result.end :]
    return ScrubbedText(text, redactions)
