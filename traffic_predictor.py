import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
import joblib
import os

class TrafficPredictor:
    def __init__(self):
        self.model = RandomForestRegressor()
        self.historical_data = {
            'time': [],
            'day_of_week': [],
            'vehicle_count': [],
            'congestion_level': [],
            'direction': []
        }
        self.prediction_window = 15  # minutes
        self.model_path = 'traffic_model.joblib'
        self.is_model_trained = False
        self.default_prediction = {
            'predicted_vehicles': 0,
            'congestion_risk': 'Low'
        }
        self.load_model()
        
    def prepare_features(self, timestamp):
        """Prepare feature vector for prediction"""
        return np.array([
            timestamp.hour,
            timestamp.minute,
            timestamp.weekday(),
            1 if self.is_peak_hour(timestamp) else 0,
            1 if self.is_weekend(timestamp) else 0
        ]).reshape(1, -1)
        
    def is_peak_hour(self, timestamp):
        """Check if given time is during peak hours"""
        hour = timestamp.hour
        return (7 <= hour <= 10) or (16 <= hour <= 19)
        
    def is_weekend(self, timestamp):
        """Check if given time is weekend"""
        return timestamp.weekday() >= 5
        
    def add_data_point(self, timestamp, vehicle_count, congestion_level, direction):
        """Add new data point to historical data"""
        self.historical_data['time'].append(timestamp)
        self.historical_data['day_of_week'].append(timestamp.weekday())
        self.historical_data['vehicle_count'].append(vehicle_count)
        self.historical_data['congestion_level'].append(congestion_level)
        self.historical_data['direction'].append(direction)
        
    def train_model(self):
        """Train prediction model on historical data"""
        if len(self.historical_data['time']) < 100:  # Need minimum data points
            return False
            
        try:
            # Fix array conversion
            X = np.array([
                [t.hour, t.minute, t.weekday(),
                 int(self.is_peak_hour(t)),  # Convert boolean to int
                 int(self.is_weekend(t))]    # Convert boolean to int
                for t in self.historical_data['time']
            ], dtype=np.float32)  # Specify dtype
            
            y = np.array(self.historical_data['vehicle_count'], dtype=np.float32)
            
            self.model.fit(X, y)
            self.is_model_trained = True
            self.save_model()
            return True
        except Exception as e:
            print(f"Training error: {str(e)}")
            return False
        
    def predict_traffic(self, current_time, direction, predict_minutes=15):
        """Predict traffic for the next n minutes"""
        try:
            if not self.is_model_trained:
                print("Model not yet trained, returning default predictions")
                return [
                    {
                        'time': current_time + timedelta(minutes=minute),
                        'predicted_vehicles': 0,
                        'congestion_risk': 'Low'
                    }
                    for minute in range(predict_minutes)
                ]
            
            predictions = []
            for minute in range(predict_minutes):
                future_time = current_time + timedelta(minutes=minute)
                features = self.prepare_features(future_time)
                
                try:
                    pred = max(0, int(self.model.predict(features)[0]))  # Ensure non-negative
                except Exception as model_error:
                    print(f"Prediction error: {str(model_error)}")
                    pred = 0
                
                predictions.append({
                    'time': future_time,
                    'predicted_vehicles': pred,
                    'congestion_risk': self.calculate_congestion_risk(pred)
                })
            
            return predictions
            
        except Exception as e:
            print(f"Traffic prediction error: {str(e)}")
            return [
                {
                    'time': current_time + timedelta(minutes=minute),
                    'predicted_vehicles': 0,
                    'congestion_risk': 'Low'
                }
                for minute in range(predict_minutes)
            ]
        
    def calculate_congestion_risk(self, predicted_vehicles):
        """Calculate congestion risk level"""
        if predicted_vehicles > 20:
            return 'High'
        elif predicted_vehicles > 10:
            return 'Medium'
        return 'Low'
        
    def save_model(self):
        """Save trained model"""
        joblib.dump(self.model, self.model_path)
        
    def load_model(self):
        """Load existing model if available"""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_model_trained = True
                return True
            except Exception as e:
                print(f"Model loading error: {str(e)}")
                self.is_model_trained = False
                return False
        return False

    def get_recommendations(self, predictions):
        """Generate traffic recommendations based on predictions"""
        highest_congestion = max(p['predicted_vehicles'] for p in predictions)
        
        recommendations = []
        if highest_congestion > 20:
            recommendations.append("High congestion expected. Consider alternative routes.")
        if any(p['congestion_risk'] == 'High' for p in predictions):
            peak_time = next(p['time'] for p in predictions if p['congestion_risk'] == 'High')
            recommendations.append(f"Peak congestion expected at {peak_time.strftime('%H:%M')}")
            
        return recommendations
