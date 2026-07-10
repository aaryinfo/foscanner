from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from email_alerts import send_email_alert
from database import get_session, AstroDailyScore, TopStockTurnDate
from market_modules.scoring import calculate_daily_astro_score, get_top_5_turn_date_stocks
from market_modules.data_fetcher import get_all_tickers, get_current_price
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_daily_astro_job():
    logger.info("Running daily astro computation job...")
    today = datetime.datetime.utcnow()
    
    # 1. Compute Astro Score
    score_report = calculate_daily_astro_score(today)
    
    # 2. Get Top 5 Turn Date Stocks
    tickers = get_all_tickers()
    # Mock current prices for scheduling or fetch real ones
    # Fetching real prices might take time, so we iterate
    current_prices = {}
    for t in tickers:
        p = get_current_price(t)
        if p:
            current_prices[t] = p
            
    top_5 = get_top_5_turn_date_stocks(today, tickers, current_prices)
    
    # 3. Save to DB
    session = get_session()
    try:
        # Check if already exists for today
        existing = session.query(AstroDailyScore).filter_by(date=today.date()).first()
        if not existing:
            new_score = AstroDailyScore(
                date=today.date(),
                score=score_report['score'],
                bias=score_report['bias'],
                nakshatra=score_report['nakshatra'],
                tithi=score_report['tithi'],
                eclipse=score_report['eclipse'],
                numerology_vib=score_report['numerology']
            )
            session.add(new_score)
            
            # Save top 5
            for item in top_5:
                session.add(TopStockTurnDate(
                    date=today.date(),
                    ticker=item['ticker'],
                    price=item['price'],
                    orb=item['orb'],
                    alignment=item['alignment']
                ))
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving to DB: {e}")
    finally:
        session.close()

    # 4. Send Email Alert
    html_body = f"""
    <h2>AstroMarket Pro - Daily Weather Report</h2>
    <p><b>Date:</b> {today.strftime('%Y-%m-%d')}</p>
    <p><b>Astro Bias Score:</b> {score_report['score']} ({score_report['bias']})</p>
    <p><b>Nakshatra:</b> {score_report['nakshatra']} ({score_report['nakshatra_tag']})</p>
    <p><b>Tithi:</b> {score_report['tithi']}</p>
    <p><b>Eclipse Status:</b> {score_report['eclipse']}</p>
    <br>
    <h3>Top 5 Stocks with Turn Dates</h3>
    <ul>
    """
    for s in top_5:
        html_body += f"<li><b>{s['ticker']}</b> - Price: {s['price']} | Alignment: {s['alignment']} (Orb: {s['orb']:.2f}°)</li>"
    html_body += "</ul>"
    
    send_email_alert(
        subject=f"AstroMarket Weather - {score_report['bias']}",
        body=html_body,
        is_html=True
    )
    logger.info("Daily astro job completed.")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule to run every day at 8:00 AM IST (which is 02:30 AM UTC)
    # Since Railway runs in UTC, we use UTC time.
    scheduler.add_job(run_daily_astro_job, 'cron', hour=2, minute=30)
    scheduler.start()
    logger.info("Scheduler started.")

if __name__ == "__main__":
    # Test run
    run_daily_astro_job()
