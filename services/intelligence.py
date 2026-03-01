import math
import random
from datetime import datetime, timedelta
from collections import defaultdict

from flask import current_app

from models import db, AppUsage
from services.analytics import calculate_dopamine_score

def get_intelligence_data(user_id):
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)
    
    # 1. Fetch entire 14-day history for the user for comparisons
    recent_logs = AppUsage.query.filter(
        AppUsage.user_id == user_id,
        AppUsage.timestamp >= fourteen_days_ago
    ).order_by(AppUsage.timestamp.asc()).all()

    if not recent_logs:
        return _empty_intelligence_payload()

    # Separate logs by week
    this_week_logs = [log for log in recent_logs if log.timestamp >= seven_days_ago]
    last_week_logs = [log for log in recent_logs if log.timestamp < seven_days_ago]
    
    if not this_week_logs:
        return _empty_intelligence_payload()

    # --- Core Metrics Aggregation Setup ---
    interval_data = defaultdict(lambda: {'prod': 0, 'soc': 0, 'ent': 0, 'total': 0, 'switches': 0, 'last_cat': None})
    hourly_heatmap = defaultdict(lambda: {'prod': 0, 'dist': 0})
    app_minutes = defaultdict(int)
    daily_dopamine = defaultdict(lambda: {'social': 0, 'ent': 0, 'prod': 0, 'total': 0})
    
    total_minutes = 0
    prod_minutes = 0
    social_minutes = 0
    late_night_minutes = 0
    sessions_count = len(this_week_logs)
    
    # Deep Work Tracking
    longest_deep_work = 0
    current_deep_work = 0
    last_prod_time = None
    
    # Time to First Distraction (TTFD)
    ttfd_list = []
    daily_first_prod = {}
    daily_first_soc = {}

    for log in this_week_logs:
        dur = log.duration_minutes
        total_minutes += dur
        app_minutes[log.app_name] += dur
        
        # Hourly Heatmap
        hour_str = log.timestamp.strftime('%H')
        
        # Late Night
        if log.timestamp.hour >= 23 or log.timestamp.hour < 2:
            late_night_minutes += dur

        # Daily Dopamine Tracking
        date_str = log.timestamp.strftime('%Y-%m-%d')
        daily_dopamine[date_str]['total'] += dur

        # TTFD Tracking
        if date_str not in daily_first_prod and log.category == 'Productivity':
            daily_first_prod[date_str] = log.timestamp
        if date_str not in daily_first_soc and (log.category == 'Social Media' or log.category == 'Entertainment'):
            daily_first_soc[date_str] = log.timestamp

        # Interval logic (Burst Index, Switches)
        iid = log.interval_id
        interval = interval_data[iid]
        interval['total'] += dur
        
        if interval['last_cat'] and interval['last_cat'] != log.category:
            interval['switches'] += 1
        interval['last_cat'] = log.category

        # Category logic
        if log.category == 'Productivity':
            prod_minutes += dur
            hourly_heatmap[hour_str]['prod'] += dur
            interval['prod'] += dur
            daily_dopamine[date_str]['prod'] += dur
            
            if last_prod_time and (log.timestamp - last_prod_time).total_seconds() < 3600:
                current_deep_work += dur
            else:
                current_deep_work = dur
            if current_deep_work > longest_deep_work:
                longest_deep_work = current_deep_work
            last_prod_time = log.timestamp
            
        elif log.category == 'Social Media':
            social_minutes += dur
            hourly_heatmap[hour_str]['dist'] += dur
            interval['soc'] += dur
            daily_dopamine[date_str]['social'] += dur
            current_deep_work = 0 # break streak
            
        elif log.category == 'Entertainment':
            hourly_heatmap[hour_str]['dist'] += dur
            interval['ent'] += dur
            daily_dopamine[date_str]['ent'] += dur
            current_deep_work = 0

    # TTFD Calculation
    for date_str in daily_first_prod:
        if date_str in daily_first_soc:
            prod_time = daily_first_prod[date_str]
            soc_time = daily_first_soc[date_str]
            if soc_time > prod_time:
                diff_mins = (soc_time - prod_time).total_seconds() / 60
                ttfd_list.append(diff_mins)
    ttfd = round(sum(ttfd_list) / len(ttfd_list), 1) if ttfd_list else "N/A"

    # Last week productivity
    last_week_prod = sum(log.duration_minutes for log in last_week_logs if log.category == 'Productivity')
    focus_growth = 0
    if last_week_prod > 0:
        focus_growth = round(((prod_minutes - last_week_prod) / last_week_prod) * 100, 1)
    else:
        focus_growth = 100 if prod_minutes > 0 else 0

    # Distraction Burst Index & Block Quality
    total_switches = 0
    total_intervals = len(interval_data)
    total_quality = 0
    prod_intervals = 0
    
    for iid, data in interval_data.items():
        total_switches += data['switches']
        if data['prod'] > 0:
            prod_intervals += 1
            quality = data['prod'] - (5 * data['switches'])
            total_quality += quality

    burst_index = round(total_switches / total_intervals, 1) if total_intervals > 0 else 0
    block_quality = round(total_quality / prod_intervals, 1) if prod_intervals > 0 else 0

    # App Dominance
    top_app = "None"
    app_dominance = 0
    if app_minutes:
        top_app = max(app_minutes, key=app_minutes.get)
        app_dominance = round((app_minutes[top_app] / total_minutes) * 100, 1) if total_minutes > 0 else 0

    # Attention Fragmentation
    active_hours = len(hourly_heatmap)
    fragmentation = round((total_intervals / active_hours), 1) if active_hours > 0 else 0

    # Relapse Risk
    prod_ratio = (prod_minutes / total_minutes) * 100 if total_minutes > 0 else 0
    risk_score = 0
    if social_minutes > 120: risk_score += 2
    if total_switches > 100: risk_score += 2
    if late_night_minutes > 60: risk_score += 2
    if prod_ratio < 40: risk_score += 2
    
    relapse_level = "LOW"
    if risk_score >= 6: relapse_level = "HIGH"
    elif risk_score >= 3: relapse_level = "MEDIUM"

    # Dopamine Stability Index
    daily_scores = []
    for d_data in daily_dopamine.values():
        score = calculate_dopamine_score(d_data['social'], d_data['ent'], d_data['prod'], d_data['total'])
        if score > 0: daily_scores.append(score)
        
    stability_index = 0
    mean_score = 0
    if len(daily_scores) > 1:
        mean_score = sum(daily_scores) / len(daily_scores)
        variance = sum((x - mean_score) ** 2 for x in daily_scores) / len(daily_scores)
        stability_index = round(math.sqrt(variance), 1)
    elif len(daily_scores) == 1:
        mean_score = daily_scores[0]

    # Fill missing heatmap hours
    final_heatmap = {}
    for i in range(24):
        h = str(i).zfill(2)
        final_heatmap[h] = hourly_heatmap.get(h, {'prod': 0, 'dist': 0})

    # -------------
    # PART 2: Algorithms
    # -------------
    
    # Anomaly Detection (Z-Score on today vs 7 day average)
    today_str = now.strftime('%Y-%m-%d')
    today_score = 0
    if today_str in daily_dopamine:
        td = daily_dopamine[today_str]
        today_score = calculate_dopamine_score(td['social'], td['ent'], td['prod'], td['total'])
        
    anomaly_flag = False
    if stability_index > 0 and mean_score > 0:
        z_score = abs(today_score - mean_score) / stability_index
        if z_score > 2.0: # 2 standard deviations
            anomaly_flag = True

    # Clustering (Heuristic K-Means Archetype)
    archetype = "Balanced User"
    if prod_ratio > 60 and burst_index < 1.0:
        archetype = "Focus Monk"
    elif burst_index > 2.5:
        archetype = "Chaotic Multitasker"
    elif late_night_minutes > 120:
        archetype = "Night Scroller"
    elif focus_growth > 50 and mean_score > 50:
        archetype = "Weekend Warrior"

    # Correlation Engine (Pearson)
    # Compare daily: dopamine score vs late night, dopamine score vs switches
    x_late = []
    x_switches = []
    y_scores = []
    
    # Re-calculate daily stats for correlation
    daily_late = defaultdict(int)
    daily_switches = defaultdict(int)
    
    for log in this_week_logs:
        d_str = log.timestamp.strftime('%Y-%m-%d')
        if log.timestamp.hour >= 23 or log.timestamp.hour < 2:
            daily_late[d_str] += log.duration_minutes
            
    for log in this_week_logs:
        iid = log.interval_id
        d_str = log.timestamp.strftime('%Y-%m-%d')
        # Simplified associative switch estimation per day
        # Just use log count as proxy for activity
        daily_switches[d_str] += 1
        
    for i, d_str in enumerate(daily_dopamine.keys()):
        d_data = daily_dopamine[d_str]
        score = calculate_dopamine_score(d_data['social'], d_data['ent'], d_data['prod'], d_data['total'])
        y_scores.append(score)
        x_late.append(daily_late.get(d_str, 0))
        x_switches.append(daily_switches.get(d_str, 0))

    def pearson_corr(x, y):
        n = len(x)
        if n < 2: return 0
        sum_x, sum_y = sum(x), sum(y)
        sum_x2, sum_y2 = sum(i*i for i in x), sum(i*i for i in y)
        sum_xy = sum(x[i]*y[i] for i in range(n))
        numerator = (n * sum_xy) - (sum_x * sum_y)
        denom_x = (n * sum_x2) - (sum_x ** 2)
        denom_y = (n * sum_y2) - (sum_y ** 2)
        if denom_x <= 0 or denom_y <= 0: return 0
        return numerator / math.sqrt(denom_x * denom_y)

    corr_late = round(pearson_corr(x_late, y_scores), 2)
    corr_switches = round(pearson_corr(x_switches, y_scores), 2)
    
    correlations = []
    if abs(corr_late) > 0.4:
        correlations.append({"name": "Late Night vs Dopamine Output", "value": corr_late, "interpretation": "Strong link between night usage and dopamine spikes."})
    if abs(corr_switches) > 0.4:
        correlations.append({"name": "Switching vs Dopamine Score", "value": corr_switches, "interpretation": "Context switching heavily influences your score."})
    if not correlations:
         correlations.append({"name": "No strong correlations", "value": 0, "interpretation": "Metrics are relatively independent this week."})

    # AI Insight Generator (Rule-based)
    insight_text = ""
    if archetype == "Focus Monk":
        insight_text = f"Your behavioral profile aligns with a <b>Focus Monk</b>. You maintain high productivity ({round(prod_ratio)}%) and low context switching. Keep prioritizing deep work. "
    elif archetype == "Chaotic Multitasker":
        insight_text = f"You are exhibiting <b>Chaotic Multitasking</b>. With a Burst Index of {burst_index}, you switch contexts too often, draining cognitive load. "
    elif archetype == "Night Scroller":
        insight_text = f"Warning: <b>Night Scroller</b> archetype detected. Your late-night usage ({late_night_minutes} min) is sabotaging your circadian rhythm. "
    else:
        insight_text = f"You maintain a balanced profile. "

    if anomaly_flag:
        insight_text += "<b>⚠️ Anomaly Detected:</b> Today's usage significantly deviates from your 7-day baseline. Did something break your routine? "
        
    if relapse_level == "HIGH":
        insight_text += "Action required: High relapse risk detected. Immediately trigger a digital detox protocol."
    else:
        insight_text += "Your dopamine stability is within acceptable thresholds."

    insight_action_1 = "Implement a strict 23:00 screen bedtime to reduce nocturnal dopamine spikes." if late_night_minutes > 30 else "Continue protecting your deep work blocks by silencing notifications."
    insight_action_2 = "Batch your social media usage into a single 30-minute block to improve your Burst Index." if burst_index > 1.5 else "Try to extend your average Deep Work record by 10 minutes next session."

    return {
        "deep_work_record": longest_deep_work,
        "burst_index": burst_index,
        "scroll_velocity": sessions_count,
        "late_night": late_night_minutes,
        "focus_growth": focus_growth,
        "top_app": top_app,
        "app_dominance": app_dominance,
        "fragmentation": fragmentation,
        "heatmap": final_heatmap,
        "relapse_risk": relapse_level,
        "stability_index": stability_index,
        "block_quality": block_quality,
        "ttfd": ttfd,
        "anomaly": anomaly_flag,
        "archetype": archetype,
        "correlations": correlations,
        "ai_insight_text": insight_text,
        "ai_action_1": insight_action_1,
        "ai_action_2": insight_action_2
    }


def _empty_intelligence_payload():
    return {
        "deep_work_record": 0, "burst_index": 0, "scroll_velocity": 0, "late_night": 0,
        "focus_growth": 0, "top_app": "N/A", "app_dominance": 0, "fragmentation": 0,
        "heatmap": {str(i).zfill(2): {'prod': 0, 'dist': 0} for i in range(24)},
        "relapse_risk": "LOW", "stability_index": 0.0, "block_quality": 0, "ttfd": "N/A",
        "anomaly": False, "archetype": "New User", "correlations": [],
        "ai_insight_text": "Not enough data to generate an intelligence profile.",
        "ai_action_1": "Log more app usage.", "ai_action_2": "Stay focused."
    }
