import pytest
from app.services import extract_citations

def test_extract_citations():
    answer = "The main concept is photosynthesis [SOURCE_1]. It requires sunlight [SOURCE_2]."
    chunks = [
        {"summary_id": "s1", "title": "T1", "source": "youtube", "chunk_text": "text1", "relevance_score": 0.9},
        {"summary_id": "s2", "title": "T2", "source": "pdf", "chunk_text": "text2", "relevance_score": 0.8}
    ]
    
    citations = extract_citations(answer, chunks)
    assert len(citations) == 2
    assert citations[0]["source_title"] == "T1"
    assert citations[1]["source_title"] == "T2"

def test_extract_citations_invalid_index():
    answer = "Concept [SOURCE_99]."
    chunks = [{"summary_id": "s1", "title": "T1", "source": "youtube", "chunk_text": "text1", "relevance_score": 0.9}]
    
    citations = extract_citations(answer, chunks)
    assert len(citations) == 0
