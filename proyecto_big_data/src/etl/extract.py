import pandas as pd
import logging
from pathlib import Path

def extract_from_excel(file_path):
    """Extrae datos de Excel manejando múltiples hojas"""
    try:
        # Leer todas las hojas
        excel_file = pd.ExcelFile(file_path)
        sheets_dict = {}
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheets_dict[sheet_name] = df
            logging.info(f"Hoja '{sheet_name}' cargada: {len(df)} filas")
        
        return sheets_dict
    except Exception as e:
        logging.error(f"Error extrayendo datos: {e}")
        raise