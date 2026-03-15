
import logging
from typing import Dict, List
import pandas as pd
import sqlite3

log = logging.getLogger(__name__)


class KPICalculator:
    """Calcula KPIs clave para el concesionario siguiendo principios SOLID."""

    def __init__(self, db_path: str = 'data/processed/concesionario.db'):
        self.db_path = db_path

    def _execute_query(self, query: str, params=None) -> pd.DataFrame:
        """Ejecuta una consulta SQL y retorna un DataFrame."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            log.error(f"Error ejecutando query: {e}")
            return pd.DataFrame()

    def _get_scalar_value(self, query: str, default: float = 0.0) -> float:
        """Ejecuta una consulta que retorna un valor escalar."""
        df = self._execute_query(query)
        if df.empty:
            return default
        try:
            value = df.iloc[0, 0]
            return float(value) if pd.notna(value) else default
        except (IndexError, ValueError):
            return default

    def calculate_rotacion_inventario(self) -> float:
        """Calcula la rotación de inventario (% unidades vendidas vs total vehículos).

        Fórmula: Rotación de inventario (%) = (Total unidades vendidas / Total vehículos) * 100
        """
        log.info("Calculando KPI: Rotación de inventario")
        total_unidades = self._get_scalar_value(
            "SELECT SUM(COALESCE(cantidad, 1)) AS total_unidades FROM hecho_ventas"
        )

        total_vehiculos = self._get_scalar_value(
            "SELECT COUNT(*) AS total FROM dim_vehiculo"
        )

        return float(total_unidades) / total_vehiculos * 100 if total_vehiculos else 0.0

    def calculate_indice_retencion_clientes(self) -> float:
        """Calcula el índice de retención de clientes (% clientes recurrentes).

        Fórmula: Índice de retención (%) = (Clientes con más de una compra / Total clientes únicos) * 100
        """
        log.info("Calculando KPI: Índice de retención de clientes")
        # Clientes con más de una venta
        clientes_recurrentes = self._get_scalar_value("""
            SELECT COUNT(*) FROM (
                SELECT id_cliente, COUNT(*) as num_compras
                FROM hecho_ventas
                WHERE id_cliente IS NOT NULL
                GROUP BY id_cliente
                HAVING COUNT(*) > 1
            )
        """)

        # Total de clientes únicos
        total_clientes = self._get_scalar_value(
            "SELECT COUNT(DISTINCT id_cliente) FROM hecho_ventas WHERE id_cliente IS NOT NULL"
        )

        return float(clientes_recurrentes) / total_clientes * 100 if total_clientes else 0.0

    def calculate_dias_promedio_inventario(self) -> float:
        """Calcula los días promedio en inventario.

        Fórmula: Días promedio en inventario = Promedio de diferencias de días entre ventas consecutivas por vehículo.
        """
        log.info("Calculando KPI: Días promedio en inventario")
        df_dates = self._execute_query("""
            SELECT hv.id_vehiculo, t.fecha_completa
            FROM hecho_ventas hv
            JOIN dim_tiempo t ON hv.id_tiempo = t.id_tiempo
            WHERE t.fecha_completa IS NOT NULL
            ORDER BY hv.id_vehiculo, t.fecha_completa
        """)

        if df_dates.empty:
            return 0.0

        df_dates['fecha_completa'] = pd.to_datetime(df_dates['fecha_completa'], errors='coerce')
        df_dates = df_dates.dropna(subset=['fecha_completa'])
        df_dates = df_dates.sort_values(['id_vehiculo', 'fecha_completa'])
        df_dates['diff_days'] = df_dates.groupby('id_vehiculo')['fecha_completa'].diff().dt.days
        df_dates = df_dates.dropna(subset=['diff_days'])

        diffs = df_dates['diff_days'].tolist()
        return float(pd.Series(diffs).mean()) if diffs else 0.0

    def calculate_margen_promedio_venta(self) -> float:
        """Calcula el margen promedio por venta.

        Fórmula: Margen promedio por venta = AVG(margen_ganancia) de hecho_ventas.
        """
        log.info("Calculando KPI: Margen promedio por venta")
        margen_promedio = self._get_scalar_value(
            "SELECT AVG(COALESCE(margen_ganancia, 0)) FROM hecho_ventas"
        )
        return float(margen_promedio) if margen_promedio else 0.0

    def calculate_kpi_quarterly(self) -> List[Dict]:
        """Calcula KPIs para gráficos.

        Fórmulas trimestrales:
        - Rotación de inventario (%): (Unidades vendidas en trimestre / Total vehículos) * 100
        - Retención de clientes (%): % de clientes del trimestre actual que ya habían comprado en trimestres anteriores
        - Margen promedio (%): AVG(margen_ganancia) por trimestre
        - Días en inventario: Promedio de días entre ventas consecutivas por vehículo en el trimestre
        """
        df_quarter = self._execute_query("""
            SELECT t.año AS year, t.trimestre AS quarter,
                   SUM(COALESCE(hv.cantidad, 1)) AS unidades,
                   AVG(COALESCE(hv.precio_venta, 0)) AS precio_promedio,
                   AVG(COALESCE(hv.margen_ganancia, 0)) AS margen_promedio
            FROM hecho_ventas hv
            JOIN dim_tiempo t ON hv.id_tiempo = t.id_tiempo
            GROUP BY t.año, t.trimestre
            ORDER BY t.año, t.trimestre
        """)

        if df_quarter.empty:
            return []

        total_vehiculos = self._get_scalar_value(
            "SELECT COUNT(*) AS total FROM dim_vehiculo"
        )

        df_quarter['periodo'] = df_quarter['year'].astype(str) + '-T' + df_quarter['quarter'].astype(str)
        df_quarter['rotacion_pct'] = (
            df_quarter['unidades'] / total_vehiculos * 100 if total_vehiculos else 0
        )

        # Valores globales para usar como fallback si no hay datos trimestrales
        global_retencion = self.calculate_indice_retencion_clientes()
        global_margen = self.calculate_margen_promedio_venta()

        # Cálculos trimestrales adicionales: retención y margen
        df_sales = self._execute_query("""
            SELECT hv.id_cliente, hv.id_tipo_pago AS id_tipo_pago, hv.margen_ganancia, t.año AS year, t.trimestre AS quarter
            FROM hecho_ventas hv
            JOIN dim_tiempo t ON hv.id_tiempo = t.id_tiempo
            WHERE hv.id_cliente IS NOT NULL
        """)

        if not df_sales.empty:
            # Retención de clientes: porcentaje de clientes del trimestre previo que vuelven a comprar
            df_customers = (
                df_sales.groupby(['year', 'quarter'])['id_cliente']
                .apply(lambda ids: set(ids.dropna().astype(int)))
                .reset_index(name='clientes')
                .sort_values(['year', 'quarter'])
            )

            retention_rows = []
            prev_customers = set()
            for _, row in df_customers.iterrows():
                current_customers = row['clientes'] or set()
                if prev_customers:
                    # Retención = % de clientes del trimestre actual que ya habían comprado en cualquier trimestre anterior
                    retained = len(prev_customers & current_customers)
                    retention_pct = (retained / len(current_customers) * 100) if current_customers else 0.0
                else:
                    retention_pct = 0.0
                retention_rows.append((row['year'], row['quarter'], retention_pct))
                prev_customers |= current_customers

            retention = pd.DataFrame(retention_rows, columns=['year', 'quarter', 'retencion_pct'])
            df_quarter = df_quarter.merge(retention, on=['year', 'quarter'], how='left')

            # Margen promedio por trimestre: AVG(margen_ganancia) por trimestre
            margen_trim = (
                df_sales.groupby(['year', 'quarter'])['margen_ganancia']
                .mean()
                .reset_index(name='margen_promedio_pct')
            )
            df_quarter = df_quarter.merge(margen_trim, on=['year', 'quarter'], how='left')

        # Completar valores faltantes por trimestre con métricas globales
        if 'retencion_pct' not in df_quarter.columns:
            df_quarter['retencion_pct'] = global_retencion
        else:
            # Si todos los valores son 0 (falta de datos), usar la media global
            if df_quarter['retencion_pct'].sum() == 0:
                df_quarter['retencion_pct'] = global_retencion
            else:
                df_quarter['retencion_pct'] = df_quarter['retencion_pct'].fillna(global_retencion)

        if 'margen_promedio_pct' not in df_quarter.columns:
            df_quarter['margen_promedio_pct'] = global_margen
        else:
            # Si todos los valores son 0 (falta de datos), usar la métrica global
            if df_quarter['margen_promedio_pct'].sum() == 0:
                df_quarter['margen_promedio_pct'] = global_margen
            else:
                df_quarter['margen_promedio_pct'] = df_quarter['margen_promedio_pct'].fillna(global_margen)

        # Días en inventario: Promedio de días entre ventas consecutivas por vehículo en el trimestre
        df_dates = self._execute_query("""
            SELECT t.año AS year, t.trimestre AS quarter, hv.id_vehiculo, t.fecha_completa
            FROM hecho_ventas hv
            JOIN dim_tiempo t ON hv.id_tiempo = t.id_tiempo
            WHERE t.fecha_completa IS NOT NULL
            ORDER BY hv.id_vehiculo, t.fecha_completa
        """)

        if not df_dates.empty:
            df_dates['fecha_completa'] = pd.to_datetime(df_dates['fecha_completa'], errors='coerce')
            df_dates = df_dates.dropna(subset=['fecha_completa'])
            df_dates = df_dates.sort_values(['id_vehiculo', 'fecha_completa'])
            df_dates['diff_days'] = df_dates.groupby('id_vehiculo')['fecha_completa'].diff().dt.days
            df_dates = df_dates.dropna(subset=['diff_days'])
            q_avg = df_dates.groupby(['year', 'quarter'])['diff_days'].mean().reset_index()
            df_quarter = df_quarter.merge(q_avg, on=['year', 'quarter'], how='left', suffixes=('', '_y'))
            df_quarter = df_quarter.loc[:, ~df_quarter.columns.duplicated()]
            if 'diff_days' in df_quarter.columns:
                df_quarter = df_quarter.rename(columns={'diff_days': 'dias_inventario'})

        cols = ['periodo', 'rotacion_pct', 'retencion_pct', 'margen_promedio_pct', 'costo_error', 'dias_inventario']
        return df_quarter.reindex(columns=cols).fillna(0).to_dict(orient='records')

    def calculate_all_kpis(self) -> Dict:
        """Calcula todos los KPIs principales."""
        log.info("Iniciando cálculo de todos los KPIs")
        kpis = {
            'rotacion_inventario_pct': self.calculate_rotacion_inventario(),
            'indice_retencion_clientes_pct': self.calculate_indice_retencion_clientes(),
            'dias_promedio_inventario': self.calculate_dias_promedio_inventario(),
            'margen_promedio_venta': self.calculate_margen_promedio_venta(),
            'kpi_quarterly': self.calculate_kpi_quarterly(),
        }
        log.info("Cálculo de KPIs completado")
        return kpis