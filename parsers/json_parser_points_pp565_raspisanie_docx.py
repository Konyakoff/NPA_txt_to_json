import docx
import re
import json
import os

def clean_text(text):
    text = re.sub(r'\s*\(в ред\.(?:[^()]*|\([^()]*\))*\)', '', text)
    text = re.sub(r'\s*\(в ред\..*?$', '', text)
    return text.strip()

def extract_section_num(text):
    if not text: return 0
    m = re.search(r'(?:раздел|глава)\s+([IVXLCDM]+|\d+)', text, re.IGNORECASE)
    if m:
        val = m.group(1)
        if val.isdigit(): return int(val)
        else: return roman_to_arabic(val)
    m2 = re.match(r'^([IVXLCDM]+|\d+)', text, re.IGNORECASE)
    if m2:
        val = m2.group(1)
        if val.isdigit(): return int(val)
        else: return roman_to_arabic(val)
    return 0

def roman_to_arabic(roman):
    roman = roman.upper()
    roman_numerals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    for i, c in enumerate(roman):
        if c not in roman_numerals: continue
        if i + 1 < len(roman) and roman_numerals[c] < roman_numerals.get(roman[i + 1], 0):
            result -= roman_numerals[c]
        else:
            result += roman_numerals[c]
    return result if result > 0 else 0

def parse_to_json(filepath, file_id):
    try:
        doc = docx.Document(filepath)
    except Exception as e:
        raise Exception(f"Ошибка при чтении docx файла: {e}")

    result_elements = []
    legal_act = 'Приложение N 1 к Положению о военно-врачебной экспертизе'
    
    current_section = None
    current_subsection = None
    
    art_num = None
    art_title = None
    subpoints_data = []
    art_text_below = []
    
    def finalize_article():
        nonlocal art_num, art_title, subpoints_data, art_text_below, result_elements
        if art_num:
            x = extract_section_num(current_section)
            y = 0
            if current_subsection:
                m = re.match(r'^(\d+)\.', current_subsection)
                if m: y = int(m.group(1))
            
            uid = f"{file_id}_{x}_{y}_{art_num}"
            
            rag_parts = [legal_act]
            if current_section: rag_parts.append(current_section)
            
            t_clean = clean_text(art_title).rstrip(':, ')
            rag_parts.append(f"Статья {art_num}. {t_clean}")
            rag_text = ", ".join(rag_parts) + ", Графа I:\n"
            
            if len(subpoints_data) == 1 and subpoints_data[0][0] == "":
                rag_text = ", ".join(rag_parts) + f", Графа I: Категория годности \"{subpoints_data[0][1]}\";\n"
            else:
                for sp, gr in subpoints_data:
                    sp_clean = clean_text(sp)
                    rag_text += f"{sp_clean}: Категория годности \"{gr}\";\n"
            
            b_clean = clean_text("\n".join(art_text_below))
            if b_clean:
                rag_text += b_clean
                
            result_elements.append({
                "id": uid,
                "legal_act": legal_act,
                "section": current_section,
                "subsection": current_subsection,
                "number": art_num,
                "rag_context": rag_text.strip()
            })
            art_num = None
            art_title = None
            subpoints_data = []
            art_text_below = []

    for block in doc.element.body:
        if block.tag.endswith('p'):
            p = docx.text.paragraph.Paragraph(block, doc)
            text = p.text.strip().replace('\n', ' ')
            if not text: continue
            
            if text.upper().startswith('ТАБЛИЦА 1') or text.startswith('Таблица 1'):
                finalize_article()
                break
                
            if text.upper().startswith('I. ОБЩИЕ ПОЛОЖЕНИЯ') or text.upper().startswith('I. ОБЩИЕ'):
                current_section = clean_text(text)
                continue
                
            if text.upper().startswith('II. РАСПИСАНИЕ БОЛЕЗНЕЙ') or text.upper().startswith('II. РАСПИСАНИЕ'):
                finalize_article()
                current_section = clean_text(text)
                continue
                
            if current_section and current_section.upper().startswith('I.'):
                m = re.match(r'^(\d+)\.\s', text)
                if m:
                    p_num = m.group(1)
                    t_val = clean_text(text[len(m.group(0)):])
                    x = extract_section_num(current_section)
                    uid = f"{file_id}_{x}_0_{p_num}"
                    rag = f"{legal_act}, {current_section}: {p_num}. {t_val}"
                    result_elements.append({
                        "id": uid,
                        "legal_act": legal_act,
                        "section": current_section,
                        "subsection": None,
                        "number": p_num,
                        "rag_context": rag
                    })
                elif result_elements and result_elements[-1]['number'] in ['1','2','3','4','5'] and result_elements[-1]['section'] == current_section:
                    result_elements[-1]['rag_context'] += '\n' + clean_text(text)
                continue
                
            m = re.match(r'^(\d+)\.\s+[А-Я]', text)
            if m and current_section and current_section.upper().startswith('II.'):
                finalize_article()
                current_subsection = clean_text(text)
                continue
                
            if art_num:
                art_text_below.append(text)
                
        elif block.tag.endswith('tbl'):
            if current_section and current_section.upper().startswith('I.'):
                continue
                
            t = docx.table.Table(block, doc)
            if len(t.rows) > 2:
                for i_row in range(2, len(t.rows)):
                    row = t.rows[i_row]
                    cells = [c.text.strip().replace('\n', ' ') for c in row.cells]
                    if len(cells) >= 5:
                        cell_0 = clean_text(cells[0])
                        if cell_0.isdigit() and cell_0 != art_num:
                            finalize_article()
                            
                            art_num = cell_0
                            art_title = clean_text(cells[1])
                            
                            cat_text = clean_text(cells[2])
                            if cat_text and re.match(r'^(А|Б|В|Г|Д|НГ|\-|[АБВГД]\-?[1-4]?)', cat_text):
                                subpoints_data.append(("", cat_text))
                            continue
                            
                        if art_num:
                            subp = clean_text(cells[1])
                            gr = clean_text(cells[2])
                            if gr and not re.match(r'^(А|Б|В|Г|Д|НГ|\-|[АБВГД]\-?[1-4]?)', gr):
                                gr = ""
                            if subp or gr:
                                subpoints_data.append((subp, gr))
                        
    finalize_article()
    return result_elements
