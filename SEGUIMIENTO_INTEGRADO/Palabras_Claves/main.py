#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import re
from collections import defaultdict
from datetime import datetime, timedelta

import scrapy  # type: ignore
from scrapy.crawler import CrawlerProcess  # type: ignore

import tkinter as tk
from tkinter import messagebox

import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

from keybert import KeyBERT  # type: ignore
import threading
import spacy  # type: ignore
import nltk  # type: ignore
from nltk.corpus import stopwords  # type: ignore

# Importar y configurar Crochet (asegúrate de tenerlo instalado: pip install crochet)
import crochet
crochet.setup()

# Descargar stopwords (si aún no están)
nltk.download('stopwords')
spanish_stopwords = set(stopwords.words('spanish'))

# Variables globales para cargar modelos bajo demanda
kw_model = None
nlp = None

def load_models():
    """Carga los modelos KeyBERT y spaCy de forma diferida."""
    global kw_model, nlp
    if kw_model is None:
        kw_model = KeyBERT(model="paraphrase-multilingual-MiniLM-L12-v2")
    if nlp is None:
        nlp = spacy.load("es_core_news_sm")

def extract_page_content(url):
    """Extrae y limpia el contenido principal de una página web."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else "Sin título"
        paragraphs = soup.find_all('p', limit=3)
        content = " ".join([p.get_text(strip=True) for p in paragraphs])
        content = re.sub(r'\s+', ' ', content).strip()
        content = re.sub(r'[^\w\sáéíóúüñÁÉÍÓÚÜÑ]', '', content)
        content = content.lower()
        combined_text = f"{title}. {content}"
        return combined_text if len(combined_text) > 50 else "Error: Contenido insuficiente para procesar."
    except Exception as e:
        return f"Error al procesar la página: {e}"

def clean_and_validate_keywords(keywords):
    """Limpia y valida palabras clave eliminando stopwords y corrigiendo uniones erróneas."""
    validated = []
    for kw in keywords:
        kw = re.sub(r'([a-záéíóúüñ])([A-ZÁÉÍÓÚÜÑ])', r'\1 \2', kw)
        kw = re.sub(r'\s+', ' ', kw).strip().lower()
        doc = nlp(kw)
        tokens = [token.text for token in doc if token.is_alpha and token.text.lower() not in spanish_stopwords]
        if len(tokens) >= 1:
            validated.append(" ".join(tokens))
    return [kw for kw in validated if len(kw.split()) > 1 or len(kw) > 4]

def extract_keywords_combined(url):
    """Extrae palabras clave combinando KeyBERT y validaciones adicionales."""
    load_models()
    content = extract_page_content(url)
    if content.startswith("Error"):
        return [content]
    keybert_keywords = kw_model.extract_keywords(
        content,
        keyphrase_ngram_range=(1, 5),
        stop_words=list(spanish_stopwords),
        use_mmr=True,
        diversity=0.5,
        top_n=15
    )
    keybert_keywords = [kw[0] for kw in keybert_keywords]
    validated = clean_and_validate_keywords(keybert_keywords)
    return list(dict.fromkeys(validated))

# --------------------------------------------------
# Extracción del historial desde history_filtrado.db (sin LIMIT)
# --------------------------------------------------

class FilteredHistoryExtractor:
    """
    Extrae todos los registros de la base de datos filtrada (history_filtrado.db).
    """
    def get_filtered_history_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'perfiles', 'Historial', 'history_filtrado.db'))
    
    def convert_chrome_time(self, chrome_time):
        epoch_start = datetime(1601, 1, 1)
        return epoch_start + timedelta(microseconds=chrome_time)
    
    def extract_history(self):
        db_path = self.get_filtered_history_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError("No se encontró history_filtrado.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = """
        SELECT urls.id, urls.url, urls.title, visits.visit_time, visits.visit_duration
        FROM urls
        JOIN visits ON urls.id = visits.url
        ORDER BY urls.id ASC;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        history_data = []
        for row in results:
            record = {
                "trackedDataID": row[0],
                "urls": [row[1]], 
                "titles": [row[2]],
                "visit_times": [self.convert_chrome_time(row[3]).isoformat() + "Z"],
                "end_times": [(self.convert_chrome_time(row[3]) + timedelta(seconds=(row[4]/1_000_000 if row[4]>0 else 5))).isoformat() + "Z"],
                "durations": [row[4] / 1_000_000 if row[4] > 0 else 5]
            }
            history_data.append(record)
        print(f"FilteredHistoryExtractor: Se extrajeron {len(history_data)} registros.")
        return history_data

