import logging
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

from etl.extract import extract_from_excel
from etl.transform import DataTransformer
from etl.load import load_to_database

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    """Función principal del ETL"""
    logging.info("=" * 60)
    logging.info("🚗 INICIANDO ETL - CONCESIONARIO MODELO ESTRELLA")
    logging.info("=" * 60)
    
    # Configuración
    config = {
        'validation': {
            'reject_future_dates': True,
            'min_date': '2020-01-01',
            'max_date': '2024-12-31',
            'min_price': 0,
            'max_price': 200000
        },
        'database': {
            'connection_string': 'postgresql://postgres:1717@localhost:5432/concesionario_db',
            'schema': 'public'
        }
    }
    
    # Ruta del archivo único
    base_path = Path(__file__).parent.parent
    file_path = str(base_path / 'data' / 'raw' / 'datos_concesionario_raw.xlsx')
    
    # El extractor espera un diccionario {nombre_tabla: ruta_archivo}
    # Usamos 'datos_concesionario' como nombre de la tabla origen
    file_paths = {
        'datos_concesionario': file_path
    }
    
    try:
        # 1. EXTRACT
        logging.info("\n📤 FASE 1: EXTRACCIÓN")
        raw_data = extract_from_excel(file_paths)
        
        if not raw_data:
            logging.error("No se pudieron extraer datos")
            return
        
        logging.info(f"✅ Datos extraídos correctamente")
        
        # 2. TRANSFORM
        logging.info("\n🔄 FASE 2: TRANSFORMACIÓN")
        transformer = DataTransformer(config)
        transformed_data = transformer.transform_all(raw_data)
        
        # Validar integridad referencial
        validation_results = transformer.validate_referential_integrity(transformed_data)
        if validation_results:
            logging.info("\n📊 Validación de integridad referencial:")
            for key, value in validation_results.items():
                if value > 0:
                    logging.warning(f"  • {key}: {value}")
                else:
                    logging.info(f"  • {key}: {value}")
        
        # 3. LOAD
        logging.info("\n📥 FASE 3: CARGA A BASE DE DATOS")
        load_to_database(
            transformed_data, 
            config['database']['connection_string'],
            config['database']['schema']
        )
        
        logging.info("\n" + "=" * 60)
        logging.info("✅ ETL COMPLETADO EXITOSAMENTE")
        logging.info("=" * 60)
        
    except Exception as e:
        logging.error(f"❌ Error en ETL: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()