"""
Sistema completo de ETL, Reportes y Predicciones
Ejecuta: python run_complete_system.py [--etl] [--reports] [--predictions]
"""

import argparse
import logging
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Agregar src al path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.run_etl import main as run_etl
from src.reports.generate_reports import main as run_reports
from src.predictions.vehicle_price_predictor import main as run_predictions


def setup_logging():
    """Configura logging"""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'system.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    parser = argparse.ArgumentParser(description='Sistema completo Concesionario')
    parser.add_argument('--etl', action='store_true', help='Ejecutar ETL')
    parser.add_argument('--reports', action='store_true', help='Generar reportes')
    parser.add_argument('--predictions', action='store_true', help='Ejecutar predicciones')
    parser.add_argument('--all', action='store_true', help='Ejecutar todo')
    
    # Usamos parse_known_args para que no explote con argumentos de otros módulos
    args, unknown = parser.parse_known_args() 
    
    setup_logging()
    
    if args.all or not (args.etl or args.reports or args.predictions):
        args.etl = args.reports = args.predictions = True

    # --- TRUCO: Limpiar sys.argv antes de llamar a las fases ---
    import sys
    original_argv = sys.argv
    sys.argv = [original_argv[0]] 
    # -----------------------------------------------------------

    print("=" * 70)
    print("SISTEMA DE GESTIÓN DE CONCESIONARIO - MODELO ESTRELLA")
    print("=" * 70)
    
    if args.etl:
        print("\n📤 FASE 1: EJECUTANDO ETL...")
        run_etl()
    
    if args.reports:
        print("\n📊 FASE 2: GENERANDO REPORTES...")
        # CORREGIDO: Sin argumentos
        run_reports()
    
    if args.predictions:
        print("\n🔮 FASE 3: EJECUTANDO PREDICCIONES...")
        # CORREGIDO: Sin argumentos
        run_predictions()

    print("\n" + "=" * 70)
    print("✅ SISTEMA COMPLETADO EXITOSAMENTE")
    print("=" * 70)


if __name__ == "__main__":
    main()