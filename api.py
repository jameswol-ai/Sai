
from flask import Flask, request, jsonify
import joblib
import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "SAI is running"})

# Load the trained model
model = None
try:
    model = joblib.load('models/model.pkl')
    print("Model loaded successfully")
except Exception as e:
    print(f"Failed to load model: {e}")

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data = request.json
        # Expect OHLCV data
        features = pd.DataFrame([data])
        # Remove timestamp if present
        features = features.drop(['timestamp'], axis=1, errors='ignore')
        
        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0]
        
        return jsonify({
            'prediction': int(prediction),
            'probability_class_0': float(probability[0]),
            'probability_class_1': float(probability[1]),
            'signal': 'BUY' if prediction == 1 else 'SELL'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'timestamp': str(pd.Timestamp.now())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
