"""
Predictive Analytics Engine for GraphMemory-IDE
Time series forecasting and capacity planning with ML models
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import warnings

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import httpx

# Suppress pandas warnings for cleaner logs
warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Prediction result data structure."""
    metric_name: str
    prediction_horizon: int  # hours ahead
    predicted_value: float
    confidence_interval: Tuple[float, float]
    model_confidence: float
    timestamp: datetime
    forecast_type: str  # trend, seasonal, anomaly_forecast
    recommendations: List[str] = field(default_factory=list)

@dataclass
class CapacityRecommendation:
    """Capacity planning recommendation."""
    resource_type: str  # nodes, memory, cpu, storage
    current_usage: float
    predicted_usage: float
    time_to_capacity: Optional[int]  # hours until capacity reached
    recommended_action: str
    urgency: str  # low, medium, high, critical
    cost_impact: Optional[float] = None

@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    metric_name: str
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0-1, how strong the trend is
    seasonality_detected: bool
    change_points: List[datetime]
    performance_health: str  # excellent, good, degraded, critical

class TimeSeriesForecaster:
    """
    Advanced time series forecasting for GraphMemory metrics.
    
    Uses multiple forecasting models including linear regression,
    seasonal decomposition, and ensemble methods.
    """
    
    def __init__(self, forecast_horizon: int = 24):
        self.forecast_horizon = forecast_horizon  # hours
        self.models = {}
        self.model_performance = {}
        self.seasonal_patterns = {}
        self.trend_cache = {}
        
        logger.info(f"TimeSeriesForecaster initialized with {forecast_horizon}h horizon")
    
    def _prepare_time_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract time-based features for forecasting."""
        df = data.copy()
        
        if 'timestamp' not in df.columns:
            logger.warning("No timestamp column found, using index")
            df['timestamp'] = pd.date_range(start='2025-01-01', periods=len(df), freq='H')
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Extract time features - ensure we have a DatetimeIndex
        try:
            # Convert index to series for .dt accessor
            if isinstance(df.index, pd.DatetimeIndex):
                ts_series = pd.Series(df.index, index=df.index)
            else:
                ts_series = pd.Series(pd.to_datetime(df.index), index=df.index)
            
            df['hour'] = ts_series.dt.hour.values
            df['day_of_week'] = ts_series.dt.dayofweek.values
            df['day_of_month'] = ts_series.dt.day.values
            df['month'] = ts_series.dt.month.values
            
            # Boolean operations need to be handled properly
            weekend_mask = ts_series.dt.dayofweek >= 5
            df['is_weekend'] = weekend_mask.astype(int).values
            
            business_hours_mask = (ts_series.dt.hour >= 9) & (ts_series.dt.hour <= 17)
            df['is_business_hours'] = business_hours_mask.astype(int).values
            
        except Exception as e:
            logger.error(f"Error extracting time features: {e}")
            # Set default values if extraction fails
            df['hour'] = 12
            df['day_of_week'] = 1
            df['day_of_month'] = 15
            df['month'] = 6
            df['is_weekend'] = 0
            df['is_business_hours'] = 1
        
        return df
    
    def _detect_seasonality(self, series: pd.Series) -> Dict[str, Any]:
        """Detect seasonal patterns in time series."""
        if len(series) < 168:  # Need at least a week of hourly data
            return {'seasonal': False, 'period': None, 'strength': 0.0}
        
        # Check for daily seasonality (24 hours)
        daily_autocorr = float(series.autocorr(lag=24)) if len(series) >= 48 else 0.0
        
        # Check for weekly seasonality (168 hours)
        weekly_autocorr = float(series.autocorr(lag=168)) if len(series) >= 336 else 0.0
        
        seasonal_strength = max(abs(daily_autocorr), abs(weekly_autocorr))
        
        if seasonal_strength > 0.3:
            period = 24 if abs(daily_autocorr) > abs(weekly_autocorr) else 168
            return {
                'seasonal': True,
                'period': period,
                'strength': seasonal_strength,
                'daily_autocorr': daily_autocorr,
                'weekly_autocorr': weekly_autocorr
            }
        
        return {'seasonal': False, 'period': None, 'strength': seasonal_strength}
    
    def _fit_linear_trend_model(self, data: pd.DataFrame, target_col: str) -> Optional[Dict[str, Any]]:
        """Fit linear trend model with time features."""
        feature_cols = ['hour', 'day_of_week', 'day_of_month', 'month', 'is_weekend', 'is_business_hours']
        
        # Add time index as feature
        data_with_time = data.copy()
        data_with_time['time_index'] = range(len(data_with_time))
        
        X = data_with_time[feature_cols + ['time_index']].fillna(0)
        y = data_with_time[target_col].fillna(method='ffill').fillna(0)
        
        if len(X) < 10:
            return None
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Calculate performance metrics
        y_pred = model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        
        return {
            'model': model,
            'features': feature_cols + ['time_index'],
            'performance': {'mae': mae, 'mse': mse, 'r2': r2},
            'trend_coefficient': model.coef_[-1]  # coefficient for time_index
        }
    
    def _fit_ensemble_model(self, data: pd.DataFrame, target_col: str) -> Optional[Dict[str, Any]]:
        """Fit ensemble model for more robust predictions."""
        feature_cols = ['hour', 'day_of_week', 'day_of_month', 'month', 'is_weekend', 'is_business_hours']
        
        data_with_time = data.copy()
        data_with_time['time_index'] = range(len(data_with_time))
        
        # Add rolling features
        data_with_time['rolling_mean_24h'] = data_with_time[target_col].rolling(24, min_periods=1).mean()
        data_with_time['rolling_std_24h'] = data_with_time[target_col].rolling(24, min_periods=1).std()
        data_with_time['lag_24h'] = data_with_time[target_col].shift(24)
        data_with_time['lag_168h'] = data_with_time[target_col].shift(168)
        
        feature_cols_extended = feature_cols + ['time_index', 'rolling_mean_24h', 'rolling_std_24h', 'lag_24h', 'lag_168h']
        
        X = data_with_time[feature_cols_extended].fillna(method='ffill').fillna(0)
        y = data_with_time[target_col].fillna(method='ffill').fillna(0)
        
        if len(X) < 20:
            return None
        
        model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X, y)
        
        # Calculate performance metrics
        y_pred = model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        
        return {
            'model': model,
            'features': feature_cols_extended,
            'performance': {'mae': mae, 'mse': mse, 'r2': r2},
            'feature_importance': dict(zip(feature_cols_extended, model.feature_importances_))
        }
    
    def train_forecasting_models(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Train forecasting models for all numeric metrics."""
        logger.info("Training time series forecasting models...")
        
        # Prepare time features
        time_data = self._prepare_time_features(data)
        
        # Get numeric columns (metrics)
        numeric_cols = time_data.select_dtypes(include=[np.number]).columns
        metric_cols = [col for col in numeric_cols if not col.startswith(('hour', 'day_', 'month', 'is_'))]
        
        training_results = {}
        
        for metric in metric_cols:
            logger.info(f"Training models for metric: {metric}")
            
            try:
                # Detect seasonality
                seasonality_info = self._detect_seasonality(time_data[metric])
                self.seasonal_patterns[metric] = seasonality_info
                
                # Train linear model
                linear_model = self._fit_linear_trend_model(time_data, metric)
                
                # Train ensemble model
                ensemble_model = self._fit_ensemble_model(time_data, metric)
                
                # Store models
                self.models[metric] = {
                    'linear': linear_model,
                    'ensemble': ensemble_model,
                    'seasonality': seasonality_info,
                    'last_trained': datetime.now()
                }
                
                # Calculate overall performance
                if linear_model and ensemble_model:
                    best_model = 'ensemble' if ensemble_model['performance']['r2'] > linear_model['performance']['r2'] else 'linear'
                    best_performance = ensemble_model['performance'] if best_model == 'ensemble' else linear_model['performance']
                else:
                    best_model = 'ensemble' if ensemble_model else 'linear'
                    best_performance = (ensemble_model or linear_model)['performance']
                
                self.model_performance[metric] = {
                    'best_model': best_model,
                    'performance': best_performance,
                    'seasonality_strength': seasonality_info['strength']
                }
                
                training_results[metric] = {
                    'status': 'success',
                    'best_model': best_model,
                    'r2_score': best_performance['r2'],
                    'seasonal': seasonality_info['seasonal']
                }
                
            except Exception as e:
                logger.error(f"Error training models for {metric}: {e}")
                training_results[metric] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        logger.info(f"Model training completed for {len(training_results)} metrics")
        return training_results
    
    def forecast_metric(self, metric_name: str, hours_ahead: int = None) -> Optional[PredictionResult]:
        """Generate forecast for a specific metric."""
        hours_ahead = hours_ahead or self.forecast_horizon
        
        if metric_name not in self.models:
            logger.warning(f"No trained model found for metric: {metric_name}")
            return None
        
        model_info = self.models[metric_name]
        
        try:
            # Choose best model
            best_model_type = self.model_performance[metric_name]['best_model']
            model_data = model_info[best_model_type]
            
            if not model_data:
                return None
            
            model = model_data['model']
            features = model_data['features']
            
            # Generate future time features
            current_time = datetime.now()
            future_time = current_time + timedelta(hours=hours_ahead)
            
            # Create feature vector for prediction
            future_features = {
                'hour': future_time.hour,
                'day_of_week': future_time.weekday(),
                'day_of_month': future_time.day,
                'month': future_time.month,
                'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                'is_business_hours': 1 if 9 <= future_time.hour <= 17 else 0,
                'time_index': 1000 + hours_ahead  # Approximate future time index
            }
            
            # Add rolling features if needed (use current values as approximation)
            if 'rolling_mean_24h' in features:
                future_features.update({
                    'rolling_mean_24h': 0,  # Would need recent data to calculate
                    'rolling_std_24h': 0,
                    'lag_24h': 0,
                    'lag_168h': 0
                })
            
            # Create feature vector
            X_future = np.array([[future_features.get(feat, 0) for feat in features]])
            
            # Make prediction
            prediction = model.predict(X_future)[0]
            
            # Calculate confidence interval (simplified)
            model_confidence = self.model_performance[metric_name]['performance']['r2']
            prediction_std = abs(prediction * (1 - model_confidence) * 0.5)
            
            confidence_interval = (
                max(0, prediction - 1.96 * prediction_std),
                prediction + 1.96 * prediction_std
            )
            
            # Generate recommendations
            recommendations = self._generate_forecast_recommendations(
                metric_name, prediction, model_confidence, hours_ahead
            )
            
            return PredictionResult(
                metric_name=metric_name,
                prediction_horizon=hours_ahead,
                predicted_value=prediction,
                confidence_interval=confidence_interval,
                model_confidence=model_confidence,
                timestamp=current_time,
                forecast_type='trend',
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error forecasting {metric_name}: {e}")
            return None
    
    def _generate_forecast_recommendations(
        self, 
        metric_name: str, 
        prediction: float, 
        confidence: float, 
        hours_ahead: int
    ) -> List[str]:
        """Generate actionable recommendations based on forecast."""
        recommendations = []
        
        if confidence < 0.5:
            recommendations.append("Low confidence prediction - monitor actual values closely")
        
        # Metric-specific recommendations
        if 'node' in metric_name.lower():
            if prediction > 1000:
                recommendations.append("High node count predicted - consider memory optimization")
            elif prediction < 10:
                recommendations.append("Low node activity predicted - monitor for system issues")
        
        elif 'search' in metric_name.lower():
            if prediction > 100:
                recommendations.append("High search activity predicted - ensure search performance")
            
        elif 'duration' in metric_name.lower():
            if prediction > 2.0:
                recommendations.append("Increased response times predicted - review performance")
        
        if hours_ahead > 12:
            recommendations.append("Long-term forecast - review regularly as new data arrives")
        
        return recommendations

class CapacityPlanner:
    """
    Intelligent capacity planning for GraphMemory-IDE.
    
    Analyzes resource usage trends and provides proactive
    scaling recommendations.
    """
    
    def __init__(self, forecaster: Optional[TimeSeriesForecaster] = None):
        self.forecaster = forecaster or TimeSeriesForecaster()
        self.capacity_thresholds = {
            'cpu_usage': 80.0,  # %
            'memory_usage': 85.0,  # %
            'disk_usage': 90.0,  # %
            'node_count': 10000,  # nodes
            'active_sessions': 1000  # sessions
        }
        self.cost_models = {
            'cpu': 0.05,  # $ per hour per core
            'memory': 0.01,  # $ per hour per GB
            'storage': 0.001  # $ per hour per GB
        }
        
    def analyze_capacity_needs(self, current_metrics: Dict[str, float]) -> List[CapacityRecommendation]:
        """Analyze current capacity and predict future needs."""
        recommendations = []
        
        for resource, current_value in current_metrics.items():
            try:
                # Get capacity threshold
                threshold = self.capacity_thresholds.get(resource)
                if not threshold:
                    continue
                
                # Calculate current usage percentage
                if 'usage' in resource:
                    current_usage_pct = current_value
                else:
                    current_usage_pct = (current_value / threshold) * 100
                
                # Forecast future usage
                forecast = self.forecaster.forecast_metric(resource, hours_ahead=24)
                
                if forecast:
                    predicted_value = forecast.predicted_value
                    predicted_usage_pct = (predicted_value / threshold) * 100 if 'usage' not in resource else predicted_value
                    
                    # Calculate time to capacity
                    time_to_capacity = self._calculate_time_to_capacity(
                        current_value, predicted_value, threshold
                    )
                    
                    # Generate recommendation
                    recommendation = self._generate_capacity_recommendation(
                        resource, current_usage_pct, predicted_usage_pct, time_to_capacity
                    )
                    
                    if recommendation:
                        recommendations.append(recommendation)
                        
            except Exception as e:
                logger.error(f"Error analyzing capacity for {resource}: {e}")
        
        return recommendations
    
    def _calculate_time_to_capacity(
        self, 
        current_value: float, 
        predicted_value: float, 
        threshold: float
    ) -> Optional[int]:
        """Calculate hours until capacity threshold is reached."""
        if predicted_value <= current_value:
            return None  # No growth or decreasing
        
        growth_rate = (predicted_value - current_value) / 24  # per hour
        
        if growth_rate <= 0:
            return None
        
        remaining_capacity = threshold - current_value
        hours_to_capacity = remaining_capacity / growth_rate
        
        return max(0, int(hours_to_capacity))
    
    def _generate_capacity_recommendation(
        self,
        resource: str,
        current_usage: float,
        predicted_usage: float,
        time_to_capacity: Optional[int]
    ) -> Optional[CapacityRecommendation]:
        """Generate capacity recommendation based on analysis."""
        
        # Determine urgency
        if current_usage >= 90:
            urgency = 'critical'
            action = 'Immediate scaling required'
        elif current_usage >= 80:
            urgency = 'high'
            action = 'Scale within 24 hours'
        elif predicted_usage >= 80:
            urgency = 'medium'
            action = 'Plan scaling within 48 hours'
        elif time_to_capacity and time_to_capacity <= 72:
            urgency = 'medium'
            action = f'Scale within {time_to_capacity} hours'
        else:
            urgency = 'low'
            action = 'Monitor and plan for future scaling'
        
        # Skip low priority recommendations if not critical
        if urgency == 'low' and current_usage < 60:
            return None
        
        # Calculate cost impact (simplified)
        cost_impact = None
        if resource in ['cpu_usage', 'memory_usage']:
            base_cost = self.cost_models.get(resource.replace('_usage', ''), 0)
            cost_impact = base_cost * 24 * 30  # Monthly cost estimate
        
        return CapacityRecommendation(
            resource_type=resource,
            current_usage=current_usage,
            predicted_usage=predicted_usage,
            time_to_capacity=time_to_capacity,
            recommended_action=action,
            urgency=urgency,
            cost_impact=cost_impact
        )

class PredictiveAnalyticsEngine:
    """
    Main predictive analytics engine combining forecasting and capacity planning.
    """
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.forecaster = TimeSeriesForecaster()
        self.capacity_planner = CapacityPlanner(self.forecaster)
        
        # Analysis state
        self.last_analysis = None
        self.historical_data = pd.DataFrame()
        self.is_trained = False
        
    async def initialize(self) -> None:
        """Initialize the predictive analytics engine."""
        logger.info("Initializing predictive analytics engine...")
        
        try:
            # Fetch historical data for training
            await self._fetch_training_data()
            
            # Train forecasting models
            if not self.historical_data.empty:
                training_results = self.forecaster.train_forecasting_models(self.historical_data)
                self.is_trained = any(result.get('status') == 'success' for result in training_results.values())
                
                logger.info(f"Training completed. Models trained: {len(training_results)}")
            else:
                logger.warning("No historical data available for training")
                
        except Exception as e:
            logger.error(f"Error initializing predictive analytics: {e}")
    
    async def _fetch_training_data(self) -> None:
        """Fetch historical metrics data for training."""
        try:
            async with httpx.AsyncClient() as client:
                # Fetch the last 7 days of data
                end_time = datetime.now()
                start_time = end_time - timedelta(days=7)
                
                metrics_queries = [
                    'graphmemory_node_operations_total',
                    'graphmemory_search_operations_total',
                    'graphmemory_total_nodes',
                    'graphmemory_active_sessions',
                    'graphmemory_http_request_duration_seconds'
                ]
                
                # For now, simulate historical data
                # In production, this would query Prometheus range endpoint
                timestamps = pd.date_range(start=start_time, end=end_time, freq='H')
                
                historical_data = []
                for ts in timestamps:
                    data_point = {'timestamp': ts}
                    
                    # Generate synthetic data for demonstration
                    base_hour = ts.hour
                    base_day = ts.dayofweek
                    
                    data_point.update({
                        'graphmemory_node_operations_total': max(0, 100 + 50 * np.sin(base_hour * np.pi / 12) + np.random.normal(0, 10)),
                        'graphmemory_search_operations_total': max(0, 50 + 25 * np.sin(base_hour * np.pi / 12) + np.random.normal(0, 5)),
                        'graphmemory_total_nodes': max(0, 1000 + ts.hour * 2 + np.random.normal(0, 20)),
                        'graphmemory_active_sessions': max(0, 20 + 15 * (1 if 9 <= base_hour <= 17 else 0.3) + np.random.normal(0, 3)),
                        'graphmemory_http_request_duration_seconds': max(0.1, 0.5 + 0.2 * np.sin(base_hour * np.pi / 12) + np.random.normal(0, 0.1))
                    })
                    
                    historical_data.append(data_point)
                
                self.historical_data = pd.DataFrame(historical_data)
                logger.info(f"Loaded {len(self.historical_data)} historical data points")
                
        except Exception as e:
            logger.error(f"Error fetching training data: {e}")
    
    async def run_predictive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive predictive analysis."""
        if not self.is_trained:
            await self.initialize()
        
        logger.info("Running predictive analysis...")
        
        try:
            # Get current metrics
            current_metrics = await self._fetch_current_metrics()
            
            # Generate forecasts
            forecasts = []
            for metric in current_metrics.keys():
                forecast = self.forecaster.forecast_metric(metric)
                if forecast:
                    forecasts.append(forecast)
            
            # Analyze capacity needs
            capacity_recommendations = self.capacity_planner.analyze_capacity_needs(current_metrics)
            
            # Perform trend analysis
            trend_analysis = self._analyze_trends()
            
            analysis_result = {
                'timestamp': datetime.now(),
                'forecasts': forecasts,
                'capacity_recommendations': capacity_recommendations,
                'trend_analysis': trend_analysis,
                'model_performance': self.forecaster.model_performance
            }
            
            self.last_analysis = analysis_result
            
            logger.info(f"Predictive analysis completed. Generated {len(forecasts)} forecasts and {len(capacity_recommendations)} capacity recommendations")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in predictive analysis: {e}")
            return {}
    
    async def _fetch_current_metrics(self) -> Dict[str, float]:
        """Fetch current metric values."""
        # Simulate current metrics
        current_time = datetime.now()
        
        return {
            'graphmemory_node_operations_total': 150.0,
            'graphmemory_search_operations_total': 75.0,
            'graphmemory_total_nodes': 1200.0,
            'graphmemory_active_sessions': 35.0,
            'graphmemory_http_request_duration_seconds': 0.6
        }
    
    def _analyze_trends(self) -> List[TrendAnalysis]:
        """Analyze trends in historical data."""
        trends = []
        
        if self.historical_data.empty:
            return trends
        
        numeric_cols = self.historical_data.select_dtypes(include=[np.number]).columns
        
        for metric in numeric_cols:
            try:
                values = self.historical_data[metric].dropna()
                
                if len(values) < 24:  # Need at least 24 hours of data
                    continue
                
                # Calculate trend direction and strength
                x = np.arange(len(values))
                correlation = np.corrcoef(x, values)[0, 1]
                
                if correlation > 0.3:
                    direction = 'increasing'
                    strength = abs(correlation)
                elif correlation < -0.3:
                    direction = 'decreasing'
                    strength = abs(correlation)
                else:
                    direction = 'stable'
                    strength = 1 - abs(correlation)
                
                # Check for seasonality
                seasonality = self.forecaster.seasonal_patterns.get(metric, {})
                seasonal = seasonality.get('seasonal', False)
                
                # Assess performance health
                if metric in ['duration', 'latency']:
                    # For latency metrics, increasing is bad
                    if direction == 'increasing' and strength > 0.5:
                        health = 'degraded'
                    elif direction == 'decreasing':
                        health = 'good'
                    else:
                        health = 'stable'
                else:
                    # For other metrics, assess based on current values
                    current_value = values.iloc[-1]
                    mean_value = values.mean()
                    
                    if current_value > mean_value * 1.5:
                        health = 'degraded'
                    elif current_value < mean_value * 0.5:
                        health = 'critical'
                    else:
                        health = 'good'
                
                trend = TrendAnalysis(
                    metric_name=metric,
                    trend_direction=direction,
                    trend_strength=strength,
                    seasonality_detected=seasonal,
                    change_points=[],  # Would require more sophisticated analysis
                    performance_health=health
                )
                
                trends.append(trend)
                
            except Exception as e:
                logger.error(f"Error analyzing trend for {metric}: {e}")
        
        return trends
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of the latest analysis."""
        if not self.last_analysis:
            return {'status': 'no_analysis_available'}
        
        analysis = self.last_analysis
        
        return {
            'timestamp': analysis['timestamp'],
            'total_forecasts': len(analysis['forecasts']),
            'capacity_alerts': len([r for r in analysis['capacity_recommendations'] if r.urgency in ['high', 'critical']]),
            'trend_summary': {
                'increasing_trends': len([t for t in analysis['trend_analysis'] if t.trend_direction == 'increasing']),
                'decreasing_trends': len([t for t in analysis['trend_analysis'] if t.trend_direction == 'decreasing']),
                'stable_trends': len([t for t in analysis['trend_analysis'] if t.trend_direction == 'stable']),
            },
            'health_status': self._assess_overall_health(analysis['trend_analysis'])
        }
    
    def _assess_overall_health(self, trends: List[TrendAnalysis]) -> str:
        """Assess overall system health based on trends."""
        if not trends:
            return 'unknown'
        
        health_scores = {'excellent': 4, 'good': 3, 'degraded': 2, 'critical': 1}
        
        avg_score = sum(health_scores.get(t.performance_health, 2) for t in trends) / len(trends)
        
        if avg_score >= 3.5:
            return 'excellent'
        elif avg_score >= 2.5:
            return 'good'
        elif avg_score >= 1.5:
            return 'degraded'
        else:
            return 'critical'

# Global analytics engine
_analytics_engine = None

def get_analytics_engine() -> PredictiveAnalyticsEngine:
    """Get or create global analytics engine."""
    global _analytics_engine
    
    if _analytics_engine is None:
        _analytics_engine = PredictiveAnalyticsEngine()
    
    return _analytics_engine

async def initialize_predictive_analytics(prometheus_url: str = "http://localhost:9090") -> PredictiveAnalyticsEngine:
    """Initialize predictive analytics system."""
    global _analytics_engine
    
    _analytics_engine = PredictiveAnalyticsEngine(prometheus_url)
    await _analytics_engine.initialize()
    
    logger.info("Predictive analytics system initialized")
    return _analytics_engine 