import pytest
from apps.api.app.services.embedding.search import cosine_similarity


def test_cosine_similarity_identical_vectors():
    vec1 = [0.5, 0.5, 0.5, 0.5]
    vec2 = [0.5, 0.5, 0.5, 0.5]
    score = cosine_similarity(vec1, vec2)
    assert pytest.approx(score, 0.001) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    score = cosine_similarity(vec1, vec2)
    assert score == 0.0


def test_cosine_similarity_empty_or_zero_vector():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0  # length mismatch


def test_cosine_similarity_bounded_between_zero_and_one():
    # Opposite direction
    vec1 = [1.0, 0.0]
    vec2 = [-1.0, 0.0]
    score = cosine_similarity(vec1, vec2)
    assert 0.0 <= score <= 1.0
