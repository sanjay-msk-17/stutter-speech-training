"""
sentences.py - Dynamic practice sentence generator for speech therapy sessions.
Generates non-repeating sentences per session focusing on vowel stretching,
controlled speech, and smooth breathing.
"""
import random

# Categorized sentence pools
VOWEL_STRETCHING = [
    "Open your mouth wide and say 'aaah' slowly and smoothly.",
    "Ease into each word — especially the vowels — like a gentle wave.",
    "Every evening, Amy eats oranges outside under umbrella trees.",
    "Ants eat all oranges and apples on each available afternoon.",
    "All aardvarks often use open arenas in autumn evenings.",
    "Over and over, old owls hoot on orange trees at noon.",
    "Ursula eagerly ordered eight avocados on open aisles today.",
    "Eagles orbit over icy oceans each afternoon until evening.",
    "Anna and Eve often eat apples in August under elms.",
    "Only one ounce of orange oil is ever enough for you.",
]

CONTROLLED_SPEECH = [
    "Take a slow, steady breath before each sentence you speak.",
    "Speak softly, smoothly, and with steady rhythm throughout.",
    "Slow your speech — let each word land clearly and calmly.",
    "Pause between phrases to breathe and reset your flow.",
    "Speak like water flowing — smooth, constant and unhurried.",
    "Each word is a step — take it gently and deliberately.",
    "Breathe in, then speak. Let the air carry your voice forward.",
    "Begin each sentence with calm confidence and steady pace.",
    "Let your words flow naturally, without rushing or forcing.",
    "Focus on one word at a time — each one matters equally.",
]

SMOOTH_BREATHING = [
    "Breathe in for four counts, hold for two, out for six.",
    "Exhale gently before you begin — this helps your voice flow.",
    "Inhale through your nose, speak on the exhale slowly.",
    "Let your breath lead your speech — never the other way around.",
    "Three slow breathbreaths before you start each speaking exercise.",
    "Your breath is your anchor — deep, steady, and controlled.",
    "Feel your belly rise as you inhale and fall as you speak.",
    "Take one calming breath before joining every conversation.",
    "Breathe out tension, breathe in calm confidence and clarity.",
    "Breathing slowly and deeply helps your voice stay strong.",
]

ALL_SENTENCES = VOWEL_STRETCHING + CONTROLLED_SPEECH + SMOOTH_BREATHING

_session_used: dict[str, set] = {}


def get_practice_sentences(user_id: str, count: int = 3) -> list[dict]:
    """
    Return `count` non-repeating sentences for the session.
    Resets after all sentences have been used for a user.
    """
    used = _session_used.get(user_id, set())
    available = [s for s in ALL_SENTENCES if s not in used]

    if len(available) < count:
        # Reset the used pool
        _session_used[user_id] = set()
        available = ALL_SENTENCES[:]

    chosen = random.sample(available, min(count, len(available)))
    _session_used.setdefault(user_id, set()).update(chosen)

    # Categorize each sentence
    result = []
    for sentence in chosen:
        if sentence in VOWEL_STRETCHING:
            category = "Vowel Stretching"
            icon = "🗣️"
        elif sentence in CONTROLLED_SPEECH:
            category = "Controlled Speech"
            icon = "🎯"
        else:
            category = "Smooth Breathing"
            icon = "🌬️"
        result.append({"sentence": sentence, "category": category, "icon": icon})

    return result
