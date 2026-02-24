import logging
import yaml
import sys
from pathlib import Path
from datetime import datetime
from src.etl.extract import extract_from_excel
from src.etl.transform import DataTransformer
from src.etl.load import load_to_database
from src.validation.data_quality import validate_data, generate_quality_report

def setup_logging(config):
    """Configura logging con rotación de archivos"""
    log_config = config.get('logging', {})
    log_file = log_config.get('file', 'logs/etl.log')
    
    # Crear directorio de logs si no existe
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
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        setup_logging(config)
        logging.info("=" * 50)
        logging.info("INICIANDO PROCESO ETL")
        logging.info("=" * 50)
        
        # 1. EXTRACT
        logging.info("\n FASE 1: EXTRACCIÓN")
        logging.info("-" * 30)
        data = extract_from_excel(config['etl']['source_file'])
        
        # Asumimos que trabajamos con la primera hoja
        df = list(data.values())[0]
        logging.info(f"Datos extraídos: {len(df)} filas, {len(df.columns)} columnas")
        
        # 2. VALIDATE (pre-transformación)
        logging.info("\n FASE 2: VALIDACIÓN PRE-TRANSFORMACIÓN")
        logging.info("-" * 30)
        validation_result = validate_data(df, config['validation'])
        
        # Generar y guardar reporte de calidad
        quality_report = generate_quality_report(df, validation_result)
        logging.info("\n" + quality_report)
        
        # Guardar reporte a archivo
        report_file = f"logs/quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open("archivo.txt", "w", encoding="utf-8") as f:
            f.write(quality_report)
        
        # Decidir si continuar basado en umbral de errores
        error_threshold = config['etl'].get('error_threshold', 10)
        if len(validation_result['issues']) > error_threshold:
            logging.error(f" Demasiados problemas críticos ({len(validation_result['issues'])}). Abortando ETL.")
            sys.exit(1)
        
        # 3. TRANSFORM
        logging.info("\n FASE 3: TRANSFORMACIÓN")
        logging.info("-" * 30)
        
        transformer = DataTransformer(config)
        df_clean = transformer.transform(df)
        
        logging.info(f" Transformación completada")
        logging.info(f"   • Filas originales: {len(df)}")
        logging.info(f"   • Filas después: {len(df_clean)}")
        
        # Mostrar resumen de transformaciones
        transform_report = transformer.get_transformation_report()
        logging.info(f"   • Pasos aplicados: {transform_report['total_steps']}")
        
        # 4. LOAD
        logging.info("\n FASE 4: CARGA A BASE DE DATOS")
        logging.info("-" * 30)
        
        conn_string = (f"postgresql://{config['database']['user']}:{config['database']['password']}"
                      f"@{config['database']['host']}:{config['database']['port']}/{config['database']['name']}")
        
        load_to_database(
            df_clean, 
            config['etl']['target_table'],
            conn_string
        )
        
        # 5. FINALIZACIÓN
        end_time = datetime.now()
        duration = end_time - start_time
        
        logging.info("\n" + "=" * 50)
        logging.info(" ETL COMPLETADO EXITOSAMENTE")
        logging.info("=" * 50)
        logging.info(f" Resumen final:")
        logging.info(f"   • Tiempo total: {duration.total_seconds():.2f} segundos")
        logging.info(f"   • Filas procesadas: {len(df_clean)}")
        logging.info(f"   • Columnas finales: {len(df_clean.columns)}")
        logging.info(f"   • Tabla destino: {config['etl']['target_table']}")
        logging.info(f"   • Reporte de calidad: {report_file}")
        logging.info("=" * 50)
        
    except Exception as e:
        logging.error(f" Error crítico en ETL: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()