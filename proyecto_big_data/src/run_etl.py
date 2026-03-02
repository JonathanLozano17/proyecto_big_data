import logging
import yaml
import sys
from pathlib import Path
from datetime import datetime

# Importar módulos actualizados
from src.etl.extract import extract_from_excel
from src.etl.transform import DataTransformer
from src.etl.load import load_to_database
from src.validation.data_quality import validate_data, generate_quality_report

def setup_logging(config):
    """Configura logging"""
    log_config = config.get('logging', {})
    log_file = log_config.get('file', 'logs/etl_concesionario.log')
    
    Path(log_file).parent.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s'),
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    start_time = datetime.now()
    
    try:
        # Cargar configuración
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        setup_logging(config)
        logging.info("=" * 60)
        logging.info("🚗 ETL CONCESIONARIO - MODELO ESTRELLA")
        logging.info("=" * 60)
        
        # 1. EXTRACT - Múltiples archivos
        logging.info("\n📂 FASE 1: EXTRACCIÓN DE DATOS")
        logging.info("-" * 40)
        
        data_raw = extract_from_excel(config['etl']['source_files'])
        logging.info(f"\n✅ Total tablas extraídas: {len(data_raw)}")
        
        # 2. VALIDATE (pre-transformación)
        logging.info("\n🔍 FASE 2: VALIDACIÓN PRE-TRANSFORMACIÓN")
        logging.info("-" * 40)
        
        all_validation_results = {}
        for table_name, df in data_raw.items():
            logging.info(f"\nValidando {table_name}:")
            table_config = config['validation'].copy()
            table_config['required_columns'] = config['validation'].get('required_columns', {}).get(table_name, [])
            
            validation_result = validate_data(df, table_config)
            all_validation_results[table_name] = validation_result
            
            # Mostrar resumen
            if validation_result['issues']:
                logging.warning(f"  ⚠️ {len(validation_result['issues'])} problemas críticos")
            if validation_result['warnings']:
                logging.warning(f"  ⚠️ {len(validation_result['warnings'])} advertencias")
            logging.info(f"  ✓ {validation_result['statistics']['total_rows']} filas")
        
        # 3. TRANSFORM
        logging.info("\n🔄 FASE 3: TRANSFORMACIÓN DE DATOS")
        logging.info("-" * 40)
        
        transformer = DataTransformer(config)
        data_clean = transformer.transform_all(data_raw)
        
        # Validar integridad referencial
        ref_validation = transformer.validate_referential_integrity(data_clean)
        logging.info("\n🔗 Validación de integridad referencial:")
        for key, value in ref_validation.items():
            if value > 0:
                logging.warning(f"  ⚠️ {key}: {value} registros inválidos")
        
        # 4. LOAD
        logging.info("\n💾 FASE 4: CARGA A BASE DE DATOS")
        logging.info("-" * 40)
        
        conn_string = (f"postgresql://{config['database']['user']}:{config['database']['password']}"
                      f"@{config['database']['host']}:{config['database']['port']}/{config['database']['name']}")
        
        load_to_database(
            data_clean,
            conn_string,
            config['etl']['target_schema']
        )
        
        # 5. REPORTE FINAL
        end_time = datetime.now()
        duration = end_time - start_time
        
        logging.info("\n" + "=" * 60)
        logging.info("✅ ETL COMPLETADO EXITOSAMENTE")
        logging.info("=" * 60)
        logging.info(f"\n📊 Resumen final:")
        logging.info(f"  • Tiempo total: {duration.total_seconds():.2f} segundos")
        logging.info(f"  • Tablas procesadas: {len(data_clean)}")
        
        for table_name, df in data_clean.items():
            logging.info(f"    - {table_name}: {len(df)} filas")
        
        logging.info(f"\n📁 Logs guardados en: logs/etl_concesionario.log")
        logging.info("=" * 60)
        
    except Exception as e:
        logging.error(f"\n❌ Error crítico en ETL: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()