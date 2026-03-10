import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import logging
from pathlib import Path
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from ..database.connection import DatabaseManager

class VehiclePricePredictor:
    """Predictor de precios de vehículos"""
    
    def __init__(self, db_path: str = None):
        self.db_manager = DatabaseManager(db_path)
        self.models = {}
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.model_dir = Path(__file__).parent.parent.parent / 'models'
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_data(self):
        """Prepara datos para el modelo de predicción de precios"""
        query = """
        SELECT 
            v.id_vehiculo,
            v.marca,
            v.modelo,
            v.tipo,
            v.año_modelo,
            v.cilindraje,
            v.tipo_combustible,
            v.color,
            hv.precio_venta as precio_real,
            hv.costo_vehiculo,
            hv.descuento,
            COALESCE(hv.financiado, 0) as financiado,
            t.año as año_venta,
            t.mes as mes_venta,
            c.edad as edad_cliente,
            c.genero as genero_cliente,
            c.tipo_cliente,
            s.tamaño as tamaño_sucursal,
            s.zona as zona_sucursal
        FROM hecho_ventas hv
        JOIN dim_vehiculo v ON hv.id_vehiculo = v.id_vehiculo
        JOIN dim_tiempo t ON hv.id_tiempo = t.id_tiempo
        JOIN dim_cliente c ON hv.id_cliente = c.id_cliente
        JOIN dim_sucursal s ON hv.id_sucursal = s.id_sucursal
        WHERE hv.precio_venta IS NOT NULL 
          AND hv.precio_venta > 0
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty:
            logging.error("No hay datos para entrenar el modelo")
            return None, None
        
        # Crear features
        X = df.drop(['precio_real', 'id_vehiculo'], axis=1, errors='ignore')
        y = df['precio_real']
        
        return X, y
    
    def preprocess_features(self, X, fit_encoders=True):
        """Preprocesa características para el modelo"""
        X_processed = X.copy()
        
        # Identificar columnas numéricas y categóricas
        numeric_cols = X_processed.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = X_processed.select_dtypes(include=['object']).columns.tolist()
        
        # Manejar valores nulos
        for col in numeric_cols:
            X_processed[col] = X_processed[col].fillna(X_processed[col].median())
        
        for col in categorical_cols:
            X_processed[col] = X_processed[col].fillna('Desconocido')
            
            # Codificar variables categóricas
            if fit_encoders:
                self.label_encoders[col] = LabelEncoder()
                X_processed[col] = self.label_encoders[col].fit_transform(X_processed[col].astype(str))
            else:
                # Usar encoders existentes
                if col in self.label_encoders:
                    # Manejar valores no vistos
                    known_classes = set(self.label_encoders[col].classes_)
                    X_processed[col] = X_processed[col].apply(
                        lambda x: x if x in known_classes else 'Desconocido'
                    )
                    X_processed[col] = self.label_encoders[col].transform(X_processed[col].astype(str))
        
        # Escalar características numéricas
        if fit_encoders:
            X_processed[numeric_cols] = self.scaler.fit_transform(X_processed[numeric_cols])
        else:
            X_processed[numeric_cols] = self.scaler.transform(X_processed[numeric_cols])
        
        return X_processed
    
    def train_models(self):
        """Entrena múltiples modelos y selecciona el mejor"""
        X, y = self.prepare_data()
        if X is None:
            return None
        
        # Preprocesar
        X_processed = self.preprocess_features(X, fit_encoders=True)
        
        # Dividir datos
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y, test_size=0.2, random_state=42
        )
        
        # Definir modelos
        models = {
            'linear_regression': LinearRegression(),
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
        }
        
        # Entrenar y evaluar
        results = {}
        best_model = None
        best_score = -np.inf
        
        for name, model in models.items():
            # Entrenar
            model.fit(X_train, y_train)
            
            # Predecir
            y_pred = model.predict(X_test)
            
            # Métricas
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            # Validación cruzada
            cv_scores = cross_val_score(model, X_processed, y, cv=5, scoring='r2')
            
            results[name] = {
                'model': model,
                'mae': float(mae),
                'rmse': float(rmse),
                'r2': float(r2),
                'cv_mean': float(cv_scores.mean()),
                'cv_std': float(cv_scores.std())
            }
            
            logging.info(f"\n Modelo: {name}")
            logging.info(f"  MAE: ${mae:,.2f}")
            logging.info(f"  RMSE: ${rmse:,.2f}")
            logging.info(f"  R²: {r2:.4f}")
            logging.info(f"  CV R²: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
            
            # Guardar el mejor modelo
            if cv_scores.mean() > best_score:
                best_score = cv_scores.mean()
                best_model = model
                self.models[name] = model
        
        # Guardar el mejor modelo
        if best_model:
            self.save_model(best_model, results)
            
            # Gráfico de importancia de características (para Random Forest)
            if 'random_forest' in models and hasattr(models['random_forest'], 'feature_importances_'):
                self.plot_feature_importance(
                    models['random_forest'], 
                    X.columns.tolist(),
                    'random_forest_importance.png'
                )
        
        return results
    
    def predict_price(self, vehicle_features):
        """Predice el precio de un vehículo"""
        if not self.models:
            # Cargar modelo guardado
            self.load_model()
        
        if not self.models:
            logging.error("No hay modelo disponible para predicción")
            return None
        
        # Usar el mejor modelo (Random Forest por defecto)
        model = self.models.get('random_forest', list(self.models.values())[0])
        
        # Preprocesar características
        X = pd.DataFrame([vehicle_features])
        X_processed = self.preprocess_features(X, fit_encoders=False)
        
        # Predecir
        prediction = model.predict(X_processed)[0]
        
        return float(prediction)
    
    def save_model(self, model, results):
        """Guarda el modelo entrenado"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Guardar modelo
        model_path = self.model_dir / f'vehicle_price_model_{timestamp}.pkl'
        joblib.dump(model, model_path)
        
        # Guardar preprocesadores
        preprocessors = {
            'scaler': self.scaler,
            'label_encoders': self.label_encoders
        }
        preprocessors_path = self.model_dir / f'preprocessors_{timestamp}.pkl'
        joblib.dump(preprocessors, preprocessors_path)
        
        # Guardar resultados
        results_path = self.model_dir / f'model_results_{timestamp}.json'
        results_serializable = {}
        for name, res in results.items():
            results_serializable[name] = {
                k: v for k, v in res.items() if k != 'model'
            }
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results_serializable, f, indent=2, default=str)
        
        logging.info(f"\n✅ Modelo guardado en: {model_path}")
        
        # Guardar como modelo actual
        joblib.dump(model, self.model_dir / 'vehicle_price_model_current.pkl')
        joblib.dump(preprocessors, self.model_dir / 'preprocessors_current.pkl')
    
    def load_model(self, model_path=None):
        """Carga el modelo guardado"""
        if model_path is None:
            model_path = self.model_dir / 'vehicle_price_model_current.pkl'
            preprocessors_path = self.model_dir / 'preprocessors_current.pkl'
        
        if model_path.exists():
            self.models['loaded'] = joblib.load(model_path)
            
            # Cargar preprocesadores
            if preprocessors_path.exists():
                preprocessors = joblib.load(preprocessors_path)
                self.scaler = preprocessors['scaler']
                self.label_encoders = preprocessors['label_encoders']
            
            logging.info(f"✅ Modelo cargado desde: {model_path}")
            return True
        else:
            logging.warning("No se encontró modelo guardado")
            return False
    
    def plot_feature_importance(self, model, feature_names, filename):
        """Grafica importancia de características"""
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1]
            
            plt.figure(figsize=(12, 6))
            plt.title("Importancia de Características")
            plt.bar(range(len(importances)), importances[indices])
            plt.xticks(range(len(importances)), 
                      [feature_names[i] for i in indices], 
                      rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(self.model_dir / filename, dpi=100, bbox_inches='tight')
            plt.close()
    
    def predict_future_sales(self, months_ahead=3):
        """Predice ventas futuras"""
        # Obtener datos históricos
        query = """
        SELECT 
            t.fecha_completa,
            COUNT(v.id_venta) as ventas,
            SUM(v.precio_venta) as ingresos
        FROM hecho_ventas v
        JOIN dim_tiempo t ON v.id_tiempo = t.id_tiempo
        GROUP BY t.fecha_completa
        ORDER BY t.fecha_completa
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty or len(df) < 10:
            return {'error': 'Datos insuficientes para predicción'}
        
        # Convertir fechas
        df['fecha'] = pd.to_datetime(df['fecha_completa'])
        df = df.set_index('fecha')
        
        # Usar 'ME' en lugar de 'M' para pandas >= 2.2
        try:
            # Intentar con 'ME' (nuevo formato)
            df_monthly = df.resample('ME').sum().reset_index()
        except:
            # Fallback a 'M' para versiones antiguas
            df_monthly = df.resample('M').sum().reset_index()
        
        # Modelo simple de series temporales (promedio móvil)
        df_monthly['ventas_ma'] = df_monthly['ventas'].rolling(window=3).mean()
        
        # Último valor conocido
        last_ventas = df_monthly['ventas'].iloc[-3:].mean()
        last_ingresos = df_monthly['ingresos'].iloc[-3:].mean()
        
        # Predicción simple
        predictions = []
        for i in range(1, months_ahead + 1):
            # Tendencia simple (2% crecimiento mensual asumido)
            growth_rate = 0.02
            predicted_ventas = last_ventas * (1 + growth_rate) ** i
            predicted_ingresos = last_ingresos * (1 + growth_rate) ** i
            
            predictions.append({
                'mes': i,
                'ventas_predichas': int(predicted_ventas),
                'ingresos_predichos': float(predicted_ingresos)
            })
        
        # Gráfico
        plt.figure(figsize=(12, 6))
        
        # Histórico
        plt.plot(df_monthly['fecha'], df_monthly['ventas'], label='Histórico', marker='o')
        
        # Predicción
        last_date = df_monthly['fecha'].iloc[-1]
        pred_dates = []
        pred_values = []
        
        for i in range(1, months_ahead + 1):
            # Añadir meses usando dateutil o pandas
            next_date = last_date + pd.DateOffset(months=i)
            pred_dates.append(next_date)
            pred_values.append(predictions[i-1]['ventas_predichas'])
        
        plt.plot(pred_dates, pred_values, 'r--', label='Predicción', marker='s')
        
        plt.title('Predicción de Ventas')
        plt.xlabel('Fecha')
        plt.ylabel('Número de Ventas')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.savefig(self.model_dir / 'sales_prediction.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        return {
            'predictions': predictions,
            'last_historical': {
                'ventas': int(last_ventas),
                'ingresos': float(last_ingresos)
            },
            'total_predicted_sales': int(sum(p['ventas_predichas'] for p in predictions)),
            'total_predicted_revenue': float(sum(p['ingresos_predichos'] for p in predictions))
        }

class CustomerSegmentation:
    """Segmentación de clientes usando RFM"""
    
    def __init__(self, db_path: str = None):
        self.db_manager = DatabaseManager(db_path)
        self.model_dir = Path(__file__).parent.parent.parent / 'models'
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def calculate_rfm(self):
        """Calcula métricas RFM (Recency, Frequency, Monetary)"""
        query = """
        SELECT 
            c.id_cliente,
            c.nombre,
            c.tipo_cliente,
            c.edad,
            c.genero,
            MAX(t.fecha_completa) as ultima_compra,
            COUNT(v.id_venta) as frecuencia,
            SUM(COALESCE(v.precio_venta, 0)) as valor_monetario,
            AVG(v.precio_venta) as ticket_promedio,
            COUNT(DISTINCT v.id_vehiculo) as vehiculos_comprados
        FROM dim_cliente c
        LEFT JOIN hecho_ventas v ON c.id_cliente = v.id_cliente
        LEFT JOIN dim_tiempo t ON v.id_tiempo = t.id_tiempo
        GROUP BY c.id_cliente, c.nombre, c.tipo_cliente, c.edad, c.genero
        """
        
        df = self.db_manager.execute_query(query)
        
        if df.empty:
            return df
        
        # Calcular Recency (días desde última compra)
        today = pd.Timestamp.now().date()
        df['ultima_compra'] = pd.to_datetime(df['ultima_compra'])
        df['recency'] = (pd.Timestamp.now() - df['ultima_compra']).dt.days
        
        # Manejar clientes sin compras
        df['recency'] = df['recency'].fillna(999)
        df['frecuencia'] = df['frecuencia'].fillna(0)
        df['valor_monetario'] = df['valor_monetario'].fillna(0)
        
        # Crear scores RFM (1-5) - manejar posibles errores de qcut
        try:
            df['r_score'] = pd.qcut(df['recency'].rank(method='first'), q=5, labels=[5,4,3,2,1])
        except:
            # Si hay problemas, usar división por cuantiles manual
            bins = df['recency'].quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0])
            df['r_score'] = pd.cut(df['recency'], bins=bins, labels=[5,4,3,2,1], include_lowest=True)
        
        try:
            df['f_score'] = pd.qcut(df['frecuencia'].rank(method='first'), q=5, labels=[1,2,3,4,5])
        except:
            bins = df['frecuencia'].quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0])
            df['f_score'] = pd.cut(df['frecuencia'], bins=bins, labels=[1,2,3,4,5], include_lowest=True)
        
        try:
            df['m_score'] = pd.qcut(df['valor_monetario'].rank(method='first'), q=5, labels=[1,2,3,4,5])
        except:
            bins = df['valor_monetario'].quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0])
            df['m_score'] = pd.cut(df['valor_monetario'], bins=bins, labels=[1,2,3,4,5], include_lowest=True)
        
        # Convertir a numérico
        for col in ['r_score', 'f_score', 'm_score']:
            df[col] = pd.to_numeric(df[col])
        
        # Score total
        df['rfm_score'] = df['r_score'] + df['f_score'] + df['m_score']
        
        # Segmentar clientes
        def segmentar(row):
            if row['rfm_score'] >= 13:
                return 'Campeones'
            elif row['rfm_score'] >= 10:
                return 'Leales'
            elif row['rfm_score'] >= 7:
                return 'Potenciales'
            elif row['rfm_score'] >= 4:
                return 'Prometedores'
            else:
                return 'En riesgo'
        
        df['segmento'] = df.apply(segmentar, axis=1)
        
        return df
    
    def analyze_segments(self):
        """Analiza los segmentos de clientes"""
        df = self.calculate_rfm()
        
        if df.empty:
            return {'error': 'No hay datos para segmentación'}
        
        # Estadísticas por segmento
        segment_stats = df.groupby('segmento').agg({
            'id_cliente': 'count',
            'frecuencia': 'mean',
            'valor_monetario': ['mean', 'sum'],
            'ticket_promedio': 'mean'
        }).round(2)
        
        # Gráfico
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Distribución de segmentos
        segment_counts = df['segmento'].value_counts()
        axes[0, 0].pie(segment_counts.values, labels=segment_counts.index, autopct='%1.1f%%')
        axes[0, 0].set_title('Distribución de Segmentos')
        
        # Valor por segmento
        segment_value = df.groupby('segmento')['valor_monetario'].sum()
        axes[0, 1].bar(range(len(segment_value)), segment_value.values)
        axes[0, 1].set_xticks(range(len(segment_value)))
        axes[0, 1].set_xticklabels(segment_value.index, rotation=45, ha='right')
        axes[0, 1].set_title('Valor Total por Segmento')
        
        # Frecuencia promedio
        segment_freq = df.groupby('segmento')['frecuencia'].mean()
        axes[1, 0].bar(range(len(segment_freq)), segment_freq.values)
        axes[1, 0].set_xticks(range(len(segment_freq)))
        axes[1, 0].set_xticklabels(segment_freq.index, rotation=45, ha='right')
        axes[1, 0].set_title('Frecuencia Promedio por Segmento')
        
        # Ticket promedio
        segment_ticket = df.groupby('segmento')['ticket_promedio'].mean()
        axes[1, 1].bar(range(len(segment_ticket)), segment_ticket.values)
        axes[1, 1].set_xticks(range(len(segment_ticket)))
        axes[1, 1].set_xticklabels(segment_ticket.index, rotation=45, ha='right')
        axes[1, 1].set_title('Ticket Promedio por Segmento')
        
        plt.tight_layout()
        plt.savefig(self.model_dir / 'customer_segments.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # Guardar resultados
        df.to_csv(self.model_dir / 'customer_segments.csv', index=False, encoding='utf-8-sig')
        
        return {
            'total_clientes': int(len(df)),
            'segmentos': segment_counts.to_dict(),
            'segmento_mas_valioso': str(segment_value.idxmax()),
            'valor_segmento_mas_valioso': float(segment_value.max()),
            'estadisticas': segment_stats.to_dict()
        }

def main_prediction():
    """Función principal para predicciones"""
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🔮 MÓDULO DE PREDICCIONES - CONCESIONARIO")
    print("=" * 60)
    
    # 1. Predicción de precios
    print("\n🚗 ENTRENANDO MODELO DE PRECIOS...")
    price_predictor = VehiclePricePredictor()
    results = price_predictor.train_models()
    
    if results:
        best_model = max(results.items(), key=lambda x: x[1]['cv_mean'])[0]
        print(f"\n✅ Mejor modelo: {best_model}")
        
        # Ejemplo de predicción
        ejemplo = {
            'marca': 'Toyota',
            'modelo': 'Corolla',
            'tipo': 'carro',
            'año_modelo': 2023,
            'cilindraje': 1800,
            'tipo_combustible': 'Gasolina',
            'color': 'Blanco',
            'costo_vehiculo': 25000,
            'descuento': 0,
            'financiado': 0,
            'año_venta': 2024,
            'mes_venta': 3,
            'edad_cliente': 35,
            'genero_cliente': 'M',
            'tipo_cliente': 'nuevo',
            'tamaño_sucursal': 'Mediana',
            'zona_sucursal': 'Centro'
        }
        
        precio_predicho = price_predictor.predict_price(ejemplo)
        if precio_predicho:
            print(f"\n💰 Predicción de precio (ejemplo): ${precio_predicho:,.2f}")
    
    # 2. Predicción de ventas futuras
    print("\n📈 PREDICIENDO VENTAS FUTURAS...")
    sales_pred = price_predictor.predict_future_sales(months_ahead=6)
    
    if 'error' not in sales_pred:
        print(f"\n📊 Predicción para próximos 6 meses:")
        print(f"  • Ventas totales predichas: {sales_pred['total_predicted_sales']}")
        print(f"  • Ingresos totales predichos: ${sales_pred['total_predicted_revenue']:,.2f}")
        
        for p in sales_pred['predictions']:
            print(f"    Mes {p['mes']}: {p['ventas_predichas']} ventas, ${p['ingresos_predichos']:,.2f}")
    else:
        print(f"\n⚠️  {sales_pred['error']}")
    
    # 3. Segmentación de clientes
    print("\n👥 ANALIZANDO SEGMENTOS DE CLIENTES...")
    segmenter = CustomerSegmentation()
    segments = segmenter.analyze_segments()
    
    if 'error' not in segments:
        print(f"\n📊 Segmentos de clientes:")
        for segment, count in segments['segmentos'].items():
            print(f"  • {segment}: {count} clientes")
        print(f"\n  Segmento más valioso: {segments['segmento_mas_valioso']}")
        print(f"  Valor: ${segments['valor_segmento_mas_valioso']:,.2f}")
    
    print("\n" + "=" * 60)
    print("✅ PREDICCIONES COMPLETADAS")
    print("=" * 60)

if __name__ == "__main__":
    main_prediction()