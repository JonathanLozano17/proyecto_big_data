import logging
from sqlalchemy import create_engine, inspect, text
import pandas as pd
from typing import Dict

def load_to_database(data_dict: Dict[str, pd.DataFrame], connection_string: str, schema: str = "public"):
    """Carga múltiples tablas a PostgreSQL asegurando que el esquema exista"""
    try:
        engine = create_engine(connection_string, connect_args={"client_encoding": "utf8"})
        
        with engine.connect() as conn:
            # 1. Crear el esquema si no existe
            if schema != "public":
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                conn.commit()
                logging.info(f"✅ Esquema '{schema}' verificado/creado exitosamente.")
            
            logging.info("✅ Conexión a base de datos exitosa")
        
        # Orden de carga (dimensiones primero, luego hechos)
        tables_in_order = [
            'dim_ciudad',
            'dim_tiempo',
            'dim_cliente',
            'dim_sucursal',
            'dim_vehiculo',
            'dim_vendedor',
            'dim_tipoPago',
            'tipo_mantenimiento',
            'hecho_ventas',
            'hecho_mantenimiento'
        ]
        
        # Cargar tablas en orden
        for table_name in tables_in_order:
            if table_name in data_dict and not data_dict[table_name].empty:
                df = data_dict[table_name]
                
                # Crear nombre de tabla en base de datos (con esquema)
                db_table = f"{schema}.{table_name}" if schema != "public" else table_name
                
                # Cargar datos
                df.to_sql(
                    name=table_name,
                    con=engine,
                    schema=schema if schema != "public" else None,
                    if_exists='replace',
                    index=False,
                    chunksize=1000
                )
                
                logging.info(f"  → {table_name}: {len(df)} filas cargadas")
            elif table_name in data_dict and data_dict[table_name].empty:
                logging.info(f"  → {table_name}: tabla vacía (no se carga)")
        
        logging.info("\n✅ Todas las tablas cargadas exitosamente")
        
        # Verificar counts
        logging.info("\n📊 Verificación de carga:")
        with engine.connect() as conn:
            for table_name in tables_in_order:
                if table_name in data_dict and not data_dict[table_name].empty:
                    try:
                        query = text(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"')
                        result = conn.execute(query)
                        count = result.scalar()
                        logging.info(f"  • {table_name}: {count} registros")
                    except Exception as e:
                        logging.warning(f"  • {table_name}: no se pudo verificar ({e})")
            
            conn.commit()
        
    except Exception as e:
        logging.error(f"Error cargando datos: {e}")
        raise