# --------------------------------------------------
# Spider de Scrapy para enriquecer cada registro (procesa solo la primera URL de cada registro)
# --------------------------------------------------

class ChromeHistorySpider(scrapy.Spider):
    name = 'chrome_history'
    
    def __init__(self, history_data):
        self.history_data = history_data

    def start_requests(self):
        # Solo procesamos la primera URL de cada registro
        for entry in self.history_data:
            if entry.get('urls'):
                meta = entry.copy()
                meta['url_index'] = 0
                print(f"Procesando registro ID {entry.get('trackedDataID')} con URL: {entry.get('urls')[0]}")
                yield scrapy.Request(
                    url=entry['urls'][0],
                    callback=self.parse_history,
                    meta=meta,
                    dont_filter=True
                )
            else:
                print(f"Registro ID {entry.get('trackedDataID')} sin URL.")

    def infer_activity_type(self, url, title):
        url = url.lower()
        title = title.lower()
        types = {
            "Book": ["goodreads.com", "books.google.com", "amazon.com/books"],
            "Article": ["medium.com", "researchgate.net", "jstor.org", "sciencedirect.com"],
            "Video": ["youtube.com", "vimeo.com", "dailymotion.com", "twitch.tv"],
            "Tool": ["docs.google.com", "drive.google.com", "dropbox.com", "github.com", "stackexchange.com"],
            "Module": ["udacity.com", "coursera.org", "edx.org", "khanacademy.org"],
            "Collaboration": ["zoom.us", "teams.microsoft.com", "slack.com", "meet.google.com"]
        }
        for act, keys in types.items():
            if any(k in url for k in keys):
                return act
        return "Other"

    def infer_domains(self, title, description, additional):
        fields = [
            "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science", "Data Science", "Statistics",
            "Engineering", "Psychology", "Sociology", "Philosophy", "Linguistics", "Economics", "Political Science",
            "Anthropology", "Geography", "Environmental Science", "Law", "History", "Art", "Music", "Theater",
            "Education", "Business", "Finance", "Accounting", "Marketing", "Medicine", "Nursing", "Pharmacy",
            "Neuroscience", "Astronomy", "Geology", "Meteorology", "Oceanography", "Agriculture", "Forestry",
            "Veterinary Science", "Dentistry", "Public Health", "Biomedical Science", "Robotics", "AI", "Machine Learning",
            "Cryptography", "Cybersecurity", "Human-Computer Interaction", "Quantum Physics", "Astrophysics", "Genetics"
        ]
        full_text = f"{title} {description} {additional}".lower()
        relevant = [f for f in fields if f.lower() in full_text]
        return relevant or ["General Knowledge"]

    def extract_description(self, response):
        desc = response.xpath('//*[contains(@name, "description") or contains(@property, "og:description")]/@content').get()
        if not desc:
            headers = response.xpath('//h1/text() | //h2/text()').getall()
            paras = response.xpath('//p/text()').getall()
            desc = ' '.join(headers[:2] + paras[:2]).strip()
        return desc[:300] if desc else None

    def extract_additional_content(self, response):
        headers = response.xpath('//h1/text() | //h2/text()').getall()
        paras = response.xpath('//p/text()').getall()
        return ' '.join(headers + paras)[:1000]

    def extract_keywords(self, response):
        kw = response.xpath('//*[contains(@name, "keywords")]/@content').get()
        if kw:
            return [k.strip() for k in kw.split(",")]
        else:
            alt = extract_keywords_combined(response.url)
            return alt if alt and not all("Error" in x for x in alt) else ["Error: Contenido insuficiente para procesar"]

    def parse_history(self, response):
        meta = response.meta
        if response.status != 200:
            yield {
                "trackedDataID": meta.get("trackedDataID", ""),
                "activityType": self.infer_activity_type(meta['urls'][0], meta['titles'][0]),
                "associatedURL": meta["urls"][0],
                "associatedDomains": [],
                "associatedKeywords": [],
                "startTime": meta.get("visit_times", [""])[0] if meta.get("visit_times") else "",
                "endTime": meta.get("end_times", [""])[0] if meta.get("end_times") else "",
                "feedback": {"score": None, "comments": None}
            }
            return
        try:
            act_type = self.infer_activity_type(meta['urls'][0], meta['titles'][0])
            desc = self.extract_description(response)
            add_cont = self.extract_additional_content(response)
            domains = self.infer_domains(meta['titles'][0], desc, add_cont)
            keywords = self.extract_keywords(response)
            if not keywords or ("Error:" in keywords[0]):
                raise Exception("Contenido insuficiente")
        except Exception as e:
            yield {
                "trackedDataID": meta.get("trackedDataID", ""),
                "activityType": self.infer_activity_type(meta['urls'][0], meta['titles'][0]),
                "associatedURL": meta["urls"][0],
                "associatedDomains": [],
                "associatedKeywords": [],
                "startTime": meta.get("visit_times", [""])[0] if meta.get("visit_times") else "",
                "endTime": meta.get("end_times", [""])[0] if meta.get("end_times") else "",
                "feedback": {"score": None, "comments": None}
            }
            return
        yield {
            "trackedDataID": meta["trackedDataID"],
            "activityType": act_type,
            "associatedURL": meta["urls"][0],
            "associatedDomains": domains,
            "associatedKeywords": keywords,
            "startTime": meta["visit_times"][0],
            "endTime": meta["end_times"][0] if meta.get("end_times") else "",
            "feedback": {"score": None, "comments": None}
        }

