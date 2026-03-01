from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets

db = SQLAlchemy()

# Association table for Friendships
friendships = db.Table('friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)

# Association table for Equipment
owned_equipment = db.Table('owned_equipment',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('equipment_id', db.Integer, db.ForeignKey('equipment.id'))
)

class Guild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    access_code = db.Column(db.String(10), unique=True, nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    members = db.relationship('User', foreign_keys='User.guild_id', backref='guild', lazy=True)
    leader = db.relationship('User', foreign_keys=[leader_id], backref='led_guilds', lazy=True)

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False) # Weapon, Armor, Potion, Artifact
    effect_type = db.Column(db.String(50), nullable=False) # attack, defense, regen_freeze, xp_boost
    effect_value = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Integer, nullable=False)

class Boss(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    boss_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    base_hp = db.Column(db.Float, nullable=False)
    current_hp = db.Column(db.Float, nullable=False)
    regen_rate = db.Column(db.Float, default=5.0)
    corruption_percent = db.Column(db.Float, default=20.0)
    relapse_count = db.Column(db.Integer, default=0)
    victory_count = db.Column(db.Integer, default=0)
    weakness_multiplier = db.Column(db.Float, default=1.0)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Phase 5: Shadow Fight 2 Bodyguard System
    current_bodyguard_index = db.Column(db.Integer, default=1) # 1-5 Bodyguards, 6=Boss

    # Relationships
    user = db.relationship('User', backref=db.backref('bosses', lazy=True))

class DailyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    assigned_date = db.Column(db.Date, nullable=False)
    coin_reward = db.Column(db.Integer, default=30)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('daily_tasks', lazy=True))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Existing features
    hex_code = db.Column(db.String(6), unique=True, nullable=False)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # RPG / Gamification Stats
    total_points = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)
    current_health = db.Column(db.Float, default=100.0)
    max_health = db.Column(db.Float, default=100.0)
    regen_rate = db.Column(db.Float, default=1.0)
    last_health_update = db.Column(db.DateTime, default=datetime.utcnow)
    attack_stat = db.Column(db.Integer, default=10)
    defense_stat = db.Column(db.Integer, default=5)
    
    # Survey & Progression
    survey_completed = db.Column(db.Boolean, default=False)
    peak_time = db.Column(db.String(50))
    last_coin_gain_date = db.Column(db.Date)
    daily_coins_earned = db.Column(db.Integer, default=0)
    lich_spawned = db.Column(db.Boolean, default=False)

    # Relationships
    friends = db.relationship('User', secondary=friendships,
                              primaryjoin=(friendships.c.user_id == id),
                              secondaryjoin=(friendships.c.friend_id == id),
                              backref=db.backref('friend_of', lazy='dynamic'), lazy='dynamic')
                              
    equipment = db.relationship('Equipment', secondary=owned_equipment, backref=db.backref('owners', lazy='dynamic'), lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.hex_code:
            self.hex_code = secrets.token_hex(3).upper()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AppUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    app_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # e.g., 'Social Media', 'Productivity', 'Entertainment'
    duration_minutes = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # The user requested logs every 3 hours. 
    # This interval_id can help group logs into 3-hour windows.
    # 0: 00-03, 1: 03-06, 2: 06-09, 3: 09-12, 4: 12-15, 5: 15-18, 6: 18-21, 7: 21-24
    interval_id = db.Column(db.Integer, nullable=False)  
