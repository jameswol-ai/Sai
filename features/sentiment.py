result = get_news_sentiment("BTC")

if result["status"] == "ok":
    st.success(result["message"])
    st.metric("News Sentiment", f"{result['score']:.2f}")

elif result["status"] == "disabled":
    st.info(result["message"])

else:
    st.warning(result["message"])