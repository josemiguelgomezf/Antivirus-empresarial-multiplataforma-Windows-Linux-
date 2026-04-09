# Antivirus empresarial multiplataforma (Windows/Linux)
# Stack: FastAPI + Tkinter + MySQL + psutil + hashlib + watchdog
# Autor: José Miguel Gómez Fernández

import threading
import hashlib
import psutil
import time
import os

from fastapi import FastAPI
import uvicorn

import tkinter as tk
from tkinter import filedialog, messagebox

# ==========================
# CONFIGURACIÓN MYSQL
# ==========================
try:
    import mysql.connector
    MYSQL_ENABLED = True
except ImportError:
    MYSQL_ENABLED = False

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "antivirus"
}

# ==========================
# BASE DE DATOS
# ==========================
class Database:
    def __init__(self):
        self.conn = None
        if MYSQL_ENABLED:
            try:
                self.conn = mysql.connector.connect(**DB_CONFIG)
                self.cursor = self.conn.cursor()
                self.init_db()
            except Exception as e:
                print("[DB] Error conexión MySQL:", e)
                self.conn = None

    def init_db(self):
        query = """
        CREATE TABLE IF NOT EXISTS signatures (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hash VARCHAR(255) UNIQUE
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    def add_signature(self, file_hash):
        if not self.conn:
            return
        try:
            self.cursor.execute("INSERT INTO signatures (hash) VALUES (%s)", (file_hash,))
            self.conn.commit()
        except:
            pass

    def get_signatures(self):
        if not self.conn:
            return []
        self.cursor.execute("SELECT hash FROM signatures")
        return [row[0] for row in self.cursor.fetchall()]

# ==========================
# MOTOR ANTIVIRUS
# ==========================
class AntivirusEngine:
    def __init__(self, db):
        self.db = db
        self.alerts = []

    def calculate_hash(self, file_path):
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except:
            return None

    def scan_file(self, file_path):
        file_hash = self.calculate_hash(file_path)
        if not file_hash:
            return "ERROR"

        signatures = self.db.get_signatures()

        if file_hash in signatures:
            alert = f"Amenaza detectada: {file_path}"
            self.alerts.append(alert)
            return "MALICIOUS"

        return "CLEAN"

    def heuristic_check(self, process):
        try:
            name = process.name().lower()
            if "malware" in name or "virus" in name:
                return True
        except:
            pass
        return False

    def monitor_processes(self):
        while True:
            for proc in psutil.process_iter(['pid', 'name']):
                if self.heuristic_check(proc):
                    alert = f"Proceso sospechoso: {proc.info['name']}"
                    self.alerts.append(alert)
            time.sleep(5)

# ==========================
# FASTAPI BACKEND
# ==========================
app = FastAPI()
db = Database()
engine = AntivirusEngine(db)

@app.get("/")
def home():
    return {"status": "Antivirus activo"}

@app.get("/alerts")
def get_alerts():
    return {"alerts": engine.alerts}

@app.post("/scan")
def scan(path: str):
    result = engine.scan_file(path)
    return {"file": path, "result": result}

# ==========================
# WATCHDOG (monitor archivos simple)
# ==========================
class FileMonitor:
    def __init__(self, engine, path="."):
        self.engine = engine
        self.path = path

    def scan_directory(self):
        for root, dirs, files in os.walk(self.path):
            for file in files:
                full_path = os.path.join(root, file)
                self.engine.scan_file(full_path)

# ==========================
# TKINTER FRONTEND
# ==========================
class AntivirusGUI:
    def __init__(self, root, engine):
        self.engine = engine
        self.root = root
        self.root.title("Antivirus Empresarial")

        self.label = tk.Label(root, text="Antivirus en ejecución")
        self.label.pack()

        self.scan_button = tk.Button(root, text="Escanear archivo", command=self.scan_file)
        self.scan_button.pack()

        self.alerts_box = tk.Text(root, height=15, width=50)
        self.alerts_box.pack()

        self.refresh_alerts()

    def scan_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            result = self.engine.scan_file(file_path)
            messagebox.showinfo("Resultado", result)

    def refresh_alerts(self):
        self.alerts_box.delete("1.0", tk.END)
        for alert in self.engine.alerts:
            self.alerts_box.insert(tk.END, alert + "\n")
        self.root.after(3000, self.refresh_alerts)

# ==========================
# EJECUCIÓN
# ==========================

def run_api():
    uvicorn.run(app, host="127.0.0.1", port=8000)


def run_process_monitor():
    engine.monitor_processes()


def main():
    # Threads backend
    threading.Thread(target=run_api, daemon=True).start()
    threading.Thread(target=run_process_monitor, daemon=True).start()

    # GUI
    root = tk.Tk()
    gui = AntivirusGUI(root, engine)
    root.mainloop()


if __name__ == "__main__":
    main()
