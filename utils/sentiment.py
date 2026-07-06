import numpy as np
import streamlit as st
from config import logger
try:
    from newsapi import NewsApiClient
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news_sentiment():
    if not SENTIMENT_AVAILABLE:
        return None
    try:
        api_key = st.secrets.get("NEWS_API_KEY")
        if not api_key: return None
        api = NewsApiClient(api_key=api_key)
        query = ("East Africa forex OR Uganda shilling OR Kenya shilling OR Tanzania shilling "
                 "OR Rwanda franc OR Burundi franc OR South Sudan pound OR Ethiopia birr")
        articles = api.get_everything(q=query, language='en', sort_by='publishedAt', page_size=10)
        if articles['status'] != 'ok': return None
        sentiments = []
        headlines = []
        for art in articles['articles']:
            text = art['title'] + " " + (art['description'] or "")
            blob = TextBlob(text)
            sentiments.append(blob.sentiment.polarity)
            headlines.append(art['title'])
        avg_sent = np.mean(sentiments) if sentiments else 0
        return {
            "score": round(avg_sent, 3),
            "headlines": headlines[:5],
            "interpretation": "Bullish" if avg_sent > 0.1 else "Bearish" if avg_sent < -0.1 else "Neutral"
        }
    except Exception as e:
        logger.error(f"News sentiment error: {e}")
        return None
