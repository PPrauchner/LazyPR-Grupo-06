from core.transforms.normalizing import compute_text_metrics, TextMetrics

def test_compute_text_metrics_standard_text():
    """Tests standard text with words and spaces."""
    metrics = compute_text_metrics("Fixing a critical bug in the core module.")
    
    assert isinstance(metrics, TextMetrics)
    assert metrics.char_count == 41
    assert metrics.word_count == 8

def test_compute_text_metrics_empty_string():
    """Tests safety with empty strings (should return 0)."""
    metrics = compute_text_metrics("")
    
    assert metrics.char_count == 0
    assert metrics.word_count == 0

def test_compute_text_metrics_none_value():
    """Tests safety with None values (common in raw datasets)."""
    metrics = compute_text_metrics(None)
    
    assert metrics.char_count == 0
    assert metrics.word_count == 0

def test_compute_text_metrics_multiple_spaces_and_newlines():
    """Tests if split() correctly handles irregular spacing and newlines."""
    body = "This   PR\nfixes\n\t something"
    metrics = compute_text_metrics(body)
    
    assert metrics.char_count == 26
    assert metrics.word_count == 4