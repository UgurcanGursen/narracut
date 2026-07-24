import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union

@dataclass
class NormalizedText:
    original_text: str
    normalized_text: str
    tokens: List[Dict[str, Any]]
    semantic_entities: List[Dict[str, Any]]

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90
}

MAGNITUDES = {
    "hundred": Decimal("100"),
    "thousand": Decimal("1000"),
    "million": Decimal("1000000"),
    "billion": Decimal("1000000000"),
    "trillion": Decimal("1000000000000")
}

CURRENCIES = {
    "$": "USD", "dollar": "USD", "dollars": "USD", "usd": "USD",
    "€": "EUR", "euro": "EUR", "euros": "EUR", "eur": "EUR",
    "£": "GBP", "pound": "GBP", "pounds": "GBP", "gbp": "GBP"
}

def clean_word(word: str) -> str:
    return word.strip(".,!?;:\\\"'()")

def parse_spoken_number(text: str) -> Optional[Decimal]:
    clean_text = text.replace(",", "").lower().strip()
    
    # Handle suffixes
    multiplier = Decimal("1")
    if clean_text.endswith("k"):
        multiplier = Decimal("1000")
        clean_text = clean_text[:-1]
    elif clean_text.endswith("m"):
        multiplier = Decimal("1000000")
        clean_text = clean_text[:-1]
    elif clean_text.endswith("b"):
        multiplier = Decimal("1000000000")
        clean_text = clean_text[:-1]
    elif clean_text.endswith("t"):
        multiplier = Decimal("1000000000000")
        clean_text = clean_text[:-1]
        
    # Strip currencies and percents
    clean_text = clean_text.replace("$", "").replace("€", "").replace("£", "").replace("%", "").strip()

    try:
        return Decimal(clean_text) * multiplier
    except InvalidOperation:
        pass

    words = [w.strip() for w in re.split(r'[\s\-]+', text.lower()) if w.strip() and w.strip() != "and"]
    if not words:
        return None

    total = Decimal("0")
    current_val = Decimal("0")
    is_decimal = False
    decimal_divider = Decimal("10")
    
    for word in words:
        clean_w = word.strip(".,!?;:\\\"'()$€£%")
        
        if clean_w in ["$", "€", "£", "%", "percent"]:
            continue
            
        if clean_w in ["point", "dot"] or word.startswith("."):
            is_decimal = True
            total += current_val
            current_val = Decimal("0")
            if clean_w in ["point", "dot"] or not clean_w:
                continue
            
        if clean_w in ["dollars", "dollar", "euros", "euro", "pounds", "pound"]:
            total += current_val
            current_val = Decimal("0")
            is_decimal = False
            continue
            
        if clean_w in ["cents", "cent", "pence"]:
            total += (current_val / Decimal("100"))
            current_val = Decimal("0")
            continue
            
        if is_decimal:
            if clean_w in WORD_TO_NUM:
                total += Decimal(str(WORD_TO_NUM[clean_w])) / decimal_divider
                decimal_divider *= 10
            else:
                digits = clean_w.replace(".", "").replace(",", "")
                if digits.isdigit():
                    for digit in digits:
                        total += Decimal(digit) / decimal_divider
                        decimal_divider *= 10
                elif clean_w in MAGNITUDES:
                    total *= MAGNITUDES[clean_w]
                else:
                    return None
            continue
            
        if clean_w in WORD_TO_NUM:
            current_val += WORD_TO_NUM[clean_w]
        elif clean_w.replace(".", "").replace(",", "").isdigit():
            current_val += Decimal(clean_w.replace(",", ""))
        elif clean_w in MAGNITUDES:
            if current_val == Decimal("0"):
                current_val = Decimal("1")
            
            if clean_w == "hundred":
                current_val *= MAGNITUDES[clean_w]
            else:
                current_val *= MAGNITUDES[clean_w]
                total += current_val
                current_val = Decimal("0")
        else:
            continue

    total += current_val
    return total

