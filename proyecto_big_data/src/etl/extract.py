import pandas as pd
import logging
from pathlib import Path
from typing import Dict

def extract_from_excel(file_paths: Dict[str, str]) -> Dict[str, pd.DataFrame]:
    """Extrae datos de múltiples archivos Excel"""
    try:
        all_data = {}
        
        for table_name, file_path in file_paths.items():
            logging.info(f"Extrayendo {table_name} desde {file_path}")
            
            if not Path(file_path).exists():
                logging.error(f"Archivo no encontrado: {file_path}")
                continue
                
            # Leer el archivo Excel
            df = pd.read_excel(file_path)
            all_data[table_name] = df
            logging.info(f"  → {table_name}: {len(df)} filas, {len(df.columns)} columnas")
        
        return all_data
        
    except Exception as e:
        logging.error(f"Error extrayendo datos: {e}")
        raise