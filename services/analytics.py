import math
from collections import defaultdict
from models import AppUsage, db
from sqlalchemy import func
from datetime import datetime, timedelta

def calculate_dopamine_score(social_dur, ent_dur, prod_dur, total_minutes):
    if total_minutes == 0: return 0
    return (social_dur * 1.5 + ent_dur * 1.0 + prod_dur * 0.2) / total_minutes * 100

def get_behavioral_patterns(user_id):
    """
    Massively expanded Advanced Behavioral Intelligence Analytics.
    """
    now = datetime.utcnow()
    last_7_days = now - timedelta(days=7)
    last_14_days = now - timedelta(days=14)

    # Base Queries for last 7 days
    base_query = db.session.query(AppUsage).filter(
        AppUsage.user_id == user_id, 
        AppUsage.timestamp >= last_7_days
    ).order_by(AppUsage.timestamp.asc())
    
    logs = base_query.all()
    
    if not logs:
        return _empty_analytics_payload()

    total_minutes = sum(log.duration_minutes for log in logs)
    
    # 1. Category Breakdown
    category_data = defaultdict(int)
    for log in logs:
        category_data[log.category] += log.duration_minutes
        
    social_dur = category_data.get('Social Media', 0)
    ent_dur = category_data.get('Entertainment', 0)
    prod_dur = category_data.get('Productivity', 0)
    
    dopamine_score = calculate_dopamine_score(social_dur, ent_dur, prod_dur, total_minutes)
    productivity_ratio = int((prod_dur / total_minutes) * 100) if total_minutes > 0 else 0

    # 2. Hourly Distribution (Peak Window) & Heatmap Data
    intervals = ["00-03", "03-06", "06-09", "09-12", "12-15", "15-18", "18-21", "21-24"]
    interval_data = defaultdict(int)
    
    # Heatmap setup: 24 arrays (one per hour) mapping hour -> {Productivity: dur, Distraction: dur}
    heatmap_data = {str(hour).zfill(2): {'prod': 0, 'dist': 0} for hour in range(24)}
    
    # Advanced Iteration logic
    longest_deep_work = 0
    current_deep_work = 0
    
    late_night_minutes = 0
    total_distinct_intervals = set()
    
    # Group logs by day and interval to detect bursts and context switches
    blocks = defaultdict(list)
    daily_productivity = defaultdict(int)
    daily_social_first = defaultdict(lambda: None)
    daily_prod_first = defaultdict(lambda: None)
    
    for log in logs:
        interval_data[intervals[log.interval_id]] += log.duration_minutes
        total_distinct_intervals.add((log.timestamp.date(), log.interval_id))
        
        # Heatmap (Using timestamp hour)
        hour_str = str(log.timestamp.hour).zfill(2)
        if log.category == 'Productivity':
            heatmap_data[hour_str]['prod'] += log.duration_minutes
            current_deep_work += log.duration_minutes
            if current_deep_work > longest_deep_work:
                longest_deep_work = current_deep_work
        else:
            heatmap_data[hour_str]['dist'] += log.duration_minutes
            current_deep_work = 0 # Break deep work
            
        # Late Night Index (23:00 - 02:00)
        hour = log.timestamp.hour
        if hour >= 23 or hour < 2:
            late_night_minutes += log.duration_minutes
            
        # Group by Date + Interval
        date_str = log.timestamp.strftime("%Y-%m-%d")
        blocks[(date_str, log.interval_id)].append(log)
        
        # Track Time to First Distraction per day
        if log.category == 'Productivity' and daily_prod_first[date_str] is None:
            daily_prod_first[date_str] = log.timestamp
        if log.category == 'Social Media' and daily_social_first[date_str] is None:
            daily_social_first[date_str] = log.timestamp

    peak_interval_id = max(interval_data.items(), key=lambda x: x[1])[0] if interval_data else "N/A"

    # Context Switch Penalty & Burst Index & Quality Score
    context_switch_count = 0
    burst_intensity_score = 0
    work_block_quality_sum = 0
    prod_intervals_count = 0
    sessions_count = len(logs) # Scroll velocity proxy (total small sessions)
    
    for block_key, block_logs in blocks.items():
        cats = [l.category for l in block_logs]
        unique_cats = set(cats)
        
        # Distraction Burst Index (how many times they switched categories in 3 hours)
        switches_in_interval = 0
        for i in range(1, len(cats)):
            if cats[i] != cats[i-1]:
                switches_in_interval += 1
                
        burst_intensity_score += switches_in_interval
        
        if 'Productivity' in unique_cats and ('Social Media' in unique_cats or 'Entertainment' in unique_cats):
            context_switch_count += 1
            
        # Work Block Quality
        prod_time_in_block = sum(l.duration_minutes for l in block_logs if l.category == 'Productivity')
        if prod_time_in_block > 0:
            quality = max(0, prod_time_in_block - (5 * switches_in_interval))
            work_block_quality_sum += quality
            prod_intervals_count += 1

    avg_block_quality = round(work_block_quality_sum / prod_intervals_count, 1) if prod_intervals_count > 0 else 0
    
    # 5. Most Addictive App & Dominance Ratio
    top_app_record = db.session.query(
        AppUsage.app_name, func.sum(AppUsage.duration_minutes).label('total')
    ).filter(AppUsage.user_id == user_id, AppUsage.timestamp >= last_7_days).group_by(AppUsage.app_name).order_by(db.desc('total')).first()
    
    top_app = top_app_record[0] if top_app_record else "None"
    top_app_mins = top_app_record[1] if top_app_record else 0
    app_dominance_ratio = int((top_app_mins / total_minutes) * 100) if total_minutes > 0 else 0

    # 6. Weekly Focus Growth (% change)
    last_week_query = db.session.query(func.sum(AppUsage.duration_minutes)).filter(
        AppUsage.user_id == user_id,
        AppUsage.category == 'Productivity',
        AppUsage.timestamp >= last_14_days,
        AppUsage.timestamp < last_7_days
    ).scalar() or 0
    
    focus_growth_pct = 0
    if last_week_query > 0:
        focus_growth_pct = int(((prod_dur - last_week_query) / last_week_query) * 100)
    elif last_week_query == 0 and prod_dur > 0:
        focus_growth_pct = 100

    # 7. Attention Fragmentation Score (Normalized)
    # Distinct active 3-hour blocks / total possible blocks (8 per day * 7 days = 56)
    fragmentation_score = int((len(total_distinct_intervals) / 56.0) * 100)

    # 8. Time to First Distraction (Average)
    ttfd_sum = 0
    ttfd_days = 0
    for date_str, prod_time in daily_prod_first.items():
        soc_time = daily_social_first[date_str]
        if prod_time and soc_time and soc_time > prod_time:
            delta = (soc_time - prod_time).total_seconds() / 60.0
            ttfd_sum += delta
            ttfd_days += 1
            
    avg_ttfd = int(ttfd_sum / ttfd_days) if ttfd_days > 0 else "N/A"

    # 9. Relapse Risk Indicator
    relapse_risk = "LOW"
    if social_dur > (2 * 60 * 7): # More than 2 hours a day avg
        relapse_risk = "MEDIUM"
        if context_switch_count > 10 and late_night_minutes > 120:
             relapse_risk = "HIGH"

    # 10. Dopamine Stability Index (Standard Deviation of daily scores)
    daily_dopamine = defaultdict(lambda: {'social': 0, 'ent': 0, 'prod': 0, 'total': 0})
    for log in logs:
        date_str = log.timestamp.strftime("%Y-%m-%d")
        if log.category == 'Social Media': daily_dopamine[date_str]['social'] += log.duration_minutes
        elif log.category == 'Entertainment': daily_dopamine[date_str]['ent'] += log.duration_minutes
        elif log.category == 'Productivity': daily_dopamine[date_str]['prod'] += log.duration_minutes
        daily_dopamine[date_str]['total'] += log.duration_minutes
        
    daily_scores = []
    for d_data in daily_dopamine.values():
        score = calculate_dopamine_score(d_data['social'], d_data['ent'], d_data['prod'], d_data['total'])
        if score > 0: daily_scores.append(score)
        
    stability_index = 0
    if len(daily_scores) > 1:
        mean_score = sum(daily_scores) / len(daily_scores)
        variance = sum((x - mean_score) ** 2 for x in daily_scores) / len(daily_scores)
        stability_index = round(math.sqrt(variance), 1)

    return {
        "category_data": dict(category_data),
        "hourly_data": dict(interval_data),
        "dopamine_score": round(dopamine_score, 1),
        "peak_window": peak_interval_id,
        "total_time": total_minutes,
        "productivity_ratio": productivity_ratio,
        "top_app": top_app,
        "context_switches": context_switch_count,
        "deep_work_record": longest_deep_work,
        "late_night_minutes": late_night_minutes,
        "app_dominance": app_dominance_ratio,
        "focus_growth": focus_growth_pct,
        "fragmentation": fragmentation_score,
        "burst_intensity": burst_intensity_score,
        "block_quality": avg_block_quality,
        "ttfd": avg_ttfd,
        "relapse_risk": relapse_risk,
        "stability_index": stability_index,
        "heatmap": heatmap_data,
        "sessions_count": sessions_count
    }