def tokenize_input(input_data: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Converts either a string or a list of whisper words into a list of dictionaries with start/end mappings.
    """
    out_tokens = []
    if isinstance(input_data, str):
        work_text = input_data
        work_text = re.sub(r'([%$€£])', r' \1 ', work_text)
        raw_tokens = re.findall(r'[a-z0-9\.\,\-]+|[%$€£]|\S', work_text, flags=re.IGNORECASE)
        for idx, t in enumerate(raw_tokens):
            out_tokens.append({
                "word": t,
                "start": -1.0,
                "end": -1.0,
                "orig_idx": idx
            })
    else:
        # It's a list of dicts from whisper: [{"word": "seventeen", "start": 1.0, "end": 1.5}, ...]
        # We need to preserve the timestamps, but also separate symbols if they are attached to words.
        # e.g., "$17.2" -> "$" and "17.2"
        global_idx = 0
        for orig_idx, w_obj in enumerate(input_data):
            orig_word = w_obj["word"]
            # Pad symbols
            work_text = re.sub(r'([%$€£])', r' \1 ', orig_word)
            sub_tokens = re.findall(r'[a-z0-9\.\,\-]+|[%$€£]|\S', work_text, flags=re.IGNORECASE)
            for t in sub_tokens:
                out_tokens.append({
                    "word": t,
                    "start": w_obj.get("start", -1.0),
                    "end": w_obj.get("end", -1.0),
                    "orig_idx": orig_idx
                })
    return out_tokens

def canonicalize_numbers(input_data: Union[str, List[Dict[str, Any]]]) -> NormalizedText:
    if isinstance(input_data, str):
        original_text = input_data
    else:
        original_text = " ".join([w["word"] for w in input_data])
        
    entities = []
    tokens = tokenize_input(input_data)
    
    normalized_tokens = []
    i = 0
    number_words = set(WORD_TO_NUM.keys()).union(set(MAGNITUDES.keys())).union({"point", "dot", "and"})
    
    while i < len(tokens):
        t_obj = tokens[i]
        t = t_obj["word"].lower()
        clean_t = clean_word(t)
        
        is_num_start = False
        parts = clean_t.split("-")
        if re.match(r'^[\d\.\,]+[kmbt]?$', clean_t, re.IGNORECASE) or any(p in number_words for p in parts) or clean_t in CURRENCIES.keys() or clean_t == "%":
            is_num_start = True
            
        if is_num_start:
            seq_objs = []
            j = i
            while j < len(tokens):
                nt_obj = tokens[j]
                nt = nt_obj["word"].lower()
                clean_nt = clean_word(nt)
                parts_nt = clean_nt.split("-")
                if re.match(r'^[\d\.\,]+[kmbt]?$', clean_nt, re.IGNORECASE) or any(p in number_words for p in parts_nt) or clean_nt in CURRENCIES.keys() or clean_nt in ["%", "percent", "cents", "cent"]:
                    seq_objs.append(nt_obj)
                    j += 1
                else:
                    break
                        
            seq_words = [o["word"].lower() for o in seq_objs]
            clean_seq_words = [clean_word(w) for w in seq_words]
            
            currency = None
            for c in CURRENCIES.keys():
                if c in clean_seq_words:
                    currency = CURRENCIES[c]
                    break
            
            is_percent = False
            if "%" in clean_seq_words or "percent" in clean_seq_words:
                is_percent = True
                
            filtered_seq = []
            for w in seq_words:
                cw = clean_word(w)
                if cw not in CURRENCIES.keys() and cw not in ["%", "percent", "cents", "cent"]:
                    filtered_seq.append(w)
                    
            val_str = " ".join(seq_words)
            val = parse_spoken_number(val_str)
            
            if val is not None:
                if ("cents" in clean_seq_words or "cent" in clean_seq_words) and (currency == "USD" or currency is None):
                    val = val / Decimal("100")
                    if currency is None: currency = "USD"
                    
                val_str_norm = "{:f}".format(val.normalize())
                
                # Build canonical token string and entity record
                if is_percent:
                    canonical_token = f"<NUM:PERCENT:{val_str_norm}>"
                    ent = {
                        "type": "percentage",
                        "value": val_str_norm,
                        "canonical_token": canonical_token
                    }
                elif currency:
                    canonical_token = f"<NUM:{currency}:{val_str_norm}>"
                    ent = {
                        "type": "currency",
                        "currency": currency,
                        "value": val_str_norm,
                        "canonical_token": canonical_token
                    }
                else:
                    is_year = False
                    if len(val_str_norm) == 4 and 1900 <= val <= 2100 and "." not in val_str_norm:
                        is_year = True
                    canonical_token = f"<NUM:{val_str_norm}>"
                    ent = {
                        "type": "number",
                        "is_year": is_year,
                        "value": val_str_norm,
                        "canonical_token": canonical_token
                    }
                    
                ent["original_token_start_index"] = seq_objs[0]["orig_idx"]
                ent["original_token_end_index"] = seq_objs[-1]["orig_idx"]
                ent["original_start_time"] = seq_objs[0].get("start", -1.0)
                ent["original_end_time"] = seq_objs[-1].get("end", -1.0)
                entities.append(ent)
                    
                normalized_tokens.append({
                    "word": canonical_token,
                    "start": seq_objs[0].get("start", -1.0),
                    "end": seq_objs[-1].get("end", -1.0),
                    "orig_word": original_text[original_text.find(seq_objs[0]["word"]):], # rough
                    "orig_idx": seq_objs[0]["orig_idx"],
                    "is_canonical": True,
                    "entity": ent
                })
                i = j
                continue
                
        # Not a number sequence
        if clean_word(t_obj["word"]):
            normalized_tokens.append({
                "word": clean_word(t_obj["word"]),
                "start": t_obj.get("start", -1.0),
                "end": t_obj.get("end", -1.0),
                "orig_word": t_obj["word"],
                "orig_idx": t_obj["orig_idx"],
                "is_canonical": False
            })
        i += 1
        
    normalized_text = " ".join([t["word"] for t in normalized_tokens])
    return NormalizedText(
        original_text=original_text,
        normalized_text=normalized_text,
        tokens=normalized_tokens,
        semantic_entities=entities
    )
