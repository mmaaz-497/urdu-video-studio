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
# Each scene's narration is spoken by TTS, which mispronounces Roman Urdu, so it gets a
# tighter allowance (one brand/technical name per scene at most).
ALLOWED_LATIN_WORDS_IN_NARRATION = 1

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


class SceneOutput(BaseModel):
    visual_prompt: str  # English, for Wan 2.2; depicts exactly what narration_ur says
    narration_ur: str  # Urdu script, <= WORDS_PER_5S_MAX words; says what this scene shows


class ScriptGenerationOutput(BaseModel):
    corrected_idea: str
    title: str
    scenes: list[SceneOutput]

    @property
    def urdu_script(self) -> str:
        """Joined narrations, kept for display / backward compatibility only."""
        return " ".join(n for n in (sc.narration_ur.strip() for sc in self.scenes) if n)


def scene_count_for(duration_seconds: int) -> int:
    return duration_seconds // 5


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def word_count(text: str) -> int:
    return len(_words(text))


def word_limit_for(duration_seconds: int) -> int:
    return scene_count_for(duration_seconds) * WORDS_PER_5S_MAX


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
            "You write short explainer videos for Pakistani students. The student's "
            "idea may be written in Roman Urdu, Urdu script, or English, and may "
            "contain spelling mistakes. Given the idea and a target duration:\n"
            "1. Rewrite the idea as `corrected_idea` ENTIRELY IN URDU SCRIPT "
            "(not Roman Urdu, not English) — if the student wrote in Roman "
            "Urdu or English, fully transliterate/translate it into Urdu "
            "letters, correcting spelling/grammar along the way. Do not leave "
            "any part of it in Latin letters. The only exception is a genuine "
            "brand or technical name with no established Urdu spelling (e.g. "
            "OmniVoice, YouTube) — keep these to an absolute minimum, ideally "
            "zero, and never more than one or two.\n"
            "2. Write a short, catchy `title`, also entirely in Urdu script "
            "(same exception as above).\n"
            "3. Write `scenes`: one entry per 5-second segment, in story order. "
            "EVERY scene has two fields that you write TOGETHER, as one moment:\n"
            "   - `visual_prompt`: an English description for an AI video generator "
            "of exactly what the viewer sees in these 5 seconds (concrete subject, "
            "action, setting, camera). It must depict precisely what that scene's "
            "`narration_ur` says — nothing the narration does not mention, and "
            "nothing in the narration that cannot be seen.\n"
            "   - `narration_ur`: the Urdu voice-over for that same scene, in "
            "proper Urdu script (never Roman Urdu), simple spoken Urdu, PRESENT "
            "TENSE, describing what is visible right now (for example: 'ایک بچہ "
            "کتاب کھولتا ہے'). The word count given is a HARD CEILING per scene — "
            "when in doubt, write shorter. Each narration is spoken on its own over "
            "its own clip, so it must make sense for that clip alone.\n"
            "Read in order, the narrations must still tell the student's idea as a "
            "story (opening, middle, close) — do not write a separate explanation "
            "unrelated to the pictures.\n"
            "Visual prompts must NEVER request any on-screen text, captions, "
            "subtitles, overlays, title cards, logos, labels, or watermarks — the "
            "video generator renders text poorly and the words are spoken aloud, "
            "not shown.\n"
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
    target_words = _target_scene_words()
    prompt = (
        f"Student idea: {idea}\n"
        f"Target video duration: {duration_seconds} seconds "
        f"({scene_count} scene(s) of 5 seconds each).\n"
        f"`corrected_idea` MUST be written entirely in Urdu script (no Roman "
        f"Urdu/English words) except at most {ALLOWED_LATIN_WORDS_IN_IDEA} genuine "
        f"brand/technical name(s).\n"
        f"Write exactly {scene_count} scene(s) in `scenes`. In each scene, "
        f"`narration_ur` MUST be at most {WORDS_PER_5S_MAX} words (hard limit, per "
        f"scene) — aim for about {target_words} — and must describe what that same "
        f"scene's `visual_prompt` shows. No scene may request on-screen "
        f"text/captions/subtitles/overlays/title cards/logos/watermarks."
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


def _target_scene_words() -> int:
    return round(WORDS_PER_5S_MAX * WORD_TARGET_RATIO)


class _Findings:
    """Per-scene validation result: `retry_feedback` drives the one retry; `hard_failures`
    are what may not survive it (the trim only fixes over-limit narrations)."""

    def __init__(self) -> None:
        self.retry_feedback: list[str] = []
        self.hard_failures: list[str] = []
        self.over_limit_scenes: list[int] = []


def _check(output: ScriptGenerationOutput, required_scenes: int) -> _Findings:
    f = _Findings()
    if len(output.scenes) != required_scenes:
        msg = f"You wrote {len(output.scenes)} scene(s); write exactly {required_scenes}."
        f.retry_feedback.append(msg)
        f.hard_failures.append("scene_count")
    if _count_latin_words(output.corrected_idea) > ALLOWED_LATIN_WORDS_IN_IDEA:
        f.retry_feedback.append(
            f"Your previous corrected_idea mixed in Latin-script (Roman Urdu/English) "
            f'words: "{output.corrected_idea}". corrected_idea MUST be written entirely '
            f"in Urdu script — transliterate every Roman Urdu/English word into Urdu "
            f"letters. Only a genuine brand/technical name with no established Urdu "
            f"spelling may stay in Latin letters, and never more than "
            f"{ALLOWED_LATIN_WORDS_IN_IDEA}."
        )
        f.hard_failures.append("idea_latin")
    for i, scene in enumerate(output.scenes, start=1):
        wc = word_count(scene.narration_ur)
        if wc == 0:
            f.retry_feedback.append(f"Scene {i} has an empty narration_ur; write it.")
            f.hard_failures.append(f"scene_{i}_empty")
        elif wc > WORDS_PER_5S_MAX:
            f.retry_feedback.append(
                f"Scene {i}'s narration_ur was {wc} words — over the hard limit of "
                f"{WORDS_PER_5S_MAX} words per scene. Rewrite it shorter (aim for about "
                f"{_target_scene_words()}), still describing what that scene's "
                f"visual_prompt shows."
            )
            f.over_limit_scenes.append(i - 1)
        if _count_latin_words(scene.narration_ur) > ALLOWED_LATIN_WORDS_IN_NARRATION:
            f.retry_feedback.append(
                f'Scene {i}\'s narration_ur contains Latin-script (Roman Urdu/English) words: '
                f'"{scene.narration_ur}". Narration MUST be entirely in Urdu script.'
            )
            f.hard_failures.append(f"scene_{i}_latin")
    return f


async def generate_script(idea: str, duration_seconds: int) -> ScriptGenerationOutput:
    """Moderates the idea, then generates scenes (visual prompt + Urdu narration written
    together) that are GUARANTEED to fit the hard limits before returning (SC-003): checks
    scene count, per-scene word limit and Urdu-script-only text, retries once with feedback
    naming exactly what was wrong, then trims any still-over-limit narration server-side at a
    sentence boundary — the Review screen must never receive an unapprovable script."""
    await moderation_service.check_idea(idea)

    required_scenes = scene_count_for(duration_seconds)

    output = await _run_once(idea, duration_seconds)
    findings = _check(output, required_scenes)

    if findings.retry_feedback:
        logger.warning(
            "llm_output_invalid_retrying",
            extra={
                "over_limit_scenes": [i + 1 for i in findings.over_limit_scenes],
                "hard_failures": findings.hard_failures,
            },
        )
        output = await _run_once(
            idea, duration_seconds, feedback=" ".join(findings.retry_feedback)
        )
        findings = _check(output, required_scenes)

    if findings.hard_failures:
        logger.error("llm_output_invalid_after_retry", extra={"failures": findings.hard_failures})
        raise AppError("SCRIPT_GENERATION_FAILED", "Couldn't generate a script. Please try again.")

    for i in findings.over_limit_scenes:
        scene = output.scenes[i]
        logger.warning(
            "llm_scene_trimmed_server_side",
            extra={"scene": i + 1, "word_count": word_count(scene.narration_ur)},
        )
        scene.narration_ur = _trim_to_sentence_boundary(scene.narration_ur, WORDS_PER_5S_MAX)

    for scene in output.scenes:
        scene.visual_prompt = _strip_text_overlay_requests(scene.visual_prompt)
        scene.narration_ur = scene.narration_ur.strip()
    return output