def _empty_analytics_payload():
    return {
        "category_data": {}, "hourly_data": {}, "dopamine_score": 0, "peak_window": "N/A",  "total_time": 0, "productivity_ratio": 0,
        "top_app": "N/A", "context_switches": 0, "deep_work_record": 0, "late_night_minutes": 0, "app_dominance": 0,
        "focus_growth": 0, "fragmentation": 0, "burst_intensity": 0, "block_quality": 0, "ttfd": "N/A", "relapse_risk": "LOW",
        "stability_index": 0, "heatmap": {str(i).zfill(2): {'prod': 0, 'dist': 0} for i in range(24)}, "sessions_count": 0
    }

def get_daily_trends(user_id, days=7):
    """
    Gets total usage per day for the last X days.
    """
    today = datetime.utcnow().date()
    trends = []
    for i in range(days):
        d = today - timedelta(days=i)
        usage = db.session.query(func.sum(AppUsage.duration_minutes)).filter(
            AppUsage.user_id == user_id,
            func.date(AppUsage.timestamp) == d
        ).scalar() or 0
        trends.append({"date": d.strftime("%Y-%m-%d"), "minutes": usage})
    
    return trends[::-1] # Return in chronological order

def generate_pseudo_ai_insights(user_id):
    """
    Generates jargon-heavy, complex-sounding insights based on the user's hardcoded stats.
    Makes it seem like a sophisticated AI is analyzing their soul.
    """
    patterns = get_behavioral_patterns(user_id)
    
    if patterns["total_time"] == 0:
        return [
            "Initializing Neural Behavioral Scan... [FAILED]",
            "Insufficient temporal data to establish limbic baseline.",
            "Recommendation: Calibrate system with minimum 24h usage telemetry."
        ]

    insights = []
    
    # Productivity vs Distraction Matrix
    if patterns["productivity_ratio"] > 50:
        insights.append(f"Cognitive Efficiency Quotient is operating at {patterns['productivity_ratio']}%. Frontal lobe engagement indicates sustained hyper-focus vectors.")
    else:
        distraction_ratio = 100 - patterns["productivity_ratio"]
        insights.append(f"Warning: Amygdala hijack detected. Cognitive bandwidth is {distraction_ratio}% fragmented by instant-gratification loops.")
        
    # App Dominance and Fragmentation
    if patterns["app_dominance"] > 40:
        insights.append(f"Hyper-fixation Anomaly located: '{patterns['top_app']}' monopolizes {patterns['app_dominance']}% of total attentional resources. Neural pathways risk over-calcification.")
    
    if patterns["fragmentation"] > 70:
        insights.append(f"Attention Slicing Index critical ({patterns['fragmentation']}%). The subject is exhibiting chronic task-switching, degrading the deep-work myelination process.")
    
    # Peak Window Analysis
    peak = patterns["peak_window"]
    if peak != "N/A":
        insights.append(f"Circadian Rhythm Alignment: Maximum cortical output isolated between {peak} hours. Suggesting biological priming for high-stakes algorithmic tasks during this delta.")

    # Late Night / Relapse
    if patterns["late_night_minutes"] > 120:
        insights.append(f"Nocturnal Prefrontal Bypass: {patterns['late_night_minutes']} minutes of unauthorized screen exposure post-23:00. Melatonin synthesis is severely compromised.")
        
    if patterns["relapse_risk"] == "HIGH":
        insights.append("CRITICAL: Predictive Behavioral Modeling anticipates an imminent Dopaminergic Relapse Event (Probability: 87.4%). Immediate environmental intervention required.")
        
    insights.append("Final Assessment: System recommends rapid recalibration of dopamine-seeking heuristic algorithms.")
    
    return insights

