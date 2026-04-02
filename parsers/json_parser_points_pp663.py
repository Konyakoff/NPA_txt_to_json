import re

def clean_header(line):
    line = re.sub(r'\s*\(в ред\.(?:[^()]*|\([^()]*\))*\)', '', line)
    line = re.sub(r'\s*\(в ред\..*$', '', line)
    return line.strip()

def roman_to_arabic(roman):
    roman = roman.upper()
    roman_numerals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    for i, c in enumerate(roman):
        if c not in roman_numerals: continue
        if i + 1 < len(roman) and roman[i+1] in roman_numerals and roman_numerals[c] < roman_numerals[roman[i + 1]]:
            result -= roman_numerals[c]
        else:
            result += roman_numerals[c]
    return result if result > 0 else 0

def extract_section_num(text):
    if not text: return 0
    m = re.search(r'(?:раздел|глава)\s+([IVXLCDM]+|\d+)', text, re.IGNORECASE)
    if m:
        val = m.group(1)
        if val.isdigit(): return int(val)
        else: return roman_to_arabic(val)
    m2 = re.search(r'^([IVXLCDM]+|\d+)', text, re.IGNORECASE)
    if m2:
        val = m2.group(1)
        if val.isdigit(): return int(val)
        else: return roman_to_arabic(val)
    return 0

def parse_to_json(lines, file_id):
    result_elements = []
    
    title_lines = []
    title_finished = False
    in_appendix = False
    
    current_section = None
    current_subsection = None
    current_article_num = None
    current_article_text = []

    def finalize_article():
        if current_article_num:
            text_val = "\n".join(current_article_text).strip()
            
            # Убираем вставки вида (в ред. Федерального закона от ...) из текста статьи и ее названия,
            # поддерживая один уровень вложенных скобок (например, "(ред. от ...)")
            text_val = re.sub(r'[ \t]*\(в ред\.(?:[^()]*|\([^()]*\))*\)', '', text_val)
            
            legal_act = " ".join(title_lines).strip() if title_lines else None
            
            x = extract_section_num(current_section)
            y = extract_section_num(current_subsection)
            z = current_article_num
            
            uid = f"{file_id}_{x}_{y}_{z}"
            
            parts = []
            if legal_act: parts.append(legal_act)
            if current_section: parts.append(current_section)
            if current_subsection: parts.append(current_subsection)
            
            rag_context = ", ".join(parts) + ":\n" + text_val
            
            result_elements.append({
                "id": uid,
                "legal_act": legal_act,
                "section": current_section,
                "subsection": current_subsection,
                "number": current_article_num,
                "rag_context": rag_context
            })

    for line in lines:
        stripped = line.strip().lstrip('\ufeff\u200b')
        
        if not stripped:
            if current_article_num:
                current_article_text.append(line.rstrip())
            continue
            
        if stripped.upper().startswith("ПРИЛОЖЕНИЕ"):
            in_appendix = True
            
        if not title_finished:
            if stripped in ["РОССИЙСКАЯ ФЕДЕРАЦИЯ", "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ", "ПРИНЯТ", "ОДОБРЕН", "УТВЕРЖДЕНО", "УТВЕРЖДЕНА"]:
                continue
            
            if stripped.startswith("(в ред.") or stripped.startswith("В соответствии со"):
                title_finished = True
                continue
                
            is_structure = False
            if stripped.upper().startswith("РАЗДЕЛ ") or stripped.upper().startswith("ГЛАВА "):
                is_structure = True
            elif re.match(r'^([IVXLCDM]+)\.\s+', stripped, re.IGNORECASE):
                is_structure = True
            elif re.match(r'^([\d\.\-]+)\.(?:\s|$)', stripped):
                is_structure = True
                
            if is_structure:
                title_finished = True
            else:
                title_lines.append(stripped)
                continue
            
        if not in_appendix:
            if stripped.upper().startswith("РАЗДЕЛ "):
                finalize_article()
                current_article_num = None
                current_article_text = []
                title_finished = True
                current_section = clean_header(stripped)
                current_subsection = None # Reset subsection when a new section starts
                continue
                
            elif stripped.upper().startswith("ГЛАВА "):
                finalize_article()
                current_article_num = None
                current_article_text = []
                title_finished = True
                current_subsection = clean_header(stripped)
                continue
                
            elif re.match(r'^([IVXLCDM]+)\.\s+', stripped, re.IGNORECASE):
                finalize_article()
                current_article_num = None
                current_article_text = []
                title_finished = True
                current_section = clean_header(stripped)
                current_subsection = None
                continue
                
            m = re.match(r'^([\d\.\-]+)\.(?:\s|$)', stripped)
            if m:
                finalize_article()
                title_finished = True
                current_article_num = m.group(1).rstrip('.')
                current_article_text = [line.rstrip()]
                continue
            
        if current_article_num:
            current_article_text.append(line.rstrip())

    finalize_article()
    return result_elements