# --------------------------------------------------
# Gestión de la base de datos (epai_keywords.sql)
# --------------------------------------------------

def initialize_database():
    db_path = os.path.join(os.getcwd(), 'epai_keywords.sql')
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute("PRAGMA integrity_check;")
            os.remove(db_path)
        except sqlite3.DatabaseError:
            print(f"El archivo '{db_path}' no es una base de datos válida. No se eliminará.")
        except Exception as e:
            print(f"Error al eliminar la base de datos: {e}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS top_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            count INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS top_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            count INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def update_database(data):
    conn = sqlite3.connect('epai_keywords.sql')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM top_keywords')
    cursor.execute('DELETE FROM top_urls')
    cursor.execute('DELETE FROM sqlite_sequence WHERE name="top_keywords"')
    cursor.execute('DELETE FROM sqlite_sequence WHERE name="top_urls"')
    keyword_counts = defaultdict(int)
    url_counts = defaultdict(int)
    for item in data:
        for keyword in item.get('associatedKeywords', []):
            keyword_counts[keyword] += 1
        url = item.get('associatedURL')
        if url:
            url_counts[url] += 1
    for keyword, count in sorted(keyword_counts.items(), key=lambda x: -x[1])[:100]:
        cursor.execute('INSERT INTO top_keywords (keyword, count) VALUES (?, ?)', (keyword, count))
    for url, count in sorted(url_counts.items(), key=lambda x: -x[1])[:30]:
        cursor.execute('INSERT INTO top_urls (url, count) VALUES (?, ?)', (url, count))
    conn.commit()
    conn.close()

class JsonWriterPipeline:
    """Pipeline para almacenar los ítems en un archivo JSON temporal."""
    def open_spider(self, spider):
        self.data = {"userID": 1, "associatedPLE": 1234, "trackedDataList": []}
    def close_spider(self, spider):
        json_path = os.path.join(os.getcwd(), 'chrome_history.json')
        if os.path.exists(json_path):
            os.remove(json_path)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
    def process_item(self, item, spider):
        self.data["trackedDataList"].append(item)
        return item

import __main__
__main__.JsonWriterPipeline = JsonWriterPipeline

@crochet.run_in_reactor
def run_crawler_in_reactor(history_data):
    process = CrawlerProcess(settings={
        "ITEM_PIPELINES": { '__main__.JsonWriterPipeline': 1 },
        "LOG_LEVEL": "INFO",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 0.5,
        "DOWNLOAD_TIMEOUT": 30,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [403, 500, 502, 503, 504],
        "HTTPERROR_ALLOWED_CODES": [403],
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    })
    process.crawl(ChromeHistorySpider, history_data=history_data)
    process.start()
    return "crawl finished"

def run_crawler():
    try:
        extractor = FilteredHistoryExtractor()
        history_data = extractor.extract_history()
        if not history_data:
            raise ValueError("No se extrajeron registros del historial.")
    except Exception as e:
        messagebox.showerror("Error", f"Error al extraer datos de history_filtrado.db:\n{e}")
        return
    initialize_database()
    try:
        run_crawler_in_reactor(history_data).wait(timeout=1800)
    except Exception as e:
        json_path = os.path.join(os.getcwd(), 'chrome_history.json')
        if os.path.exists(json_path):
            messagebox.showwarning("Advertencia", f"Error durante el crawl, pero se generó JSON parcialmente:\n{e}")
        else:
            messagebox.showerror("Error", f"Error durante el crawl y no se generó JSON:\n{e}")
            return
    json_path = os.path.join(os.getcwd(), 'chrome_history.json')
    if not os.path.exists(json_path):
        messagebox.showerror("Error", "No se creó el archivo chrome_history.json.")
        return
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            num_items = len(data.get('trackedDataList', []))
            print(f"run_crawler: Se han extraído {num_items} ítems en total.")
            if num_items == 0:
                raise ValueError("El archivo chrome_history.json está vacío o incompleto.")
    except Exception as e:
        messagebox.showerror("Error", f"Error al leer el JSON extraído:\n{e}")

# --------------------------------------------------
# INTERFAZ GRÁFICA: Extracción y Selección
# --------------------------------------------------

class KeywordExtractionFrame(tk.Frame):
    def __init__(self, parent, on_complete_callback):
        super().__init__(parent)
        self.on_complete_callback = on_complete_callback
        self.create_widgets()
    
    def create_widgets(self):
        tk.Label(self, text="Extracción de Palabras Claves", font=('Helvetica', 16, 'bold')).pack(pady=10)
        self.run_button = tk.Button(self, text="Ejecutar Extracción", command=self.run_extraction)
        self.run_button.pack(pady=10)
    
    def run_extraction(self):
        self.run_button.config(state=tk.DISABLED)
        self.after(100, self.do_extraction)
    
    def do_extraction(self):
        threading.Thread(target=self._extraction_thread).start()
    
    def _extraction_thread(self):
        run_crawler()  # Ejecuta el crawl y genera chrome_history.json
        self.after(0, self.extraction_complete)
    
    def extraction_complete(self):
        messagebox.showinfo("Extracción completada", "Se han extraído los datos. Ahora seleccione los registros a usar.")
        self.on_complete_callback()

class KeywordSelectionFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.items = []
        self.check_vars = []
    
    def load_data(self):
        try:
            with open('chrome_history.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.items = data.get("trackedDataList", [])
            if not self.items:
                raise ValueError("No hay registros extraídos.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los datos extraídos:\n{e}")
    
    def create_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()
        tk.Label(self, text="Selección de Palabras Claves", font=('Helvetica', 16, 'bold')).pack(pady=10)
        canvas = tk.Canvas(self, width=750, height=400)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.check_vars = []
        for idx, item in enumerate(self.items):
            var = tk.BooleanVar(value=True)
            self.check_vars.append(var)
            txt = (f"ID: {item.get('trackedDataID')}\n"
                   f"URL: {item.get('associatedURL','')}\n"
                   f"Actividad: {item.get('activityType','')}\n"
                   f"Palabras: {', '.join(item.get('associatedKeywords', []))}")
            cb = tk.Checkbutton(inner, text=txt, variable=var, anchor="w", justify="left", wraplength=700)
            cb.pack(fill="x", pady=2)
        self.gen_button = tk.Button(self, text="Generar JSON Final", command=self.generate_final_json)
        self.gen_button.pack(pady=10)
    
    def generate_final_json(self):
        final_items = [item for item, var in zip(self.items, self.check_vars) if var.get()]
        if not final_items:
            messagebox.showerror("Error", "No se ha seleccionado ningún registro.")
            return
        final_data = {"userID": 1, "associatedPLE": 1234, "trackedDataList": final_items}
        try:
            final_path = os.path.join(os.getcwd(), "final_keywords.json")
            if os.path.exists(final_path):
                os.remove(final_path)
            with open(final_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Éxito", "JSON final generado como 'final_keywords.json'.")
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar el JSON final:\n{e}")

class KeywordTracker(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.extraction_frame = KeywordExtractionFrame(self, self.show_selection_frame)
        self.selection_frame = KeywordSelectionFrame(self)
        self.extraction_frame.pack(fill="both", expand=True)
    
    def show_selection_frame(self):
        self.extraction_frame.pack_forget()
        self.selection_frame.load_data()
        self.selection_frame.create_widgets()
        self.selection_frame.pack(fill="both", expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Palabras Claves")
    tracker = KeywordTracker(root)
    tracker.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    root.mainloop()