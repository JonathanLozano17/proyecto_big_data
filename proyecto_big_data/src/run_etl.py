import logging
import sys
from pathlib import Path
import yaml

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

from src.etl.extract import extract_from_excel
from src.etl.transform import DataTransformer
from src.etl.load import load_to_database, save_to_csv_backup
from src.database.connection import DatabaseManager

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/etl.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def load_config():
    """Carga configuración desde YAML"""
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    """Función principal del ETL"""
    logging.info("=" * 60)
    logging.info(" INICIANDO ETL - CONCESIONARIO MODELO ESTRELLA (SQLite)")
    logging.info("=" * 60)
    
    # Cargar configuración
    config = load_config()
    
    # Configuración específica para SQLite
    db_config = {
        'database': {
            'path': config['database']['path'],
            'type': config['database'].get('type', 'sqlite')
        }
    }
    
    # Ruta del archivo único
    base_path = Path(__file__).parent.parent
    file_path = base_path / config['etl']['source_files']['datos_concesionario']
    
    file_paths = {
        'datos_concesionario': str(file_path)
    }
    
    try:
        # 1. EXTRACT
        logging.info("\n FASE 1: EXTRACCIÓN")
        raw_data = extract_from_excel(file_paths)
        
        if not raw_data:
            logging.error("No se pudieron extraer datos")
            return
        
        logging.info(f" Datos extraídos correctamente")
        
        # 2. TRANSFORM
        logging.info("\n FASE 2: TRANSFORMACIÓN")
        transformer = DataTransformer(config)
        transformed_data = transformer.transform_all(raw_data)
        
        # Validar integridad referencial
        validation_results = transformer.validate_referential_integrity(transformed_data)
        if validation_results:
            logging.info("\n Validación de integridad referencial:")
            for key, value in validation_results.items():
                if value > 0:
                    logging.warning(f"  • {key}: {value}")
                else:
                    logging.info(f"  • {key}: {value}")
        
        # 3. BACKUP CSV (opcional pero recomendado)
        logging.info("\n Creando backup CSV...")
        save_to_csv_backup(transformed_data)
        
        # 4. LOAD a SQLite
        logging.info("\n FASE 3: CARGA A SQLite")
        db_path = load_to_database(
            transformed_data,
            db_path=config['database']['path'],
            schema=config['database'].get('schema', 'main')
        )
        
        logging.info(f"\n Base de datos SQLite creada: {db_path}")
        logging.info("=" * 60)
        logging.info(" ETL COMPLETADO EXITOSAMENTE")
        logging.info("=" * 60)
        
    except Exception as e:
        logging.error(f" Error en ETL: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()