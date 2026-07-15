"""
Antivirus Empresarial Multiplataforma (Windows/Linux)
Stack:
- FastAPI (API REST local)
- Tkinter (interfaz gráfica)
- SQLite (base de datos local)
- psutil (monitorización de procesos)
- hashlib (firmas SHA256)
- logging (logs locales)

Autor: José Miguel Gómez Fernández
TFM - Uso exclusivamente local
Versión 2.0 - Mejorada
"""

import threading
import hashlib
import time
import os
import sqlite3
import logging
import json
import re
import mimetypes
import platform
import struct
import math
import random
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# ==========================
# DEPENDENCIAS OPCIONALES
# ==========================
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[WARN] psutil no está instalado. Instálalo con: pip install psutil")

try:
    from fastapi import FastAPI, Query
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("[WARN] FastAPI o uvicorn no están instalados. Instálalo con: pip install fastapi uvicorn")

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont

# ==========================
# CONFIGURACIÓN
# ==========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR  = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

DB_PATH  = DATA_DIR / "antivirus.db"
LOG_PATH = LOG_DIR  / "antivirus.log"

APP_VERSION = "2.0.0"
APP_AUTHOR  = "José Miguel Gómez Fernández"

# ==========================
# LOGGING
# ==========================
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)
logging.info("=== Inicio del Antivirus Empresarial v2.0 ===")


# ==========================
# PALETA DE COLORES
# ==========================
COLORS = {
    "bg_dark":      "#0a0e1a",
    "bg_panel":     "#0f1629",
    "bg_card":      "#141d35",
    "accent_blue":  "#00aaff",
    "accent_cyan":  "#00e5ff",
    "accent_green": "#00ff88",
    "accent_red":   "#ff3366",
    "accent_orange":"#ff8800",
    "accent_purple":"#aa44ff",
    "text_primary": "#e8f0ff",
    "text_secondary":"#7890b0",
    "text_dim":     "#3a4a6a",
    "border":       "#1e2d4a",
    "success":      "#00cc66",
    "warning":      "#ffaa00",
    "danger":       "#ff2244",
    "info":         "#0088ff",
}

