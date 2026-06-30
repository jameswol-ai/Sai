import os
import streamlit as st

def get_news_sentiment(symbol="BTC"):
    """
    Returns:
        {
            "status": "ok" | "disabled" | "error",
            "score": float,
            "articles": list,
            "message": str
        }
    """

    try:
        from newsapi import NewsApiClient
        from textblob import TextBlob

    except ImportError:
        return {
            "status": "disabled",
            "score": 0,
            "articles": [],
            "message": "Install: pip install newsapi-python textblob"
        }

    api_key = os.getenv("NEWS_API_KEY")

    if not api_key:
        return {
            "status": "disabled",
            "score": 0,
            "articles": [],
            "message": "NEWS_API_KEY not configured."
        }

    try:
        newsapi = NewsApiClient(api_key=api_key)

        response = newsapi.get_everything(
            q=symbol,
            language="en",
            sort_by="publishedAt",
            page_size=10,
        )

        articles = response.get("articles", [])

        sentiments = []

        for article in articles:
            text = (
                (article.get("title") or "")
                + " "
                + (article.get("description") or "")
            )

            polarity = TextBlob(text).sentiment.polarity
            sentiments.append(polarity)

        score = sum(sentiments) / len(sentiments) if sentiments else 0

        return {
            "status": "ok",
            "score": score,
            "articles": articles,
            "message": f"{len(articles)} articles analyzed."
        }

    except Exception as e:
        return {
            "status": "error",
            "score": 0,
            "articles": [],
            "message": str(e)
        }