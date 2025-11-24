import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
DATA_FILE = os.path.join(BASE_DIR, 'features', 'calendar', 'AIs', 'Categorisation_AI', 'event_data.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'features', 'calendar', 'AIs', 'Categorisation_AI', 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'categorization_model.joblib')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.joblib')

def train_model():
    """
    Trains a text classification model on the event log data.
    """
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        logger.warning("Event log file not found or is empty. Cannot train model.")
        return

    os.makedirs(MODEL_DIR, exist_ok=True)

    # Load data
    df = pd.read_csv(DATA_FILE)
    df.dropna(subset=['original_user_message', 'user_selected_calendar_name'], inplace=True)

    if len(df) < 10: # Need a minimum amount of data to train
        logger.warning(f"Not enough data to train model. Found only {len(df)} samples.")
        return

    # Prepare data
    X = df['original_user_message']
    y = df['user_selected_calendar_name']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Vectorize text
    vectorizer = TfidfVectorizer(stop_words='english', max_df=0.9, min_df=2)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Train model
    model = LinearSVC(class_weight='balanced', dual=False, random_state=42)
    model.fit(X_train_vec, y_train)

    # Evaluate model
    y_pred = model.predict(X_test_vec)
    report = classification_report(y_test, y_pred)
    logger.info(f"Classification Report:\n{report}")

    # Save model and vectorizer
    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    logger.info(f"Model and vectorizer saved to {MODEL_DIR}")

if __name__ == '__main__':
    # Example of how to run the training
    # You would run this script manually from your terminal when you want to retrain the model
    logging.basicConfig(level=logging.INFO)
    train_model()
