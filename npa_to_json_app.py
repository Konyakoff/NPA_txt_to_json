import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json
import threading

def detect_encoding_and_read(filepath):
    encodings_to_try = ['utf-8-sig', 'utf-16', 'utf-8', 'windows-1251', 'cp866']
    for enc in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                text = f.read()
                if '\x00' in text and enc not in ['utf-16', 'utf-16-le', 'utf-16-be']:
                    continue
                return text.splitlines()
        except UnicodeDecodeError:
            continue
    try:
        with open(filepath, 'r', encoding='utf-16le') as f:
            return f.read().splitlines()
    except Exception:
        pass
    raise Exception("Не удалось определить кодировку файла или прочитать его.")

def process_json_file(filepath, json_type, progress_callback=None, is_docx=False):
    from parsers import json_parser_articles, json_parser_points, json_parser_articles_53fz, json_parser_articles_kas, json_parser_points_pp565, json_parser_points_pp663, json_parser_points_plenum, json_parser_points_pp565_raspisanie, json_parser_points_pp565_raspisanie_docx
    
    if not is_docx:
        lines = detect_encoding_and_read(filepath)
    else:
        lines = None
        
    file_id = os.path.splitext(os.path.basename(filepath))[0]
    
    parsed_type = None
    if json_type == "Статьи":
        parsed_type = "articles"
    elif json_type == "Пункты":
        parsed_type = "points"
    elif json_type == "Статьи (53-ФЗ)":
        parsed_type = "articles_53fz"
    elif json_type == "Статьи (Кодекс СудПроизводства)":
        parsed_type = "articles_kas"
    elif json_type == "пункты (PP565 + другие)":
        parsed_type = "points_pp565"
    elif json_type == "Пункты (PP663 О Призыве)":
        parsed_type = "points_pp663"
    elif json_type == "Пункты (Пленум ВерхСуда)":
        parsed_type = "points_plenum"
    elif json_type == "Приложение к Положению о ВВЭ":
        parsed_type = "points_pp565_raspisanie_docx" if is_docx else "points_pp565_raspisanie"
        
    if not parsed_type:
        raise Exception("Выбран неизвестный тип парсера.")
        
    if progress_callback:
        progress_callback("Анализ и конвертация структуры...")
        
    if parsed_type == "articles":
        result_elements = json_parser_articles.parse_to_json(lines, file_id)
    elif parsed_type == "articles_53fz":
        result_elements = json_parser_articles_53fz.parse_to_json(lines, file_id)
    elif parsed_type == "articles_kas":
        result_elements = json_parser_articles_kas.parse_to_json(lines, file_id)
    elif parsed_type == "points_pp565":
        result_elements = json_parser_points_pp565.parse_to_json(lines, file_id)
    elif parsed_type == "points_pp663":
        result_elements = json_parser_points_pp663.parse_to_json(lines, file_id)
    elif parsed_type == "points_plenum":
        result_elements = json_parser_points_plenum.parse_to_json(lines, file_id)
    elif parsed_type == "points_pp565_raspisanie":
        result_elements = json_parser_points_pp565_raspisanie.parse_to_json(lines, file_id)
    elif parsed_type == "points_pp565_raspisanie_docx":
        result_elements = json_parser_points_pp565_raspisanie_docx.parse_to_json(filepath, file_id)
    else:
        result_elements = json_parser_points.parse_to_json(lines, file_id)
        
    base_path, ext = os.path.splitext(filepath)
    counter = 1
    out_filepath = f"{base_path}_{counter}.json"
    while os.path.exists(out_filepath):
        counter += 1
        out_filepath = f"{base_path}_{counter}.json"
        
    if progress_callback:
        progress_callback("Сохранение файла...")
        
    with open(out_filepath, 'w', encoding='utf-8') as f:
        json.dump(result_elements, f, ensure_ascii=False, indent=2)
        
    stats = {
        "processed": len(result_elements),
        "total": len(result_elements),
        "errors": 0
    }
    return out_filepath, stats

class JsonParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Конвертер НПА в JSON")
        self.root.geometry("550x350")
        self.root.eval('tk::PlaceWindow . center')
        self.root.configure(padx=20, pady=20)
        
        title_label_json = tk.Label(root, text="Конвертация НПА в JSON", font=("Arial", 14, "bold"))
        title_label_json.pack(pady=(10, 10))
        
        desc_label_json = tk.Label(
            root, 
            text="Выберите файл для извлечения структуры и конвертации в JSON.\nСкрипт создаст массив объектов для каждой статьи/пункта.", 
            font=("Arial", 10), justify=tk.CENTER
        )
        desc_label_json.pack(pady=(0, 20))

        self.all_parser_values = ["Статьи", "Пункты", "Статьи (53-ФЗ)", "Статьи (Кодекс СудПроизводства)", "пункты (PP565 + другие)", "Пункты (PP663 О Призыве)", "Пункты (Пленум ВерхСуда)", "Приложение к Положению о ВВЭ"]
        self.docx_parser_values = ["Приложение к Положению о ВВЭ"]

        self.is_docx_var = tk.BooleanVar(value=False)
        self.docx_checkbox = tk.Checkbutton(
            root, text="Расписание болезней в Docx формате", 
            variable=self.is_docx_var, 
            command=self.toggle_docx_mode,
            font=("Arial", 10)
        )
        self.docx_checkbox.pack(pady=(0, 10))

        # Выпадающий список для JSON
        self.json_type_var = tk.StringVar()
        self.json_type_combo = ttk.Combobox(
            root, 
            textvariable=self.json_type_var,
            values=self.all_parser_values,
            state="readonly",
            width=50,
            font=("Arial", 10)
        )
        self.json_type_combo.current(0)
        self.json_type_combo.pack(pady=(0, 20))
        
        self.btn_json = tk.Button(
            root, text="Выбрать файл для JSON", command=self.select_file_for_json, 
            font=("Arial", 12), bg="#2196F3", fg="white",
            padx=20, pady=10, cursor="hand2"
        )
        self.btn_json.pack()

        self.status_label_json = tk.Label(root, text="", font=("Arial", 9), fg="blue")
        self.status_label_json.pack(pady=(10, 0))

    def toggle_docx_mode(self):
        if self.is_docx_var.get():
            self.json_type_combo['values'] = self.docx_parser_values
            self.json_type_combo.current(0)
        else:
            self.json_type_combo['values'] = self.all_parser_values
            self.json_type_combo.current(0)

    def update_status_json(self, text):
        self.status_label_json.config(text=text)

    def process_in_thread_json(self, filepath, json_type, is_docx):
        try:
            out_file, stats = process_json_file(
                filepath,
                json_type,
                progress_callback=lambda msg: self.root.after(0, self.update_status_json, msg),
                is_docx=is_docx
            )
            self.root.after(0, self.finish_success_json, out_file, stats)
        except Exception as e:
            self.root.after(0, self.finish_error_json, str(e))

    def finish_success_json(self, out_file, stats):
        self.btn_json.config(state=tk.NORMAL)
        self.json_type_combo.config(state="readonly")
        self.docx_checkbox.config(state=tk.NORMAL)
        self.status_label_json.config(text="Готово!")
        
        msg = f"Файл успешно конвертирован в JSON!\n\nРезультат сохранен в:\n{os.path.basename(out_file)}\n\nОтчет:\nПолучено JSON-объектов: {stats['processed']}\nОшибок: {stats['errors']}"
        messagebox.showinfo("Успех", msg)

    def finish_error_json(self, err_msg):
        self.btn_json.config(state=tk.NORMAL)
        self.json_type_combo.config(state="readonly")
        self.docx_checkbox.config(state=tk.NORMAL)
        self.status_label_json.config(text="Ошибка!")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Ошибка", f"Произошла ошибка при конвертации:\n{err_msg}")

    def select_file_for_json(self):
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        
        is_docx = self.is_docx_var.get()
        ftypes = (("Документы Word", "*.docx"),) if is_docx else (("Текстовые файлы", "*.txt"), ("Все файлы", "*.*"))
            
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Выберите файл НПА для конвертации в JSON",
            filetypes=ftypes
        )
        if filepath:
            self.btn_json.config(state=tk.DISABLED)
            self.json_type_combo.config(state=tk.DISABLED)
            self.docx_checkbox.config(state=tk.DISABLED)
            self.status_label_json.config(text="Обработка файла, пожалуйста подождите...")
            
            json_type = self.json_type_var.get()
            t = threading.Thread(target=self.process_in_thread_json, args=(filepath, json_type, is_docx))
            t.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonParserApp(root)
    root.mainloop()
