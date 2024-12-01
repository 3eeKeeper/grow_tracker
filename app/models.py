from app.extensions import db, login_manager
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import base64
import os

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    phone_number = db.Column(db.String(15), unique=True, nullable=True)
    notifications_enabled = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    plants = db.relationship('Plant', backref='owner', lazy='dynamic')
    chat_messages = db.relationship('ChatMessage', backref='author', lazy='dynamic')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_last_seen(self):
        self.last_seen = datetime.utcnow()
        self.is_online = True
        db.session.commit()

    def set_offline(self):
        self.is_online = False
        db.session.commit()

    def update_user_online_status(self, is_online):
        """Update user's online status."""
        self.is_online = is_online
        self.last_seen = datetime.utcnow()
        db.session.commit()

# Plant monitoring association table
plant_monitoring = db.Table('plant_monitoring',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('plant_id', db.Integer, db.ForeignKey('plant.id'), primary_key=True)
)

class Plant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    strain = db.Column(db.String(64))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_group_grow = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=False)
    profile_image_id = db.Column(db.Integer, db.ForeignKey('plant_image.id'), nullable=True)
    
    # Archive fields
    is_archived = db.Column(db.Boolean, default=False)
    archive_date = db.Column(db.DateTime, nullable=True)
    archive_reason = db.Column(db.String(20), nullable=True)  # 'harvested' or 'died'
    archive_notes = db.Column(db.Text, nullable=True)
    
    # Growth tracking
    current_stage_id = db.Column(db.Integer, db.ForeignKey('growth_stage.id'), nullable=True)
    last_growth_update = db.Column(db.DateTime)
    target_harvest_date = db.Column(db.DateTime)
    
    # Relationships
    notes = db.relationship('Note', backref='plant', lazy='dynamic', cascade='all, delete-orphan')
    waterings = db.relationship('Watering', backref='plant', lazy='dynamic', cascade='all, delete-orphan')
    images = db.relationship('PlantImage', 
                           foreign_keys='PlantImage.plant_id',
                           backref='plant', 
                           lazy='dynamic', 
                           cascade='all, delete-orphan')
    profile_image = db.relationship('PlantImage',
                                  foreign_keys=[profile_image_id],
                                  post_update=True)
    milestones = db.relationship('Milestone', backref='plant', lazy='dynamic', cascade='all, delete-orphan')
    followers = db.relationship('PlantFollower', backref='plant', lazy='dynamic', cascade='all, delete-orphan')
    
    def current_growth_stage(self):
        """Get the current growth stage"""
        return GrowthStage.query.get(self.current_stage_id)
    
    def advance_growth_stage(self, stage_name, notes=None):
        """Advance to the next growth stage"""
        # End current stage if exists
        current = self.current_growth_stage()
        if current:
            current.end_date = datetime.utcnow()
        
        # Get stage defaults
        defaults = GrowthStage.get_default_stages().get(stage_name, {})
        
        # Create new stage
        new_stage = GrowthStage(
            plant_id=self.id,
            stage_name=stage_name,
            notes=notes,
            **{k: v for k, v in defaults.items() if k != 'duration_days'}
        )
        
        db.session.add(new_stage)
        self.current_stage_id = new_stage.id
        self.last_growth_update = datetime.utcnow()
        
        # Update target harvest date
        if stage_name == 'flowering':
            self.target_harvest_date = datetime.utcnow() + timedelta(days=70)
        
        db.session.commit()
        return new_stage
    
    def get_growth_summary(self):
        """Get a summary of plant growth data"""
        latest_data = GrowthData.query.filter_by(plant_id=self.id).order_by(
            GrowthData.timestamp.desc()
        ).first()
        
        current_stage = self.current_growth_stage()
        days_in_stage = None
        if current_stage:
            days_in_stage = (datetime.utcnow() - current_stage.start_date).days
        
        summary = {
            'current_stage': current_stage.stage_name if current_stage else None,
            'days_in_stage': days_in_stage,
            'age_days': (datetime.utcnow() - self.start_date).days,
            'health_score': latest_data.health_score if latest_data else None,
            'growth_rate': latest_data.growth_rate if latest_data else None,
            'height': latest_data.height if latest_data else None,
            'target_harvest': self.target_harvest_date
        }
        
        return summary
    
    def get_stage_recommendations(self):
        """Get recommendations based on current growth stage"""
        stage = self.current_growth_stage()
        if not stage:
            return None
            
        latest_data = GrowthData.query.filter_by(plant_id=self.id).order_by(
            GrowthData.timestamp.desc()
        ).first()
        
        recommendations = []
        
        if latest_data:
            if latest_data.temperature < stage.ideal_temp_low:
                recommendations.append(
                    f"🌡️ Temperature is low ({latest_data.temperature}°C). "
                    f"Increase to {stage.ideal_temp_low}-{stage.ideal_temp_high}°C"
                )
            elif latest_data.temperature > stage.ideal_temp_high:
                recommendations.append(
                    f"🌡️ Temperature is high ({latest_data.temperature}°C). "
                    f"Decrease to {stage.ideal_temp_low}-{stage.ideal_temp_high}°C"
                )
                
            if latest_data.humidity < stage.ideal_humidity_low:
                recommendations.append(
                    f"💧 Humidity is low ({latest_data.humidity}%). "
                    f"Increase to {stage.ideal_humidity_low}-{stage.ideal_humidity_high}%"
                )
            elif latest_data.humidity > stage.ideal_humidity_high:
                recommendations.append(
                    f"💧 Humidity is high ({latest_data.humidity}%). "
                    f"Decrease to {stage.ideal_humidity_low}-{stage.ideal_humidity_high}%"
                )
                
            if latest_data.ph_level < stage.ideal_ph_low:
                recommendations.append(
                    f"⚗️ pH is low ({latest_data.ph_level}). "
                    f"Adjust to {stage.ideal_ph_low}-{stage.ideal_ph_high}"
                )
            elif latest_data.ph_level > stage.ideal_ph_high:
                recommendations.append(
                    f"⚗️ pH is high ({latest_data.ph_level}). "
                    f"Adjust to {stage.ideal_ph_low}-{stage.ideal_ph_high}"
                )
        
        return recommendations

class PlantPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    can_edit = db.Column(db.Boolean, default=False)
    can_water = db.Column(db.Boolean, default=True)
    can_add_notes = db.Column(db.Boolean, default=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Watering(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float)  # in liters
    nutrients = db.Column(db.Text)  # JSON string of nutrients
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class PlantImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text)
    is_profile = db.Column(db.Boolean, default=False)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class ChatMessage(db.Model):
    """Model for storing chat messages."""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        """Convert chat message to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'username': self.user.username if self.user else None
        }

class PlantFollower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    followed_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('followed_plants', lazy='dynamic'))
    __table_args__ = (db.UniqueConstraint('user_id', 'plant_id', name='_user_plant_follow_uc'),)

class GrowthStage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    stage_name = db.Column(db.String(64), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    ideal_temp_low = db.Column(db.Float)
    ideal_temp_high = db.Column(db.Float)
    ideal_humidity_low = db.Column(db.Float)
    ideal_humidity_high = db.Column(db.Float)
    ideal_ph_low = db.Column(db.Float)
    ideal_ph_high = db.Column(db.Float)
    
    @classmethod
    def get_default_stages(cls):
        return {
            'germination': {
                'ideal_temp_low': 20,
                'ideal_temp_high': 25,
                'ideal_humidity_low': 70,
                'ideal_humidity_high': 90,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 7.0
            },
            'seedling': {
                'ideal_temp_low': 22,
                'ideal_temp_high': 28,
                'ideal_humidity_low': 60,
                'ideal_humidity_high': 80,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 7.0
            },
            'vegetative': {
                'ideal_temp_low': 24,
                'ideal_temp_high': 30,
                'ideal_humidity_low': 50,
                'ideal_humidity_high': 70,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 7.0
            },
            'flowering': {
                'ideal_temp_low': 26,
                'ideal_temp_high': 32,
                'ideal_humidity_low': 40,
                'ideal_humidity_high': 60,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 7.0
            }
        }

class GrowthData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    ph_level = db.Column(db.Float)
    health_score = db.Column(db.Float)
    growth_rate = db.Column(db.Float)
    height = db.Column(db.Float)

class Strain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    flowering_time = db.Column(db.Integer)  # in days
    difficulty = db.Column(db.Integer)  # 1-5 scale
    yield_indoor = db.Column(db.String(64))
    yield_outdoor = db.Column(db.String(64))
    height_indoor = db.Column(db.String(64))
    height_outdoor = db.Column(db.String(64))
    growing_tips = db.relationship('GrowingTip', backref='strain', lazy='dynamic')
    ratings = db.relationship('StrainRating', backref='strain', lazy='dynamic')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def average_rating(self):
        ratings = [r.rating for r in self.ratings]
        return sum(ratings) / len(ratings) if ratings else 0

    def get_tips_by_stage(self, stage_name):
        return self.growing_tips.filter_by(growth_stage=stage_name).all()

class StrainRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strain_id = db.Column(db.Integer, db.ForeignKey('strain.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 scale
    review = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'strain_id', name='_user_strain_rating_uc'),)

class GrowingTip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strain_id = db.Column(db.Integer, db.ForeignKey('strain.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    growth_stage = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text, nullable=False)
    upvotes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(64))
    requirement = db.Column(db.String(64), nullable=False)
    requirement_value = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='_user_achievement_uc'),)
