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

def process_json_file(filepath, json_type, progress_callback=None):
    from parsers import json_parser_articles, json_parser_points
    lines = detect_encoding_and_read(filepath)
    file_id = os.path.splitext(os.path.basename(filepath))[0]
    
    parsed_type = None
    if "1.St" in json_type or "6.FZ" in json_type or "7.FZ" in json_type or "8.St" in json_type or "9.Glava" in json_type:
        parsed_type = "articles"
    elif "2.PP" in json_type or "4.PP" in json_type or "5.PP" in json_type or "10.Plenum" in json_type:
        parsed_type = "points"
        
    if not parsed_type:
        raise Exception("Алгоритмы для работы этого файла пока не прописаны.")
        
    if progress_callback:
        progress_callback("Анализ и конвертация структуры...")
        
    if parsed_type == "articles":
        result_elements = json_parser_articles.parse_to_json(lines, file_id)
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
        self.root.geometry("550x300")
        self.root.eval('tk::PlaceWindow . center')
        self.root.configure(padx=20, pady=20)
        
        title_label_json = tk.Label(root, text="Конвертация НПА в JSON", font=("Arial", 14, "bold"))
        title_label_json.pack(pady=(10, 10))
        
        desc_label_json = tk.Label(
            root, 
            text="Выберите .txt файл для извлечения структуры и конвертации в JSON.\nСкрипт создаст массив объектов для каждой статьи/пункта.", 
            font=("Arial", 10), justify=tk.CENTER
        )
        desc_label_json.pack(pady=(0, 20))

        # Выпадающий список для JSON
        # Path to data directory (assuming it's in the parent directory relative to this script)
        json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'Conv_to_json')
        json_files = []
        if os.path.exists(json_dir):
            for f in sorted(os.listdir(json_dir)):
                if f.endswith('.txt'):
                    json_files.append(f)

        self.json_type_var = tk.StringVar()
        self.json_type_combo = ttk.Combobox(
            root, 
            textvariable=self.json_type_var,
            values=json_files if json_files else ["Нет файлов .txt"],
            state="readonly",
            width=50,
            font=("Arial", 10)
        )
        if json_files:
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

    def update_status_json(self, text):
        self.status_label_json.config(text=text)

    def process_in_thread_json(self, filepath, json_type):
        try:
            out_file, stats = process_json_file(
                filepath,
                json_type,
                progress_callback=lambda msg: self.root.after(0, self.update_status_json, msg)
            )
            self.root.after(0, self.finish_success_json, out_file, stats)
        except Exception as e:
            self.root.after(0, self.finish_error_json, str(e))

    def finish_success_json(self, out_file, stats):
        self.btn_json.config(state=tk.NORMAL)
        self.json_type_combo.config(state="readonly")
        self.status_label_json.config(text="Готово!")
        
        msg = f"Файл успешно конвертирован в JSON!\n\nРезультат сохранен в:\n{os.path.basename(out_file)}\n\nОтчет:\nПолучено JSON-объектов: {stats['processed']}\nОшибок: {stats['errors']}"
        messagebox.showinfo("Успех", msg)

    def finish_error_json(self, err_msg):
        self.btn_json.config(state=tk.NORMAL)
        self.json_type_combo.config(state="readonly")
        self.status_label_json.config(text="Ошибка!")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Ошибка", f"Произошла ошибка при конвертации:\n{err_msg}")

    def select_file_for_json(self):
        initial_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        conv_dir = os.path.join(initial_dir, 'data', 'Conv_to_json')
        if os.path.exists(conv_dir):
            initial_dir = conv_dir
            
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Выберите файл НПА для конвертации в JSON",
            filetypes=(("Текстовые файлы", "*.txt"), ("Все файлы", "*.*"))
        )
        if filepath:
            self.btn_json.config(state=tk.DISABLED)
            self.json_type_combo.config(state=tk.DISABLED)
            self.status_label_json.config(text="Обработка файла, пожалуйста подождите...")
            
            json_type = self.json_type_var.get()
            t = threading.Thread(target=self.process_in_thread_json, args=(filepath, json_type))
            t.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonParserApp(root)
    root.mainloop()
