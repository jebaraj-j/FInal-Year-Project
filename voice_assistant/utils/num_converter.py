"""
Utility to convert numbers to words and vice-versa for VOSK speech recognition.
"""

NUM_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty", 30: "thirty", 40: "forty",
    50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty",
    90: "ninety", 100: "hundred"
}

def number_to_words(n: int) -> str:
    """Convert integer (0-100) to words."""
    if n in NUM_WORDS:
        return NUM_WORDS[n]
    
    if 21 <= n <= 99:
        tens = (n // 10) * 10
        ones = n % 10
        return f"{NUM_WORDS[tens]} {NUM_WORDS[ones]}"
    
    return str(n)

def words_to_number(s: str) -> int:
    """Convert words string to integer (e.g. 'fifty five' -> 55)."""
    s = s.lower().strip()
    
    # Reverse lookup for exact matches
    for k, v in NUM_WORDS.items():
        if v == s:
            if k == 100 and "one" not in s: return 100
            return k
    
    # Check for combined numbers like 'fifty five'
    parts = s.split()
    if len(parts) == 2:
        tens = 0
        ones = 0
        for k, v in NUM_WORDS.items():
            if v == parts[0]: tens = k
            if v == parts[1]: ones = k
        if tens >= 20 and 1 <= ones <= 9:
            return tens + ones
            
    # Fallback to digits if possible
    import re
    digits = re.findall(r'\d+', s)
    if digits:
        return int(digits[0])
        
    return 0

def get_all_number_words(limit: int = 100) -> list:
    """Get all number words in a list up to limit."""
    return [number_to_words(i) for i in range(limit + 1)]
