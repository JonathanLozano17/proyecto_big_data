import logging
import yaml
from pathlib import Path
from src.etl.extract import extract_from_excel
from src.etl.transform import transform_data
from src.etl.load import load_to_database
from src.validation.data_quality import validate_data

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/etl.log'),
        logging.StreamHandler()
    ]
)

def main():
    # Cargar configuración
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    logging.info("Iniciando proceso ETL...")
    
    # 1. EXTRACT
    logging.info("Extrayendo datos...")
    data = extract_from_excel(config['etl']['source_file'])
    
    # Asumimos que trabajamos con la primera hoja
    df = list(data.values())[0]
    logging.info(f"Datos extraídos: {len(df)} filas")
    
    # 2. VALIDATE (pre-transformación)
    logging.info("Validando datos...")
    validation_result = validate_data(df, config['validation'])
    if not validation_result['passed']:
        logging.warning(f"Problemas de validación: {validation_result['issues']}")
    
    # 3. TRANSFORM
    logging.info("Transformando datos...")
    df_clean = transform_data(df, config)
    
    # 4. LOAD
    logging.info("Cargando datos...")
    conn_string = f"postgresql://{config['database']['user']}:{config['database']['password']}@{config['database']['host']}:{config['database']['port']}/{config['database']['name']}"
    
    load_to_database(
        df_clean, 
        config['etl']['target_table'],
        conn_string
    )
    
    logging.info("¡ETL completado exitosamente!")

if __name__ == "__main__":
    main()