# ==========================
# BASE DE DATOS SQLITE
# ==========================
class Database:
    def __init__(self, db_path=DB_PATH):
        self.conn   = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._lock  = threading.Lock()
        self.init_db()

    def init_db(self):
        with self._lock:
            self.cursor.executescript("""
                CREATE TABLE IF NOT EXISTS signatures (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash      TEXT UNIQUE NOT NULL,
                    name      TEXT,
                    threat_type TEXT DEFAULT 'UNKNOWN',
                    added_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    severity   TEXT DEFAULT 'MEDIUM',
                    category   TEXT DEFAULT 'GENERAL',
                    message    TEXT NOT NULL,
                    resolved   INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS scan_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    scan_type   TEXT,
                    path        TEXT,
                    files_scanned INTEGER DEFAULT 0,
                    threats_found INTEGER DEFAULT 0,
                    duration_sec  REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS quarantine (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    original_path TEXT,
                    file_hash   TEXT,
                    threat_name TEXT,
                    status      TEXT DEFAULT 'QUARANTINED'
                );

                CREATE TABLE IF NOT EXISTS code_analysis (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    language    TEXT,
                    analyzed_by TEXT,
                    risk_level  TEXT,
                    issues_found INTEGER DEFAULT 0,
                    report      TEXT
                );
            """)
            self.conn.commit()

            # Seed firmas de ejemplo si la tabla está vacía
            self.cursor.execute("SELECT COUNT(*) FROM signatures")
            if self.cursor.fetchone()[0] == 0:
                self._seed_signatures()

    def _seed_signatures(self):
        """Firmas de malware conocido (hashes ficticios para demo)"""
        demo_sigs = [
            ("44d88612fea8a8f36de82e1278abb02f", "EICAR-Test-File",          "EICAR"),
            ("a3a3e41db44c21edd3f5d040e38b55eb", "Trojan.GenericKD.46587123", "TROJAN"),
            ("b5dc4e5fa3d36c7e4c2b1a3f8d9e0a2c", "Ransomware.WannaCry.Var",  "RANSOMWARE"),
            ("c6ef4f2a3b5d8e1c9f0a2b4d6e8f0a1b", "Adware.BrowseFox.C",       "ADWARE"),
            ("d7fg5g3b4c6d9e2c0a3b5d7f9a0b2d4", "Spyware.AgentTesla.Gen",   "SPYWARE"),
        ]
        for h, name, ttype in demo_sigs:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO signatures (hash, name, threat_type) VALUES (?,?,?)",
                    (h, name, ttype)
                )
            except Exception:
                pass
        self.conn.commit()

    # ---- Signatures ----
    def add_signature(self, file_hash, name="", threat_type="UNKNOWN"):
        with self._lock:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO signatures (hash, name, threat_type) VALUES (?,?,?)",
                    (file_hash, name, threat_type)
                )
                self.conn.commit()
            except Exception as e:
                logging.error(f"Error insertando firma: {e}")

    def get_signatures(self):
        with self._lock:
            self.cursor.execute("SELECT hash FROM signatures")
            return [row[0] for row in self.cursor.fetchall()]

    def get_signature_count(self):
        with self._lock:
            self.cursor.execute("SELECT COUNT(*) FROM signatures")
            return self.cursor.fetchone()[0]

    # ---- Alerts ----
    def add_alert(self, message, severity="MEDIUM", category="GENERAL"):
        with self._lock:
            self.cursor.execute(
                "INSERT INTO alerts (message, severity, category) VALUES (?,?,?)",
                (message, severity, category)
            )
            self.conn.commit()

    def get_alerts(self, limit=200):
        with self._lock:
            self.cursor.execute("""
                SELECT timestamp, severity, category, message, id
                FROM alerts ORDER BY id DESC LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()

    def get_alert_stats(self):
        with self._lock:
            self.cursor.execute("""
                SELECT severity, COUNT(*) FROM alerts GROUP BY severity
            """)
            return dict(self.cursor.fetchall())

    def resolve_alert(self, alert_id):
        with self._lock:
            self.cursor.execute(
                "UPDATE alerts SET resolved=1 WHERE id=?", (alert_id,)
            )
            self.conn.commit()

    # ---- Scan History ----
    def add_scan(self, scan_type, path, files_scanned, threats_found, duration):
        with self._lock:
            self.cursor.execute("""
                INSERT INTO scan_history (scan_type, path, files_scanned, threats_found, duration_sec)
                VALUES (?,?,?,?,?)
            """, (scan_type, path, files_scanned, threats_found, duration))
            self.conn.commit()

    def get_scan_history(self, limit=50):
        with self._lock:
            self.cursor.execute("""
                SELECT timestamp, scan_type, path, files_scanned, threats_found, duration_sec
                FROM scan_history ORDER BY id DESC LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()

    def get_scan_stats(self):
        with self._lock:
            self.cursor.execute("""
                SELECT SUM(files_scanned), SUM(threats_found), COUNT(*)
                FROM scan_history
            """)
            row = self.cursor.fetchone()
            return {
                "total_files":   row[0] or 0,
                "total_threats": row[1] or 0,
                "total_scans":   row[2] or 0,
            }

    # ---- Quarantine ----
    def add_quarantine(self, original_path, file_hash, threat_name):
        with self._lock:
            self.cursor.execute("""
                INSERT INTO quarantine (original_path, file_hash, threat_name)
                VALUES (?,?,?)
            """, (original_path, file_hash, threat_name))
            self.conn.commit()

    def get_quarantine(self):
        with self._lock:
            self.cursor.execute("""
                SELECT id, timestamp, original_path, threat_name, status
                FROM quarantine ORDER BY id DESC
            """)
            return self.cursor.fetchall()

    # ---- Code Analysis ----
    def add_code_analysis(self, language, analyzed_by, risk_level, issues_found, report):
        with self._lock:
            self.cursor.execute("""
                INSERT INTO code_analysis (language, analyzed_by, risk_level, issues_found, report)
                VALUES (?,?,?,?,?)
            """, (language, analyzed_by, risk_level, issues_found, report))
            self.conn.commit()

    def get_code_analysis_history(self, limit=20):
        with self._lock:
            self.cursor.execute("""
                SELECT timestamp, language, analyzed_by, risk_level, issues_found
                FROM code_analysis ORDER BY id DESC LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()


# ==========================
# ANALIZADOR DE MALWARE MULTIMEDIA
# ==========================
class MultimediaAnalyzer:
    """Analiza archivos multimedia en busca de técnicas de esteganografía y exploits conocidos"""

    MULTIMEDIA_EXTENSIONS = {
        "image":  [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".ico", ".svg"],
        "video":  [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
        "audio":  [".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a"],
        "doc":    [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"],
    }

    # Firmas de formatos conocidos (magic bytes)
    MAGIC_BYTES = {
        b"\xFF\xD8\xFF":          ("JPEG", "image"),
        b"\x89PNG\r\n\x1a\n":    ("PNG",  "image"),
        b"GIF87a":                ("GIF",  "image"),
        b"GIF89a":                ("GIF",  "image"),
        b"BM":                    ("BMP",  "image"),
        b"\x00\x00\x01\x00":     ("ICO",  "image"),
        b"RIFF":                  ("AVI/WAV", "media"),
        b"\x1aE\xdf\xa3":        ("MKV",  "video"),
        b"ftyp":                  ("MP4",  "video"),
        b"ID3":                   ("MP3",  "audio"),
        b"%PDF":                  ("PDF",  "doc"),
        b"PK\x03\x04":           ("ZIP/DOCX/XLSX", "doc"),
    }

    # Patrones sospechosos dentro de archivos multimedia
    SUSPICIOUS_PATTERNS = [
        (b"<script",       "Script embebido en archivo multimedia",  "HIGH"),
        (b"javascript:",   "Referencia a javascript en binario",      "HIGH"),
        (b"eval(",         "Llamada eval() sospechosa",               "MEDIUM"),
        (b"powershell",    "Referencia a PowerShell",                 "HIGH"),
        (b"cmd.exe",       "Referencia a CMD",                        "HIGH"),
        (b"/bin/sh",       "Referencia a shell Unix",                 "HIGH"),
        (b"base64",        "Posible payload base64",                  "MEDIUM"),
        (b"http://",       "URL HTTP embebida",                       "LOW"),
        (b"https://",      "URL HTTPS embebida",                      "LOW"),
        (b"\x4d\x5a",     "Ejecutable PE embebido (MZ header)",       "CRITICAL"),
        (b"\x7fELF",      "Binario ELF embebido",                    "CRITICAL"),
        (b"IHDR" + b"\x00"*8, "Posible manipulación de chunk PNG",   "LOW"),
    ]

    def __init__(self):
        pass

    def get_file_type(self, file_path):
        ext = Path(file_path).suffix.lower()
        for ftype, exts in self.MULTIMEDIA_EXTENSIONS.items():
            if ext in exts:
                return ftype
        return None

    def detect_magic_bytes(self, data):
        for magic, (fmt, ftype) in self.MAGIC_BYTES.items():
            if data.startswith(magic):
                return fmt, ftype
        return "UNKNOWN", "unknown"

    def check_extension_mismatch(self, file_path, detected_format):
        ext = Path(file_path).suffix.lower()
        ext_map = {
            ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
            ".gif": "GIF",  ".bmp": "BMP",   ".pdf": "PDF",
            ".mp3": "MP3",
        }
        declared = ext_map.get(ext, "")
        if declared and detected_format != "UNKNOWN" and declared not in detected_format:
            return True
        return False

    def analyze_entropy(self, data):
        """Calcula entropía de Shannon — alta entropía puede indicar cifrado/compresión maliciosa"""
        if not data:
            return 0.0
        freq = defaultdict(int)
        for byte in data:
            freq[byte] += 1
        n = len(data)
        entropy = -sum((c/n) * math.log2(c/n) for c in freq.values())
        return round(entropy, 3)

    def analyze_file(self, file_path):
        results = {
            "file":           file_path,
            "size_bytes":     0,
            "file_type":      "UNKNOWN",
            "detected_format": "UNKNOWN",
            "extension_mismatch": False,
            "entropy":        0.0,
            "high_entropy":   False,
            "suspicious_patterns": [],
            "risk_level":     "CLEAN",
            "details":        [],
        }

        try:
            size = os.path.getsize(file_path)
            results["size_bytes"] = size

            if size > 50 * 1024 * 1024:  # máx 50 MB para análisis
                results["details"].append("Archivo demasiado grande para análisis completo (>50 MB)")
                read_size = 1024 * 1024
            else:
                read_size = size

            with open(file_path, "rb") as f:
                data = f.read(read_size)

            fmt, ftype = self.detect_magic_bytes(data)
            results["detected_format"] = fmt
            results["file_type"]       = ftype

            # Comprobación de tipo por extensión
            ext_type = self.get_file_type(file_path)
            if ext_type:
                results["extension_mismatch"] = self.check_extension_mismatch(file_path, fmt)
                if results["extension_mismatch"]:
                    results["details"].append(
                        f"ALERTA: El tipo real del archivo ({fmt}) no coincide con la extensión"
                    )

            # Entropía
            entropy = self.analyze_entropy(data[:65536])  # primeros 64 KB
            results["entropy"]      = entropy
            results["high_entropy"] = entropy > 7.2
            if results["high_entropy"]:
                results["details"].append(
                    f"Entropía alta ({entropy}) — posible contenido cifrado o comprimido sospechoso"
                )

            # Búsqueda de patrones sospechosos
            max_sev = "CLEAN"
            sev_order = {"CLEAN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
            for pattern, desc, sev in self.SUSPICIOUS_PATTERNS:
                if pattern in data:
                    results["suspicious_patterns"].append({
                        "pattern": desc,
                        "severity": sev
                    })
                    results["details"].append(f"[{sev}] {desc}")
                    if sev_order.get(sev, 0) > sev_order.get(max_sev, 0):
                        max_sev = sev

            if max_sev != "CLEAN":
                results["risk_level"] = max_sev
            elif results["high_entropy"] or results["extension_mismatch"]:
                results["risk_level"] = "MEDIUM"
            else:
                results["risk_level"] = "CLEAN"

        except PermissionError:
            results["details"].append("Sin permisos para leer el archivo")
            results["risk_level"] = "ERROR"
        except Exception as e:
            results["details"].append(f"Error durante el análisis: {e}")
            results["risk_level"] = "ERROR"

        return results


# ==========================
# ANALIZADOR DE CÓDIGO FUENTE
# ==========================
class CodeSecurityAnalyzer:
    """
    Analiza código fuente en texto plano en busca de vulnerabilidades de seguridad.
    Soporta detección de lenguaje y permite especificar el programador para el informe.
    """

    LANGUAGES = {
        "Python":     [".py"],
        "JavaScript": [".js", ".mjs", ".cjs"],
        "TypeScript": [".ts", ".tsx"],
        "Java":       [".java"],
        "C/C++":      [".c", ".cpp", ".h", ".hpp"],
        "PHP":        [".php"],
        "Ruby":       [".rb"],
        "Go":         [".go"],
        "Rust":       [".rs"],
        "Shell":      [".sh", ".bash"],
        "PowerShell": [".ps1"],
        "SQL":        [".sql"],
        "Generic":    [],
    }

    # (patrón regex, descripción, severidad, categoría CWE)
    VULN_PATTERNS = {
        "Python": [
            (r"eval\s*\(",                 "Uso de eval() — ejecución de código arbitrario",           "CRITICAL", "CWE-95"),
            (r"exec\s*\(",                 "Uso de exec() — ejecución de código arbitrario",           "CRITICAL", "CWE-95"),
            (r"__import__\s*\(",           "Import dinámico sospechoso",                               "HIGH",     "CWE-95"),
            (r"subprocess\.call\s*\(.*shell\s*=\s*True", "subprocess con shell=True — inyección de comandos", "CRITICAL", "CWE-78"),
            (r"os\.system\s*\(",           "os.system() — riesgo de inyección de comandos",            "HIGH",     "CWE-78"),
            (r"pickle\.loads?\s*\(",       "Deserialización insegura con pickle",                      "HIGH",     "CWE-502"),
            (r"yaml\.load\s*\([^,)]+\)",   "yaml.load sin Loader seguro",                             "MEDIUM",   "CWE-502"),
            (r"input\s*\(.*password",      "Lectura de contraseña con input()",                        "LOW",      "CWE-312"),
            (r"hashlib\.(md5|sha1)\s*\(",  "Uso de MD5/SHA1 (débiles para contraseñas)",               "MEDIUM",   "CWE-327"),
            (r"random\.(random|randint)",  "Uso de random no criptográfico",                           "LOW",      "CWE-338"),
            (r"SQL\s*=.*\+.*",             "Posible concatenación de SQL (SQL Injection)",             "HIGH",     "CWE-89"),
            (r"cursor\.execute\(.*%.*%",   "SQL con formato string — riesgo de SQL Injection",        "HIGH",     "CWE-89"),
            (r"open\(.*['\"]w['\"].*\).*input", "Escritura de archivo con entrada del usuario",        "MEDIUM",   "CWE-73"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Contraseña hardcodeada",                           "HIGH",     "CWE-259"),
            (r"secret\s*=\s*['\"][^'\"]+['\"]",   "Secreto hardcodeado",                              "HIGH",     "CWE-259"),
            (r"token\s*=\s*['\"][^'\"]+['\"]",    "Token hardcodeado",                                "HIGH",     "CWE-259"),
            (r"DEBUG\s*=\s*True",          "Modo DEBUG habilitado",                                    "LOW",      "CWE-489"),
            (r"verify\s*=\s*False",        "Verificación SSL deshabilitada",                           "HIGH",     "CWE-295"),
        ],
        "JavaScript": [
            (r"eval\s*\(",                 "Uso de eval() — ejecución de código arbitrario",           "CRITICAL", "CWE-95"),
            (r"innerHTML\s*=",             "Asignación directa a innerHTML — riesgo de XSS",           "HIGH",     "CWE-79"),
            (r"document\.write\s*\(",      "document.write() — riesgo de XSS",                        "HIGH",     "CWE-79"),
            (r"\.dangerouslySetInnerHTML", "dangerouslySetInnerHTML — riesgo de XSS (React)",          "HIGH",     "CWE-79"),
            (r"Math\.random\s*\(\)",       "Math.random() no es criptográficamente seguro",            "LOW",      "CWE-338"),
            (r"localStorage\.(set|get)Item\(.*password", "Contraseña en localStorage",                "HIGH",     "CWE-312"),
            (r"console\.(log|warn|error)\(.*password", "Contraseña en log",                           "MEDIUM",   "CWE-312"),
            (r"password\s*[:=]\s*['\"][^'\"]+['\"]", "Contraseña hardcodeada",                       "HIGH",     "CWE-259"),
            (r"https?://[^'\"\s]+",        "URL hardcodeada (revisar si expone endpoints)",            "LOW",      "CWE-312"),
            (r"require\s*\([^)]*\$",       "require() con variable — posible Path Traversal",         "MEDIUM",   "CWE-22"),
            (r"child_process",             "Uso de child_process — riesgo de inyección",               "HIGH",     "CWE-78"),
        ],
        "Java": [
            (r"Runtime\.getRuntime\(\)\.exec", "exec() de Runtime — inyección de comandos",           "CRITICAL", "CWE-78"),
            (r"Class\.forName\s*\(",       "Carga dinámica de clase",                                  "MEDIUM",   "CWE-470"),
            (r"ObjectInputStream",         "Deserialización con ObjectInputStream",                    "HIGH",     "CWE-502"),
            (r"MessageDigest\.getInstance\(['\"]MD5['\"]", "Uso de MD5",                              "MEDIUM",   "CWE-327"),
            (r"MessageDigest\.getInstance\(['\"]SHA-1['\"]", "Uso de SHA-1",                          "MEDIUM",   "CWE-327"),
            (r"prepareStatement\(.*\+",    "Concatenación en PreparedStatement — SQL Injection",       "HIGH",     "CWE-89"),
            (r"password\s*=\s*\"[^\"]+\"", "Contraseña hardcodeada",                                  "HIGH",     "CWE-259"),
            (r"e\.printStackTrace\(\)",    "Exposición de stack trace al usuario",                     "LOW",      "CWE-209"),
            (r"System\.exit\s*\(",         "System.exit() en código de producción",                    "LOW",      "CWE-382"),
            (r"random\s*=\s*new\s+Random\(\)", "java.util.Random — no criptográfico",                 "LOW",      "CWE-338"),
        ],
        "PHP": [
            (r"eval\s*\(",                 "eval() — ejecución de código arbitrario",                  "CRITICAL", "CWE-95"),
            (r"exec\s*\(",                 "exec() — inyección de comandos",                           "CRITICAL", "CWE-78"),
            (r"system\s*\(",               "system() — inyección de comandos",                         "CRITICAL", "CWE-78"),
            (r"shell_exec\s*\(",           "shell_exec() — inyección de comandos",                     "CRITICAL", "CWE-78"),
            (r"\$_GET\[",                  "Uso directo de $_GET (sin sanitización)",                   "MEDIUM",   "CWE-20"),
            (r"\$_POST\[",                 "Uso directo de $_POST (sin sanitización)",                  "MEDIUM",   "CWE-20"),
            (r"mysql_query\s*\(",          "mysql_query() obsoleto y vulnerable",                      "HIGH",     "CWE-89"),
            (r"md5\s*\(",                  "Uso de md5() para contraseñas",                            "HIGH",     "CWE-327"),
            (r"include\s*\(\s*\$",         "include() con variable — LFI",                             "CRITICAL", "CWE-98"),
            (r"require\s*\(\s*\$",         "require() con variable — LFI",                             "CRITICAL", "CWE-98"),
        ],
        "SQL": [
            (r"'.*'.*OR.*'.*'=",          "Patrón clásico de SQL Injection",                          "CRITICAL", "CWE-89"),
            (r"DROP\s+TABLE",             "DROP TABLE — riesgo de destrucción de datos",               "HIGH",     "CWE-89"),
            (r"GRANT\s+ALL",              "GRANT ALL — permisos excesivos",                            "MEDIUM",   "CWE-269"),
            (r"xp_cmdshell",              "xp_cmdshell — ejecución de comandos en MSSQL",              "CRITICAL", "CWE-78"),
            (r"--\s*$",                   "Comentario de línea (posible truncado de query)",           "LOW",      "CWE-89"),
        ],
        "Shell": [
            (r"eval\s+\$",                "eval con variable — inyección de comandos",                 "CRITICAL", "CWE-78"),
            (r"curl\s+.*\|\s*sh",         "Descarga y ejecución de script remoto",                    "CRITICAL", "CWE-494"),
            (r"wget\s+.*\|\s*sh",         "Descarga y ejecución de script remoto",                    "CRITICAL", "CWE-494"),
            (r"chmod\s+777",              "Permisos 777 — acceso universal",                           "HIGH",     "CWE-732"),
            (r"rm\s+-rf\s+/",             "rm -rf / — eliminación recursiva de root",                  "CRITICAL", "CWE-73"),
            (r":\(\)\{.*\|.*&\}",         "Fork bomb detectada",                                       "CRITICAL", "CWE-400"),
            (r"PASSWORD=",                "Contraseña en variable de entorno de script",               "HIGH",     "CWE-312"),
        ],
        "Generic": [
            (r"(?i)password\s*=\s*['\"][^'\"]{3,}['\"]", "Contraseña hardcodeada",                   "HIGH",     "CWE-259"),
            (r"(?i)api_key\s*=\s*['\"][^'\"]{8,}['\"]",  "API key hardcodeada",                      "HIGH",     "CWE-259"),
            (r"(?i)secret\s*=\s*['\"][^'\"]{3,}['\"]",   "Secreto hardcodeado",                      "HIGH",     "CWE-259"),
            (r"(?i)token\s*=\s*['\"][^'\"]{8,}['\"]",    "Token hardcodeado",                        "HIGH",     "CWE-259"),
            (r"10\.\d+\.\d+\.\d+",        "Dirección IP privada hardcodeada",                         "LOW",      "CWE-312"),
            (r"192\.168\.\d+\.\d+",       "IP de red local hardcodeada",                              "LOW",      "CWE-312"),
        ],
    }

    RISK_WEIGHTS = {"CRITICAL": 40, "HIGH": 15, "MEDIUM": 5, "LOW": 1}

    def detect_language(self, code_text, hint_lang=None, filename=None):
        if hint_lang and hint_lang in self.LANGUAGES:
            return hint_lang

        if filename:
            ext = Path(filename).suffix.lower()
            for lang, exts in self.LANGUAGES.items():
                if ext in exts:
                    return lang

        # Heurísticas básicas
        if "def " in code_text and "import " in code_text:
            return "Python"
        if "function " in code_text and ("var " in code_text or "let " in code_text or "const " in code_text):
            return "JavaScript"
        if "public class " in code_text or "import java." in code_text:
            return "Java"
        if "<?php" in code_text:
            return "PHP"
        if "#!/bin/bash" in code_text or "#!/bin/sh" in code_text:
            return "Shell"
        if "SELECT " in code_text.upper() and "FROM " in code_text.upper():
            return "SQL"

        return "Generic"

    def analyze(self, code_text, language=None, filename=None, analyzed_by="Desconocido"):
        lang = self.detect_language(code_text, language, filename)
        patterns = self.VULN_PATTERNS.get(lang, []) + self.VULN_PATTERNS.get("Generic", [])

        issues = []
        score  = 0

        lines = code_text.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern, desc, sev, cwe in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "line":        line_num,
                        "line_content": line.strip()[:120],
                        "description": desc,
                        "severity":    sev,
                        "cwe":         cwe,
                    })
                    score += self.RISK_WEIGHTS.get(sev, 0)

        # Deduplicar por descripción + línea
        seen = set()
        unique_issues = []
        for issue in issues:
            key = (issue["description"], issue["line"])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        # Risk level
        if score == 0:
            risk_level = "LIMPIO"
        elif score < 10:
            risk_level = "BAJO"
        elif score < 30:
            risk_level = "MEDIO"
        elif score < 70:
            risk_level = "ALTO"
        else:
            risk_level = "CRÍTICO"

        report = {
            "language":    lang,
            "analyzed_by": analyzed_by,
            "risk_level":  risk_level,
            "risk_score":  score,
            "issues_count": len(unique_issues),
            "issues":      unique_issues,
            "lines_analyzed": len(lines),
            "timestamp":   datetime.now().isoformat(),
            "summary": self._generate_summary(lang, unique_issues, risk_level, analyzed_by, score)
        }
        return report

    def _generate_summary(self, lang, issues, risk_level, analyzed_by, score):
        critical = sum(1 for i in issues if i["severity"] == "CRITICAL")
        high     = sum(1 for i in issues if i["severity"] == "HIGH")
        medium   = sum(1 for i in issues if i["severity"] == "MEDIUM")
        low      = sum(1 for i in issues if i["severity"] == "LOW")

        lines = [
            f"── INFORME DE SEGURIDAD DE CÓDIGO ──",
            f"Lenguaje detectado : {lang}",
            f"Analista           : {analyzed_by}",
            f"Nivel de riesgo    : {risk_level}  (Puntuación: {score})",
            f"Total de problemas : {len(issues)}",
            f"  · CRÍTICO        : {critical}",
            f"  · ALTO           : {high}",
            f"  · MEDIO          : {medium}",
            f"  · BAJO           : {low}",
            "",
        ]
        if issues:
            lines.append("── VULNERABILIDADES ENCONTRADAS ──")
            for i in issues:
                lines.append(
                    f"  [{i['severity']:8}] Línea {i['line']:4} | {i['description']} ({i['cwe']})"
                )
                lines.append(f"    → {i['line_content']}")
        else:
            lines.append("No se han encontrado vulnerabilidades conocidas.")

        if critical or high:
            lines += [
                "",
                "── RECOMENDACIÓN ──",
                "Este código presenta vulnerabilidades CRÍTICAS o ALTAS.",
                "Se recomienda revisión urgente antes de despliegue en producción.",
            ]
        return "\n".join(lines)


# ==========================
# MOTOR ANTIVIRUS
# ==========================
class AntivirusEngine:
    def __init__(self, db):
        self.db               = db
        self.alerts           = []
        self.monitoring_active = False
        self._monitor_thread  = None
        self.files_scanned    = 0
        self.threats_found    = 0
        self.scan_in_progress = False
        self.scan_progress    = 0.0
        self.scan_status      = "Inactivo"
        self.multimedia_analyzer = MultimediaAnalyzer()
        self.code_analyzer    = CodeSecurityAnalyzer()
        self._callbacks       = []  # para notificar a la GUI

    def register_callback(self, cb):
        self._callbacks.append(cb)

    def _notify(self, event, data=None):
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception:
                pass

    def add_alert(self, message, severity="MEDIUM", category="GENERAL"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "severity":  severity,
            "category":  category,
            "message":   message,
        }
        self.alerts.append(entry)
        self.db.add_alert(message, severity, category)
        logging.warning(f"[{severity}][{category}] {message}")
        self._notify("alert", entry)

    def calculate_hash(self, file_path):
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logging.error(f"Error calculando hash de {file_path}: {e}")
            return None

    def scan_file(self, file_path):
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND", None

        self.files_scanned += 1
        file_hash = self.calculate_hash(file_path)

        if not file_hash:
            return "ERROR", None

        signatures = self.db.get_signatures()
        if file_hash in signatures:
            self.threats_found += 1
            self.add_alert(
                f"Amenaza detectada por firma: {file_path}",
                severity="HIGH", category="MALWARE"
            )
            self.db.add_quarantine(str(file_path), file_hash, "Malware (firma)")
            return "MALICIOUS", file_hash

        # Heurística básica de extensión peligrosa
        dangerous_exts = [".exe", ".bat", ".cmd", ".scr", ".pif", ".com", ".vbs", ".ps1"]
        if Path(file_path).suffix.lower() in dangerous_exts:
            self.add_alert(
                f"Extensión potencialmente peligrosa: {file_path}",
                severity="LOW", category="HEURISTIC"
            )
            return "SUSPICIOUS", file_hash

        return "CLEAN", file_hash

    def scan_directory(self, dir_path, progress_callback=None):
        """Escanea directorio con callback de progreso"""
        self.scan_in_progress = True
        self.scan_status      = f"Escaneando: {dir_path}"
        start_time = time.time()
        count = 0
        threats = 0

        all_files = []
        try:
            for root, _, files in os.walk(dir_path):
                for f in files:
                    all_files.append(os.path.join(root, f))
        except Exception as e:
            logging.error(f"Error listando directorio: {e}")

        total = len(all_files) or 1
        for i, fp in enumerate(all_files):
            result, _ = self.scan_file(fp)
            if result == "MALICIOUS":
                threats += 1
            count += 1
            self.scan_progress = (i + 1) / total * 100
            if progress_callback:
                progress_callback(self.scan_progress, fp)

        duration = time.time() - start_time
        self.db.add_scan("DIRECTORY", dir_path, count, threats, duration)
        self.scan_in_progress = False
        self.scan_status = "Inactivo"
        self.scan_progress = 0.0
        return count, threats, duration

    def scan_system(self, progress_callback=None):
        """Escaneo general del sistema"""
        system = platform.system()
        if system == "Windows":
            paths = ["C:\\Windows\\System32", "C:\\Users", os.environ.get("TEMP", "C:\\Temp")]
        else:
            paths = ["/tmp", "/var/tmp", os.path.expanduser("~")]

        total_files = total_threats = 0
        start_time = time.time()
        self.scan_in_progress = True
        self.scan_status = "Escaneo del sistema en curso..."

        for p in paths:
            if os.path.exists(p):
                f, t, _ = self.scan_directory(p, progress_callback)
                total_files   += f
                total_threats += t

        duration = time.time() - start_time
        self.db.add_scan("SYSTEM", "SISTEMA COMPLETO", total_files, total_threats, duration)
        self.scan_in_progress = False
        self.scan_status = "Inactivo"
        self.add_alert(
            f"Escaneo de sistema completado: {total_files} archivos, {total_threats} amenazas",
            severity="INFO", category="SYSTEM"
        )
        return total_files, total_threats, duration

    def scan_multimedia_file(self, file_path):
        return self.multimedia_analyzer.analyze_file(file_path)

    def scan_multimedia_directory(self, dir_path):
        results = []
        multi_exts = set()
        for exts in MultimediaAnalyzer.MULTIMEDIA_EXTENSIONS.values():
            multi_exts.update(exts)

        for root, _, files in os.walk(dir_path):
            for f in files:
                if Path(f).suffix.lower() in multi_exts:
                    fp = os.path.join(root, f)
                    r  = self.multimedia_analyzer.analyze_file(fp)
                    results.append(r)
                    if r["risk_level"] not in ("CLEAN", "ERROR"):
                        self.add_alert(
                            f"Archivo multimedia sospechoso [{r['risk_level']}]: {fp}",
                            severity=r["risk_level"] if r["risk_level"] in ("HIGH","CRITICAL") else "MEDIUM",
                            category="MULTIMEDIA"
                        )
        return results

    def analyze_code(self, code_text, language=None, filename=None, analyzed_by="Desconocido"):
        report = self.code_analyzer.analyze(code_text, language, filename, analyzed_by)
        self.db.add_code_analysis(
            report["language"],
            report["analyzed_by"],
            report["risk_level"],
            report["issues_count"],
            report["summary"]
        )
        if report["risk_level"] in ("ALTO", "CRÍTICO"):
            self.add_alert(
                f"Código con vulnerabilidades {report['risk_level']} detectado "
                f"({report['issues_count']} problemas, {report['language']}) — "
                f"Analizado por: {report['analyzed_by']}",
                severity="HIGH", category="CODE_SECURITY"
            )
        return report

    def heuristic_check(self, process):
        try:
            name = process.name().lower()
            suspicious = ["malware","virus","trojan","ransomware","keylog","cryptominer","spyware"]
            for kw in suspicious:
                if kw in name:
                    return True, kw
            # Alta CPU
            cpu = process.cpu_percent(interval=0.1)
            if cpu > 85:
                return True, f"CPU alta ({cpu:.0f}%)"
        except Exception:
            pass
        return False, None

    def start_monitoring(self):
        if self.monitoring_active:
            return
        self.monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()
        self.add_alert("Monitorización activa iniciada", severity="INFO", category="MONITOR")
        self._notify("monitor_started")

    def stop_monitoring(self):
        self.monitoring_active = False
        self.add_alert("Monitorización activa detenida", severity="INFO", category="MONITOR")
        self._notify("monitor_stopped")

    def _monitor_loop(self):
        if not PSUTIL_AVAILABLE:
            return
        while self.monitoring_active:
            try:
                for proc in psutil.process_iter(["pid", "name", "username"]):
                    suspicious, reason = self.heuristic_check(proc)
                    if suspicious:
                        self.add_alert(
                            f"Proceso sospechoso [{reason}]: {proc.info['name']} (PID {proc.info['pid']})",
                            severity="HIGH", category="PROCESS"
                        )
            except Exception as e:
                logging.error(f"Monitor loop error: {e}")
            time.sleep(5)

    def get_system_stats(self):
        if not PSUTIL_AVAILABLE:
            return {}
        try:
            return {
                "cpu_percent":    psutil.cpu_percent(interval=0.5),
                "mem_percent":    psutil.virtual_memory().percent,
                "disk_percent":   psutil.disk_usage("/").percent,
                "process_count":  len(psutil.pids()),
                "net_sent_mb":    round(psutil.net_io_counters().bytes_sent / 1024 / 1024, 1),
                "net_recv_mb":    round(psutil.net_io_counters().bytes_recv / 1024 / 1024, 1),
            }
        except Exception:
            return {}


# ==========================
# FASTAPI
# ==========================
if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Antivirus Empresarial API",
        description="API REST local — TFM José Miguel Gómez Fernández",
        version=APP_VERSION
    )
    db     = Database()
    engine = AntivirusEngine(db)

    @app.get("/")
    def home():
        return {"status": "Antivirus activo", "version": APP_VERSION}

    @app.get("/alerts")
    def get_alerts(limit: int = Query(100, ge=1, le=500)):
        return {"alerts": engine.db.get_alerts(limit)}

    @app.get("/alerts/stats")
    def alert_stats():
        return engine.db.get_alert_stats()

    @app.post("/scan/file")
    def scan_file(path: str):
        result, fhash = engine.scan_file(path)
        return {"file": path, "result": result, "hash": fhash}

    @app.post("/scan/multimedia")
    def scan_multimedia(path: str):
        return engine.scan_multimedia_file(path)

    @app.post("/scan/code")
    def scan_code(code: str, language: str = "", analyzed_by: str = "API"):
        return engine.analyze_code(code, language or None, analyzed_by=analyzed_by)

    @app.get("/quarantine")
    def get_quarantine():
        return {"quarantine": engine.db.get_quarantine()}

    @app.get("/scan/history")
    def scan_history():
        return {"history": engine.db.get_scan_history()}

    @app.get("/signatures/count")
    def sig_count():
        return {"count": engine.db.get_signature_count()}

    @app.get("/monitor/status")
    def monitor_status():
        return {"active": engine.monitoring_active}

    @app.post("/monitor/start")
    def monitor_start():
        engine.start_monitoring()
        return {"status": "started"}

    @app.post("/monitor/stop")
    def monitor_stop():
        engine.stop_monitoring()
        return {"status": "stopped"}

    @app.get("/system/stats")
    def system_stats():
        return engine.get_system_stats()

else:
    db     = Database()
    engine = AntivirusEngine(db)


# ==========================
# WIDGETS AUXILIARES
# ==========================
class TkCanvas:
    """Helpers para dibujo con Canvas de tkinter"""

    @staticmethod
    def rounded_rect(canvas, x1, y1, x2, y2, radius=8, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)


class GaugeWidget(tk.Canvas):
    """Medidor semicircular animado"""
    def __init__(self, parent, label="", size=120, **kwargs):
        super().__init__(parent, width=size, height=size//2 + 20,
                         bg=COLORS["bg_card"], highlightthickness=0, **kwargs)
        self.size  = size
        self.label = label
        self._value = 0
        self._draw(0)

    def set_value(self, val):
        val = max(0, min(100, val))
        self._value = val
        self._draw(val)

    def _draw(self, val):
        self.delete("all")
        cx = self.size // 2
        cy = self.size // 2
        r  = self.size // 2 - 8
        pad = 8

        # Fondo arco
        self.create_arc(
            pad, pad, self.size-pad, self.size-pad,
            start=0, extent=180, style="arc",
            outline=COLORS["border"], width=8
        )

        # Arco de valor
        extent = val / 100 * 180
        color = (
            COLORS["accent_green"] if val < 50
            else COLORS["accent_orange"] if val < 80
            else COLORS["accent_red"]
        )
        if extent > 0:
            self.create_arc(
                pad, pad, self.size-pad, self.size-pad,
                start=180, extent=-extent, style="arc",
                outline=color, width=8
            )

        # Texto
        self.create_text(cx, cy - 5,
            text=f"{val:.0f}%",
            fill=COLORS["text_primary"],
            font=("Courier", 12, "bold")
        )
        self.create_text(cx, cy + 10,
            text=self.label,
            fill=COLORS["text_secondary"],
            font=("Courier", 8)
        )


class SparklineWidget(tk.Canvas):
    """Minigráfico de línea histórica"""
    def __init__(self, parent, color=None, points=30, height=50, width=200, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=COLORS["bg_card"], highlightthickness=0, **kwargs)
        self.color   = color or COLORS["accent_cyan"]
        self.max_pts = points
        self.data    = [0.0] * points
        self.w       = width
        self.h       = height

    def push(self, val):
        self.data.append(val)
        if len(self.data) > self.max_pts:
            self.data.pop(0)
        self._redraw()

    def _redraw(self):
        self.delete("all")
        n   = len(self.data)
        mx  = max(self.data) or 1
        mn  = min(self.data)
        rng = mx - mn or 1
        pts = []
        for i, v in enumerate(self.data):
            x = i / (n - 1) * self.w if n > 1 else self.w / 2
            y = self.h - ((v - mn) / rng) * (self.h - 4) - 2
            pts.append((x, y))

        if len(pts) > 1:
            flat = [c for p in pts for c in p]
            self.create_line(flat, fill=self.color, width=2, smooth=True)
            # Relleno debajo
            poly = [0, self.h] + flat + [self.w, self.h]
            self.create_polygon(poly, fill=self.color, stipple="gray25", outline="")


class AlertBadge(tk.Label):
    def __init__(self, parent, severity, **kwargs):
        colors = {
            "CRITICAL": ("#ff0033", "#fff"),
            "HIGH":     ("#ff3366", "#fff"),
            "MEDIUM":   ("#ff8800", "#000"),
            "LOW":      ("#ffcc00", "#000"),
            "INFO":     ("#0088ff", "#fff"),
        }
        bg, fg = colors.get(severity, ("#444", "#fff"))
        super().__init__(parent, text=severity, bg=bg, fg=fg,
                         font=("Courier", 7, "bold"), padx=4, pady=1, **kwargs)


# ==========================
# INTERFAZ TKINTER PRINCIPAL
# ==========================
class AntivirusGUI:
    def __init__(self, root, engine):
        self.root   = root
        self.engine = engine

        self.root.title(f"ShieldCore Enterprise v{APP_VERSION} — {APP_AUTHOR}")
        self.root.geometry("1300x820")
        self.root.configure(bg=COLORS["bg_dark"])
        self.root.minsize(1100, 700)

        # Fuente mono
        self._setup_styles()

        # Layout principal
        self._build_header()
        self._build_body()
        self._build_status_bar()

        # Registrar callback de alertas
        self.engine.register_callback(self._on_engine_event)

        # Arrancar actualizaciones periódicas
        self._update_stats()
        self._update_alerts()
        self._update_gauges()

    # ──────────────────────────────
    # ESTILOS
    # ──────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TNotebook",
            background=COLORS["bg_dark"],
            borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
            background=COLORS["bg_panel"],
            foreground=COLORS["text_secondary"],
            font=("Courier", 9, "bold"),
            padding=(12, 6),
            borderwidth=0)
        style.map("Dark.TNotebook.Tab",
            background=[("selected", COLORS["bg_card"])],
            foreground=[("selected", COLORS["accent_cyan"])])
        style.configure("Treeview",
            background=COLORS["bg_card"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_card"],
            font=("Courier", 9),
            rowheight=22)
        style.configure("Treeview.Heading",
            background=COLORS["bg_panel"],
            foreground=COLORS["accent_blue"],
            font=("Courier", 9, "bold"))
        style.configure("TProgressbar",
            troughcolor=COLORS["bg_panel"],
            background=COLORS["accent_cyan"],
            borderwidth=0)

    # ──────────────────────────────
    # CABECERA
    # ──────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg=COLORS["bg_panel"], height=64)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        # Logo / título
        logo_frame = tk.Frame(hdr, bg=COLORS["bg_panel"])
        logo_frame.pack(side="left", padx=16, pady=8)

        tk.Label(logo_frame, text="⬡", font=("Courier", 24, "bold"),
                 fg=COLORS["accent_cyan"], bg=COLORS["bg_panel"]).pack(side="left")
        title_f = tk.Frame(logo_frame, bg=COLORS["bg_panel"])
        title_f.pack(side="left", padx=8)
        tk.Label(title_f, text="SHIELDCORE ENTERPRISE",
                 font=("Courier", 14, "bold"),
                 fg=COLORS["text_primary"], bg=COLORS["bg_panel"]).pack(anchor="w")
        tk.Label(title_f, text=f"v{APP_VERSION} · {APP_AUTHOR}",
                 font=("Courier", 8),
                 fg=COLORS["text_secondary"], bg=COLORS["bg_panel"]).pack(anchor="w")

        # Indicadores de estado en cabecera
        indicators = tk.Frame(hdr, bg=COLORS["bg_panel"])
        indicators.pack(side="right", padx=16)

        self.monitor_ind = tk.Label(indicators, text="● MONITOR OFF",
            font=("Courier", 9, "bold"),
            fg=COLORS["accent_red"], bg=COLORS["bg_panel"])
        self.monitor_ind.pack(side="right", padx=10)

        self.api_ind = tk.Label(indicators,
            text="● API ON" if FASTAPI_AVAILABLE else "● API OFF",
            font=("Courier", 9, "bold"),
            fg=COLORS["accent_green"] if FASTAPI_AVAILABLE else COLORS["accent_red"],
            bg=COLORS["bg_panel"])
        self.api_ind.pack(side="right", padx=10)

        self.clock_lbl = tk.Label(indicators, text="",
            font=("Courier", 9), fg=COLORS["text_secondary"], bg=COLORS["bg_panel"])
        self.clock_lbl.pack(side="right", padx=10)
        self._tick_clock()

    def _tick_clock(self):
        self.clock_lbl.config(text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ──────────────────────────────
    # CUERPO PRINCIPAL
    # ──────────────────────────────
    def _build_body(self):
        body = tk.Frame(self.root, bg=COLORS["bg_dark"])
        body.pack(fill="both", expand=True, padx=8, pady=4)

        # Sidebar izquierdo
        self._build_sidebar(body)

        # Panel derecho con pestañas
        right = tk.Frame(body, bg=COLORS["bg_dark"])
        right.pack(side="left", fill="both", expand=True, padx=(4, 0))

        self.notebook = ttk.Notebook(right, style="Dark.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self._build_tab_dashboard()
        self._build_tab_scanner()
        self._build_tab_multimedia()
        self._build_tab_code_security()
        self._build_tab_alerts()
        self._build_tab_quarantine()
        self._build_tab_history()
        self._build_tab_api_client()

    # ──────────────────────────────
    # SIDEBAR
    # ──────────────────────────────
    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=COLORS["bg_panel"], width=220)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="ACCIONES RÁPIDAS",
                 font=("Courier", 8, "bold"),
                 fg=COLORS["text_dim"], bg=COLORS["bg_panel"]
                 ).pack(pady=(12, 4), padx=10, anchor="w")

        def btn(text, cmd, color=None):
            c = color or COLORS["accent_blue"]
            b = tk.Button(sb, text=text, command=cmd,
                          bg=COLORS["bg_card"], fg=c,
                          font=("Courier", 9, "bold"),
                          relief="flat", bd=0, cursor="hand2",
                          activebackground=COLORS["border"],
                          activeforeground=c,
                          anchor="w", padx=10, pady=6)
            b.pack(fill="x", padx=8, pady=2)
            return b

        btn("▶  Escanear Archivo",      self.scan_file_dialog)
        btn("▶  Escanear Carpeta",      self.scan_folder_dialog)
        btn("▶  Escaneo del Sistema",   self.scan_system_dialog, COLORS["accent_purple"])

        tk.Frame(sb, bg=COLORS["border"], height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(sb, text="MONITORIZACIÓN",
                 font=("Courier", 8, "bold"),
                 fg=COLORS["text_dim"], bg=COLORS["bg_panel"]
                 ).pack(pady=(0, 4), padx=10, anchor="w")

        self.monitor_btn = tk.Button(sb,
            text="■  Iniciar Monitor",
            command=self.toggle_monitor,
            bg=COLORS["bg_card"], fg=COLORS["accent_green"],
            font=("Courier", 9, "bold"),
            relief="flat", bd=0, cursor="hand2",
            activebackground=COLORS["border"],
            activeforeground=COLORS["accent_green"],
            anchor="w", padx=10, pady=6)
        self.monitor_btn.pack(fill="x", padx=8, pady=2)

        tk.Frame(sb, bg=COLORS["border"], height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(sb, text="MULTIMEDIA",
                 font=("Courier", 8, "bold"),
                 fg=COLORS["text_dim"], bg=COLORS["bg_panel"]
                 ).pack(pady=(0, 4), padx=10, anchor="w")

        btn("▶  Analizar Multimedia",   self.multimedia_file_dialog, COLORS["accent_orange"])
        btn("▶  Carpeta Multimedia",    self.multimedia_folder_dialog, COLORS["accent_orange"])

        tk.Frame(sb, bg=COLORS["border"], height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(sb, text="CÓDIGO FUENTE",
                 font=("Courier", 8, "bold"),
                 fg=COLORS["text_dim"], bg=COLORS["bg_panel"]
                 ).pack(pady=(0, 4), padx=10, anchor="w")

        btn("▶  Analizar Código",       self.open_code_tab, COLORS["accent_purple"])

        tk.Frame(sb, bg=COLORS["border"], height=1).pack(fill="x", padx=8, pady=8)
        tk.Label(sb, text="ESTADÍSTICAS",
                 font=("Courier", 8, "bold"),
                 fg=COLORS["text_dim"], bg=COLORS["bg_panel"]
                 ).pack(pady=(0, 4), padx=10, anchor="w")

        # Mini stats en sidebar
        stats_frame = tk.Frame(sb, bg=COLORS["bg_card"])
        stats_frame.pack(fill="x", padx=8, pady=2)

        self.sb_scanned_lbl = tk.Label(stats_frame, text="Archivos escaneados\n0",
            font=("Courier", 8), fg=COLORS["text_primary"],
            bg=COLORS["bg_card"], justify="center")
        self.sb_scanned_lbl.pack(pady=4)

        self.sb_threats_lbl = tk.Label(stats_frame, text="Amenazas detectadas\n0",
            font=("Courier", 8), fg=COLORS["accent_red"],
            bg=COLORS["bg_card"], justify="center")
        self.sb_threats_lbl.pack(pady=4)

        self.sb_sigs_lbl = tk.Label(stats_frame,
            text=f"Firmas cargadas\n{db.get_signature_count()}",
            font=("Courier", 8), fg=COLORS["accent_green"],
            bg=COLORS["bg_card"], justify="center")
        self.sb_sigs_lbl.pack(pady=4)

    # ──────────────────────────────
    # TAB: DASHBOARD
    # ──────────────────────────────
    def _build_tab_dashboard(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  📊 Dashboard  ")

        # Fila de gauges
        gauges_row = tk.Frame(tab, bg=COLORS["bg_dark"])
        gauges_row.pack(fill="x", padx=8, pady=8)

        gauge_data = [
            ("CPU",    COLORS["accent_cyan"]),
            ("RAM",    COLORS["accent_blue"]),
            ("DISCO",  COLORS["accent_purple"]),
            ("SHIELD", COLORS["accent_green"]),
        ]
        self.gauges = {}
        for label, color in gauge_data:
            card = tk.Frame(gauges_row, bg=COLORS["bg_card"], relief="flat")
            card.pack(side="left", fill="x", expand=True, padx=4)
            g = GaugeWidget(card, label=label, size=130)
            g.pack(pady=8, padx=8)
            self.gauges[label] = g

        # Fila de sparklines
        sparks_row = tk.Frame(tab, bg=COLORS["bg_dark"])
        sparks_row.pack(fill="x", padx=8, pady=4)

        spark_cfg = [
            ("CPU %",     COLORS["accent_cyan"]),
            ("RAM %",     COLORS["accent_blue"]),
            ("Red RX MB", COLORS["accent_green"]),
            ("Amenazas",  COLORS["accent_red"]),
        ]
        self.sparklines = {}
        for label, color in spark_cfg:
            card = tk.Frame(sparks_row, bg=COLORS["bg_card"])
            card.pack(side="left", fill="both", expand=True, padx=4, pady=2)
            tk.Label(card, text=label, font=("Courier", 8),
                     fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(anchor="w", padx=6, pady=2)
            sp = SparklineWidget(card, color=color, width=220, height=55)
            sp.pack(padx=4, pady=4)
            self.sparklines[label] = sp

        # Panel de estado del sistema
        info_row = tk.Frame(tab, bg=COLORS["bg_dark"])
        info_row.pack(fill="both", expand=True, padx=8, pady=4)

        # Procesos
        proc_card = tk.Frame(info_row, bg=COLORS["bg_card"])
        proc_card.pack(side="left", fill="both", expand=True, padx=(0,4))

        tk.Label(proc_card, text="PROCESOS ACTIVOS",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_blue"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.proc_tree = ttk.Treeview(proc_card,
            columns=("PID", "Nombre", "CPU%", "RAM MB"),
            show="headings", height=10)
        for col in ("PID", "Nombre", "CPU%", "RAM MB"):
            self.proc_tree.heading(col, text=col)
            self.proc_tree.column(col, width=80)
        self.proc_tree.pack(fill="both", expand=True, padx=4, pady=4)

        # Info del sistema
        sys_card = tk.Frame(info_row, bg=COLORS["bg_card"], width=260)
        sys_card.pack(side="right", fill="y", padx=(4,0))
        sys_card.pack_propagate(False)

        tk.Label(sys_card, text="INFO DEL SISTEMA",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_blue"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.sys_info_lbl = tk.Label(sys_card, text="Cargando...",
            font=("Courier", 9), fg=COLORS["text_primary"],
            bg=COLORS["bg_card"], justify="left", anchor="nw")
        self.sys_info_lbl.pack(fill="both", expand=True, padx=8, pady=4)

        self._update_sys_info()
        self._update_procs()

    def _update_sys_info(self):
        info = [
            ("OS",          platform.system() + " " + platform.release()),
            ("Hostname",    platform.node()),
            ("Arquitectura",platform.machine()),
            ("Python",      platform.python_version()),
            ("Firmas BD",   str(db.get_signature_count())),
            ("Monitoriz.",  "ACTIVA ●" if self.engine.monitoring_active else "INACTIVA ○"),
        ]
        txt = "\n".join(f"{k:<14}: {v}" for k, v in info)
        try:
            self.sys_info_lbl.config(text=txt)
        except Exception:
            pass
        self.root.after(5000, self._update_sys_info)

    def _update_procs(self):
        if not PSUTIL_AVAILABLE:
            return
        try:
            for row in self.proc_tree.get_children():
                self.proc_tree.delete(row)
            procs = sorted(
                psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]),
                key=lambda p: p.info.get("cpu_percent", 0) or 0,
                reverse=True
            )[:15]
            for p in procs:
                try:
                    mem = round((p.info["memory_info"].rss if p.info.get("memory_info") else 0) / 1024 / 1024, 1)
                    cpu = p.info.get("cpu_percent", 0) or 0
                    self.proc_tree.insert("", "end",
                        values=(p.info["pid"], p.info["name"][:30], f"{cpu:.1f}", mem))
                except Exception:
                    pass
        except Exception:
            pass
        self.root.after(5000, self._update_procs)

    def _update_gauges(self):
        stats = self.engine.get_system_stats()
        if stats:
            self.gauges["CPU"].set_value(stats.get("cpu_percent", 0))
            self.gauges["RAM"].set_value(stats.get("mem_percent", 0))
            self.gauges["DISCO"].set_value(stats.get("disk_percent", 0))
            shield = max(0, 100 - (self.engine.threats_found * 10))
            self.gauges["SHIELD"].set_value(shield)

            self.sparklines["CPU %"].push(stats.get("cpu_percent", 0))
            self.sparklines["RAM %"].push(stats.get("mem_percent", 0))
            self.sparklines["Red RX MB"].push(stats.get("net_recv_mb", 0) % 100)
            self.sparklines["Amenazas"].push(min(100, self.engine.threats_found * 5))

        self.root.after(3000, self._update_gauges)

    # ──────────────────────────────
    # TAB: ESCÁNER
    # ──────────────────────────────
    def _build_tab_scanner(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  🔍 Escáner  ")

        # Barra de progreso de escaneo
        prog_card = tk.Frame(tab, bg=COLORS["bg_card"])
        prog_card.pack(fill="x", padx=8, pady=8)

        tk.Label(prog_card, text="ESTADO DEL ESCANEO",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_blue"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=(6,2))

        self.scan_status_lbl = tk.Label(prog_card, text="Inactivo",
            font=("Courier", 9), fg=COLORS["text_secondary"], bg=COLORS["bg_card"])
        self.scan_status_lbl.pack(anchor="w", padx=8)

        self.scan_progress_var = tk.DoubleVar(value=0)
        self.scan_progress_bar = ttk.Progressbar(prog_card,
            variable=self.scan_progress_var, maximum=100,
            style="TProgressbar", length=400)
        self.scan_progress_bar.pack(fill="x", padx=8, pady=6)

        self.scan_file_lbl = tk.Label(prog_card, text="",
            font=("Courier", 7), fg=COLORS["text_dim"], bg=COLORS["bg_card"])
        self.scan_file_lbl.pack(anchor="w", padx=8, pady=(0,6))

        # Botones de escaneo
        btns_row = tk.Frame(tab, bg=COLORS["bg_dark"])
        btns_row.pack(fill="x", padx=8, pady=4)

        scan_btns = [
            ("🗋  Escanear Archivo",        self.scan_file_dialog,   COLORS["accent_blue"]),
            ("🗀  Escanear Carpeta",         self.scan_folder_dialog, COLORS["accent_cyan"]),
            ("🖥  Escaneo del Sistema",      self.scan_system_dialog, COLORS["accent_purple"]),
            ("➕  Añadir Firma SHA256",      self.add_signature_dialog, COLORS["accent_orange"]),
        ]
        for text, cmd, color in scan_btns:
            tk.Button(btns_row, text=text, command=cmd,
                      bg=COLORS["bg_card"], fg=color,
                      font=("Courier", 9, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=COLORS["border"],
                      padx=12, pady=8
                      ).pack(side="left", padx=4)

        # Resultados
        res_card = tk.Frame(tab, bg=COLORS["bg_card"])
        res_card.pack(fill="both", expand=True, padx=8, pady=4)

        tk.Label(res_card, text="RESULTADOS DE ESCANEO",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_blue"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.scan_tree = ttk.Treeview(res_card,
            columns=("Archivo", "Resultado", "Hash"),
            show="headings")
        self.scan_tree.heading("Archivo",    text="Archivo")
        self.scan_tree.heading("Resultado",  text="Resultado")
        self.scan_tree.heading("Hash",       text="SHA256")
        self.scan_tree.column("Archivo",  width=400)
        self.scan_tree.column("Resultado",width=120)
        self.scan_tree.column("Hash",     width=300)

        sb2 = ttk.Scrollbar(res_card, orient="vertical", command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=sb2.set)
        self.scan_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sb2.pack(side="right", fill="y", pady=4)

        # Colores por resultado
        self.scan_tree.tag_configure("MALICIOUS",  background="#330011", foreground=COLORS["accent_red"])
        self.scan_tree.tag_configure("SUSPICIOUS", background="#331100", foreground=COLORS["accent_orange"])
        self.scan_tree.tag_configure("CLEAN",      background=COLORS["bg_card"], foreground=COLORS["accent_green"])

    # ──────────────────────────────
    # TAB: MULTIMEDIA
    # ──────────────────────────────
    def _build_tab_multimedia(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  🎬 Multimedia  ")

        # Info
        info_card = tk.Frame(tab, bg=COLORS["bg_card"])
        info_card.pack(fill="x", padx=8, pady=8)
        tk.Label(info_card,
            text="ANÁLISIS DE MALWARE EN ARCHIVOS MULTIMEDIA",
            font=("Courier", 10, "bold"),
            fg=COLORS["accent_orange"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)
        tk.Label(info_card,
            text="Detecta steganografía, ejecutables embebidos, scripts maliciosos, entropía anormal y spoofing de extensiones.",
            font=("Courier", 8), fg=COLORS["text_secondary"], bg=COLORS["bg_card"],
            wraplength=900, justify="left").pack(anchor="w", padx=8, pady=(0,6))

        # Botones
        btns = tk.Frame(tab, bg=COLORS["bg_dark"])
        btns.pack(fill="x", padx=8, pady=4)
        tk.Button(btns, text="🎬  Analizar Archivo Multimedia", command=self.multimedia_file_dialog,
                  bg=COLORS["bg_card"], fg=COLORS["accent_orange"],
                  font=("Courier", 9, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=12, pady=8).pack(side="left", padx=4)
        tk.Button(btns, text="🗀  Analizar Carpeta Multimedia", command=self.multimedia_folder_dialog,
                  bg=COLORS["bg_card"], fg=COLORS["accent_orange"],
                  font=("Courier", 9, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=12, pady=8).pack(side="left", padx=4)

        # Resultados
        split = tk.Frame(tab, bg=COLORS["bg_dark"])
        split.pack(fill="both", expand=True, padx=8, pady=4)

        # Árbol de archivos analizados
        left_card = tk.Frame(split, bg=COLORS["bg_card"])
        left_card.pack(side="left", fill="both", expand=True, padx=(0,4))

        tk.Label(left_card, text="ARCHIVOS ANALIZADOS",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_orange"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.media_tree = ttk.Treeview(left_card,
            columns=("Archivo","Formato","Entropía","Riesgo"),
            show="headings")
        for col, w in [("Archivo",300),("Formato",80),("Entropía",80),("Riesgo",100)]:
            self.media_tree.heading(col, text=col)
            self.media_tree.column(col, width=w)
        self.media_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.media_tree.tag_configure("CRITICAL", background="#330000", foreground=COLORS["accent_red"])
        self.media_tree.tag_configure("HIGH",     background="#220011", foreground=COLORS["accent_red"])
        self.media_tree.tag_configure("MEDIUM",   background="#221100", foreground=COLORS["accent_orange"])
        self.media_tree.tag_configure("CLEAN",    background=COLORS["bg_card"], foreground=COLORS["accent_green"])
        self.media_tree.bind("<<TreeviewSelect>>", self._on_media_select)

        # Detalle
        right_card = tk.Frame(split, bg=COLORS["bg_card"], width=340)
        right_card.pack(side="right", fill="y", padx=(4,0))
        right_card.pack_propagate(False)

        tk.Label(right_card, text="DETALLE",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_orange"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.media_detail = tk.Text(right_card,
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Courier", 8), relief="flat", bd=0, wrap="word",
            state="disabled")
        self.media_detail.pack(fill="both", expand=True, padx=6, pady=6)

        self._media_results = []

    def _on_media_select(self, event):
        sel = self.media_tree.selection()
        if not sel:
            return
        idx = self.media_tree.index(sel[0])
        if idx < len(self._media_results):
            r = self._media_results[idx]
            detail = (
                f"Archivo    : {r['file']}\n"
                f"Tamaño     : {r['size_bytes']:,} bytes\n"
                f"Formato    : {r['detected_format']}\n"
                f"Tipo       : {r['file_type']}\n"
                f"Entropía   : {r['entropy']}\n"
                f"Alta entrop: {'SÍ' if r['high_entropy'] else 'No'}\n"
                f"Mismatch   : {'SÍ ⚠' if r['extension_mismatch'] else 'No'}\n"
                f"Riesgo     : {r['risk_level']}\n\n"
                f"── DETALLES ──\n"
            ) + "\n".join(r.get("details", []))
            self.media_detail.config(state="normal")
            self.media_detail.delete("1.0", "end")
            self.media_detail.insert("1.0", detail)
            self.media_detail.config(state="disabled")

    # ──────────────────────────────
    # TAB: CÓDIGO FUENTE
    # ──────────────────────────────
    def _build_tab_code_security(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  🔐 Código  ")
        self._code_tab = tab

        # Info
        info_card = tk.Frame(tab, bg=COLORS["bg_card"])
        info_card.pack(fill="x", padx=8, pady=8)
        tk.Label(info_card,
            text="ANÁLISIS DE SEGURIDAD DE CÓDIGO FUENTE",
            font=("Courier", 10, "bold"),
            fg=COLORS["accent_purple"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)
        tk.Label(info_card,
            text="Analiza código en texto plano en busca de vulnerabilidades CWE. Soporta Python, JS, Java, PHP, SQL, Shell y más.",
            font=("Courier", 8), fg=COLORS["text_secondary"], bg=COLORS["bg_card"],
            wraplength=900).pack(anchor="w", padx=8, pady=(0,6))

        # Opciones
        opts = tk.Frame(tab, bg=COLORS["bg_dark"])
        opts.pack(fill="x", padx=8, pady=4)

        tk.Label(opts, text="Lenguaje:", font=("Courier", 9),
                 fg=COLORS["text_secondary"], bg=COLORS["bg_dark"]).pack(side="left")
        self.lang_var = tk.StringVar(value="Auto-detectar")
        langs = ["Auto-detectar"] + list(CodeSecurityAnalyzer.LANGUAGES.keys())
        lang_menu = tk.OptionMenu(opts, self.lang_var, *langs)
        lang_menu.config(bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                         font=("Courier", 9), relief="flat",
                         activebackground=COLORS["border"],
                         highlightthickness=0)
        lang_menu.pack(side="left", padx=8)

        tk.Label(opts, text="Programador/Analista:", font=("Courier", 9),
                 fg=COLORS["text_secondary"], bg=COLORS["bg_dark"]).pack(side="left", padx=(12,0))
        self.analyst_var = tk.StringVar(value="")
        analyst_entry = tk.Entry(opts, textvariable=self.analyst_var,
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            font=("Courier", 9), relief="flat", bd=0, width=24,
            insertbackground=COLORS["accent_cyan"])
        analyst_entry.pack(side="left", padx=8)

        tk.Button(opts, text="🔐  Analizar Código",
                  command=self._analyze_code,
                  bg=COLORS["accent_purple"], fg="#fff",
                  font=("Courier", 9, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=12, pady=6
                  ).pack(side="left", padx=8)

        tk.Button(opts, text="📂  Cargar desde archivo",
                  command=self._load_code_file,
                  bg=COLORS["bg_card"], fg=COLORS["accent_purple"],
                  font=("Courier", 9, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=12, pady=6
                  ).pack(side="left", padx=4)

        # Editor + Resultados
        split = tk.Frame(tab, bg=COLORS["bg_dark"])
        split.pack(fill="both", expand=True, padx=8, pady=4)

        # Editor
        editor_card = tk.Frame(split, bg=COLORS["bg_card"])
        editor_card.pack(side="left", fill="both", expand=True, padx=(0,4))
        tk.Label(editor_card, text="CÓDIGO A ANALIZAR",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_purple"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)
        self.code_editor = tk.Text(editor_card,
            bg="#0d0d1a", fg=COLORS["text_primary"],
            font=("Courier", 10), relief="flat", bd=0,
            insertbackground=COLORS["accent_cyan"],
            wrap="none", undo=True)
        self.code_editor.pack(fill="both", expand=True, padx=6, pady=6)
        # Placeholder
        self.code_editor.insert("1.0", "# Pega aquí el código a analizar...\n")

        # Resultados
        result_card = tk.Frame(split, bg=COLORS["bg_card"], width=420)
        result_card.pack(side="right", fill="y")
        result_card.pack_propagate(False)
        tk.Label(result_card, text="INFORME DE SEGURIDAD",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_purple"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.code_report = tk.Text(result_card,
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            font=("Courier", 9), relief="flat", bd=0, wrap="word",
            state="disabled")
        self.code_report.pack(fill="both", expand=True, padx=6, pady=6)

    def _analyze_code(self):
        code = self.code_editor.get("1.0", "end").strip()
        if not code or code == "# Pega aquí el código a analizar...":
            messagebox.showwarning("Sin código", "Por favor, introduce código a analizar.")
            return
        lang_sel = self.lang_var.get()
        lang     = None if lang_sel == "Auto-detectar" else lang_sel
        analyst  = self.analyst_var.get().strip() or "Desconocido"

        def run():
            report = self.engine.analyze_code(code, language=lang, analyzed_by=analyst)
            self._display_code_report(report)

        threading.Thread(target=run, daemon=True).start()

    def _display_code_report(self, report):
        color_map = {
            "CRÍTICO": COLORS["accent_red"],
            "ALTO":    COLORS["accent_orange"],
            "MEDIO":   COLORS["accent_orange"],
            "BAJO":    COLORS["warning"],
            "LIMPIO":  COLORS["accent_green"],
        }
        fg = color_map.get(report["risk_level"], COLORS["text_primary"])

        self.code_report.config(state="normal")
        self.code_report.delete("1.0", "end")
        self.code_report.insert("1.0", report["summary"])

        # Colorear nivel de riesgo
        start = self.code_report.search("Nivel de riesgo", "1.0")
        if start:
            end = f"{start} lineend"
            self.code_report.tag_add("risk_line", start, end)
            self.code_report.tag_config("risk_line", foreground=fg)

        self.code_report.config(state="disabled")

    def _load_code_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de código",
            filetypes=[
                ("Código fuente", "*.py *.js *.ts *.java *.php *.rb *.go *.rs *.sh *.ps1 *.sql *.c *.cpp *.h"),
                ("Todos los archivos", "*.*")
            ]
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self.code_editor.delete("1.0", "end")
                self.code_editor.insert("1.0", content)
                # Auto-detectar lenguaje por extensión
                ext = Path(path).suffix.lower()
                for lang, exts in CodeSecurityAnalyzer.LANGUAGES.items():
                    if ext in exts:
                        self.lang_var.set(lang)
                        break
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")

    def open_code_tab(self):
        for i in range(self.notebook.index("end")):
            if "Código" in self.notebook.tab(i, "text"):
                self.notebook.select(i)
                break

    # ──────────────────────────────
    # TAB: ALERTAS
    # ──────────────────────────────
    def _build_tab_alerts(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  🚨 Alertas  ")

        # Filtros
        filters = tk.Frame(tab, bg=COLORS["bg_panel"])
        filters.pack(fill="x", padx=8, pady=6)

        tk.Label(filters, text="Severidad:", font=("Courier", 9),
                 fg=COLORS["text_secondary"], bg=COLORS["bg_panel"]).pack(side="left", padx=6)
        self.sev_filter = tk.StringVar(value="TODAS")
        for sev in ["TODAS","CRITICAL","HIGH","MEDIUM","LOW","INFO"]:
            tk.Radiobutton(filters, text=sev, variable=self.sev_filter, value=sev,
                bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_card"],
                activebackground=COLORS["bg_panel"],
                font=("Courier", 8),
                command=self._update_alerts
            ).pack(side="left", padx=4)

        tk.Button(filters, text="🔄 Actualizar",
                  command=self._update_alerts,
                  bg=COLORS["bg_card"], fg=COLORS["accent_blue"],
                  font=("Courier", 8, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=8, pady=4
                  ).pack(side="right", padx=8)

        # Árbol de alertas
        tree_card = tk.Frame(tab, bg=COLORS["bg_card"])
        tree_card.pack(fill="both", expand=True, padx=8, pady=4)

        self.alerts_tree = ttk.Treeview(tree_card,
            columns=("Timestamp","Severidad","Categoría","Mensaje"),
            show="headings")
        self.alerts_tree.heading("Timestamp", text="Fecha/Hora")
        self.alerts_tree.heading("Severidad", text="Severidad")
        self.alerts_tree.heading("Categoría", text="Categoría")
        self.alerts_tree.heading("Mensaje",   text="Mensaje")
        self.alerts_tree.column("Timestamp", width=140)
        self.alerts_tree.column("Severidad", width=80)
        self.alerts_tree.column("Categoría", width=100)
        self.alerts_tree.column("Mensaje",   width=600)

        self.alerts_tree.tag_configure("CRITICAL", background="#330000", foreground="#ff4455")
        self.alerts_tree.tag_configure("HIGH",     background="#220011", foreground=COLORS["accent_red"])
        self.alerts_tree.tag_configure("MEDIUM",   background="#221100", foreground=COLORS["accent_orange"])
        self.alerts_tree.tag_configure("LOW",      background="#221500", foreground=COLORS["warning"])
        self.alerts_tree.tag_configure("INFO",     background=COLORS["bg_card"], foreground=COLORS["accent_blue"])

        sb3 = ttk.Scrollbar(tree_card, orient="vertical", command=self.alerts_tree.yview)
        self.alerts_tree.configure(yscrollcommand=sb3.set)
        self.alerts_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sb3.pack(side="right", fill="y", pady=4)

    def _update_alerts(self, *_):
        try:
            for row in self.alerts_tree.get_children():
                self.alerts_tree.delete(row)

            sev_filter = self.sev_filter.get() if hasattr(self, "sev_filter") else "TODAS"
            for ts, sev, cat, msg, aid in self.engine.db.get_alerts(200):
                if sev_filter != "TODAS" and sev != sev_filter:
                    continue
                self.alerts_tree.insert("", "end",
                    values=(ts, sev, cat, msg),
                    tags=(sev,))
        except Exception:
            pass
        self.root.after(5000, self._update_alerts)

    # ──────────────────────────────
    # TAB: CUARENTENA
    # ──────────────────────────────
    def _build_tab_quarantine(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  ☣ Cuarentena  ")

        info = tk.Frame(tab, bg=COLORS["bg_card"])
        info.pack(fill="x", padx=8, pady=8)
        tk.Label(info, text="ARCHIVOS EN CUARENTENA",
                 font=("Courier", 10, "bold"),
                 fg=COLORS["accent_red"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.quar_tree = ttk.Treeview(tab,
            columns=("ID","Fecha","Ruta Original","Amenaza","Estado"),
            show="headings")
        for col, w in [("ID",50),("Fecha",140),("Ruta Original",380),("Amenaza",180),("Estado",100)]:
            self.quar_tree.heading(col, text=col)
            self.quar_tree.column(col, width=w)
        self.quar_tree.pack(fill="both", expand=True, padx=8, pady=4)

        tk.Button(tab, text="🔄 Actualizar",
                  command=self._refresh_quarantine,
                  bg=COLORS["bg_card"], fg=COLORS["accent_red"],
                  font=("Courier", 9, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=12, pady=6
                  ).pack(pady=4)

        self._refresh_quarantine()

    def _refresh_quarantine(self):
        for row in self.quar_tree.get_children():
            self.quar_tree.delete(row)
        for qid, ts, path, threat, status in self.engine.db.get_quarantine():
            self.quar_tree.insert("", "end", values=(qid, ts, path, threat, status))

    # ──────────────────────────────
    # TAB: HISTORIAL
    # ──────────────────────────────
    def _build_tab_history(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  📋 Historial  ")

        # Resumen
        stats_card = tk.Frame(tab, bg=COLORS["bg_card"])
        stats_card.pack(fill="x", padx=8, pady=8)
        tk.Label(stats_card, text="RESUMEN GLOBAL",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_blue"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        self.history_stats_lbl = tk.Label(stats_card, text="",
            font=("Courier", 9), fg=COLORS["text_primary"],
            bg=COLORS["bg_card"])
        self.history_stats_lbl.pack(anchor="w", padx=8, pady=4)

        # Historial de escaneos
        tk.Label(tab, text="ESCANEOS REALIZADOS",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_blue"], bg=COLORS["bg_dark"]).pack(anchor="w", padx=12, pady=4)

        self.history_tree = ttk.Treeview(tab,
            columns=("Fecha","Tipo","Ruta","Archivos","Amenazas","Duración"),
            show="headings")
        for col, w in [("Fecha",140),("Tipo",100),("Ruta",280),("Archivos",80),("Amenazas",80),("Duración",80)]:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=w)
        self.history_tree.pack(fill="both", expand=True, padx=8, pady=4)

        tk.Button(tab, text="🔄 Actualizar Historial",
                  command=self._refresh_history,
                  bg=COLORS["bg_card"], fg=COLORS["accent_blue"],
                  font=("Courier", 9, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=12, pady=6
                  ).pack(pady=4)

        self._refresh_history()

    def _refresh_history(self):
        stats = self.engine.db.get_scan_stats()
        self.history_stats_lbl.config(
            text=(
                f"Escaneos totales: {stats['total_scans']}   "
                f"Archivos escaneados: {stats['total_files']:,}   "
                f"Amenazas encontradas: {stats['total_threats']}"
            )
        )
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        for ts, stype, path, files, threats, dur in self.engine.db.get_scan_history():
            self.history_tree.insert("", "end",
                values=(ts, stype, path, files, threats, f"{dur:.1f}s"))

    # ──────────────────────────────
    # TAB: CLIENTE API
    # ──────────────────────────────
    def _build_tab_api_client(self):
        tab = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(tab, text="  🌐 API  ")

        info = tk.Frame(tab, bg=COLORS["bg_card"])
        info.pack(fill="x", padx=8, pady=8)
        tk.Label(info,
            text=f"API REST LOCAL — {'http://127.0.0.1:8000' if FASTAPI_AVAILABLE else 'DESHABILITADA (instala fastapi uvicorn)'}",
            font=("Courier", 10, "bold"),
            fg=COLORS["accent_cyan"] if FASTAPI_AVAILABLE else COLORS["accent_red"],
            bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        # Endpoints disponibles
        endpoints = [
            ("GET",  "/",                "Estado del antivirus"),
            ("GET",  "/alerts",          "Listado de alertas"),
            ("GET",  "/alerts/stats",    "Estadísticas de alertas"),
            ("POST", "/scan/file",       "Escanear archivo por ruta"),
            ("POST", "/scan/multimedia", "Analizar archivo multimedia"),
            ("POST", "/scan/code",       "Analizar código fuente"),
            ("GET",  "/quarantine",      "Ver cuarentena"),
            ("GET",  "/scan/history",    "Historial de escaneos"),
            ("GET",  "/signatures/count","Número de firmas cargadas"),
            ("GET",  "/monitor/status",  "Estado del monitor"),
            ("POST", "/monitor/start",   "Iniciar monitorización"),
            ("POST", "/monitor/stop",    "Detener monitorización"),
            ("GET",  "/system/stats",    "Estadísticas del sistema"),
        ]

        ep_card = tk.Frame(tab, bg=COLORS["bg_card"])
        ep_card.pack(fill="x", padx=8, pady=4)
        tk.Label(ep_card, text="ENDPOINTS DISPONIBLES",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_cyan"], bg=COLORS["bg_card"]).pack(anchor="w", padx=8, pady=6)

        for method, path, desc in endpoints:
            row = tk.Frame(ep_card, bg=COLORS["bg_card"])
            row.pack(fill="x", padx=8, pady=1)
            color = COLORS["accent_green"] if method == "GET" else COLORS["accent_orange"]
            tk.Label(row, text=f"{method:5}", font=("Courier", 8, "bold"),
                     fg=color, bg=COLORS["bg_card"], width=6).pack(side="left")
            tk.Label(row, text=path, font=("Courier", 8),
                     fg=COLORS["accent_cyan"], bg=COLORS["bg_card"], width=25, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=("Courier", 8),
                     fg=COLORS["text_secondary"], bg=COLORS["bg_card"]).pack(side="left", padx=8)

        # Consola de respuesta API
        tk.Label(tab, text="CONSOLA DE RESPUESTA",
                 font=("Courier", 9, "bold"),
                 fg=COLORS["accent_cyan"], bg=COLORS["bg_dark"]).pack(anchor="w", padx=12, pady=(8,2))

        self.api_console = tk.Text(tab,
            bg="#060a12", fg=COLORS["accent_cyan"],
            font=("Courier", 9), relief="flat", bd=0, wrap="word",
            state="disabled", height=12)
        self.api_console.pack(fill="both", expand=True, padx=8, pady=4)

        self._api_log("▶ API cliente listo. La API arranca en http://127.0.0.1:8000")
        if FASTAPI_AVAILABLE:
            self._api_log("▶ Documentación interactiva: http://127.0.0.1:8000/docs")

    def _api_log(self, msg):
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            self.api_console.config(state="normal")
            self.api_console.insert("end", f"[{ts}] {msg}\n")
            self.api_console.see("end")
            self.api_console.config(state="disabled")
        except Exception:
            pass

    # ──────────────────────────────
    # BARRA DE ESTADO
    # ──────────────────────────────
    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=COLORS["bg_panel"], height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_lbl = tk.Label(bar, text="■ Sistema protegido",
            font=("Courier", 8, "bold"),
            fg=COLORS["accent_green"], bg=COLORS["bg_panel"])
        self.status_lbl.pack(side="left", padx=12, pady=4)

        self.scan_pct_lbl = tk.Label(bar, text="",
            font=("Courier", 8),
            fg=COLORS["text_secondary"], bg=COLORS["bg_panel"])
        self.scan_pct_lbl.pack(side="left", padx=8)

        tk.Label(bar, text=f"OS: {platform.system()} {platform.release()}  |  Python {platform.python_version()}",
                 font=("Courier", 8),
                 fg=COLORS["text_dim"], bg=COLORS["bg_panel"]
                 ).pack(side="right", padx=12)

    def _update_stats(self):
        try:
            stats = self.engine.db.get_scan_stats()
            self.sb_scanned_lbl.config(
                text=f"Archivos escaneados\n{stats['total_files']:,}")
            self.sb_threats_lbl.config(
                text=f"Amenazas detectadas\n{stats['total_threats']}")

            if self.engine.scan_in_progress:
                self.scan_status_lbl.config(
                    text=self.engine.scan_status, fg=COLORS["accent_cyan"])
                self.scan_progress_var.set(self.engine.scan_progress)
                self.scan_pct_lbl.config(text=f"Escaneando... {self.engine.scan_progress:.0f}%")
            else:
                self.scan_status_lbl.config(text="Inactivo", fg=COLORS["text_secondary"])
                self.scan_progress_var.set(0)
                self.scan_pct_lbl.config(text="")
        except Exception:
            pass
        self.root.after(1000, self._update_stats)

    # ──────────────────────────────
    # CALLBACKS DEL ENGINE
    # ──────────────────────────────
    def _on_engine_event(self, event, data=None):
        if event == "alert":
            self.root.after(0, self._flash_alert, data)
        elif event == "monitor_started":
            self.root.after(0, lambda: (
                self.monitor_ind.config(text="● MONITOR ON", fg=COLORS["accent_green"]),
                self.monitor_btn.config(text="■  Detener Monitor", fg=COLORS["accent_red"])
            ))
        elif event == "monitor_stopped":
            self.root.after(0, lambda: (
                self.monitor_ind.config(text="● MONITOR OFF", fg=COLORS["accent_red"]),
                self.monitor_btn.config(text="■  Iniciar Monitor", fg=COLORS["accent_green"])
            ))

    def _flash_alert(self, data):
        if data and data.get("severity") in ("HIGH","CRITICAL"):
            self.status_lbl.config(
                text=f"⚠ AMENAZA: {data.get('message','')[:80]}",
                fg=COLORS["accent_red"])
            self.root.after(5000, lambda:
                self.status_lbl.config(text="■ Sistema protegido", fg=COLORS["accent_green"]))

    # ──────────────────────────────
    # ACCIONES
    # ──────────────────────────────
    def toggle_monitor(self):
        if self.engine.monitoring_active:
            self.engine.stop_monitoring()
        else:
            if not PSUTIL_AVAILABLE:
                messagebox.showwarning("psutil no disponible",
                    "Instala psutil para usar la monitorización:\npip install psutil")
                return
            self.engine.start_monitoring()

    def scan_file_dialog(self):
        path = filedialog.askopenfilename(title="Seleccionar archivo a escanear")
        if not path:
            return
        result, fhash = self.engine.scan_file(path)
        tag = result if result in ("MALICIOUS","SUSPICIOUS","CLEAN") else "CLEAN"
        self.scan_tree.insert("", 0, values=(path, result, fhash or "—"), tags=(tag,))
        self._update_alerts()
        self._refresh_history()
        color = {
            "MALICIOUS":  COLORS["accent_red"],
            "SUSPICIOUS": COLORS["accent_orange"],
            "CLEAN":      COLORS["accent_green"],
        }.get(result, COLORS["text_primary"])
        messagebox.showinfo("Resultado",
            f"Archivo: {path}\nResultado: {result}\nHash: {fhash or 'N/A'}")

    def scan_folder_dialog(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta a escanear")
        if not path:
            return
        self._run_scan_threaded("DIRECTORY", path)

    def scan_system_dialog(self):
        if messagebox.askyesno("Escaneo del sistema",
                "¿Iniciar escaneo general del sistema?\n\nEsto puede tardar varios minutos."):
            self._run_scan_threaded("SYSTEM", None)

    def _run_scan_threaded(self, scan_type, path):
        def progress_cb(pct, current_file):
            self.root.after(0, lambda: (
                self.scan_status_lbl.config(
                    text=f"Escaneando: {Path(current_file).name}",
                    fg=COLORS["accent_cyan"]),
                self.scan_progress_var.set(pct),
                self.scan_file_lbl.config(text=current_file[:80])
            ))

        def run():
            if scan_type == "SYSTEM":
                files, threats, dur = self.engine.scan_system(progress_cb)
            else:
                files, threats, dur = self.engine.scan_directory(path, progress_cb)

            self.root.after(0, lambda: (
                self._refresh_history(),
                self._update_alerts(),
                messagebox.showinfo("Escaneo completado",
                    f"Archivos escaneados: {files:,}\n"
                    f"Amenazas encontradas: {threats}\n"
                    f"Duración: {dur:.1f} segundos")
            ))

        threading.Thread(target=run, daemon=True).start()

    def add_signature_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Añadir Firma SHA256")
        win.geometry("520x220")
        win.configure(bg=COLORS["bg_dark"])

        tk.Label(win, text="AÑADIR FIRMA DE MALWARE",
                 font=("Courier", 10, "bold"),
                 fg=COLORS["accent_orange"], bg=COLORS["bg_dark"]).pack(pady=12)

        fields = {}
        for label in ("Hash SHA256", "Nombre del malware", "Tipo de amenaza"):
            row = tk.Frame(win, bg=COLORS["bg_dark"])
            row.pack(fill="x", padx=20, pady=4)
            tk.Label(row, text=f"{label}:", font=("Courier", 9),
                     fg=COLORS["text_secondary"], bg=COLORS["bg_dark"], width=20, anchor="e"
                     ).pack(side="left")
            e = tk.Entry(row, bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                         font=("Courier", 9), relief="flat", bd=0, width=34,
                         insertbackground=COLORS["accent_cyan"])
            e.pack(side="left", padx=6)
            fields[label] = e

        def submit():
            h    = fields["Hash SHA256"].get().strip()
            name = fields["Nombre del malware"].get().strip()
            ttype= fields["Tipo de amenaza"].get().strip() or "UNKNOWN"
            if len(h) == 64:
                self.engine.db.add_signature(h, name, ttype)
                self.sb_sigs_lbl.config(text=f"Firmas cargadas\n{db.get_signature_count()}")
                messagebox.showinfo("Firma añadida", f"Firma guardada:\n{h}")
                win.destroy()
            else:
                messagebox.showerror("Error", "El hash SHA256 debe tener exactamente 64 caracteres.")

        tk.Button(win, text="Guardar Firma",
                  command=submit,
                  bg=COLORS["accent_orange"], fg="#000",
                  font=("Courier", 9, "bold"), relief="flat", bd=0,
                  cursor="hand2", padx=16, pady=6
                  ).pack(pady=12)

    def multimedia_file_dialog(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo multimedia",
            filetypes=[
                ("Multimedia", "*.jpg *.jpeg *.png *.gif *.bmp *.webp *.mp4 *.avi *.mkv "
                               "*.mp3 *.wav *.pdf *.doc *.docx *.svg"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not path:
            return
        result = self.engine.scan_multimedia_file(path)
        self._media_results.append(result)
        tag = result["risk_level"] if result["risk_level"] in ("CRITICAL","HIGH","MEDIUM") else "CLEAN"
        self.media_tree.insert("", 0,
            values=(
                Path(path).name,
                result["detected_format"],
                str(result["entropy"]),
                result["risk_level"],
            ),
            tags=(tag,))
        self._update_alerts()
        # Ir a la pestaña multimedia
        for i in range(self.notebook.index("end")):
            if "Multimedia" in self.notebook.tab(i, "text"):
                self.notebook.select(i)
                break

    def multimedia_folder_dialog(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta a analizar")
        if not path:
            return

        def run():
            results = self.engine.scan_multimedia_directory(path)
            for r in results:
                self._media_results.append(r)
                tag = r["risk_level"] if r["risk_level"] in ("CRITICAL","HIGH","MEDIUM") else "CLEAN"
                self.root.after(0, lambda r=r, tag=tag: self.media_tree.insert("", "end",
                    values=(Path(r["file"]).name, r["detected_format"], str(r["entropy"]), r["risk_level"]),
                    tags=(tag,)))
            self.root.after(0, lambda: (
                self._update_alerts(),
                messagebox.showinfo("Análisis completado",
                    f"Archivos multimedia analizados: {len(results)}\n"
                    f"Con riesgo: {sum(1 for r in results if r['risk_level'] != 'CLEAN')}")
            ))

        threading.Thread(target=run, daemon=True).start()

    def _api_log(self, msg):
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            self.api_console.config(state="normal")
            self.api_console.insert("end", f"[{ts}] {msg}\n")
            self.api_console.see("end")
            self.api_console.config(state="disabled")
        except Exception:
            pass


# ==========================
# EJECUCIÓN
# ==========================
def run_api():
    if FASTAPI_AVAILABLE:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    else:
        print("[INFO] FastAPI no instalado. API REST deshabilitada.")


def run_process_monitor():
    engine.monitor_processes() if hasattr(engine, "monitor_processes") else None


def main():
    # API REST local
    if FASTAPI_AVAILABLE:
        threading.Thread(target=run_api, daemon=True).start()
        logging.info("API REST iniciada en http://127.0.0.1:8000")

    # GUI
    root = tk.Tk()

    try:
        root.iconbitmap("")
    except Exception:
        pass

    app_gui = AntivirusGUI(root, engine)
    root.mainloop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ShieldCore Enterprise Server")
    parser.add_argument("--server", action="store_true", help="Iniciar API FastAPI")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.server:
        if not FASTAPI_AVAILABLE:
            print("FastAPI no está instalado.")
            exit(1)

        print(f"Iniciando ShieldCore API en {args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        # Solo lanzar GUI si existe entorno gráfico
        try:
            root = tk.Tk()
            gui = AntivirusGUI(root, engine)
            root.mainloop()
        except Exception as e:
            print(f"No se pudo iniciar la GUI: {e}")
