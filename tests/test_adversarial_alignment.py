import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v2.audio_engine import find_cue_time

def _make_mock_words(text):
    words = []
    current_time = 0.0
    for w in text.split():
        words.append({
            "word": w,
            "start": current_time,
            "end": current_time + 0.5
        })
        current_time += 0.5
    return words

def test_swapped_order():
    words = _make_mock_words("I want to buy the red car today")
    cue = "car red" # Swapped
    res = find_cue_time(words, cue)
    
    # Due to order penalty / DP alignment, confidence should be lower than a perfect match.
    # Actually, DP with order enforcement might match only one word or heavily penalize.
    assert res["score"] < 0.85
    
def test_negation_mismatch():
    words = _make_mock_words("I am not going to do that")
    cue = "am going" # Missing negation
    res = find_cue_time(words, cue)
    
    print("NEGATION RES:", res)
    assert res["score"] < 0.85
    # The algorithm will drop 'am' to avoid the negation penalty, resulting in low token similarity
    assert res["details"]["token_similarity"] < 1.0

def test_numeric_mismatch():
    words = _make_mock_words("The company made seventeen billion dollars")
    cue = "sixteen billion"
    res = find_cue_time(words, cue)
    
    print("NUMERIC RES:", res)
    assert res["score"] < 0.85
    # The algorithm will drop 'sixteen/seventeen' to avoid the numeric penalty
    assert res["details"]["token_similarity"] < 1.0

def test_numeric_equivalent():
    words = _make_mock_words("The company made 17 billion dollars")
    cue = "seventeen billion"
    res = find_cue_time(words, cue)
    
    assert res["score"] > 0.85
    assert res["details"]["semantic_number_score"] == 1.0


def test_numeric_equivalent_unqualified_cue_matches_currency_token():
    words = _make_mock_words("Revenue was 17 dollars")
    res = find_cue_time(words, "Revenue was seventeen")

    assert res["time"] == 0.0
    assert res["score"] > 0.85
    assert res["details"]["semantic_number_score"] == 1.0


def test_numeric_equivalent_ignores_punctuation():
    words = _make_mock_words("Revenue was 17 billion.")
    res = find_cue_time(words, "Revenue was seventeen billion!")

    assert res["time"] == 0.0
    assert res["score"] > 0.85


def test_numeric_different_value_does_not_match():
    words = _make_mock_words("Revenue was 70 billion")
    res = find_cue_time(words, "Revenue was seventeen billion")

    assert res["score"] == 0.0
    assert res["details"]["semantic_number_score"] == 0.0


def test_numeric_decimal_does_not_match_integer():
    words = _make_mock_words("Revenue was 17.5 billion")
    res = find_cue_time(words, "Revenue was seventeen billion")

    assert res["score"] == 0.0
    assert res["details"]["semantic_number_score"] == 0.0


def test_numeric_different_explicit_currencies_do_not_match():
    words = _make_mock_words("Revenue was 17 dollars")
    res = find_cue_time(words, "Revenue was seventeen euros")

    assert res["score"] == 0.0
    assert res["details"]["semantic_number_score"] == 0.0


def test_numeric_equivalent_uses_surrounding_context_for_time():
    words = _make_mock_words("Revenue was 17 billion. Costs were 17 billion.")
    res = find_cue_time(words, "Costs were seventeen billion")

    assert res["time"] == 2.0
    assert res["matched_text"] == "Costs were 17 billion."
    assert res["score"] > 0.85

def test_ambiguity_margin_overlapping():
    words = _make_mock_words("this is a test this is a test this is a test")
    cue = "this is a test"
    res = find_cue_time(words, cue)
    
    # Should have identical candidates at different times, so margin is very small (only differs by position_score)
    assert res["ambiguity_margin"] < 0.10
