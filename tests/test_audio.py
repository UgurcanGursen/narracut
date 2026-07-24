import pytest
from v2.audio_engine import find_cue_time

def create_mock_words(text):
    words = text.split()
    return [{"word": w, "start": i, "end": i+1, "orig_word": w} for i, w in enumerate(words)]

def test_find_cue_time_swap_words():
    # Adversarial test: Swapping key nouns
    target_words = create_mock_words("Revenue fell while software grew")
    
    # Correct order
    res_correct = find_cue_time(target_words, "Revenue fell while software grew")
    assert res_correct["score"] > 0.8
    
    # Swapped order
    res_swapped = find_cue_time(target_words, "Software fell while revenue grew")
    assert res_swapped["score"] < 0.7  # Penalized by SequenceMatcher

def test_find_cue_time_negation():
    # Adversarial test: Negation injection
    target_words = create_mock_words("The company moved quickly but not enough")
    
    # Correct
    res_correct = find_cue_time(target_words, "The company moved quickly but not enough")
    assert res_correct["score"] > 0.8
    
    # Mismatch negation
    res_negated = find_cue_time(target_words, "The company did not move quickly enough")
    assert res_negated["score"] < 0.6  # Heavy negation penalty

def test_find_cue_time_numbers():
    # Adversarial test: Semantic number injection
    target_words = create_mock_words("Revenue was seventeen point two billion")
    
    # Correct
    res_correct = find_cue_time(target_words, "Revenue was seventeen point two billion")
    assert res_correct["score"] > 0.8
    
    # Mismatch numbers
    res_wrong_num = find_cue_time(target_words, "Revenue was seventy-two billion")
    assert res_wrong_num["score"] < 0.6  # Heavy semantic number penalty
