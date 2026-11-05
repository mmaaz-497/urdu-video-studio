import asyncio
import re

from agents import Agent, Runner, set_default_openai_key, set_tracing_disabled
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.services import moderation_service

logger = get_logger(__name__)

LLM_CALL_TIMEOUT_SECONDS = 20.0
WORDS_PER_5S_MAX = 12  # hard per-5s-scene ceiling; calibrated on real OmniVoice (research.md A9)
WORD_TARGET_RATIO = 0.92  # prompted target, leaving headroom under the hard ceiling

# corrected_idea must be ~100% Urdu script; this allows a couple of genuine
# brand/technical names (e.g. "OmniVoice") to stay in Latin letters.
ALLOWED_LATIN_WORDS_IN_IDEA = 2

_SENTENCE_END_CHARS = "۔.!?"
_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    if settings.OPENAI_API_KEY:
        set_default_openai_key(settings.OPENAI_API_KEY, use_for_tracing=False)
    set_tracing_disabled(True)
    _configured = True


class ScriptGenerationOutput(BaseModel):
    corrected_idea: str
    title: str
    urdu_script: str
    scenes: list[str]


def scene_count_for(duration_seconds: int) -> int:
    return duration_seconds // 5


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def word_count(text: str) -> int:
    return len(_words(text))


def word_limit_for(duration_seconds: int) -> int:
    return scene_count_for(duration_seconds) * WORDS_PER_5S_MAX


def _target_word_count(duration_seconds: int) -> int:
    return round(word_limit_for(duration_seconds) * WORD_TARGET_RATIO)


def _count_latin_words(text: str) -> int:
    """Counts words containing any Latin letter — used to catch corrected_idea
    left partly in Roman Urdu/English instead of fully transliterated."""
    return len([w for w in _words(text) if _LATIN_LETTER_RE.search(w)])


def _trim_to_sentence_boundary(text: str, limit: int) -> str:
    """Hard safety net: if the model is still over `limit` words after one
    retry, trim server-side so the Review screen never receives an
    unapprovable script (SC-003) — prefers cutting at the last sentence
    ending at-or-before the word limit over a mid-sentence word cut."""
    words = _words(text)
    if len(words) <= limit:
        return text.strip()

    truncated = " ".join(words[:limit])
    last_end = max((truncated.rfind(c) for c in _SENTENCE_END_CHARS), default=-1)
    if last_end > 0:
        candidate = truncated[: last_end + 1].strip()
        if word_count(candidate) >= 1:
            return candidate
    return truncated


# Phrases that mean "render this literal text/graphic on screen" — Wan 2.2
# renders text poorly and the narration is spoken Urdu, not displayed text,
# so these are stripped from scene prompts rather than trusted to the prompt
# instructions alone.
_TEXT_OVERLAY_KEYWORDS = re.compile(
    r"(overlay\s*text|on[- ]?screen\s*(?:caption|text)|caption|watermark|logo|subtitle|"
    r"title\s*card|label(?:s)?\b)",
    re.IGNORECASE,
)
_QUOTED_TEXT = re.compile(r"[\"“][^\"”]*[\"”]")


def _strip_text_overlay_requests(scene: str) -> str:
    scene = _QUOTED_TEXT.sub("", scene)
    clauses = re.split(r"(?<=[;.,])\s+", scene)
    kept = [c for c in clauses if c.strip() and not _TEXT_OVERLAY_KEYWORDS.search(c)]
    cleaned = " ".join(kept)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"^[;:,.\s]+|[;:,.\s]+$", "", cleaned).strip()
    return cleaned or "A simple visual demonstration of the idea."


def _build_agent(model: str) -> Agent:
    return Agent(
        name="UrduScriptWriter",
        instructions=(
            "You write short video scripts for Pakistani students making "
            "educational/explainer videos. The student's idea may be written in "
            "Roman Urdu, Urdu script, or English, and may contain spelling "
            "mistakes. Given the idea and a target duration:\n"
            "1. Rewrite the idea as `corrected_idea` ENTIRELY IN URDU SCRIPT "
            "(not Roman Urdu, not English) — if the student wrote in Roman "
            "Urdu or English, fully transliterate/translate it into Urdu "
            "letters, correcting spelling/grammar along the way. Do not leave "
            "any part of it in Latin letters. The only exception is a genuine "
            "brand or technical name with no established Urdu spelling (e.g. "
            "OmniVoice, YouTube) — keep these to an absolute minimum, ideally "
            "zero, and never more than one or two.\n"
            "2. Write a short, catchy `title` for the video, also entirely in "
            "Urdu script (same exception as above).\n"
            "3. Write a natural, grammatically correct narration script in "
            "proper Urdu script (not Roman Urdu) as `urdu_script`. The given "
            "word count is a HARD CEILING you must stay at or under, not a "
            "rough target — when in doubt, write shorter.\n"
            "4. Break the video into `scenes`: short English visual-description "
            "prompts (one per scene) suitable for an AI video generator, each "
            "describing only the visual action/subject on screen during that "
            "5-second segment. Scenes must NEVER request any on-screen text, "
            "captions, subtitles, overlays, title cards, logos, or watermarks — "
            "the video generator renders text poorly and the narration is "
            "spoken aloud in Urdu, not shown as text.\n"
            "Respond only via the structured output fields."
        ),
        output_type=ScriptGenerationOutput,
        model=model,
    )


