import re
import json

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

def is_grafa(l):
    return bool(re.match(r'^(А|Б|В|Г|Д|НГ|\-)(?:-\d+)?(?:\s*\([А-Я]\s*-\s*[А-Я]+\))?$|^\([А-Я]\s*-\s*[А-Я]+\)$', l.strip()))

def parse_to_json(lines, file_id):
    result_elements = []
    
    legal_act = "Приложение N 1 к Положению о военно-врачебной экспертизе"
    
    current_section = None
    current_subsection = None
    
    state = "INIT"
    
    current_point_num = None
    current_point_text = []
    
    art_num = None
    art_title = None
    subpoints_data = [] 
    current_subpoint_text = []
    grafa_state = 0
    art_text_below = []
    
    def finalize_general_point():
        if current_point_num:
            text_val = "\n".join(current_point_text).strip()
            text_val = re.sub(r'[ \t]*\(в ред\.(?:[^()]*|\([^()]*\))*\)', '', text_val)
            
            x = extract_section_num(current_section)
            y = 0
            z = current_point_num
            
            uid = f"{file_id}_{x}_{y}_{z}"
            
            parts = [legal_act]
            if current_section: parts.append(current_section)
            
            rag_context = ", ".join(parts) + ": " + current_point_num + ". " + text_val
            
            result_elements.append({
                "id": uid,
                "legal_act": legal_act,
                "section": current_section,
                "subsection": None,
                "number": current_point_num,
                "rag_context": rag_context
            })

    def finalize_article():
        if art_num:
            x = extract_section_num(current_section)
            y = 0
            if current_subsection:
                m = re.match(r'^(\d+)\.', current_subsection)
                if m: y = int(m.group(1))
            z = art_num
            
            uid = f"{file_id}_{x}_{y}_{z}"
            
            rag_parts = [legal_act]
            if current_section: rag_parts.append(current_section)
            title_clean = re.sub(r'[ \t]*\(в ред\.(?:[^()]*|\([^()]*\))*\)', '', art_title).strip()
            rag_parts.append(f"Статья {art_num}. {title_clean}")
            
            rag_text = ", ".join(rag_parts) + ", Графа I:\n"
            if len(subpoints_data) == 1 and subpoints_data[0][0] == "":
                rag_text = ", ".join(rag_parts) + f", Графа I: Категория годности \"{subpoints_data[0][1]}\";\n"
            else:
                for sp, gr in subpoints_data:
                    sp_clean = re.sub(r'[ \t]*\(в ред\.(?:[^()]*|\([^()]*\))*\)', '', sp).strip()
                    rag_text += f"{sp_clean}: Категория годности \"{gr}\";\n"
            
            below_clean = "\n".join(art_text_below).strip()
            below_clean = re.sub(r'[ \t]*\(в ред\.(?:[^()]*|\([^()]*\))*\)', '', below_clean)
            if below_clean:
                rag_text += below_clean
                
            result_elements.append({
                "id": uid,
                "legal_act": legal_act,
                "section": current_section,
                "subsection": current_subsection,
                "number": art_num,
                "rag_context": rag_text.strip()
            })

    for line in lines:
        stripped = line.strip().lstrip('\ufeff\u200b')
        if not stripped: continue
        
        if stripped.upper().startswith("ТАБЛИЦА 1") or stripped.startswith("Таблица 1"):
            if state in ["ART_TEXT", "ART_SUBPOINT_WAIT_GRAFA1", "ART_GRAFA_WAIT", "ART_WAIT_SUBPOINT", "ART_WAIT_SUBPOINT_OR_TEXT"]:
                finalize_article()
                state = "DONE"
            break
            
        if state == "DONE":
            break

        if stripped.upper().startswith("I. ОБЩИЕ ПОЛОЖЕНИЯ") or stripped.upper().startswith("I. ОБЩИЕ"):
            current_section = clean_header(stripped)
            state = "GEN_PROV"
            continue
            
        if stripped.upper().startswith("II. РАСПИСАНИЕ БОЛЕЗНЕЙ") or stripped.upper().startswith("II. РАСПИСАНИЕ"):
            finalize_general_point()
            current_section = clean_header(stripped)
            current_point_num = None
            current_point_text = []
            state = "RASP_BOLEZNEY"
            continue
            
        if state == "GEN_PROV":
            m = re.match(r'^(\d+)\.\s', stripped)
            if m:
                finalize_general_point()
                current_point_num = m.group(1)
                current_point_text = [stripped[len(m.group(0)):].strip()]
            elif current_point_num:
                current_point_text.append(stripped)
            continue
            
        if state in ["RASP_BOLEZNEY", "WAIT_SUBSEC", "ART_TABLE_HEADER", "ART_NUM", "ART_TITLE", "ART_WAIT_SUBPOINT", "ART_SUBPOINT_WAIT_GRAFA1", "ART_GRAFA_WAIT", "ART_TEXT", "ART_WAIT_SUBPOINT_OR_TEXT"]:
            m = re.match(r'^(\d+)\.\s+[А-Я]', stripped)
            if m and state in ["RASP_BOLEZNEY", "ART_TEXT", "WAIT_SUBSEC", "ART_WAIT_SUBPOINT_OR_TEXT"]:
                if state in ["ART_TEXT", "ART_WAIT_SUBPOINT_OR_TEXT"]:
                    finalize_article()
                    art_num = None
                    art_title = None
                    subpoints_data = []
                    current_subpoint_text = []
                    art_text_below = []
                current_subsection = clean_header(stripped)
                state = "WAIT_SUBSEC"
                continue
                
            if stripped.startswith("Статья расписания болезней") or stripped.startswith("Наименование болезней"):
                if state in ["ART_TEXT", "ART_WAIT_SUBPOINT", "ART_WAIT_SUBPOINT_OR_TEXT", "ART_GRAFA_WAIT"]:
                    finalize_article()
                art_num = None
                art_title = None
                subpoints_data = []
                current_subpoint_text = []
                art_text_below = []
                state = "ART_TABLE_HEADER"
                continue
                
            if state == "ART_TABLE_HEADER":
                if stripped.startswith("III графа"):
                    # Check if number is merged
                    if len(stripped) > 9:
                        num_part = stripped[9:]
                        if re.match(r'^\d+$', num_part):
                            art_num = num_part
                            state = "ART_TITLE"
                            continue
                    state = "ART_NUM"
                elif re.match(r'^\d+$', stripped) and ' ' not in stripped:
                    # Sometimes "III графа" is missing or split strangely, and we just see the number
                    art_num = stripped
                    state = "ART_TITLE"
                elif re.match(r'^[I]{1,3}\s+графа', stripped):
                    pass # Ignore other headers and wait for III графа
                continue
                
            if state == "ART_NUM":
                if re.match(r'^\d+$', stripped):
                    art_num = stripped
                    state = "ART_TITLE"
                continue
                
            if state == "ART_TITLE":
                art_title = stripped
                state = "ART_WAIT_SUBPOINT"
                continue
                
            if state == "ART_WAIT_SUBPOINT":
                if stripped.startswith('(в ред.'): continue
                if re.match(r'^[а-я]\)', stripped):
                    current_subpoint_text = [stripped]
                    state = "ART_SUBPOINT_WAIT_GRAFA1"
                elif is_grafa(stripped):
                    subpoints_data.append(("", stripped))
                    grafa_state = 1
                    state = "ART_GRAFA_WAIT"
                else:
                    art_text_below.append(stripped)
                    state = "ART_TEXT"
                continue
                
            if state == "ART_SUBPOINT_WAIT_GRAFA1":
                if stripped.startswith('(в ред.'): continue
                if is_grafa(stripped):
                    subpoints_data.append(("\n".join(current_subpoint_text), stripped))
                    current_subpoint_text = []
                    grafa_state = 1
                    state = "ART_GRAFA_WAIT"
                else:
                    current_subpoint_text.append(stripped)
                continue
                
            if state == "ART_GRAFA_WAIT":
                if stripped.startswith('(в ред.'): continue
                if is_grafa(stripped):
                    grafa_state += 1
                    if grafa_state == 3:
                        state = "ART_WAIT_SUBPOINT_OR_TEXT"
                else:
                    if re.match(r'^[а-я]\)', stripped):
                        current_subpoint_text = [stripped]
                        state = "ART_SUBPOINT_WAIT_GRAFA1"
                    else:
                        art_text_below.append(stripped)
                        state = "ART_TEXT"
                continue
                    
            if state == "ART_TEXT" or state == "ART_WAIT_SUBPOINT_OR_TEXT":
                if stripped.startswith('(в ред.'): continue
                if re.match(r'^[а-я]\)', stripped) and state == "ART_WAIT_SUBPOINT_OR_TEXT":
                    current_subpoint_text = [stripped]
                    state = "ART_SUBPOINT_WAIT_GRAFA1"
                    continue
                if re.match(r'^\d+$', stripped) and ' ' not in stripped:
                    finalize_article()
                    art_num = stripped
                    art_title = None
                    subpoints_data = []
                    current_subpoint_text = []
                    art_text_below = []
                    state = "ART_TITLE"
                    continue
                
                if stripped in ["Наименование болезней", "Наименование болезней, степень нарушения функции", "Категория годности к военной службе", "Статья расписания болезней"]:
                    continue
                if stripped == "степень нарушения функции":
                    continue
                
                # Check for merged header artifacts like "I графа", "II графа", "III графа"
                if re.match(r'^[I]{1,3}\s+графа', stripped):
                    continue
                if re.match(r'^графа', stripped):
                    continue
                    
                art_text_below.append(stripped)
                state = "ART_TEXT"
                continue

    if state in ["GEN_PROV"]:
        finalize_general_point()
    elif state in ["ART_TEXT", "ART_WAIT_SUBPOINT", "ART_WAIT_SUBPOINT_OR_TEXT", "ART_GRAFA_WAIT"]:
        finalize_article()
        
    return result_elements