import joblib
import os
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
import pandas as pd

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join('features', 'calendar', 'AIs', 'Categorisation_AI', 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'categorization_model.joblib')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.joblib')
DATA_FILE = os.path.join('features', 'calendar', 'AIs', 'Categorisation_AI', 'event_data.csv')

class CategorizationPredictor:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self._load_model_and_vectorizer()

    def _load_model_and_vectorizer(self):
        """Loads the trained model and TF-IDF vectorizer."""
        if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH):
            logger.warning("Custom AI model or vectorizer not found. Please train the model first by running trainer.py.")
            return

        try:
            self.model = joblib.load(MODEL_PATH)
            self.vectorizer = joblib.load(VECTORIZER_PATH)
            logger.info("Custom AI model and vectorizer loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading custom AI model or vectorizer: {e}")
            self.model = None
            self.vectorizer = None

    def predict(self, text: str) -> str | None:
        """
        Predicts the calendar name for a given text using the custom AI model.
        Returns the predicted calendar name or None if the model is not loaded.
        """
        if self.model is None or self.vectorizer is None:
            return None
        
        try:
            text_vec = self.vectorizer.transform([text])
            predicted_calendar_name = self.model.predict(text_vec)[0]
            
            logger.info(f"Custom AI predicted calendar name: '{predicted_calendar_name}' for text: '{text}'")
            return predicted_calendar_name
        except Exception as e:
            logger.error(f"Error during custom AI prediction: {e}")
            return None

if __name__ == '__main__':
    # Example usage:
    # Ensure you have run trainer.py first to create the model files
    logging.basicConfig(level=logging.INFO)
    predictor = CategorizationPredictor()
    if predictor.model:
        test_text = "Meeting with John tomorrow at 3 PM"
        predicted_id = predictor.predict(test_text)
        print(f"Prediction for '{test_text}': {predicted_id}")
    else:
        print("Model not loaded. Please train the model first.")
