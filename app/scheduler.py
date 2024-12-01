from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from app.models import Plant, User, Watering, GrowthStage
from app.extensions import db
from app.signal_service import SignalService

scheduler = None

def check_growth_stages():
    """Check and update plant growth stages."""
    with scheduler.app.app_context():
        plants = Plant.query.filter_by(is_archived=False).all()
        for plant in plants:
            if plant.current_stage_id:
                stage = GrowthStage.query.get(plant.current_stage_id)
                if stage and stage.end_date and stage.end_date <= datetime.utcnow():
                    # Time to advance to next stage
                    next_stage = GrowthStage.get_default_stages().get(stage.stage_name)
                    if next_stage:
                        plant.advance_growth_stage(next_stage)
                        db.session.commit()

def check_watering_schedule():
    """Check if plants need watering."""
    with scheduler.app.app_context():
        plants = Plant.query.filter_by(is_archived=False).all()
        for plant in plants:
            last_watering = plant.waterings.order_by(Watering.timestamp.desc()).first()
            if last_watering and datetime.utcnow() - last_watering.timestamp > timedelta(days=2):
                owner = User.query.get(plant.owner_id)
                if owner:
                    signal_service = SignalService(
                        scheduler.app.config.get('SIGNAL_BOT_NUMBER'),
                        scheduler.app.config.get('SIGNAL_API_URL')
                    )
                    signal_service.send_message(
                        owner.phone_number,
                        f"🌱 Your plant {plant.name} needs watering! Last watered {last_watering.timestamp.strftime('%Y-%m-%d %H:%M')}"
                    )

def init_scheduler(app):
    """Initialize the scheduler with the given Flask app."""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.app = app
        
        # Add jobs
        scheduler.add_job(
            func=check_growth_stages,
            trigger=IntervalTrigger(hours=1),
            id='check_growth_stages',
            name='Check plant growth stages',
            replace_existing=True)
            
        scheduler.add_job(
            func=check_watering_schedule,
            trigger=IntervalTrigger(hours=12),
            id='check_watering',
            name='Check watering schedule',
            replace_existing=True)
        
        scheduler.start()
