import re

# ========== BUZZWORD FILTER ==========

# Words that indicate corporate fluff rather than concrete information
BUZZWORDS = [
    "dynamic", "synergy", "rockstar", "ninja", "guru", "fast-paced",
    "passion", "passionate", "family", "culture", "tight-knit",
    "game-changer", "disruptive", "innovative", "cutting-edge",
    "world-class", "best-in-class", "competitive salary", "great benefits"
]

# Sentence starters that typically indicate real responsibilities
RESPONSIBILITY_STARTERS = [
    "you will", "responsible for", "the role involves", "responsibilities include",
    "key duties", "this position", "the candidate will", "you'll be",
    "we are looking for", "we need", "required to", "expected to"
]

# ========== SUMMARIZATION LOGIC ==========

def calculate_buzzword_density(sentence):
    """
    Returns the ratio of buzzwords to total words in a sentence.
    Higher density = more fluff.
    """
    words = sentence.lower().split()
    if not words:
        return 0
    
    buzz_count = sum(1 for word in words if any(buzz in word for buzz in BUZZWORDS))
    return buzz_count / len(words)


def is_responsibility_sentence(sentence):
    """
    Checks if sentence starts with a responsibility indicator.
    """
    sentence_lower = sentence.strip().lower()
    return any(sentence_lower.startswith(starter) for starter in RESPONSIBILITY_STARTERS)


def generate_noise_free_summary(text, max_sentences=2):
    """
    Generates a concise summary by filtering out buzzword-heavy sentences
    and prioritizing concrete responsibility statements.
    
    Args:
        text: Job description text
        max_sentences: How many sentences to return (default: 2)
    
    Returns:
        String containing the summary (or empty string if text is too short)
    """
    if not text or len(text) < 100:
        return None
    
    # Split into sentences
    sentences = re.split(r'[.!?]\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]  # Filter very short ones
    
    # Score each sentence
    scored_sentences = []
    for sent in sentences:
        score = 0
        
        # Penalty for high buzzword density
        buzz_density = calculate_buzzword_density(sent)
        score -= buzz_density * 10
        
        # Bonus for responsibility indicators
        if is_responsibility_sentence(sent):
            score += 5
        
        # Bonus for length (but not too long)
        word_count = len(sent.split())
        if 10 <= word_count <= 30:
            score += 2
        
        scored_sentences.append((score, sent))
    
    # Sort by score (highest first) and take top N
    scored_sentences.sort(reverse=True)
    top_sentences = [sent for score, sent in scored_sentences[:max_sentences]]
    
    # Return as single string
    summary = ". ".join(top_sentences)
    return summary + "." if summary and not summary.endswith(".") else summary or None
