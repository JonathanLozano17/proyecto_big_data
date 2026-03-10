import sqlite3
import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import json

class DatabaseManager:
    """Manejador de base de datos SQLite"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Cargar configuración
            config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            db_path = config['database']['path']
        
        self.db_path = db_path
        # Asegurar que el directorio existe
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
    def get_connection(self):
        """Obtiene conexión a SQLite"""
        conn = sqlite3.connect(self.db_path)
        # Habilitar foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Mejorar manejo de tipos
        conn.execute("PRAGMA journal_mode = WAL")  # Mejor concurrencia
        return conn
    
    def table_exists(self, table_name: str) -> bool:
        """Verifica si una tabla existe"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """Obtiene el esquema de una tabla"""
        conn = self.get_connection()
        query = f"PRAGMA table_info({table_name})"
        schema = pd.read_sql(query, conn)
        conn.close()
        return schema
    
    def backup_database(self, backup_path: Optional[str] = None):
        """Crea un backup de la base de datos"""
        if backup_path is None:
            backup_dir = Path(__file__).parent.parent.parent / 'data' / 'backups'
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backup_dir / f"concesionario_backup_{timestamp}.db"
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        logging.info(f"✅ Backup creado: {backup_path}")
        return backup_path
    
    def execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Ejecuta una consulta y retorna DataFrame"""
        conn = self.get_connection()
        try:
            df = pd.read_sql_query(query, conn, params=params)
            return df
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Ejecuta una actualización y retorna número de filas afectadas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()