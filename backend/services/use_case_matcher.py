"""
Use Case Matcher Service

Provides functionality to match user input text against available use cases,
detect protocol mismatches, and suggest appropriate use cases.
"""

from typing import List, Dict, Optional, Set
import re
from dataclasses import dataclass

from db.models import UseCase


@dataclass
class UseCaseMatch:
    """Represents a matched use case with confidence score"""
    use_case: UseCase
    confidence: float
    matched_keywords: List[str]


def tokenize(text: str) -> List[str]:
    """
    Tokenize input text for matching.
    Removes common stop words and splits on whitespace/punctuation.
    """
    # Lowercase and split on non-alphanumeric
    tokens = re.findall(r'\b\w+\b', text.lower())

    # Remove common stop words that don't help with protocol detection
    stop_words = {
        'i', 'want', 'to', 'the', 'a', 'an', 'on', 'in', 'at', 'for',
        'with', 'from', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'change', 'update', 'modify', 'configure', 'set', 'add', 'remove'
    }

    return [t for t in tokens if t not in stop_words and len(t) > 1]


def match_input_to_use_case(input_text: str, use_cases: List[UseCase]) -> List[UseCaseMatch]:
    """
    Score all use cases against input text based on keyword matching.

    Args:
        input_text: User's voice command or text input
        use_cases: List of available use cases to match against

    Returns:
        List of UseCaseMatch objects sorted by confidence (highest first)
    """
    tokens = tokenize(input_text.lower())
    token_set = set(tokens)
    matches = []

    for uc in use_cases:
        if not uc.is_active or not uc.trigger_keywords:
            continue

        # Normalize trigger keywords
        keywords_lower = [kw.lower().strip() for kw in uc.trigger_keywords]

        # Find matched keywords
        matched = []
        for kw in keywords_lower:
            # Check if keyword appears in tokens or as substring
            kw_tokens = kw.split()
            if len(kw_tokens) == 1:
                # Single word keyword - check token set
                if kw in token_set or any(kw in token for token in tokens):
                    matched.append(kw)
            else:
                # Multi-word keyword - check if appears in original text
                if kw in input_text.lower():
                    matched.append(kw)

        # Calculate confidence based on keyword overlap
        if keywords_lower:
            confidence = (len(matched) / len(keywords_lower)) * 100
        else:
            confidence = 0

        # Bonus for exact protocol mentions (bgp, ospf, eigrp, etc.)
        protocol_keywords = {'bgp', 'ospf', 'eigrp', 'rip', 'static'}
        matched_protocols = protocol_keywords.intersection(set(matched))
        if matched_protocols:
            confidence = min(confidence * 1.5, 100)  # Boost but cap at 100

        if confidence > 0:
            matches.append(UseCaseMatch(
                use_case=uc,
                confidence=confidence,
                matched_keywords=matched
            ))

    return sorted(matches, key=lambda m: m.confidence, reverse=True)