async def _run_once(
    idea: str, duration_seconds: int, feedback: str | None = None
) -> ScriptGenerationOutput:
    _ensure_configured()
    settings = get_settings()
    agent = _build_agent(settings.OPENAI_MODEL)
    scene_count = scene_count_for(duration_seconds)
    hard_limit = word_limit_for(duration_seconds)
    target_words = _target_word_count(duration_seconds)
    prompt = (
        f"Student idea: {idea}\n"
        f"Target video duration: {duration_seconds} seconds "
        f"({scene_count} scene(s) of 5 seconds each).\n"
        f"`corrected_idea` MUST be written entirely in Urdu script (no Roman "
        f"Urdu/English words) except at most {ALLOWED_LATIN_WORDS_IN_IDEA} genuine "
        f"brand/technical name(s).\n"
        f"Write exactly {scene_count} scene(s) in `scenes`, with no on-screen "
        f"text/captions/subtitles/overlays/title cards/logos/watermarks requested "
        f"in any scene.\n"
        f"The `urdu_script` MUST be at most {hard_limit} words total (hard limit) — "
        f"aim for about {target_words} words."
    )
    if feedback:
        prompt += f"\n\n{feedback}"
    try:
        result = await asyncio.wait_for(
            Runner.run(agent, prompt), timeout=LLM_CALL_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        logger.error("llm_call_timed_out")
        raise AppError(
            "SCRIPT_GENERATION_FAILED", "Couldn't generate a script. Please try again."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - any SDK/network error surfaces as a friendly error
        logger.error("llm_call_failed", exc_info=exc)
        raise AppError(
            "SCRIPT_GENERATION_FAILED", "Couldn't generate a script. Please try again."
        ) from exc
    return result.final_output


async def generate_script(idea: str, duration_seconds: int) -> ScriptGenerationOutput:
    """Moderates the idea, then generates a script that is GUARANTEED to fit
    the hard scene-count/word-count limits and be fully Urdu-script before
    returning (SC-003): retries once with explicit feedback naming the
    overage/mixed-script issue, then trims server-side at a sentence boundary
    if still over the word limit — the Review screen must never receive an
    unapprovable script."""
    await moderation_service.check_idea(idea)

    required_scenes = scene_count_for(duration_seconds)
    hard_limit = word_limit_for(duration_seconds)

    output = await _run_once(idea, duration_seconds)
    wc = word_count(output.urdu_script)
    scenes_ok = len(output.scenes) == required_scenes
    idea_ok = _count_latin_words(output.corrected_idea) <= ALLOWED_LATIN_WORDS_IN_IDEA

    if not scenes_ok or wc > hard_limit or not idea_ok:
        logger.warning(
            "llm_output_invalid_retrying",
            extra={
                "word_count": wc,
                "hard_limit": hard_limit,
                "scenes_ok": scenes_ok,
                "idea_ok": idea_ok,
            },
        )
        feedback_parts = []
        if wc > hard_limit:
            feedback_parts.append(
                f"Your previous urdu_script was {wc} words — over the hard limit of "
                f"{hard_limit} words. Rewrite it shorter, at or under {hard_limit} words "
                f"(aim for about {_target_word_count(duration_seconds)})."
            )
        if not scenes_ok:
            feedback_parts.append(
                f"You wrote {len(output.scenes)} scene(s); write exactly {required_scenes}."
            )
        if not idea_ok:
            feedback_parts.append(
                f"Your previous corrected_idea mixed in Latin-script (Roman Urdu/English) "
                f'words: "{output.corrected_idea}". corrected_idea MUST be written entirely '
                f"in Urdu script — transliterate every Roman Urdu/English word into Urdu "
                f"letters. Only a genuine brand/technical name with no established Urdu "
                f"spelling may stay in Latin letters, and never more than "
                f"{ALLOWED_LATIN_WORDS_IN_IDEA}."
            )
        output = await _run_once(idea, duration_seconds, feedback=" ".join(feedback_parts))
        wc = word_count(output.urdu_script)
        scenes_ok = len(output.scenes) == required_scenes
        idea_ok = _count_latin_words(output.corrected_idea) <= ALLOWED_LATIN_WORDS_IN_IDEA

    if not scenes_ok or not idea_ok:
        raise AppError("SCRIPT_GENERATION_FAILED", "Couldn't generate a script. Please try again.")

    if wc > hard_limit:
        logger.warning(
            "llm_output_trimmed_server_side", extra={"word_count": wc, "hard_limit": hard_limit}
        )
        output.urdu_script = _trim_to_sentence_boundary(output.urdu_script, hard_limit)

    output.scenes = [_strip_text_overlay_requests(s) for s in output.scenes]
    return output
