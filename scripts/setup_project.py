import os
import sys
import random
from datetime import datetime, timedelta

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db, User, AppUsage, Equipment

def seed_project():
    with app.app_context():
        print("Initializing database...")
        db.create_all()

        # Seed Equipment
        print("Checking equipment...")
        if Equipment.query.first():
            print("Equipment already seeded. Skipping.")
        else:
            print("Seeding equipment...")
            items = [
                Equipment(name='Rusty Spoon of Discipline', type='Weapon', effect_type='attack', effect_value=5, cost=30),
                Equipment(name='Sword of Focus', type='Weapon', effect_type='attack', effect_value=15, cost=100),
                Equipment(name='Aegis of Willpower', type='Armor', effect_type='defense', effect_value=10, cost=85),
                Equipment(name='Cloak of Serenity', type='Armor', effect_type='defense', effect_value=25, cost=180),
                Equipment(name='Frozen Hourglass', type='Artifact', effect_type='regen_freeze', effect_value=1, cost=500),
                Equipment(name='Scroll of Wisdom', type='Artifact', effect_type='xp_boost', effect_value=1.5, cost=300)
            ]
            db.session.bulk_save_objects(items)
            db.session.commit()
            print("Equipment successfully seeded.")

        # Seed initial test user if none exists
        print("Checking for existing users...")
        if User.query.first():
            print("Database already contains users. Skipping demo data seeding.")
        else:
            print("Seeding initial demo user data...")
            users_info = [
                {"username": "Admin", "streak": 15, "points": 2000, "personality": "Balanced"},
                {"username": "DemoUser", "streak": 2, "points": 150, "personality": "Distracted"}
            ]

            apps_config = [
                ("Instagram", "Social Media"),
                ("TikTok", "Social Media"),
                ("YouTube", "Entertainment"),
                ("VS Code", "Productivity"),
                ("Notion", "Productivity")
            ]

            for u_info in users_info:
                user = User(
                    username=u_info["username"],
                    current_streak=u_info["streak"],
                    total_points=u_info["points"]
                )
                user.set_password('password')
                db.session.add(user)
                db.session.flush()

                start_date = datetime.utcnow() - timedelta(days=7)
                for d in range(8):
                    current_day = start_date + timedelta(days=d)
                    
                    if u_info["personality"] == "Balanced":
                        prob_social = 0.4
                        prob_prod = 0.5
                    else:
                        prob_social = 0.7
                        prob_prod = 0.1

                    for interval in range(8):
                        num_apps = random.randint(1, 3)
                        for _ in range(num_apps):
                            rand = random.random()
                            if rand < prob_social:
                                app_name, cat = random.choice([a for a in apps_config if a[1] == "Social Media"])
                                dur = random.randint(30, 60)
                            elif rand < prob_social + prob_prod:
                                app_name, cat = random.choice([a for a in apps_config if a[1] == "Productivity"])
                                dur = random.randint(20, 90)
                            else:
                                app_name, cat = random.choice([a for a in apps_config if a[1] == "Entertainment"])
                                dur = random.randint(30, 120)

                            usage = AppUsage(
                                user_id=user.id,
                                app_name=app_name,
                                category=cat,
                                duration_minutes=dur,
                                timestamp=current_day.replace(hour=interval*3, minute=random.randint(0, 59)),
                                interval_id=interval
                            )
                            db.session.add(usage)
            
            db.session.commit()
            print("Demo users successfully generated.")

        print("\nSetup Complete! Project is ready to run.")

if __name__ == "__main__":
    seed_project()
