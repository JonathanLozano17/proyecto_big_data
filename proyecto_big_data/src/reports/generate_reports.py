import pandas as pd
import numpy as np 
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from datetime import datetime, timedelta
import json
import sys
import os
from ..database.connection import DatabaseManager

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class ReportGenerator:
    """Generador de reportes analíticos"""
    
    def __init__(self, db_path: str = None):
        self.db_manager = DatabaseManager(db_path)
        self.output_dir = Path(__file__).parent.parent.parent / 'reports'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar estilo de gráficos
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
    
    def generate_all_reports(self):
        """Genera todos los reportes disponibles"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_dir = self.output_dir / f'report_{timestamp}'
        report_dir.mkdir(exist_ok=True)
        
        # Usar logging sin emojis para Windows
        logging.info(f"\nGenerando reportes en: {report_dir}")
        
        reports = {
            'ventas_por_tiempo': self.ventas_por_tiempo,
            'top_clientes': self.top_clientes,
            'rendimiento_vendedores': self.rendimiento_vendedores,
            'mantenimiento_por_tipo': self.mantenimiento_por_tipo,
            'analisis_financiero': self.analisis_financiero,
            'dashboard_ventas': self.dashboard_ventas,
            'calidad_datos': self.reporte_calidad_datos
        }
        
        results = {}
        for name, func in reports.items():
            try:
                logging.info(f"  -> Generando: {name}")
                result = func(report_dir)
                results[name] = result
            except Exception as e:
                logging.error(f"  Error en {name}: {e}")
                results[name] = {'error': str(e)}
        
        # Guardar resumen
        self.guardar_resumen(results, report_dir)
        
        logging.info(f"\nReportes generados en: {report_dir}")
        return report_dir
    
    def ventas_por_tiempo(self, output_dir):
        """Análisis de ventas por dimensión temporal"""
        query = """
        SELECT 
            t.año,
            t.mes,
            t.nombre_mes,
            t.trimestre,
            COUNT(v.id_venta) as num_ventas,
            SUM(v.precio_venta) as ingresos_totales,
            AVG(v.precio_venta) as ticket_promedio,
            SUM(v.precio_venta - v.costo_vehiculo) as ganancia_total,
            COUNT(DISTINCT v.id_cliente) as clientes_unicos
        FROM hecho_ventas v
        JOIN dim_tiempo t ON v.id_tiempo = t.id_tiempo
        GROUP BY t.año, t.mes, t.nombre_mes, t.trimestre
        ORDER BY t.año, t.mes
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty:
            return {'error': 'No hay datos de ventas'}
        
        # Gráficos
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Ventas por mes
        df_mensual = df.copy()
        df_mensual['periodo'] = df_mensual['año'].astype(str) + '-' + df_mensual['mes'].astype(str).str.zfill(2)
        axes[0, 0].plot(range(len(df_mensual)), df_mensual['ingresos_totales'], marker='o')
        axes[0, 0].set_title('Ingresos Mensuales')
        axes[0, 0].set_xticks(range(len(df_mensual)))
        axes[0, 0].set_xticklabels(df_mensual['periodo'], rotation=45, ha='right')
        
        # Ventas por trimestre
        df_trim = df.groupby(['año', 'trimestre'])['ingresos_totales'].sum().reset_index()
        df_trim['periodo'] = df_trim['año'].astype(str) + '-T' + df_trim['trimestre'].astype(str)
        axes[0, 1].bar(range(len(df_trim)), df_trim['ingresos_totales'])
        axes[0, 1].set_title('Ingresos por Trimestre')
        axes[0, 1].set_xticks(range(len(df_trim)))
        axes[0, 1].set_xticklabels(df_trim['periodo'], rotation=45, ha='right')
        
        # Ticket promedio
        axes[1, 0].plot(range(len(df_mensual)), df_mensual['ticket_promedio'], marker='s', color='green')
        axes[1, 0].set_title('Ticket Promedio Mensual')
        axes[1, 0].set_xticks(range(len(df_mensual)))
        axes[1, 0].set_xticklabels(df_mensual['periodo'], rotation=45, ha='right')
        
        # Distribución por año
        df_anual = df.groupby('año')['ingresos_totales'].sum().reset_index()
        axes[1, 1].bar(df_anual['año'].astype(str), df_anual['ingresos_totales'])
        axes[1, 1].set_title('Ingresos por Año')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'ventas_por_tiempo.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # Guardar datos
        df.to_csv(output_dir / 'ventas_por_tiempo.csv', index=False, encoding='utf-8-sig')
        
        return {
            'total_ingresos': float(df['ingresos_totales'].sum()),
            'total_ventas': int(df['num_ventas'].sum()),
            'ticket_promedio_general': float(df['ingresos_totales'].sum() / df['num_ventas'].sum()) if df['num_ventas'].sum() > 0 else 0,
            'mes_max_ventas': str(df.loc[df['ingresos_totales'].idxmax(), 'nombre_mes']) if not df.empty else None
        }
    
    def top_clientes(self, output_dir):
        """Top clientes por volumen de compras"""
        # Primero verificar qué columnas existen en dim_cliente
        check_query = "PRAGMA table_info(dim_cliente)"
        columns_df = self.db_manager.execute_query(check_query)
        column_names = columns_df['name'].tolist() if not columns_df.empty else []
        
        # Construir consulta dinámicamente
        select_cols = """
            c.id_cliente,
            c.nombre as nombre_cliente,
            c.tipo_cliente
        """
        
        if 'nombre_ciudad' in column_names:
            select_cols += ", c.nombre_ciudad"
        elif 'ciudad' in column_names:
            select_cols += ", c.ciudad as nombre_ciudad"
        else:
            select_cols += ", 'N/A' as nombre_ciudad"
        
        query = f"""
        SELECT 
            {select_cols},
            COUNT(v.id_venta) as num_compras,
            SUM(v.precio_venta) as total_gastado,
            AVG(v.precio_venta) as ticket_promedio,
            COUNT(DISTINCT v.id_vehiculo) as vehiculos_comprados,
            MAX(v.precio_venta) as compra_maxima
        FROM hecho_ventas v
        JOIN dim_cliente c ON v.id_cliente = c.id_cliente
        GROUP BY c.id_cliente, c.nombre, c.tipo_cliente
        ORDER BY total_gastado DESC
        LIMIT 20
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty:
            return {'error': 'No hay datos de clientes'}
        
        # Gráfico
        fig, ax = plt.subplots(figsize=(12, 6))
        y_pos = range(len(df))
        ax.barh(y_pos, df['total_gastado'])
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['nombre_cliente'])
        ax.set_xlabel('Total Gastado ($)')
        ax.set_title('Top 20 Clientes por Gasto Total')
        ax.invert_yaxis()
        
        # Añadir valores
        for i, (_, row) in enumerate(df.iterrows()):
            ax.text(row['total_gastado'], i, f'  ${row["total_gastado"]:,.0f}', va='center')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'top_clientes.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        df.to_csv(output_dir / 'top_clientes.csv', index=False, encoding='utf-8-sig')
        
        return {
            'top_cliente': str(df.iloc[0]['nombre_cliente']) if not df.empty else None,
            'top_gasto': float(df.iloc[0]['total_gastado']) if not df.empty else 0,
            'clientes_recurrentes': int(len(df[df['num_compras'] > 1]))
        }
    
    def rendimiento_vendedores(self, output_dir):
        """Análisis de rendimiento de vendedores"""
        # Verificar columnas en hecho_ventas
        check_ventas = "PRAGMA table_info(hecho_ventas)"
        ventas_cols = self.db_manager.execute_query(check_ventas)
        ventas_col_names = ventas_cols['name'].tolist() if not ventas_cols.empty else []
        
        # Construir consulta sin comision_vendedor si no existe
        comision_select = "0 as comision_total"
        if 'comision_vendedor' in ventas_col_names:
            comision_select = "SUM(hv.comision_vendedor) as comision_total"
        
        query = f"""
        SELECT 
            v.id_vendedor,
            v.nombre as nombre_vendedor,
            v.experiencia_anios,
            s.nombre as sucursal,
            COUNT(hv.id_venta) as ventas_realizadas,
            SUM(hv.precio_venta) as ingresos_generados,
            AVG(hv.precio_venta) as ticket_promedio,
            {comision_select},
            COUNT(DISTINCT hv.id_cliente) as clientes_atendidos
        FROM hecho_ventas hv
        JOIN dim_vendedor v ON hv.id_vendedor = v.id_vendedor
        JOIN dim_sucursal s ON hv.id_sucursal = s.id_sucursal
        GROUP BY v.id_vendedor, v.nombre, v.experiencia_anios, s.nombre
        ORDER BY ingresos_generados DESC
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty:
            return {'error': 'No hay datos de vendedores'}
        
        # Gráfico 1: Top vendedores
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Ingresos por vendedor
        top10 = df.head(10)
        y_pos = range(len(top10))
        axes[0].barh(y_pos, top10['ingresos_generados'])
        axes[0].set_yticks(y_pos)
        axes[0].set_yticklabels(top10['nombre_vendedor'])
        axes[0].set_xlabel('Ingresos Generados ($)')
        axes[0].set_title('Top 10 Vendedores por Ingresos')
        axes[0].invert_yaxis()
        
        # Relación experiencia vs rendimiento
        axes[1].scatter(df['experiencia_anios'], df['ingresos_generados'], alpha=0.6)
        axes[1].set_xlabel('Años de Experiencia')
        axes[1].set_ylabel('Ingresos Generados ($)')
        axes[1].set_title('Experiencia vs Rendimiento')
        
        # Añadir línea de tendencia si hay suficientes datos
        if len(df) > 1:
            import numpy as np
            z = np.polyfit(df['experiencia_anios'], df['ingresos_generados'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(df['experiencia_anios'].min(), df['experiencia_anios'].max(), 50)
            axes[1].plot(x_line, p(x_line), "r--", alpha=0.8)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'rendimiento_vendedores.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        df.to_csv(output_dir / 'rendimiento_vendedores.csv', index=False, encoding='utf-8-sig')
        
        return {
            'mejor_vendedor': str(df.iloc[0]['nombre_vendedor']),
            'ingresos_mejor': float(df.iloc[0]['ingresos_generados']),
            'promedio_ventas_vendedor': float(df['ventas_realizadas'].mean()),
            'correlacion_experiencia': float(df['experiencia_anios'].corr(df['ingresos_generados'])) if len(df) > 1 else 0
        }
    
    def mantenimiento_por_tipo(self, output_dir):
        """Análisis de servicios de mantenimiento"""
        query = """
        SELECT 
            tm.nombre_tipo as tipo_mantenimiento,
            tm.descripcion,
            COUNT(m.id_mantenimiento) as num_servicios,
            SUM(COALESCE(m.costo_servicio, 0) + COALESCE(m.costo_repuestos, 0)) as ingresos_totales,
            AVG(COALESCE(m.costo_servicio, 0) + COALESCE(m.costo_repuestos, 0)) as costo_promedio,
            AVG(m.horas_taller) as horas_promedio,
            SUM(COALESCE(m.repuestos_usados, 0)) as total_repuestos,
            AVG(m.kilometraje_vehiculo) as km_promedio
        FROM hecho_mantenimiento m
        JOIN tipo_mantenimiento tm ON m.id_tipo_mantenimiento = tm.id_tipo_mantenimiento
        GROUP BY tm.nombre_tipo, tm.descripcion
        ORDER BY num_servicios DESC
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty:
            return {'error': 'No hay datos de mantenimiento'}
        
        # Gráficos
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Distribución por tipo
        axes[0].pie(df['num_servicios'], labels=df['tipo_mantenimiento'], autopct='%1.1f%%')
        axes[0].set_title('Distribución de Servicios por Tipo')
        
        # Costo promedio por tipo
        x_pos = range(len(df))
        axes[1].bar(x_pos, df['costo_promedio'])
        axes[1].set_xticks(x_pos)
        axes[1].set_xticklabels(df['tipo_mantenimiento'], rotation=45, ha='right')
        axes[1].set_xlabel('Tipo de Mantenimiento')
        axes[1].set_ylabel('Costo Promedio ($)')
        axes[1].set_title('Costo Promedio por Tipo de Mantenimiento')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'mantenimiento_por_tipo.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        df.to_csv(output_dir / 'mantenimiento_por_tipo.csv', index=False, encoding='utf-8-sig')
        
        return {
            'servicio_mas_comun': str(df.iloc[0]['tipo_mantenimiento']),
            'total_servicios': int(df['num_servicios'].sum()),
            'ingresos_mantenimiento': float(df['ingresos_totales'].sum()),
            'costo_promedio_general': float(df['ingresos_totales'].sum() / df['num_servicios'].sum()) if df['num_servicios'].sum() > 0 else 0
        }
    
    def analisis_financiero(self, output_dir):
        """Análisis financiero completo"""
        query = """
        SELECT 
            t.año,
            t.mes,
            COUNT(v.id_venta) as ventas,
            SUM(v.precio_venta) as ingresos,
            SUM(v.costo_vehiculo) as costos,
            SUM(v.precio_venta - v.costo_vehiculo) as margen,
            AVG((v.precio_venta - v.costo_vehiculo) / v.precio_venta * 100) as margen_porcentaje,
            SUM(CASE WHEN v.financiado = 1 THEN v.precio_venta ELSE 0 END) as ventas_financiadas,
            COUNT(CASE WHEN v.financiado = 1 THEN 1 END) as num_financiadas
        FROM hecho_ventas v
        JOIN dim_tiempo t ON v.id_tiempo = t.id_tiempo
        GROUP BY t.año, t.mes
        ORDER BY t.año, t.mes
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty:
            return {'error': 'No hay datos financieros'}
        
        # Métricas adicionales
        df['periodo'] = df['año'].astype(str) + '-' + df['mes'].astype(str).str.zfill(2)
        df['tasa_financiacion'] = (df['ventas_financiadas'] / df['ingresos'] * 100).fillna(0)
        
        # Gráfico
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        x_pos = range(len(df))
        
        # Ingresos vs Costos
        axes[0, 0].plot(x_pos, df['ingresos'], marker='o', label='Ingresos')
        axes[0, 0].plot(x_pos, df['costos'], marker='s', label='Costos')
        axes[0, 0].set_title('Ingresos vs Costos')
        axes[0, 0].legend()
        axes[0, 0].set_xticks(x_pos[::3])
        axes[0, 0].set_xticklabels(df['periodo'][::3], rotation=45, ha='right')
        
        # Margen de ganancia
        axes[0, 1].bar(x_pos, df['margen'])
        axes[0, 1].set_title('Margen de Ganancia Absoluto')
        axes[0, 1].set_xticks(x_pos[::3])
        axes[0, 1].set_xticklabels(df['periodo'][::3], rotation=45, ha='right')
        
        # Porcentaje de margen
        axes[1, 0].plot(x_pos, df['margen_porcentaje'], marker='o', color='green')
        axes[1, 0].set_title('Margen de Ganancia (%)')
        axes[1, 0].set_xticks(x_pos[::3])
        axes[1, 0].set_xticklabels(df['periodo'][::3], rotation=45, ha='right')
        
        # Tasa de financiación
        axes[1, 1].bar(x_pos, df['tasa_financiacion'], color='purple')
        axes[1, 1].set_title('Tasa de Financiación (%)')
        axes[1, 1].set_xticks(x_pos[::3])
        axes[1, 1].set_xticklabels(df['periodo'][::3], rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'analisis_financiero.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        df.to_csv(output_dir / 'analisis_financiero.csv', index=False, encoding='utf-8-sig')
        
        return {
            'ingresos_totales': float(df['ingresos'].sum()),
            'costos_totales': float(df['costos'].sum()),
            'margen_total': float(df['margen'].sum()),
            'margen_promedio': float(df['margen_porcentaje'].mean()),
            'tasa_financiacion_promedio': float(df['tasa_financiacion'].mean())
        }
    
    def dashboard_ventas(self, output_dir):
        """Crea un dashboard HTML interactivo"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Dashboard Concesionario</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .container { display: flex; flex-wrap: wrap; gap: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1 1 300px; }
        .metric { font-size: 24px; font-weight: bold; color: #3498db; }
        .chart-container { width: 100%; margin-top: 20px; background: white; padding: 20px; border-radius: 10px; }
        img { max-width: 100%; height: auto; border-radius: 5px; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #3498db; color: white; padding: 10px; }
        td { padding: 8px; border-bottom: 1px solid #ddd; }
        .timestamp { color: #7f8c8d; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Dashboard Concesionario - Modelo Estrella</h1>
        <p>Reporte generado: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    </div>
    
    <div class="container">
        <div class="card">
            <h3>Ventas</h3>
            <div class="metric" id="total-ventas">Cargando...</div>
            <p>Total de transacciones</p>
        </div>
        <div class="card">
            <h3>Ingresos</h3>
            <div class="metric" id="total-ingresos">Cargando...</div>
            <p>Ingresos totales</p>
        </div>
        <div class="card">
            <h3>Clientes</h3>
            <div class="metric" id="total-clientes">Cargando...</div>
            <p>Clientes únicos</p>
        </div>
        <div class="card">
            <h3>Mantenimientos</h3>
            <div class="metric" id="total-mant">Cargando...</div>
            <p>Servicios realizados</p>
        </div>
    </div>
    
    <div class="chart-container">
        <h2>Análisis de Ventas</h2>
        <img src="ventas_por_tiempo.png" alt="Ventas por tiempo">
    </div>
    
    <div class="chart-container">
        <h2>Análisis Financiero</h2>
        <img src="analisis_financiero.png" alt="Análisis financiero">
    </div>
    
    <div class="chart-container">
        <h2>Top Clientes</h2>
        <img src="top_clientes.png" alt="Top clientes">
    </div>
    
    <div class="chart-container">
        <h2>Mantenimiento por Tipo</h2>
        <img src="mantenimiento_por_tipo.png" alt="Mantenimiento">
    </div>
    
    <div class="chart-container">
        <h2>Rendimiento de Vendedores</h2>
        <img src="rendimiento_vendedores.png" alt="Rendimiento vendedores">
    </div>
    
    <div class="timestamp">
        <p>Dashboard generado automáticamente por el sistema ETL</p>
    </div>
    
    <script>
        // Cargar métricas dinámicamente
        fetch('resumen.json')
            .then(response => response.json())
            .then(data => {
                document.getElementById('total-ventas').textContent = data.total_ventas || '0';
                document.getElementById('total-ingresos').textContent = '$' + (data.ingresos_totales || 0).toLocaleString();
                document.getElementById('total-clientes').textContent = data.total_clientes || '0';
                document.getElementById('total-mant').textContent = data.total_mantenimientos || '0';
            })
            .catch(error => {
                console.error('Error cargando datos:', error);
            });
    </script>
</body>
</html>"""
        
        with open(output_dir / 'dashboard.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return {'dashboard': 'dashboard.html'}
    
    def reporte_calidad_datos(self, output_dir):
        """Reporte de calidad de datos actual"""
        # Obtener lista de tablas
        tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
        tables_df = self.db_manager.execute_query(tables_query)
        
        resultados = {}
        
        # Verificar nulos en tablas principales
        for table in ['hecho_ventas', 'hecho_mantenimiento', 'dim_cliente']:
            try:
                count = self.db_manager.execute_query(f"SELECT COUNT(*) FROM {table}").iloc[0, 0]
                
                # Verificar nulos en columnas clave
                if table == 'hecho_ventas':
                    nulos = self.db_manager.execute_query(
                        "SELECT COUNT(*) FROM hecho_ventas WHERE id_cliente IS NULL"
                    ).iloc[0, 0]
                    resultados[f'nulos_{table}'] = int(nulos)
                elif table == 'hecho_mantenimiento':
                    nulos = self.db_manager.execute_query(
                        "SELECT COUNT(*) FROM hecho_mantenimiento WHERE id_cliente IS NULL"
                    ).iloc[0, 0]
                    resultados[f'nulos_{table}'] = int(nulos)
                
                resultados[f'total_{table}'] = int(count)
            except:
                resultados[f'total_{table}'] = 0
                resultados[f'nulos_{table}'] = 0
        
        # Verificar duplicados en ventas
        try:
            duplicados = self.db_manager.execute_query(
                "SELECT COUNT(*) - COUNT(DISTINCT id_venta) FROM hecho_ventas"
            ).iloc[0, 0]
            resultados['duplicados_ventas'] = int(duplicados)
        except:
            resultados['duplicados_ventas'] = 0
        
        # Verificar relaciones rotas
        try:
            rotas = self.db_manager.execute_query("""
                SELECT COUNT(*) FROM hecho_ventas 
                WHERE id_cliente NOT IN (SELECT id_cliente FROM dim_cliente WHERE id_cliente IS NOT NULL)
            """).iloc[0, 0]
            resultados['relaciones_rotas_ventas'] = int(rotas)
        except:
            resultados['relaciones_rotas_ventas'] = 0
        
        # Estadísticas generales
        stats = {
            'tablas': {},
            'calidad': resultados
        }
        
        for table in ['dim_cliente', 'dim_vehiculo', 'hecho_ventas', 'hecho_mantenimiento']:
            try:
                count = self.db_manager.execute_query(f"SELECT COUNT(*) FROM {table}").iloc[0, 0]
                stats['tablas'][table] = int(count)
            except:
                stats['tablas'][table] = 0
        
        # Guardar reporte
        with open(output_dir / 'calidad_datos.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, default=str)
        
        return stats
    
    def guardar_resumen(self, results, output_dir):
        """Guarda resumen de todos los reportes"""
        # Obtener métricas generales
        query_general = """
        SELECT 
            (SELECT COUNT(*) FROM hecho_ventas) as total_ventas,
            (SELECT COUNT(*) FROM hecho_mantenimiento) as total_mantenimientos,
            (SELECT COUNT(*) FROM dim_cliente) as total_clientes,
            (SELECT COUNT(*) FROM dim_vehiculo) as total_vehiculos,
            (SELECT SUM(precio_venta) FROM hecho_ventas) as ingresos_totales,
            (SELECT AVG(precio_venta) FROM hecho_ventas) as ticket_promedio
        """
        
        try:
            df_gral = self.db_manager.execute_query(query_general)
            resumen = df_gral.iloc[0].to_dict() if not df_gral.empty else {}
            # Convertir a tipos nativos de Python
            for k, v in resumen.items():
                if pd.isna(v):
                    resumen[k] = 0
                elif isinstance(v, (np.integer, np.floating)):
                    resumen[k] = float(v) if isinstance(v, np.floating) else int(v)
        except Exception as e:
            logging.warning(f"Error obteniendo métricas generales: {e}")
            resumen = {}
        
        # Combinar con resultados de reportes
        resumen.update({
            'fecha_generacion': datetime.now().isoformat(),
            'reportes_generados': list(results.keys()),
            'resultados': {k: v for k, v in results.items() if isinstance(v, dict) and 'error' not in v}
        })
        
        # Guardar JSON
        with open(output_dir / 'resumen.json', 'w', encoding='utf-8') as f:
            json.dump(resumen, f, indent=2, default=str)
        
        # Guardar como texto legible (sin emojis)
        with open(output_dir / 'resumen.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("RESUMEN DE REPORTES - CONCESIONARIO\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("METRICAS GENERALES:\n")
            f.write(f"  * Ventas totales: {resumen.get('total_ventas', 0):,}\n")
            f.write(f"  * Mantenimientos: {resumen.get('total_mantenimientos', 0):,}\n")
            f.write(f"  * Clientes unicos: {resumen.get('total_clientes', 0):,}\n")
            f.write(f"  * Vehiculos: {resumen.get('total_vehiculos', 0):,}\n")
            f.write(f"  * Ingresos totales: ${resumen.get('ingresos_totales', 0):,.2f}\n")
            f.write(f"  * Ticket promedio: ${resumen.get('ticket_promedio', 0):,.2f}\n\n")
            
            f.write("RESULTADOS POR REPORTE:\n")
            for name, result in results.items():
                if isinstance(result, dict) and 'error' not in result:
                    f.write(f"  * {name}:\n")
                    for k, v in list(result.items())[:5]:
                        if isinstance(v, float):
                            f.write(f"      - {k}: {v:.2f}\n")
                        else:
                            f.write(f"      - {k}: {v}\n")
                    f.write("\n")
            
            f.write("=" * 60 + "\n")

def main():
    """Función principal para generar reportes"""
    logging.basicConfig(level=logging.INFO)
    
    generator = ReportGenerator()
    report_dir = generator.generate_all_reports()
    
    print(f"\nReportes generados en: {report_dir}")
    print(f"Abre el archivo: {report_dir}/dashboard.html para ver el dashboard")

if __name__ == "__main__":
    main()