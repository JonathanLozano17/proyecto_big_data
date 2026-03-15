"""
report_generator.py  —  Generador de reportes analíticos del concesionario.

Uso:
    python report_generator.py
    python report_generator.py --db data/processed/concesionario.db
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sqlite3

from ..kpis.kpi_calculator import KPICalculator

# ── Encoding para Windows ──────────────────────────────────────────────────────
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE MANAGER (autocontenido, sin imports relativos)
# ──────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    def __init__(self, db_path: str = 'data/processed/concesionario.db'):
        self.db_path = db_path

    def execute_query(self, query: str, params=None) -> pd.DataFrame:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            log.error(f"Error ejecutando query: {e}")
            return pd.DataFrame()

    def table_columns(self, table: str) -> list:
        df = self.execute_query(f"PRAGMA table_info({table})")
        return df['name'].tolist() if not df.empty else []


# ──────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ──────────────────────────────────────────────────────────────────────────────

class ReportGenerator:
    """Generador de reportes analíticos para el concesionario."""

    def __init__(self, db_path: str = 'data/processed/concesionario.db'):
        self.db = DatabaseManager(db_path)
        self.output_dir = Path('reports')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette('husl')

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def generate_all_reports(self) -> Path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_dir = self.output_dir / f'report_{timestamp}'
        report_dir.mkdir(exist_ok=True)
        log.info(f"Generando reportes en: {report_dir}")

        tasks = {
            'ventas_por_tiempo':      self.ventas_por_tiempo,
            'top_clientes':           self.top_clientes,
            'rendimiento_vendedores': self.rendimiento_vendedores,
            'mantenimiento_por_tipo': self.mantenimiento_por_tipo,
            'analisis_financiero':    self.analisis_financiero,
            'dashboard_ventas':       self.dashboard_ventas,
            'calidad_datos':          self.reporte_calidad_datos,
        }

        results = {}
        for name, fn in tasks.items():
            try:
                log.info(f"  -> Generando: {name}")
                results[name] = fn(report_dir)
            except Exception as e:
                log.error(f"  Error en {name}: {e}")
                results[name] = {'error': str(e)}

        self._guardar_resumen(results, report_dir)
        log.info(f"Reportes guardados en: {report_dir}")
        return report_dir

    # ── Ventas por tiempo ─────────────────────────────────────────────────────

    def ventas_por_tiempo(self, out: Path) -> dict:
        df = self.db.execute_query("""
            SELECT t.año, t.mes, t.nombre_mes, t.trimestre,
                   COUNT(v.id_venta)                         AS num_ventas,
                   SUM(v.precio_venta)                       AS ingresos_totales,
                   AVG(v.precio_venta)                       AS ticket_promedio,
                   SUM(v.precio_venta - v.costo_vehiculo)    AS ganancia_total,
                   COUNT(DISTINCT v.id_cliente)              AS clientes_unicos
            FROM hecho_ventas v
            JOIN dim_tiempo t ON v.id_tiempo = t.id_tiempo
            GROUP BY t.año, t.mes, t.nombre_mes, t.trimestre
            ORDER BY t.año, t.mes
        """)
        if df.empty:
            return {'error': 'No hay datos de ventas'}

        df['periodo'] = df['año'].astype(str) + '-' + df['mes'].astype(str).str.zfill(2)

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        axes[0, 0].plot(range(len(df)), df['ingresos_totales'], marker='o')
        axes[0, 0].set_title('Ingresos Mensuales')
        axes[0, 0].set_xticks(range(len(df)))
        axes[0, 0].set_xticklabels(df['periodo'], rotation=45, ha='right')

        df_trim = df.groupby(['año', 'trimestre'])['ingresos_totales'].sum().reset_index()
        df_trim['periodo'] = df_trim['año'].astype(str) + '-T' + df_trim['trimestre'].astype(str)
        axes[0, 1].bar(range(len(df_trim)), df_trim['ingresos_totales'])
        axes[0, 1].set_xticks(range(len(df_trim)))
        axes[0, 1].set_xticklabels(df_trim['periodo'], rotation=45, ha='right')
        axes[0, 1].set_title('Ingresos por Trimestre')

        axes[1, 0].plot(range(len(df)), df['ticket_promedio'], marker='s', color='green')
        axes[1, 0].set_title('Ticket Promedio Mensual')
        axes[1, 0].set_xticks(range(len(df)))
        axes[1, 0].set_xticklabels(df['periodo'], rotation=45, ha='right')

        df_anual = df.groupby('año')['ingresos_totales'].sum().reset_index()
        axes[1, 1].bar(df_anual['año'].astype(str), df_anual['ingresos_totales'])
        axes[1, 1].set_title('Ingresos por Año')

        plt.tight_layout()
        plt.savefig(out / 'ventas_por_tiempo.png', dpi=100, bbox_inches='tight')
        plt.close()
        df.to_csv(out / 'ventas_por_tiempo.csv', index=False, encoding='utf-8-sig')

        total_v = df['num_ventas'].sum()
        return {
            'total_ingresos':        float(df['ingresos_totales'].sum()),
            'total_ventas':          int(total_v),
            'ticket_promedio_general': float(df['ingresos_totales'].sum() / total_v) if total_v else 0,
            'mes_max_ventas':        str(df.loc[df['ingresos_totales'].idxmax(), 'nombre_mes']),
        }

    # ── Top clientes ──────────────────────────────────────────────────────────

    def top_clientes(self, out: Path) -> dict:
        df = self.db.execute_query("""
            SELECT c.id_cliente,
                   c.nombre           AS nombre_cliente,
                   c.tipo_cliente,
                   COUNT(v.id_venta)          AS num_compras,
                   SUM(v.precio_venta)        AS total_gastado,
                   AVG(v.precio_venta)        AS ticket_promedio,
                   COUNT(DISTINCT v.id_vehiculo) AS vehiculos_comprados,
                   MAX(v.precio_venta)        AS compra_maxima
            FROM hecho_ventas v
            JOIN dim_cliente c ON v.id_cliente = c.id_cliente
            GROUP BY c.id_cliente, c.nombre, c.tipo_cliente
            ORDER BY total_gastado DESC
            LIMIT 20
        """)
        if df.empty:
            return {'error': 'No hay datos de clientes'}

        fig, ax = plt.subplots(figsize=(12, 7))
        y_pos = range(len(df))
        ax.barh(y_pos, df['total_gastado'])
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['nombre_cliente'], fontsize=8)
        ax.set_xlabel('Total Gastado ($)')
        ax.set_title('Top 20 Clientes por Gasto Total')
        ax.invert_yaxis()
        for i, (_, row) in enumerate(df.iterrows()):
            ax.text(row['total_gastado'], i, f'  ${row["total_gastado"]:,.0f}', va='center', fontsize=7)
        plt.tight_layout()
        plt.savefig(out / 'top_clientes.png', dpi=100, bbox_inches='tight')
        plt.close()
        df.to_csv(out / 'top_clientes.csv', index=False, encoding='utf-8-sig')

        return {
            'top_cliente':         str(df.iloc[0]['nombre_cliente']),
            'top_gasto':           float(df.iloc[0]['total_gastado']),
            'clientes_recurrentes': int(len(df[df['num_compras'] > 1])),
        }

    # ── Rendimiento vendedores ────────────────────────────────────────────────
    # FIX: la columna en DB se llama 'experiencia_años' (con tilde normalizada
    # a 'experiencia_anios' por SQLite en algunos casos) — detectamos dinámicamente.

    def rendimiento_vendedores(self, out: Path) -> dict:
        # Detectar nombre real de la columna de experiencia
        cols = self.db.table_columns('dim_vendedor')
        exp_col = next(
            (c for c in cols if 'experi' in c.lower()),
            None
        )
        exp_select = f"v.{exp_col}" if exp_col else "0"
        exp_label  = exp_col if exp_col else 'experiencia'

        # Detectar si existe comision_vendedor en hecho_ventas
        ventas_cols = self.db.table_columns('hecho_ventas')
        comision_select = (
            "SUM(hv.comision_vendedor)" if 'comision_vendedor' in ventas_cols else "0"
        ) + " AS comision_total"

        df = self.db.execute_query(f"""
            SELECT v.id_vendedor,
                   v.nombre          AS nombre_vendedor,
                   {exp_select}      AS experiencia,
                   s.nombre          AS sucursal,
                   COUNT(hv.id_venta)        AS ventas_realizadas,
                   SUM(hv.precio_venta)      AS ingresos_generados,
                   AVG(hv.precio_venta)      AS ticket_promedio,
                   {comision_select},
                   COUNT(DISTINCT hv.id_cliente) AS clientes_atendidos
            FROM hecho_ventas hv
            JOIN dim_vendedor  v ON hv.id_vendedor  = v.id_vendedor
            JOIN dim_sucursal  s ON hv.id_sucursal  = s.id_sucursal
            GROUP BY v.id_vendedor, v.nombre, {exp_select}, s.nombre
            ORDER BY ingresos_generados DESC
        """)
        if df.empty:
            return {'error': 'No hay datos de vendedores'}

        df['experiencia'] = pd.to_numeric(df['experiencia'], errors='coerce').fillna(0)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        top10 = df.head(10)
        y_pos = range(len(top10))
        axes[0].barh(y_pos, top10['ingresos_generados'])
        axes[0].set_yticks(y_pos)
        axes[0].set_yticklabels(top10['nombre_vendedor'], fontsize=8)
        axes[0].set_xlabel('Ingresos Generados ($)')
        axes[0].set_title('Top 10 Vendedores por Ingresos')
        axes[0].invert_yaxis()

        axes[1].scatter(df['experiencia'], df['ingresos_generados'], alpha=0.6)
        axes[1].set_xlabel('Años de Experiencia')
        axes[1].set_ylabel('Ingresos Generados ($)')
        axes[1].set_title('Experiencia vs Rendimiento')
        if len(df) > 1:
            z = np.polyfit(df['experiencia'], df['ingresos_generados'], 1)
            p = np.poly1d(z)
            xs = np.linspace(df['experiencia'].min(), df['experiencia'].max(), 50)
            axes[1].plot(xs, p(xs), 'r--', alpha=0.8)

        plt.tight_layout()
        plt.savefig(out / 'rendimiento_vendedores.png', dpi=100, bbox_inches='tight')
        plt.close()
        df.to_csv(out / 'rendimiento_vendedores.csv', index=False, encoding='utf-8-sig')

        corr = float(df['experiencia'].corr(df['ingresos_generados'])) if len(df) > 1 else 0
        return {
            'mejor_vendedor':           str(df.iloc[0]['nombre_vendedor']),
            'ingresos_mejor':           float(df.iloc[0]['ingresos_generados']),
            'promedio_ventas_vendedor': float(df['ventas_realizadas'].mean()),
            'correlacion_experiencia':  corr,
        }

    # ── Mantenimiento por tipo ────────────────────────────────────────────────
    # FIX: bug de indentación — el fallback query_simple ahora está correctamente
    # dentro del bloque if df.empty.

    def mantenimiento_por_tipo(self, out: Path) -> dict:
        # Detectar nombre de la tabla de tipos de mantenimiento
        tables = self.db.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )['name'].tolist()
        tipo_mant_table = next(
            (t for t in tables if 'tipo' in t.lower() and 'mant' in t.lower()),
            None
        )

        df = pd.DataFrame()

        if tipo_mant_table:
            # Detectar columna ID en hecho_mantenimiento
            hm_cols = self.db.table_columns('hecho_mantenimiento')
            id_col  = next(
                (c for c in hm_cols if 'id' in c.lower() and 'tipo' not in c.lower() and 'cliente' not in c.lower() and 'vehiculo' not in c.lower() and 'sucursal' not in c.lower() and 'tiempo' not in c.lower()),
                'rowid'
            )
            # Detectar columna nombre en la tabla de tipos
            tm_cols    = self.db.table_columns(tipo_mant_table)
            nombre_col = next((c for c in tm_cols if 'nombre' in c.lower()), tm_cols[1] if len(tm_cols) > 1 else 'nombre_tipo')
            desc_col   = next((c for c in tm_cols if 'desc' in c.lower()), None)
            desc_select = f"tm.{desc_col}" if desc_col else "'' AS descripcion"

            df = self.db.execute_query(f"""
                SELECT tm.{nombre_col}   AS tipo_mantenimiento,
                       {desc_select}     AS descripcion,
                       COUNT(m.{id_col}) AS num_servicios,
                       SUM(COALESCE(m.costo_servicio,  0) + COALESCE(m.costo_repuestos, 0)) AS ingresos_totales,
                       AVG(COALESCE(m.costo_servicio,  0) + COALESCE(m.costo_repuestos, 0)) AS costo_promedio,
                       AVG(m.horas_taller)             AS horas_promedio,
                       SUM(COALESCE(m.repuestos_usados,0))                                  AS total_repuestos,
                       AVG(m.kilometraje_vehiculo)     AS km_promedio
                FROM hecho_mantenimiento m
                JOIN {tipo_mant_table} tm ON m.id_tipo_mantenimiento = tm.id_tipo_mantenimiento
                GROUP BY tm.{nombre_col}
                ORDER BY num_servicios DESC
            """)

        # FIX: fallback correctamente indentado dentro del bloque if df.empty
        if df.empty:
            df = self.db.execute_query("""
                SELECT 'Todos'              AS tipo_mantenimiento,
                       'Servicios generales' AS descripcion,
                       COUNT(*)             AS num_servicios,
                       SUM(COALESCE(costo_servicio,  0) + COALESCE(costo_repuestos, 0)) AS ingresos_totales,
                       AVG(COALESCE(costo_servicio,  0) + COALESCE(costo_repuestos, 0)) AS costo_promedio,
                       AVG(horas_taller)    AS horas_promedio,
                       SUM(COALESCE(repuestos_usados, 0)) AS total_repuestos,
                       AVG(kilometraje_vehiculo)          AS km_promedio
                FROM hecho_mantenimiento
            """)

        if df.empty:
            return {'error': 'No hay datos de mantenimiento'}

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        axes[0].pie(df['num_servicios'], labels=df['tipo_mantenimiento'], autopct='%1.1f%%')
        axes[0].set_title('Distribución de Servicios por Tipo')

        x_pos = range(len(df))
        axes[1].bar(x_pos, df['costo_promedio'])
        axes[1].set_xticks(x_pos)
        axes[1].set_xticklabels(df['tipo_mantenimiento'], rotation=45, ha='right', fontsize=7)
        axes[1].set_title('Costo Promedio por Tipo de Mantenimiento')
        axes[1].set_ylabel('Costo Promedio ($)')

        plt.tight_layout()
        plt.savefig(out / 'mantenimiento_por_tipo.png', dpi=100, bbox_inches='tight')
        plt.close()
        df.to_csv(out / 'mantenimiento_por_tipo.csv', index=False, encoding='utf-8-sig')

        total_s = df['num_servicios'].sum()
        return {
            'servicio_mas_comun':    str(df.iloc[0]['tipo_mantenimiento']),
            'total_servicios':       int(total_s),
            'ingresos_mantenimiento': float(df['ingresos_totales'].sum()),
            'costo_promedio_general': float(df['ingresos_totales'].sum() / total_s) if total_s else 0,
        }

    # ── Análisis financiero ───────────────────────────────────────────────────

    def analisis_financiero(self, out: Path) -> dict:
        df = self.db.execute_query("""
            SELECT t.año, t.mes,
                   COUNT(v.id_venta)  AS ventas,
                   SUM(v.precio_venta)  AS ingresos,
                   SUM(v.costo_vehiculo) AS costos,
                   SUM(v.precio_venta - v.costo_vehiculo) AS margen,
                   AVG((v.precio_venta - v.costo_vehiculo) / NULLIF(v.precio_venta, 0) * 100) AS margen_porcentaje,
                   SUM(CASE WHEN v.financiado = 1 THEN v.precio_venta ELSE 0 END) AS ventas_financiadas,
                   COUNT(CASE WHEN v.financiado = 1 THEN 1 END) AS num_financiadas
            FROM hecho_ventas v
            JOIN dim_tiempo t ON v.id_tiempo = t.id_tiempo
            GROUP BY t.año, t.mes
            ORDER BY t.año, t.mes
        """)
        if df.empty:
            return {'error': 'No hay datos financieros'}

        df['periodo'] = df['año'].astype(str) + '-' + df['mes'].astype(str).str.zfill(2)
        df['tasa_financiacion'] = (df['ventas_financiadas'] / df['ingresos'].replace(0, np.nan) * 100).fillna(0)

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        x = range(len(df))
        xt = x if len(df) <= 10 else range(0, len(df), max(1, len(df)//10))

        axes[0, 0].plot(x, df['ingresos'], marker='o', label='Ingresos')
        axes[0, 0].plot(x, df['costos'],   marker='s', label='Costos')
        axes[0, 0].set_title('Ingresos vs Costos')
        axes[0, 0].legend()
        axes[0, 0].set_xticks(list(xt))
        axes[0, 0].set_xticklabels(df['periodo'].iloc[list(xt)], rotation=45, ha='right')

        axes[0, 1].bar(x, df['margen'])
        axes[0, 1].set_title('Margen de Ganancia Absoluto')
        axes[0, 1].set_xticks(list(xt))
        axes[0, 1].set_xticklabels(df['periodo'].iloc[list(xt)], rotation=45, ha='right')

        axes[1, 0].plot(x, df['margen_porcentaje'], marker='o', color='green')
        axes[1, 0].set_title('Margen de Ganancia (%)')
        axes[1, 0].set_xticks(list(xt))
        axes[1, 0].set_xticklabels(df['periodo'].iloc[list(xt)], rotation=45, ha='right')

        axes[1, 1].bar(x, df['tasa_financiacion'], color='purple')
        axes[1, 1].set_title('Tasa de Financiación (%)')
        axes[1, 1].set_xticks(list(xt))
        axes[1, 1].set_xticklabels(df['periodo'].iloc[list(xt)], rotation=45, ha='right')

        plt.tight_layout()
        plt.savefig(out / 'analisis_financiero.png', dpi=100, bbox_inches='tight')
        plt.close()
        df.to_csv(out / 'analisis_financiero.csv', index=False, encoding='utf-8-sig')

        return {
            'ingresos_totales':          float(df['ingresos'].sum()),
            'costos_totales':            float(df['costos'].sum()),
            'margen_total':              float(df['margen'].sum()),
            'margen_promedio':           float(df['margen_porcentaje'].mean()),
            'tasa_financiacion_promedio': float(df['tasa_financiacion'].mean()),
        }

    # ── Dashboard HTML ────────────────────────────────────────────────────────

    def dashboard_ventas(self, out: Path) -> dict:
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Concesionario</title>
    <style>
        body  {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header  {{ background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .container {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,.1); flex: 1 1 200px; text-align: center; }}
        .metric {{ font-size: 28px; font-weight: bold; color: #3498db; }}
        .chart-box {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,.08); }}
        img {{ max-width: 100%; height: auto; border-radius: 5px; }}
        footer {{ color: #7f8c8d; font-size: 12px; text-align: center; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Dashboard Concesionario — Modelo Estrella</h1>
        <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="container" id="kpis">
        <div class="card"><h3>Ventas</h3><div class="metric" id="kv">—</div><p>Transacciones</p></div>
        <div class="card"><h3>Ingresos</h3><div class="metric" id="ki">—</div><p>Total</p></div>
        <div class="card"><h3>Clientes</h3><div class="metric" id="kc">—</div><p>Únicos</p></div>
        <div class="card"><h3>Mantenimientos</h3><div class="metric" id="km">—</div><p>Servicios</p></div>
    </div>

    <div class="container" id="kpis-kpi">
        <h2 style="width:100%; margin-bottom: 12px;">Métricas de KPIs</h2>
        <div class="card"><h3>Rotación Inventario</h3><div class="metric" id="kr">—</div><p>% Unidades vendidas</p></div>
        <div class="card"><h3>Índice Retención</h3><div class="metric" id="kf">—</div><p>% Clientes recurrentes</p></div>
        <div class="card"><h3>Días en Inventario</h3><div class="metric" id="kd">—</div><p>Promedio</p></div>
        <div class="card"><h3>Margen Promedio Venta</h3><div class="metric" id="kt">—</div><p>Margen promedio</p></div>
    </div>

    <div class="chart-box"><h2>Ventas por Tiempo</h2><img src="ventas_por_tiempo.png"></div>
    <div class="chart-box"><h2>Análisis Financiero</h2><img src="analisis_financiero.png"></div>
    <div class="chart-box"><h2>Top Clientes</h2><img src="top_clientes.png"></div>
    <div class="chart-box"><h2>Mantenimiento por Tipo</h2><img src="mantenimiento_por_tipo.png"></div>
    <div class="chart-box"><h2>Rendimiento de Vendedores</h2><img src="rendimiento_vendedores.png"></div>

    <div class="chart-box"><h2>KPIs Trimestrales</h2>
        <div style="display:flex; flex-wrap: wrap; gap: 20px; justify-content: center;">
            <div style="flex:1 1 45%; max-width: 800px;"><img src="kpi_rotacion_quarterly.png"></div>
            <div style="flex:1 1 45%; max-width: 800px;"><img src="kpi_retencion_quarterly.png"></div>
            <div style="flex:1 1 45%; max-width: 800px;"><img src="kpi_margen_promedio_quarterly.png"></div>
            <div style="flex:1 1 45%; max-width: 800px;"><img src="kpi_dias_inventario_quarterly.png"></div>
        </div>
    </div>

    <footer>Dashboard generado automáticamente por el sistema ETL</footer>

    <script>
        fetch('resumen.json').then(r => r.json()).then(d => {{
            document.getElementById('kv').textContent = (d.total_ventas  || 0).toLocaleString();
            document.getElementById('ki').textContent = '$' + ((d.ingresos_totales || 0)).toLocaleString(undefined, {{maximumFractionDigits:0}});
            document.getElementById('kc').textContent = (d.total_clientes || 0).toLocaleString();
            document.getElementById('km').textContent = (d.total_mantenimientos || 0).toLocaleString();

            // KPIs secundarios
            document.getElementById('kr').textContent = d.rotacion_inventario_pct != null
                ? `${{d.rotacion_inventario_pct.toFixed(1)}}%`
                : 'N/A';
            document.getElementById('kf').textContent = d.indice_retencion_clientes_pct != null
                ? `${{d.indice_retencion_clientes_pct.toFixed(1)}}%`
                : 'N/A';
            document.getElementById('kd').textContent = d.dias_promedio_inventario != null
                ? d.dias_promedio_inventario.toFixed(1)
                : 'N/A';
            document.getElementById('kt').textContent = d.margen_promedio_venta != null
                ? d.margen_promedio_venta.toFixed(2)
                : 'N/A';
        }}).catch(() => {{}});
    </script>
</body>
</html>"""
        (out / 'dashboard.html').write_text(html, encoding='utf-8')
        return {'dashboard': str(out / 'dashboard.html')}

    # ── Calidad de datos ──────────────────────────────────────────────────────

    def reporte_calidad_datos(self, out: Path) -> dict:
        stats: dict = {'tablas': {}, 'calidad': {}}

        for table in ['hecho_ventas', 'hecho_mantenimiento', 'dim_cliente', 'dim_vehiculo']:
            try:
                n = self.db.execute_query(f"SELECT COUNT(*) AS n FROM {table}").iloc[0, 0]
                stats['tablas'][table] = int(n)
            except Exception:
                stats['tablas'][table] = 0

        # Nulos en columnas clave
        for table, col in [('hecho_ventas', 'id_cliente'),
                            ('hecho_mantenimiento', 'id_cliente')]:
            try:
                n = self.db.execute_query(
                    f"SELECT COUNT(*) AS n FROM {table} WHERE {col} IS NULL"
                ).iloc[0, 0]
                stats['calidad'][f'nulos_{table}_{col}'] = int(n)
            except Exception:
                stats['calidad'][f'nulos_{table}_{col}'] = 0

        # Duplicados en ventas
        try:
            d = self.db.execute_query(
                "SELECT COUNT(*) - COUNT(DISTINCT id_venta) AS n FROM hecho_ventas"
            ).iloc[0, 0]
            stats['calidad']['duplicados_ventas'] = int(d)
        except Exception:
            stats['calidad']['duplicados_ventas'] = 0

        # Relaciones rotas
        try:
            r = self.db.execute_query("""
                SELECT COUNT(*) AS n FROM hecho_ventas
                WHERE id_cliente NOT IN (
                    SELECT id_cliente FROM dim_cliente WHERE id_cliente IS NOT NULL
                )
            """).iloc[0, 0]
            stats['calidad']['relaciones_rotas_ventas'] = int(r)
        except Exception:
            stats['calidad']['relaciones_rotas_ventas'] = 0

        (out / 'calidad_datos.json').write_text(
            json.dumps(stats, indent=2, default=str), encoding='utf-8'
        )
        return stats

    # ── Resumen general ───────────────────────────────────────────────────────

    def _guardar_resumen(self, results: dict, out: Path):
        try:
            row = self.db.execute_query("""
                SELECT
                    (SELECT COUNT(*)         FROM hecho_ventas)        AS total_ventas,
                    (SELECT COUNT(*)         FROM hecho_mantenimiento) AS total_mantenimientos,
                    (SELECT COUNT(*)         FROM dim_cliente)         AS total_clientes,
                    (SELECT COUNT(*)         FROM dim_vehiculo)        AS total_vehiculos,
                    (SELECT SUM(precio_venta) FROM hecho_ventas)       AS ingresos_totales,
                    (SELECT AVG(precio_venta) FROM hecho_ventas)       AS ticket_promedio
            """).iloc[0]
            resumen = {k: (0 if pd.isna(v) else (int(v) if isinstance(v, (np.integer, int)) else float(v)))
                       for k, v in row.items()}
        except Exception as e:
            log.warning(f"Error métricas generales: {e}")
            resumen = {}

        # Calcular KPIs usando el módulo dedicado
        kpi_calc = KPICalculator(self.db.db_path)
        kpi_results = kpi_calc.calculate_all_kpis()
        resumen.update(kpi_results)

        resumen['fecha_generacion'] = datetime.now().isoformat()
        resumen['reportes'] = {k: v for k, v in results.items() if 'error' not in str(v)}

        # ── Gráficas de KPIs trimestrales ──────────
        def _save_kpi_time_series(fname: str, title: str, labels: list, values: list, ylabel: str, fmt: str = '{:.1f}'):
            try:
                fig, ax = plt.subplots(figsize=(12, 8))
                ax.bar(labels, values, color="tomato")
                ax.set_title(title, fontsize=15)
                ax.set_ylabel(ylabel)
                ax.set_xlabel('Período (Trimestre)')
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=11)
                for i, v in enumerate(values):
                    if not pd.isna(v):
                        ax.text(i, v, fmt.format(v), ha='center', va='bottom', fontsize=10)
                fig.tight_layout()
                fig.savefig(out / f'{fname}.png', dpi=120, bbox_inches='tight')
                plt.close(fig)
            except Exception:
                pass

        q_data = resumen.get('kpi_quarterly', []) or []
        labels = [str(x.get('periodo', '')) for x in q_data]
        rot_vals = [x.get('rotacion_pct', 0) for x in q_data]
        ret_vals = [x.get('retencion_pct', 0) for x in q_data]
        fin_vals = [x.get('margen_promedio_pct', 0) for x in q_data]
        dias_vals = [x.get('dias_inventario', 0) for x in q_data]

        _save_kpi_time_series('kpi_rotacion_quarterly', 'Rotación de Inventario (trimestral)', labels, rot_vals, '%', '{:.1f}%')
        _save_kpi_time_series('kpi_retencion_quarterly', 'Índice de Retención (trimestral)', labels, ret_vals, '%', '{:.1f}%')
        _save_kpi_time_series('kpi_margen_promedio_quarterly', 'Margen Promedio (trimestral)', labels, fin_vals, '', '{:.2f}')
        _save_kpi_time_series('kpi_dias_inventario_quarterly', 'Días medio en inventario (trimestral)', labels, dias_vals, 'días', '{:.1f}')

        # Sanitizar valores no JSON (NaN, inf, -inf) para que el dashboard JS pueda parsear
        def _safe_val(x):
            try:
                if isinstance(x, float) and (pd.isna(x) or x != x or x in (float('inf'), float('-inf'))):
                    return None
            except Exception:
                pass
            if isinstance(x, dict):
                return {k: _safe_val(v) for k, v in x.items()}
            if isinstance(x, list):
                return [_safe_val(v) for v in x]
            return x

        resumen_safe = _safe_val(resumen)
        (out / 'resumen.json').write_text(
            json.dumps(resumen_safe, indent=2, default=str), encoding='utf-8'
        )

        with open(out / 'resumen.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("RESUMEN DE REPORTES - CONCESIONARIO\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"  * Ventas totales   : {resumen.get('total_ventas', 0):,}\n")
            f.write(f"  * Mantenimientos   : {resumen.get('total_mantenimientos', 0):,}\n")
            f.write(f"  * Clientes unicos  : {resumen.get('total_clientes', 0):,}\n")
            f.write(f"  * Vehiculos        : {resumen.get('total_vehiculos', 0):,}\n")
            f.write(f"  * Ingresos totales : ${resumen.get('ingresos_totales', 0):,.2f}\n")
            f.write(f"  * Ticket promedio  : ${resumen.get('ticket_promedio', 0):,.2f}\n")
            f.write("=" * 60 + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Genera reportes del concesionario')
    parser.add_argument('--db', default='data/processed/concesionario.db',
                        help='Ruta al archivo SQLite')
    args = parser.parse_args()

    gen = ReportGenerator(db_path=args.db)
    report_dir = gen.generate_all_reports()
    print(f"\nReportes generados en: {report_dir}")
    print(f"Abre: {report_dir}/dashboard.html")


if __name__ == '__main__':
    main()