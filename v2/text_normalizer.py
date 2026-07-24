import re
from num2words import num2words

def normalize_text(text: str, lang="en") -> str:
    """
    Normalizes numbers, currencies, percentages, decimals, and dates into words.
    Uses num2words for accurate conversion.
    """
    if not text:
        return text

    # Handle negative numbers first (e.g., -25%)
    text = re.sub(r'-\s*(\d)', r'minus \1', text)

    # Handle percentages: 5%, 25% -> 5 percent
    text = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'\1 percent', text)

    # Handle currencies with decimals using num2words currency mode
    def _replace_currency_usd(match):
        val = float(match.group(1))
        return num2words(val, to='currency', currency='USD').replace(',', '')
    def _replace_currency_eur(match):
        val = float(match.group(1))
        return num2words(val, to='currency', currency='EUR').replace(',', '')
    def _replace_currency_gbp(match):
        val = float(match.group(1))
        return num2words(val, to='currency', currency='GBP').replace(',', '')

    text = re.sub(r'\$\s*(\d+(?:\.\d+)?)', _replace_currency_usd, text)
    text = re.sub(r'€\s*(\d+(?:\.\d+)?)', _replace_currency_eur, text)
    text = re.sub(r'£\s*(\d+(?:\.\d+)?)', _replace_currency_gbp, text)

    # Handle years (19XX or 20XX)
    def _replace_year(match):
        val = int(match.group(1))
        return num2words(val, to='year').replace('-', ' ')
    
    text = re.sub(r'\b(19\d{2}|20\d{2})\b', _replace_year, text)

    # Now find all remaining numbers and convert them using num2words
    def _replace_number(match):
        num_str = match.group(0)
        try:
            # If it's a decimal
            if '.' in num_str:
                return num2words(float(num_str), lang=lang)
            # If it's an integer
            else:
                return num2words(int(num_str), lang=lang)
        except:
            return num_str

    # Find standalone numbers (including decimals)
    text = re.sub(r'\b\d+(?:\.\d+)?\b', _replace_number, text)

    # Clean up excess spaces and punctuation for matching
    text = text.replace("-", " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()
