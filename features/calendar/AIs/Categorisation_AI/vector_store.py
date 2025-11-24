import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import os
import logging

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join('features', 'calendar', 'AIs', 'Categorisation_AI', 'event_data.csv')
VECTOR_STORE_DIR = os.path.join('features', 'calendar', 'AIs', 'Categorisation_AI', 'vector_store')
VECTORIZER_PATH = os.path.join(VECTOR_STORE_DIR, 'event_vectorizer.joblib')
MATRIX_PATH = os.path.join(VECTOR_STORE_DIR, 'event_matrix.joblib')

def create_vector_store():
    """
    Creates and saves a TF-IDF vector representation of the event data.
    This acts as a simple, file-based vector database.
    """
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        logger.warning("Event log file not found or is empty. Cannot create vector store.")
        return

    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    # Load data
    df = pd.read_csv(DATA_FILE)
    df.dropna(subset=['original_user_message'], inplace=True)
    
    # Use 'original_user_message' as the document text
    documents = df['original_user_message']

    # Create and fit the vectorizer
    vectorizer = TfidfVectorizer(stop_words='english', max_df=0.95, min_df=1)
    tfidf_matrix = vectorizer.fit_transform(documents)

    # Save the vectorizer and the matrix
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(tfidf_matrix, MATRIX_PATH)
    
    logger.info(f"Vector store created and saved to {VECTOR_STORE_DIR}")
    logger.info(f"Shape of TF-IDF matrix: {tfidf_matrix.shape}")

if __name__ == '__main__':
    # Example of how to build the vector store
    logging.basicConfig(level=logging.INFO)
    create_vector_store()
