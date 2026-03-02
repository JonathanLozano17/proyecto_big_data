import logging
from sqlalchemy import create_engine, inspect
import pandas as pd
from typing import Dict

from sqlalchemy import create_engine, text # Importa 'text'

def load_to_database(data_dict: Dict[str, pd.DataFrame], connection_string: str, schema: str = "public"):
    """Carga múltiples tablas a PostgreSQL asegurando que el esquema exista"""
    try:
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # 1. Crear el esquema si no existe
            if schema != "public":
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                conn.commit() # Importante confirmar la creación del esquema
                logging.info(f"✅ Esquema '{schema}' verificado/creado exitosamente.")
            
            logging.info("✅ Conexión a base de datos exitosa")
        
        # Cargar cada tabla en orden (dimensiones primero, luego hechos)
        dimension_order = [
            'dim_ciudad',
            'dim_tiempo',
            'dim_cliente',
            'dim_sucursal',
            'dim_vehiculo',
            'dim_vendedor',
            'dim_tipoPago',
            'tipo_mantenimiento'
        ]
        
        fact_order = [
            'hecho_ventas',
            'hecho_mantenimiento'
        ]
        
        # Cargar dimensiones
        for table_name in dimension_order:
            if table_name in data_dict:
                df = data_dict[table_name]
                
                # Crear nombre de tabla en base de datos (con esquema)
                db_table = f"{schema}.{table_name}"
                
                # Cargar datos
                df.to_sql(
                    name=table_name,
                    con=engine,
                    schema=schema,
                    if_exists='replace',
                    index=False,
                    chunksize=1000
                )
                
                logging.info(f"  → {table_name}: {len(df)} filas cargadas")
        
        # Cargar tablas de hechos
        for table_name in fact_order:
            if table_name in data_dict:
                df = data_dict[table_name]
                
                db_table = f"{schema}.{table_name}"
                
                df.to_sql(
                    name=table_name,
                    con=engine,
                    schema=schema,
                    if_exists='replace',
                    index=False,
                    chunksize=1000
                )
                
                logging.info(f"  → {table_name}: {len(df)} filas cargadas")
        
        logging.info("\n✅ Todas las tablas cargadas exitosamente")
        
# Verificar counts
        logging.info("\n📊 Verificación de carga:")
        with engine.connect() as conn:
            for table_name in dimension_order + fact_order:
                if table_name in data_dict:
                    # Agregamos comillas dobles para respetar el nombre exacto con mayúsculas
                    query = text(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"')
                    result = conn.execute(query)
                    count = result.scalar()
                    logging.info(f"  • {table_name}: {count} registros")
            
            # ¡IMPORTANTE! Commit para cerrar la transacción de lectura correctamente
            conn.commit()
        
    except Exception as e:
        logging.error(f"Error cargando datos: {e}")
        raise