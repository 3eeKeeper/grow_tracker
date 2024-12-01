from app import db
from datetime import datetime
from sqlalchemy import func

class Strain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(20))  # indica, sativa, hybrid
    flowering_time = db.Column(db.Integer)  # typical flowering time in days
    difficulty = db.Column(db.Integer)  # 1-5 scale
    description = db.Column(db.Text)
    
    # Growing characteristics
    ideal_temp_low = db.Column(db.Float)
    ideal_temp_high = db.Column(db.Float)
    ideal_humidity_low = db.Column(db.Float)
    ideal_humidity_high = db.Column(db.Float)
    height_low = db.Column(db.Float)  # typical height range in cm
    height_high = db.Column(db.Float)
    
    # Community data
    rating = db.Column(db.Float)  # Average user rating
    total_ratings = db.Column(db.Integer, default=0)
    total_grows = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float)  # Percentage of successful grows
    
    # Relationships
    plants = db.relationship('Plant', backref='strain_info', lazy='dynamic')
    growing_tips = db.relationship('GrowingTip', backref='strain', lazy='dynamic')
    
    def update_statistics(self):
        """Update strain statistics based on completed grows"""
        completed_grows = Plant.query.filter_by(
            strain=self.name,
            is_archived=True
        ).all()
        
        if not completed_grows:
            return
        
        self.total_grows = len(completed_grows)
        successful_grows = sum(1 for p in completed_grows if p.archive_reason == 'harvested')
        self.success_rate = (successful_grows / self.total_grows) * 100
        
        # Update average growth time
        growth_times = [
            (p.archive_date - p.start_date).days
            for p in completed_grows
            if p.archive_reason == 'harvested'
        ]
        if growth_times:
            self.average_growth_time = sum(growth_times) / len(growth_times)
            
        db.session.commit()

class GrowingTip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strain_id = db.Column(db.Integer, db.ForeignKey('strain.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    growth_stage = db.Column(db.String(64))  # Which stage this tip applies to
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    upvotes = db.Column(db.Integer, default=0)
    
    # Relationships
    author = db.relationship('User', backref='growing_tips')

class StrainRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strain_id = db.Column(db.Integer, db.ForeignKey('strain.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)  # 1-5 scale
    review = db.Column(db.Text)
    grow_difficulty = db.Column(db.Integer)  # 1-5 scale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('strain_id', 'user_id', name='_user_strain_rating_uc'),)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(64))  # Icon identifier
    requirement_type = db.Column(db.String(32))  # e.g., 'plants_grown', 'success_rate'
    requirement_value = db.Column(db.Integer)
    
    @staticmethod
    def get_default_achievements():
        return [
            {
                'name': 'First Harvest',
                'description': 'Successfully complete your first grow',
                'icon': '🌱',
                'requirement_type': 'plants_harvested',
                'requirement_value': 1
            },
            {
                'name': 'Master Grower',
                'description': 'Achieve a 90% success rate with 10+ grows',
                'icon': '🏆',
                'requirement_type': 'success_rate',
                'requirement_value': 90
            },
            {
                'name': 'Strain Expert',
                'description': 'Successfully grow 5 different strains',
                'icon': '🧬',
                'requirement_type': 'unique_strains',
                'requirement_value': 5
            },
            {
                'name': 'Community Leader',
                'description': 'Have 10 growing tips with 50+ upvotes each',
                'icon': '👑',
                'requirement_type': 'upvoted_tips',
                'requirement_value': 10
            }
        ]

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'))
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='achievements')
    achievement = db.relationship('Achievement')

def check_user_achievements(user):
    """Check and award any newly earned achievements"""
    # Get user's growing statistics
    completed_grows = Plant.query.filter_by(
        owner_id=user.id,
        is_archived=True
    ).all()
    
    successful_grows = sum(1 for p in completed_grows if p.archive_reason == 'harvested')
    total_grows = len(completed_grows)
    success_rate = (successful_grows / total_grows * 100) if total_grows > 0 else 0
    
    unique_strains = db.session.query(func.count(func.distinct(Plant.strain))).\
        filter(Plant.owner_id == user.id, Plant.archive_reason == 'harvested').scalar()
    
    # Check each achievement
    for achievement in Achievement.query.all():
        # Skip if already earned
        if UserAchievement.query.filter_by(
            user_id=user.id,
            achievement_id=achievement.id
        ).first():
            continue
        
        # Check requirements
        earned = False
        if achievement.requirement_type == 'plants_harvested':
            earned = successful_grows >= achievement.requirement_value
        elif achievement.requirement_type == 'success_rate':
            earned = success_rate >= achievement.requirement_value and total_grows >= 10
        elif achievement.requirement_type == 'unique_strains':
            earned = unique_strains >= achievement.requirement_value
        elif achievement.requirement_type == 'upvoted_tips':
            highly_rated_tips = GrowingTip.query.filter_by(user_id=user.id).\
                filter(GrowingTip.upvotes >= 50).count()
            earned = highly_rated_tips >= achievement.requirement_value
        
        # Award achievement if earned
        if earned:
            user_achievement = UserAchievement(user_id=user.id, achievement_id=achievement.id)
            db.session.add(user_achievement)
            db.session.commit()
            
            # Send notification if user has Signal enabled
            if user.signal_verified and user.notification_preferences.get('achievements'):
                from app.signal_service import SignalService
                from flask import current_app
                
                signal = SignalService(
                    current_app.config['SIGNAL_BOT_NUMBER'],
                    current_app.config['SIGNAL_API_URL']
                )
                
                message = (
                    f"🎉 Achievement Unlocked: {achievement.icon} {achievement.name}\n"
                    f"{achievement.description}"
                )
                signal.send_message(user.phone_number, message)
