import sqlite3
import json
from datetime import datetime
from pathlib import Path


class TestDatabase:
    def __init__(self, db_path="izod_tests.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT UNIQUE NOT NULL,
                test_name TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                width REAL,
                thickness REAL,
                sample_length REAL,
                depth_notch REAL,
                error_mc REAL,
                scale_hammer REAL,
                graph_degrees TEXT,
                graph_joules TEXT,
                final_energy REAL,
                final_angle REAL,
                completed INTEGER DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()
        conn.close()
    
    def generate_test_id(self):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"TEST_{timestamp}"
    
    def save_test(self, test_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        date_str = now.strftime("%d/%m/%y")
        time_str = now.strftime("%H:%M:%S")
        timestamp_str = now.isoformat()
        
        graph_degrees_json = json.dumps(test_data.get("graph_degrees", []))
        graph_joules_json = json.dumps(test_data.get("graph_joules", []))
        
        cursor.execute("""
            INSERT INTO tests (
                test_id, test_name, date, time, timestamp,
                width, thickness, sample_length, depth_notch, error_mc, scale_hammer,
                graph_degrees, graph_joules, final_energy, final_angle, completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_data.get("test_id"),
            test_data.get("test_name", ""),
            date_str,
            time_str,
            timestamp_str,
            test_data.get("width"),
            test_data.get("thickness"),
            test_data.get("sample_length"),
            test_data.get("depth_notch"),
            test_data.get("error_mc"),
            test_data.get("scale_hammer"),
            graph_degrees_json,
            graph_joules_json,
            test_data.get("final_energy"),
            test_data.get("final_angle"),
            1
        ))
        
        conn.commit()
        conn.close()
        
        return date_str, time_str
    
    def get_all_tests(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, test_id, test_name, date, time, timestamp
            FROM tests
            ORDER BY timestamp DESC
        """)
        
        tests = cursor.fetchall()
        conn.close()
        
        return tests
    
    def save_setting(self, key: str, value: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
        conn.close()

    def get_setting(self, key: str, default: str = "") -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default

    def get_test_by_id(self, test_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tests WHERE test_id = ?
        """, (test_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        columns = [
            "id", "test_id", "test_name", "date", "time", "timestamp",
            "width", "thickness", "sample_length", "depth_notch", "error_mc", "scale_hammer",
            "graph_degrees", "graph_joules", "final_energy", "final_angle", "completed"
        ]
        
        test_data = dict(zip(columns, row))
        
        test_data["graph_degrees"] = json.loads(test_data["graph_degrees"])
        test_data["graph_joules"] = json.loads(test_data["graph_joules"])
        
        return test_data
