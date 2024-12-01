from app import db
from datetime import datetime

class GrowthStage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    stage_name = db.Column(db.String(64), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Environmental recommendations
    ideal_temp_low = db.Column(db.Float)
    ideal_temp_high = db.Column(db.Float)
    ideal_humidity_low = db.Column(db.Float)
    ideal_humidity_high = db.Column(db.Float)
    ideal_ph_low = db.Column(db.Float)
    ideal_ph_high = db.Column(db.Float)
    light_schedule = db.Column(db.String(20))  # e.g., "18/6", "12/12"
    
    # Relationships
    plant = db.relationship('Plant', backref='growth_stages')
    
    @staticmethod
    def get_default_stages():
        """Get default growth stages with recommendations"""
        return {
            'seedling': {
                'ideal_temp_low': 20,
                'ideal_temp_high': 25,
                'ideal_humidity_low': 65,
                'ideal_humidity_high': 70,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 6.5,
                'light_schedule': '18/6',
                'duration_days': 14
            },
            'vegetative': {
                'ideal_temp_low': 21,
                'ideal_temp_high': 28,
                'ideal_humidity_low': 40,
                'ideal_humidity_high': 60,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 6.5,
                'light_schedule': '18/6',
                'duration_days': 28
            },
            'flowering': {
                'ideal_temp_low': 20,
                'ideal_temp_high': 26,
                'ideal_humidity_low': 40,
                'ideal_humidity_high': 50,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 6.5,
                'light_schedule': '12/12',
                'duration_days': 56
            },
            'late_flowering': {
                'ideal_temp_low': 18,
                'ideal_temp_high': 24,
                'ideal_humidity_low': 35,
                'ideal_humidity_high': 45,
                'ideal_ph_low': 6.0,
                'ideal_ph_high': 6.2,
                'light_schedule': '12/12',
                'duration_days': 14
            }
        }

class GrowthData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Measurements
    height = db.Column(db.Float)  # in cm
    ph_level = db.Column(db.Float)
    temperature = db.Column(db.Float)  # in Celsius
    humidity = db.Column(db.Float)  # percentage
    
    # Analysis
    growth_rate = db.Column(db.Float)  # cm per day
    health_score = db.Column(db.Integer)  # 0-100
    
    # Relationships
    plant = db.relationship('Plant', backref='growth_data')
    
    def calculate_health_score(self):
        """Calculate plant health score based on environmental factors"""
        score = 100
        current_stage = self.plant.current_growth_stage()
        
        if current_stage:
            # Temperature check
            if self.temperature:
                if self.temperature < current_stage.ideal_temp_low:
                    score -= 10
                elif self.temperature > current_stage.ideal_temp_high:
                    score -= 10
                    
            # Humidity check
            if self.humidity:
                if self.humidity < current_stage.ideal_humidity_low:
                    score -= 10
                elif self.humidity > current_stage.ideal_humidity_high:
                    score -= 10
                    
            # pH check
            if self.ph_level:
                if self.ph_level < current_stage.ideal_ph_low:
                    score -= 10
                elif self.ph_level > current_stage.ideal_ph_high:
                    score -= 10
        
        return max(0, score)  # Ensure score doesn't go below 0

    def calculate_growth_rate(self):
        """Calculate growth rate based on previous measurements"""
        previous = GrowthData.query.filter(
            GrowthData.plant_id == self.plant_id,
            GrowthData.timestamp < self.timestamp,
            GrowthData.height.isnot(None)
        ).order_by(GrowthData.timestamp.desc()).first()
        
        if previous and self.height:
            days = (self.timestamp - previous.timestamp).days
            if days > 0:
                self.growth_rate = (self.height - previous.height) / days
                return self.growth_rate
        
        return None
