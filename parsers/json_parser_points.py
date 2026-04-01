import re

def clean_header(line):
    line = re.sub(r'\s*\(в ред\..*?\)\s*$', '', line)
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
    state = "SEARCHING_TITLE"
    
    current_section = None
    current_point_num = None
    current_point_text = []
    
    max_point_number = -1

    def finalize_point():
        if current_point_num:
            text_val = "\n".join(current_point_text).strip()
            legal_act = " ".join(title_lines).strip() if title_lines else None
            
            x = extract_section_num(current_section)
            y = 0
            z = current_point_num
            
            uid = f"{file_id}_{x}_{y}_{z}"
            
            parts = []
            if legal_act: parts.append(legal_act)
            if current_section: parts.append(current_section)
            parts.append(current_point_num)
            
            rag_context = ", ".join(parts) + ":\n" + text_val
            
            result_elements.append({
                "id": uid,
                "legal_act": legal_act,
                "section": current_section,
                "subsection": None,
                "number": current_point_num,
                "rag_context": rag_context
            })

    roman_regex = re.compile(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV)\.\s+')
    point_regex = re.compile(r'^([\d\.\-]+)\.(?:\s|$)')

    for line in lines:
        stripped = line.strip().lstrip('\ufeff\u200b')
        
        if state == "SEARCHING_TITLE":
            if stripped == "ПОСТАНОВЛЕНИЕ" or "УКАЗ" in stripped.upper() or "ПРИКАЗ" in stripped.upper() or stripped.isupper():
                if stripped != "РОССИЙСКАЯ ФЕДЕРАЦИЯ" and stripped != "ПРИНЯТ" and stripped != "ОДОБРЕН":
                    state = "COLLECTING_TITLE"
                    title_lines.append(stripped)
            continue
            
        elif state == "COLLECTING_TITLE":
            if stripped.startswith("(в ред.") or stripped.startswith("В соответствии со"):
                state = "PARSING_CONTENT"
                continue
                
            if stripped:
                if roman_regex.match(stripped) or point_regex.match(stripped):
                    state = "PARSING_CONTENT"
                else:
                    title_lines.append(stripped)
                    continue
            else:
                continue
                
        if state == "PARSING_CONTENT":
            if not stripped:
                if current_point_num:
                    current_point_text.append(line.rstrip())
                continue
                
            roman_match = roman_regex.match(stripped)
            if roman_match:
                finalize_point()
                current_point_num = None
                current_point_text = []
                current_section = clean_header(stripped)
                continue
                
            point_match = point_regex.match(stripped)
            if point_match:
                point_num_str = point_match.group(1).rstrip('.')
                first_num_part_str = re.split(r'[^\d]', point_num_str)[0]
                first_num_part = int(first_num_part_str) if first_num_part_str else 0
                
                if first_num_part > max_point_number:
                    finalize_point()
                    max_point_number = first_num_part
                    current_point_num = point_num_str
                    current_point_text = [line.rstrip()]
                    continue
                else:
                    if current_point_num:
                        current_point_text.append(line.rstrip())
                    continue
                
            if current_point_num:
                current_point_text.append(line.rstrip())

    finalize_point()
    return result_elements
