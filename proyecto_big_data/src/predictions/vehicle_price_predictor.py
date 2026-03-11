"""
predictions.py  —  Predicciones de precios, ventas futuras y segmentación RFM.

Uso:
    python predictions.py
    python predictions.py --db data/processed/concesionario.db --months 6
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sqlite3

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

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
# DATABASE MANAGER (autocontenido)
# ──────────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    def __init__(self, db_path: str = 'data/processed/concesionario.db'):
        self.db_path = db_path

    def execute_query(self, query: str, params=None) -> pd.DataFrame:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            log.error(f"Query error: {e}")
            return pd.DataFrame()

    def table_columns(self, table: str) -> list:
        df = self.execute_query(f"PRAGMA table_info({table})")
        return df['name'].tolist() if not df.empty else []


# ──────────────────────────────────────────────────────────────────────────────
# VEHICLE PRICE PREDICTOR
# ──────────────────────────────────────────────────────────────────────────────

class VehiclePricePredictor:
    """Entrena y utiliza modelos ML para predecir el precio de venta de vehículos."""

    def __init__(self, db_path: str = 'data/processed/concesionario.db'):
        self.db = DatabaseManager(db_path)
        self.models: dict = {}
        self.scaler = StandardScaler()
        self.label_encoders: dict = {}
        self.feature_cols: list = []
        self.model_dir = Path('models')
        self.model_dir.mkdir(parents=True, exist_ok=True)

    # ── Preparación de datos ──────────────────────────────────────────────────

    def _detect_sucursal_cols(self) -> tuple:
        """Detecta los nombres reales de las columnas de dim_sucursal."""
        cols = self.db.table_columns('dim_sucursal')
        tam = next((c for c in cols if 'tama' in c.lower() or 'tam' in c.lower()), None)
        zona = next((c for c in cols if 'zona' in c.lower()), None)
        return tam, zona

    def prepare_data(self):
        tam_col, zona_col = self._detect_sucursal_cols()
        tam_select  = f"s.{tam_col} AS tamano_sucursal" if tam_col  else "'desconocido' AS tamano_sucursal"
        zona_select = f"s.{zona_col} AS zona_sucursal"  if zona_col else "'desconocido' AS zona_sucursal"

        # Detectar columna año del vehículo (puede ser 'año_modelo' o 'ano_modelo')
        veh_cols = self.db.table_columns('dim_vehiculo')
        anio_col = next((c for c in veh_cols if 'a' in c.lower() and 'o' in c.lower() and 'mod' in c.lower()), 'año_modelo')

        df = self.db.execute_query(f"""
            SELECT
                v.id_vehiculo,
                v.marca,
                v.modelo,
                v.tipo,
                v.{anio_col}           AS anio_modelo,
                v.cilindraje,
                v.tipo_combustible,
                v.color,
                hv.precio_venta        AS precio_real,
                hv.costo_vehiculo,
                COALESCE(hv.descuento, 0) AS descuento,
                COALESCE(hv.financiado, 0) AS financiado,
                t.año                  AS anio_venta,
                t.mes                  AS mes_venta,
                c.edad                 AS edad_cliente,
                c.genero               AS genero_cliente,
                c.tipo_cliente,
                {tam_select},
                {zona_select}
            FROM hecho_ventas hv
            JOIN dim_vehiculo v ON hv.id_vehiculo = v.id_vehiculo
            JOIN dim_tiempo   t ON hv.id_tiempo   = t.id_tiempo
            JOIN dim_cliente  c ON hv.id_cliente  = c.id_cliente
            JOIN dim_sucursal s ON hv.id_sucursal  = s.id_sucursal
            WHERE hv.precio_venta IS NOT NULL
              AND hv.precio_venta > 0
        """)

        if df.empty:
            log.error("No hay datos para entrenar el modelo")
            return None, None

        X = df.drop(columns=['precio_real', 'id_vehiculo'], errors='ignore')
        y = df['precio_real']
        self.feature_cols = X.columns.tolist()
        return X, y

    # ── Preprocesamiento ──────────────────────────────────────────────────────

    def _preprocess(self, X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        Xp = X.copy()
        num_cols = Xp.select_dtypes(include=np.number).columns.tolist()
        cat_cols = Xp.select_dtypes(include='object').columns.tolist()

        # Nulos numéricos
        for c in num_cols:
            Xp[c] = Xp[c].fillna(Xp[c].median() if fit else 0)

        # Nulos categóricos + encoding
        for c in cat_cols:
            Xp[c] = Xp[c].fillna('desconocido').astype(str)
            if fit:
                le = LabelEncoder()
                vals = Xp[c].tolist()
                if 'desconocido' not in vals:
                    vals.append('desconocido')
                le.fit(vals)
                self.label_encoders[c] = le
                Xp[c] = le.transform(Xp[c])
            else:
                if c in self.label_encoders:
                    le = self.label_encoders[c]
                    known = set(le.classes_)
                    Xp[c] = Xp[c].apply(
                        lambda x: le.transform([x])[0] if x in known
                        else (le.transform(['desconocido'])[0] if 'desconocido' in known else 0)
                    )

        # Escalar
        if fit:
            Xp[num_cols] = self.scaler.fit_transform(Xp[num_cols])
        else:
            Xp[num_cols] = self.scaler.transform(Xp[num_cols])

        return Xp

    # ── Entrenamiento ─────────────────────────────────────────────────────────

    def train_models(self) -> dict:
        X, y = self.prepare_data()
        if X is None:
            return {}

        Xp = self._preprocess(X, fit=True)
        X_train, X_test, y_train, y_test = train_test_split(Xp, y, test_size=0.2, random_state=42)

        candidates = {
            'linear_regression':  LinearRegression(),
            'random_forest':      RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            'gradient_boosting':  GradientBoostingRegressor(n_estimators=100, random_state=42),
        }

        results = {}
        best_name, best_cv, best_model = None, -np.inf, None

        for name, mdl in candidates.items():
            mdl.fit(X_train, y_train)
            yp = mdl.predict(X_test)
            mae  = mean_absolute_error(y_test, yp)
            rmse = np.sqrt(mean_squared_error(y_test, yp))
            r2   = r2_score(y_test, yp)
            cv   = cross_val_score(mdl, Xp, y, cv=5, scoring='r2')

            log.info(f"\n Modelo: {name}")
            log.info(f"  MAE: ${mae:,.2f}")
            log.info(f"  RMSE: ${rmse:,.2f}")
            log.info(f"  R²: {r2:.4f}")
            log.info(f"  CV R²: {cv.mean():.4f} (+/- {cv.std()*2:.4f})")

            results[name] = dict(mae=float(mae), rmse=float(rmse), r2=float(r2),
                                 cv_mean=float(cv.mean()), cv_std=float(cv.std()))
            self.models[name] = mdl

            if cv.mean() > best_cv:
                best_cv, best_name, best_model = cv.mean(), name, mdl

        if best_model:
            self._save_model(best_model, results)
            # Importancia de características (Random Forest)
            rf = candidates.get('random_forest')
            if rf and hasattr(rf, 'feature_importances_'):
                self._plot_feature_importance(rf, X.columns.tolist())

        log.info(f"\n✅ Modelo guardado en: {self.model_dir}")
        return results

    # ── Predicción de precio ──────────────────────────────────────────────────

    def predict_price(self, features: dict) -> float:
        if not self.models:
            if not self._load_model():
                return 50_000.0

        mdl = self.models.get('random_forest') or next(iter(self.models.values()))

        # Asegurar que el dataframe tiene las mismas columnas que en entrenamiento
        row = {c: features.get(c, np.nan) for c in self.feature_cols}
        Xp = self._preprocess(pd.DataFrame([row]), fit=False)
        try:
            pred = float(mdl.predict(Xp)[0])
            return float(np.clip(pred, 10_000, 200_000))
        except Exception as e:
            log.error(f"Error predicción: {e}")
            return 50_000.0

    # ── Predicción de ventas futuras ──────────────────────────────────────────

    def predict_future_sales(self, months_ahead: int = 6) -> dict:
        df = self.db.execute_query("""
            SELECT t.fecha_completa,
                   COUNT(v.id_venta)  AS ventas,
                   SUM(v.precio_venta) AS ingresos
            FROM hecho_ventas v
            JOIN dim_tiempo t ON v.id_tiempo = t.id_tiempo
            GROUP BY t.fecha_completa
            ORDER BY t.fecha_completa
        """)

        if df.empty or len(df) < 10:
            return {'error': 'Datos insuficientes para predicción'}

        df['fecha'] = pd.to_datetime(df['fecha_completa'])
        df = df.set_index('fecha')

        # Resample mensual (compatible con pandas >= 2.2 y anteriores)
        for freq in ('ME', 'M'):
            try:
                df_m = df.resample(freq).sum().reset_index()
                break
            except Exception:
                df_m = None
        if df_m is None or df_m.empty:
            return {'error': 'No se pudo agregar datos mensuales'}

        # Promedios de últimos 3 meses
        last_v = df_m['ventas'].iloc[-3:].mean()
        last_i = df_m['ingresos'].iloc[-3:].mean()
        growth = 0.02   # 2% mensual asumido

        predictions = [
            {
                'mes': i,
                'ventas_predichas':  int(last_v * (1 + growth) ** i),
                'ingresos_predichos': float(last_i * (1 + growth) ** i),
            }
            for i in range(1, months_ahead + 1)
        ]

        # Gráfico
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df_m['fecha'], df_m['ventas'], marker='o', label='Histórico')
        last_date = df_m['fecha'].iloc[-1]
        pred_dates = [last_date + pd.DateOffset(months=i) for i in range(1, months_ahead + 1)]
        pred_vals  = [p['ventas_predichas'] for p in predictions]
        ax.plot(pred_dates, pred_vals, 'r--', marker='s', label='Predicción')
        ax.set_title('Predicción de Ventas')
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Ventas')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(self.model_dir / 'sales_prediction.png', dpi=100, bbox_inches='tight')
        plt.close()

        return {
            'predictions':             predictions,
            'total_predicted_sales':   int(sum(p['ventas_predichas']  for p in predictions)),
            'total_predicted_revenue': float(sum(p['ingresos_predichos'] for p in predictions)),
        }

    # ── Persistencia ─────────────────────────────────────────────────────────

    def _save_model(self, model, results: dict):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        joblib.dump(model, self.model_dir / f'vehicle_price_model_{ts}.pkl')
        joblib.dump({'scaler': self.scaler, 'label_encoders': self.label_encoders,
                     'feature_cols': self.feature_cols},
                    self.model_dir / f'preprocessors_{ts}.pkl')
        # Guardar como "current" para carga rápida
        joblib.dump(model, self.model_dir / 'vehicle_price_model_current.pkl')
        joblib.dump({'scaler': self.scaler, 'label_encoders': self.label_encoders,
                     'feature_cols': self.feature_cols},
                    self.model_dir / 'preprocessors_current.pkl')
        # Resultados JSON
        clean = {k: {kk: vv for kk, vv in v.items()} for k, v in results.items()}
        (self.model_dir / f'model_results_{ts}.json').write_text(
            json.dumps(clean, indent=2), encoding='utf-8'
        )

    def _load_model(self) -> bool:
        mp = self.model_dir / 'vehicle_price_model_current.pkl'
        pp = self.model_dir / 'preprocessors_current.pkl'
        if mp.exists():
            self.models['loaded'] = joblib.load(mp)
            if pp.exists():
                pre = joblib.load(pp)
                self.scaler          = pre['scaler']
                self.label_encoders  = pre['label_encoders']
                self.feature_cols    = pre.get('feature_cols', [])
            return True
        return False

    def _plot_feature_importance(self, model, feature_names: list):
        imp = model.feature_importances_
        idx = np.argsort(imp)[::-1]
        plt.figure(figsize=(12, 5))
        plt.title('Importancia de Características')
        plt.bar(range(len(imp)), imp[idx])
        plt.xticks(range(len(imp)), [feature_names[i] for i in idx], rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(self.model_dir / 'feature_importance.png', dpi=100, bbox_inches='tight')
        plt.close()


# ──────────────────────────────────────────────────────────────────────────────
# CUSTOMER SEGMENTATION (RFM)
# ──────────────────────────────────────────────────────────────────────────────

class CustomerSegmentation:
    """Segmentación RFM de clientes."""

    def __init__(self, db_path: str = 'data/processed/concesionario.db'):
        self.db = DatabaseManager(db_path)
        self.model_dir = Path('models')
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def calculate_rfm(self) -> pd.DataFrame:
        df = self.db.execute_query("""
            SELECT c.id_cliente, c.nombre, c.tipo_cliente, c.edad, c.genero,
                   MAX(t.fecha_completa)            AS ultima_compra,
                   COUNT(v.id_venta)                AS frecuencia,
                   SUM(COALESCE(v.precio_venta, 0)) AS valor_monetario,
                   AVG(v.precio_venta)              AS ticket_promedio,
                   COUNT(DISTINCT v.id_vehiculo)    AS vehiculos_comprados
            FROM dim_cliente c
            LEFT JOIN hecho_ventas v ON c.id_cliente = v.id_cliente
            LEFT JOIN dim_tiempo   t ON v.id_tiempo  = t.id_tiempo
            GROUP BY c.id_cliente, c.nombre, c.tipo_cliente, c.edad, c.genero
        """)
        if df.empty:
            return df

        now = pd.Timestamp.now()
        df['ultima_compra']   = pd.to_datetime(df['ultima_compra'], errors='coerce')
        df['recency']         = (now - df['ultima_compra']).dt.days.fillna(999)
        df['frecuencia']      = df['frecuencia'].fillna(0)
        df['valor_monetario'] = df['valor_monetario'].fillna(0)

        def _qcut_safe(series, labels):
            try:
                return pd.qcut(series.rank(method='first'), q=5, labels=labels)
            except Exception:
                cuts = series.quantile([0, .2, .4, .6, .8, 1.0]).unique()
                if len(cuts) < 2:
                    return pd.Series(labels[0], index=series.index)
                return pd.cut(series, bins=cuts, labels=labels[:len(cuts)-1], include_lowest=True)

        df['r_score'] = pd.to_numeric(_qcut_safe(df['recency'],         [5, 4, 3, 2, 1]))
        df['f_score'] = pd.to_numeric(_qcut_safe(df['frecuencia'],      [1, 2, 3, 4, 5]))
        df['m_score'] = pd.to_numeric(_qcut_safe(df['valor_monetario'], [1, 2, 3, 4, 5]))
        df['rfm_score'] = df[['r_score', 'f_score', 'm_score']].sum(axis=1)

        def _segmentar(score):
            if score >= 13: return 'Campeones'
            if score >= 10: return 'Leales'
            if score >= 7:  return 'Prometedores'
            if score >= 4:  return 'Potenciales'
            return 'En riesgo'

        df['segmento'] = df['rfm_score'].apply(_segmentar)
        return df

    def analyze_segments(self) -> dict:
        df = self.calculate_rfm()
        if df.empty:
            return {'error': 'No hay datos para segmentación'}

        seg_counts = df['segmento'].value_counts()
        seg_value  = df.groupby('segmento')['valor_monetario'].sum()

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        axes[0, 0].pie(seg_counts.values, labels=seg_counts.index, autopct='%1.1f%%')
        axes[0, 0].set_title('Distribución de Segmentos')

        xp = range(len(seg_value))
        axes[0, 1].bar(xp, seg_value.values)
        axes[0, 1].set_xticks(xp)
        axes[0, 1].set_xticklabels(seg_value.index, rotation=30, ha='right')
        axes[0, 1].set_title('Valor Total por Segmento')

        seg_freq = df.groupby('segmento')['frecuencia'].mean()
        xp2 = range(len(seg_freq))
        axes[1, 0].bar(xp2, seg_freq.values)
        axes[1, 0].set_xticks(xp2)
        axes[1, 0].set_xticklabels(seg_freq.index, rotation=30, ha='right')
        axes[1, 0].set_title('Frecuencia Promedio por Segmento')

        seg_tick = df.groupby('segmento')['ticket_promedio'].mean()
        xp3 = range(len(seg_tick))
        axes[1, 1].bar(xp3, seg_tick.values)
        axes[1, 1].set_xticks(xp3)
        axes[1, 1].set_xticklabels(seg_tick.index, rotation=30, ha='right')
        axes[1, 1].set_title('Ticket Promedio por Segmento')

        plt.tight_layout()
        plt.savefig(self.model_dir / 'customer_segments.png', dpi=100, bbox_inches='tight')
        plt.close()

        df.to_csv(self.model_dir / 'customer_segments.csv', index=False, encoding='utf-8-sig')

        return {
            'total_clientes':               int(len(df)),
            'segmentos':                    seg_counts.to_dict(),
            'segmento_mas_valioso':         str(seg_value.idxmax()),
            'valor_segmento_mas_valioso':   float(seg_value.max()),
        }


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main(db_path: str = 'data/processed/concesionario.db', months_ahead: int = 6):
    print("=" * 60)
    print("MODULO DE PREDICCIONES - CONCESIONARIO")
    print("=" * 60)

    # ── 1. Precio de vehículos ──────────────────────────────────────────────
    print("\n[1/3] ENTRENANDO MODELO DE PRECIOS...")
    predictor = VehiclePricePredictor(db_path)
    results   = predictor.train_models()

    if results:
        best = max(results, key=lambda k: results[k]['cv_mean'])
        print(f"\n  Mejor modelo  : {best}")
        print(f"  CV R²         : {results[best]['cv_mean']:.4f}")
        print(f"  MAE           : ${results[best]['mae']:,.2f}")

        # Ejemplo de predicción
        ejemplo = {
            'marca': 'Toyota', 'modelo': 'Corolla', 'tipo': 'carro',
            'anio_modelo': 2023, 'cilindraje': 1800,
            'tipo_combustible': 'Gasolina', 'color': 'Blanco',
            'costo_vehiculo': 25000, 'descuento': 0, 'financiado': 0,
            'anio_venta': 2024, 'mes_venta': 3,
            'edad_cliente': 35, 'genero_cliente': 'M', 'tipo_cliente': 'nuevo',
            'tamano_sucursal': 'mediana', 'zona_sucursal': 'centro',
        }
        precio = predictor.predict_price(ejemplo)
        print(f"\n  Precio predicho (ejemplo): ${precio:,.2f}")

    # ── 2. Ventas futuras ───────────────────────────────────────────────────
    print(f"\n[2/3] PREDICIENDO VENTAS FUTURAS ({months_ahead} meses)...")
    sales = predictor.predict_future_sales(months_ahead=months_ahead)

    if 'error' not in sales:
        print(f"\n  Ventas totales predichas  : {sales['total_predicted_sales']}")
        print(f"  Ingresos totales predichos: ${sales['total_predicted_revenue']:,.2f}")
        for p in sales['predictions']:
            print(f"    Mes {p['mes']:>2}: {p['ventas_predichas']:>4} ventas | ${p['ingresos_predichos']:>14,.2f}")
    else:
        print(f"\n  Advertencia: {sales['error']}")

    # ── 3. Segmentación RFM ─────────────────────────────────────────────────
    print("\n[3/3] SEGMENTACION DE CLIENTES (RFM)...")
    segmenter = CustomerSegmentation(db_path)
    segs      = segmenter.analyze_segments()

    if 'error' not in segs:
        print(f"\n  Total clientes : {segs['total_clientes']}")
        for seg, cnt in segs['segmentos'].items():
            print(f"    {seg:<18}: {cnt} clientes")
        print(f"\n  Segmento mas valioso: {segs['segmento_mas_valioso']}")
        print(f"  Valor              : ${segs['valor_segmento_mas_valioso']:,.2f}")
    else:
        print(f"\n  Advertencia: {segs['error']}")

    print("\n" + "=" * 60)
    print("PREDICCIONES COMPLETADAS")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Predicciones del concesionario')
    parser.add_argument('--db',     default='data/processed/concesionario.db',
                        help='Ruta al archivo SQLite')
    parser.add_argument('--months', type=int, default=6,
                        help='Meses a predecir (default: 6)')
    args = parser.parse_args()
    main(db_path=args.db, months_ahead=args.months)