def validate_use_case_selection(
    input_text: str,
    selected_use_case: UseCase,
    all_use_cases: List[UseCase]
) -> Dict:
    """
    Validate if the selected use case matches the input text.

    Args:
        input_text: User's voice command or text input
        selected_use_case: The use case selected by the user
        all_use_cases: All available use cases for comparison

    Returns:
        Dictionary with validation result:
        - is_valid: bool - Whether selection is valid
        - confidence: float - Confidence score for selected use case
        - error: str (optional) - Error code if invalid
        - message: str (optional) - Human-readable error message
        - suggested_use_case: str (optional) - Suggested use case name
        - suggested_display_name: str (optional) - Display name of suggestion
        - matched_keywords: List[str] (optional) - Keywords that matched
    """
    # Get all matches
    matches = match_input_to_use_case(input_text, all_use_cases)

    if not matches:
        # No clear match found - allow selected use case
        return {
            "is_valid": True,
            "confidence": 50,
            "note": "No clear protocol detected from input"
        }

    best_match = matches[0]

    # Find the selected use case in the matches
    selected_match = None
    for match in matches:
        if match.use_case.name == selected_use_case.name:
            selected_match = match
            break

    # Check if selected use case is the best match or close to it
    if best_match.use_case.name == selected_use_case.name:
        return {
            "is_valid": True,
            "confidence": best_match.confidence,
            "matched_keywords": best_match.matched_keywords
        }

    # Mismatch detected - but only flag if confidence difference is significant
    MISMATCH_THRESHOLD = 30  # Minimum confidence for the best match to trigger warning
    CONFIDENCE_DELTA_THRESHOLD = 20  # How much better best match must be

    selected_confidence = selected_match.confidence if selected_match else 0

    # Only flag mismatch if:
    # 1. Best match has decent confidence (>30%)
    # 2. Best match is significantly better than selected (>20% delta)
    if (best_match.confidence > MISMATCH_THRESHOLD and
        best_match.confidence - selected_confidence > CONFIDENCE_DELTA_THRESHOLD):

        return {
            "is_valid": False,
            "error": "PROTOCOL_MISMATCH",
            "message": (
                f"Your command appears to be about {best_match.use_case.display_name}, "
                f"but you selected {selected_use_case.display_name}."
            ),
            "suggested_use_case": best_match.use_case.name,
            "suggested_display_name": best_match.use_case.display_name,
            "confidence": round(best_match.confidence, 1),
            "matched_keywords": best_match.matched_keywords,
            "current_use_case": selected_use_case.name,
            "current_display_name": selected_use_case.display_name
        }

    # Not enough confidence difference - allow selected use case
    return {
        "is_valid": True,
        "confidence": selected_confidence,
        "note": "Low confidence difference, proceeding with selected use case"
    }


def get_protocol_from_text(input_text: str) -> Optional[str]:
    """
    Extract protocol name from input text using pattern matching.

    Args:
        input_text: User's voice command or text input

    Returns:
        Protocol name (lowercase) or None if not detected
    """
    text_lower = input_text.lower()

    # Protocol patterns (ordered by specificity)
    protocol_patterns = [
        # BGP patterns
        (r'\bbgp\b', 'bgp'),
        (r'\bas\s+\d+', 'bgp'),  # AS number
        (r'\basn\s+\d+', 'bgp'),  # ASN
        (r'\bautonomous\s+system\b', 'bgp'),
        (r'\bneighbor\s+\d+\.\d+\.\d+\.\d+', 'bgp'),
        (r'\bpeer\b', 'bgp'),

        # OSPF patterns
        (r'\bospf\b', 'ospf'),
        (r'\barea\s+\d+', 'ospf'),
        (r'\bnetwork\s+statement\b', 'ospf'),
        (r'\brouter\s+id\b', 'ospf'),

        # EIGRP patterns
        (r'\beigrp\b', 'eigrp'),

        # Static routing
        (r'\bstatic\s+route\b', 'static'),
        (r'\bip\s+route\b', 'static'),

        # Security/Credentials
        (r'\bpassword\b', 'credential'),
        (r'\bcredential\b', 'credential'),
        (r'\benable\s+secret\b', 'credential'),
        (r'\busername\b', 'credential'),
    ]

    for pattern, protocol in protocol_patterns:
        if re.search(pattern, text_lower):
            return protocol

    return None


def get_match_explanation(match: UseCaseMatch) -> str:
    """
    Generate human-readable explanation of why a use case matched.

    Args:
        match: UseCaseMatch object

    Returns:
        Explanation string
    """
    keyword_str = ", ".join(f'"{kw}"' for kw in match.matched_keywords[:3])
    if len(match.matched_keywords) > 3:
        keyword_str += f" and {len(match.matched_keywords) - 3} more"

    return (
        f"{match.use_case.display_name} "
        f"({match.confidence:.0f}% confidence, matched: {keyword_str})"
    )
