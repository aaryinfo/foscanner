from flask import Flask, render_template, jsonify
import datetime
from scheduler import start_scheduler, run_daily_astro_job
from database import init_db, get_session, AstroDailyScore, TopStockTurnDate
from market_modules.scoring import calculate_daily_astro_score

app = Flask(__name__)

# Initialize DB
init_db()

# Start background scheduler
start_scheduler()

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/today")
def get_today_data():
    session = get_session()
    today = datetime.date.today()
    
    score_record = session.query(AstroDailyScore).filter_by(date=today).first()
    top_stocks = session.query(TopStockTurnDate).filter_by(date=today).all()
    
    if not score_record:
        # If today's job hasn't run yet, calculate it on the fly (for demo/fallback purposes)
        # Note: we don't recalculate top 5 stocks here to avoid long loading times.
        live_report = calculate_daily_astro_score(datetime.datetime.utcnow())
        score_data = {
            "date": live_report['date'],
            "score": live_report['score'],
            "bias": live_report['bias'],
            "nakshatra": live_report['nakshatra'],
            "tithi": live_report['tithi'],
            "eclipse": live_report['eclipse'],
            "numerology_vib": live_report['numerology']
        }
    else:
        score_data = {
            "date": score_record.date.strftime("%Y-%m-%d"),
            "score": score_record.score,
            "bias": score_record.bias,
            "nakshatra": score_record.nakshatra,
            "tithi": score_record.tithi,
            "eclipse": score_record.eclipse,
            "numerology_vib": score_record.numerology_vib
        }
        
    stocks_data = [
        {
            "ticker": s.ticker,
            "price": s.price,
            "orb": s.orb,
            "alignment": s.alignment
        } for s in top_stocks
    ]
    
    session.close()
    
    return jsonify({
        "score_data": score_data,
        "top_stocks": stocks_data
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
