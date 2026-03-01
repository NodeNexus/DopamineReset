from app import app, db
from models import User, Equipment

with app.app_context():
    db.create_all()
    # Create a default user if none exists
    if not User.query.first():
        default_user = User(username="default_user")
        default_user.set_password("password") # Provide a default password
        db.session.add(default_user)
        db.session.commit()
        print("Default user created.")
        
    # Seed armory if empty
    if not Equipment.query.first():
        items = [
            Equipment(name='Rusty Spoon of Discipline', type='Weapon', effect_type='attack', effect_value=5, cost=30),
            Equipment(name='Sword of Focus', type='Weapon', effect_type='attack', effect_value=15, cost=100),
            Equipment(name='Aegis of Willpower', type='Armor', effect_type='defense', effect_value=10, cost=85),
            Equipment(name='Cloak of Serenity', type='Armor', effect_type='defense', effect_value=25, cost=180),
            Equipment(name='Frozen Hourglass', type='Artifact', effect_type='regen_freeze', effect_value=1, cost=500),
            Equipment(name='Scroll of Wisdom', type='Artifact', effect_type='xp_boost', effect_value=1.5, cost=300)
        ]
        for item in items:
            db.session.add(item)
        db.session.commit()
        print("Armory has been automatically seeded.")
