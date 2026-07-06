def bot_loop(queue_obj, stop_event):
    logger.info("Bot thread started.")
    while not stop_event.is_set():
        try:
            trades = run_bot()   # now returns a list
            for trade_info in trades:
                queue_obj.put(trade_info)
                # Telegram alert if enabled and signal strong
                with BOT_CONFIG["lock"]:
                    if BOT_CONFIG.get("alert_signals"):
                        thresh = st.session_state.alert_threshold
                        if trade_info["trade"] in ("BUY", "SELL"):
                            send_telegram(
                                f"🤖 Bot signal: {trade_info['trade']} {trade_info['symbol']} "
                                f"@ {trade_info['price']:.2f} (units: {trade_info['amount']})"
                            )
        except Exception as e:
            error_data = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "error": str(e)}
            queue_obj.put(error_data)
            logger.exception("Bot loop error")
            with BOT_CONFIG["lock"]:
                if BOT_CONFIG["alert_errors"]:
                    send_telegram(f"🚨 Bot error: {e}")
            time.sleep(5)
            continue
        time.sleep(5)
    logger.info("Bot thread exited.")
