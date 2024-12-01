from flask import current_app
from app.models import User, Plant, Watering, Note, PlantFollower, GrowthStage, GrowthData, Strain, StrainRating, GrowingTip, Achievement, UserAchievement
from datetime import datetime
import requests
import re
from app.extensions import db
from sqlalchemy import func

class SignalCommandHandler:
    COMMANDS = {
        'status': r'^status(?:\s+(.+))?$',     # status [plant_name]
        'water': r'^water\s+(.+)$',            # water [plant_name]
        'note': r'^note\s+(.+?)\s*:\s*(.+)$',  # note [plant_name]: [note_text]
        'list': r'^list$',                     # list
        'help': r'^help$',                     # help
        'ph': r'^ph\s+(.+?)\s+(\d+\.?\d*)$',   # ph [plant_name] [value]
        'public': r'^public$',                 # public
        'follow': r'^follow\s+(\d+)$',         # follow [plant_id]
        'unfollow': r'^unfollow\s+(\d+)$',     # unfollow [plant_id]
        'following': r'^following$',           # following
        'stage': r'^stage\s+(.+?)\s+(.+)$',    # stage [plant_name] [stage_name]
        'data': r'^data\s+(.+?)\s+(.+)$',      # data [plant_name] [key=value,key=value,...]
        'recommend': r'^recommend\s+(.+)$',    # recommend [plant_name]
        'strain': r'^strain\s+(.+)$',           # strain [name] - Get strain info
        'rate': r'^rate\s+(.+?)\s+(\d)(?:\s+(.+))?$',  # rate [strain] [1-5] [review]
        'tip': r'^tip\s+(.+?)\s+(.+?)\s+(.+)$',  # tip [strain] [stage] [content]
        'tips': r'^tips\s+(.+?)(?:\s+(.+))?$',   # tips [strain] [stage]
        'achievements': r'^achievements$',        # List achievements
        'stats': r'^stats(?:\s+(.+))?$'         # stats [plant_name] - Get detailed stats
    }

    def __init__(self):
        self.user = None
        
    def set_user(self, user):
        self.user = user
        
    def handle_command(self, sender_number, message_text):
        """Handle incoming command."""
        user = User.query.filter_by(phone_number=sender_number).first()
        if not user:
            return "❌ Your number is not registered. Please register through the web interface first."
            
        self.set_user(user)
        return self.handle_message(message_text)

    def handle_message(self, message_text):
        """Process incoming Signal messages and return appropriate response"""
        message_text = message_text.lower().strip()
        
        # Check if user is verified
        if not self.user.signal_verified:
            # Check if this is a verification code
            if message_text.isdigit() and len(message_text) == 6:
                if message_text == self.user.signal_verification_code:
                    self.user.signal_verified = True
                    db.session.commit()
                    return "✅ Your Signal account has been verified! Send 'help' to see available commands."
                return "❌ Invalid verification code. Please try again."
            return "⚠️ Your Signal account is not verified. Please enter the verification code from your profile page."

        for command, pattern in self.COMMANDS.items():
            match = re.match(pattern, message_text)
            if match:
                handler = getattr(self, f'handle_{command}')
                return handler(*match.groups())
        
        return "⚠️ Unknown command. Send 'help' for available commands."

    def handle_status(self, plant_name=None):
        if plant_name:
            plant = Plant.query.filter_by(owner_id=self.user.id, name=plant_name.strip()).first()
            if not plant:
                return f"❌ Plant '{plant_name}' not found"
            return self._get_plant_status(plant)
        
        # Return status of all plants
        plants = Plant.query.filter_by(owner_id=self.user.id, is_archived=False).all()
        if not plants:
            return "You have no active plants."
        
        return "\n\n".join([self._get_plant_status(p) for p in plants])

    def _get_plant_status(self, plant):
        """Get detailed plant status including growth data"""
        growth_summary = plant.get_growth_summary()
        last_watering = plant.waterings.order_by(Watering.timestamp.desc()).first()
        last_note = plant.notes.order_by(Note.timestamp.desc()).first()
        
        status = [
            f"🌱 {plant.name} ({plant.strain})",
            f"Age: {growth_summary['age_days']} days"
        ]
        
        # Growth stage info
        if growth_summary['current_stage']:
            status.extend([
                f"\n📈 Growth Stage: {growth_summary['current_stage']}",
                f"Days in stage: {growth_summary['days_in_stage']}"
            ])
            
            if growth_summary['target_harvest']:
                days_to_harvest = (growth_summary['target_harvest'] - datetime.utcnow()).days
                if days_to_harvest > 0:
                    status.append(f"Estimated harvest in: {days_to_harvest} days")
        
        # Growth metrics
        if growth_summary['height']:
            status.append(f"\n📏 Height: {growth_summary['height']} cm")
        if growth_summary['growth_rate']:
            status.append(f"Growth rate: {growth_summary['growth_rate']:.1f} cm/day")
        if growth_summary['health_score']:
            status.append(f"Health score: {growth_summary['health_score']}%")
        
        # Care info
        if last_watering:
            days_since_water = (datetime.utcnow() - last_watering.timestamp).days
            status.append(f"\n💧 Last watered: {days_since_water} days ago")
        
        if last_note:
            status.append(f"\n📝 Latest note: {last_note.content[:50]}...")
        
        # Add recommendations if conditions need attention
        recommendations = plant.get_stage_recommendations()
        if recommendations:
            status.append("\n⚠️ Recommendations:")
            status.extend(f"• {rec}" for rec in recommendations)
        
        return "\n".join(status)

    def handle_public(self):
        """List all public plants"""
        public_plants = Plant.query.filter_by(is_public=True, is_archived=False).all()
        if not public_plants:
            return "No public plants available."
        
        plant_list = []
        for plant in public_plants:
            followers = PlantFollower.query.filter_by(plant_id=plant.id).count()
            plant_list.append(
                f"🌱 ID#{plant.id}: {plant.name} ({plant.strain})\n"
                f"   Owner: {plant.owner.username}\n"
                f"   Followers: {followers}"
            )
        
        return "Public Plants:\n\n" + "\n\n".join(plant_list)

    def handle_follow(self, plant_id):
        """Follow a public plant"""
        try:
            plant_id = int(plant_id)
        except ValueError:
            return "❌ Invalid plant ID"

        plant = Plant.query.get(plant_id)
        if not plant:
            return "❌ Plant not found"
        
        if not plant.is_public:
            return "❌ This plant is not public"
        
        if plant.owner_id == self.user.id:
            return "❌ You can't follow your own plant"
        
        existing = PlantFollower.query.filter_by(
            user_id=self.user.id,
            plant_id=plant_id
        ).first()
        
        if existing:
            return "You're already following this plant"
        
        follower = PlantFollower(user_id=self.user.id, plant_id=plant_id)
        db.session.add(follower)
        db.session.commit()
        
        return f"✅ Now following {plant.name}"

    def handle_unfollow(self, plant_id):
        """Unfollow a plant"""
        try:
            plant_id = int(plant_id)
        except ValueError:
            return "❌ Invalid plant ID"

        follower = PlantFollower.query.filter_by(
            user_id=self.user.id,
            plant_id=plant_id
        ).first()
        
        if not follower:
            return "❌ You're not following this plant"
        
        db.session.delete(follower)
        db.session.commit()
        
        plant = Plant.query.get(plant_id)
        return f"✅ Unfollowed {plant.name}"

    def handle_following(self):
        """List plants you're following"""
        followed = PlantFollower.query.filter_by(user_id=self.user.id).all()
        if not followed:
            return "You're not following any plants"
        
        plant_list = []
        for follow in followed:
            plant = follow.plant
            plant_list.append(
                f"🌱 ID#{plant.id}: {plant.name} ({plant.strain})\n"
                f"   Owner: {plant.owner.username}"
            )
        
        return "Plants You Follow:\n\n" + "\n\n".join(plant_list)

    def handle_stage(self, plant_name, stage_name):
        """Handle growth stage changes"""
        plant = Plant.query.filter_by(owner_id=self.user.id, name=plant_name.strip()).first()
        if not plant:
            return f"❌ Plant '{plant_name}' not found"
        
        stage_name = stage_name.lower().strip()
        valid_stages = GrowthStage.get_default_stages().keys()
        
        if stage_name not in valid_stages:
            return f"❌ Invalid stage. Valid stages are: {', '.join(valid_stages)}"
        
        plant.advance_growth_stage(stage_name)
        
        return (
            f"✅ Updated {plant.name} to {stage_name} stage\n"
            f"Send 'recommend {plant.name}' for care instructions"
        )

    def handle_data(self, plant_name, data_str):
        """Handle growth data updates"""
        plant = Plant.query.filter_by(owner_id=self.user.id, name=plant_name.strip()).first()
        if not plant:
            return f"❌ Plant '{plant_name}' not found"
        
        try:
            # Parse data string (format: temp=25,humidity=60,ph=6.5,height=30)
            data_dict = dict(item.split('=') for item in data_str.split(','))
            
            growth_data = GrowthData(plant_id=plant.id)
            
            if 'temp' in data_dict:
                growth_data.temperature = float(data_dict['temp'])
            if 'humidity' in data_dict:
                growth_data.humidity = float(data_dict['humidity'])
            if 'ph' in data_dict:
                growth_data.ph_level = float(data_dict['ph'])
            if 'height' in data_dict:
                growth_data.height = float(data_dict['height'])
            
            # Calculate health score and growth rate
            growth_data.calculate_health_score()
            growth_data.calculate_growth_rate()
            
            db.session.add(growth_data)
            db.session.commit()
            
            return (
                f"✅ Updated growth data for {plant.name}\n"
                f"Health Score: {growth_data.health_score}%\n"
                f"Growth Rate: {growth_data.growth_rate:.1f} cm/day if available"
            )
            
        except (ValueError, KeyError) as e:
            return (
                "❌ Invalid data format. Use: temp=25,humidity=60,ph=6.5,height=30\n"
                "All values are optional but must be numbers"
            )

    def handle_recommend(self, plant_name):
        """Get recommendations for a plant"""
        plant = Plant.query.filter_by(owner_id=self.user.id, name=plant_name.strip()).first()
        if not plant:
            return f"❌ Plant '{plant_name}' not found"
        
        stage = plant.current_growth_stage()
        if not stage:
            return f"❌ No growth stage set for {plant.name}. Use 'stage {plant.name} [stage_name]' to set it."
        
        recommendations = plant.get_stage_recommendations()
        if not recommendations:
            return (
                f"✅ {plant.name} conditions are optimal!\n"
                f"Current Stage: {stage.stage_name}\n"
                f"Ideal Conditions:\n"
                f"🌡️ Temp: {stage.ideal_temp_low}-{stage.ideal_temp_high}°C\n"
                f"💧 Humidity: {stage.ideal_humidity_low}-{stage.ideal_humidity_high}%\n"
                f"⚗️ pH: {stage.ideal_ph_low}-{stage.ideal_ph_high}"
            )
        
        return (
            f"Recommendations for {plant.name} ({stage.stage_name} stage):\n\n"
            + "\n".join(recommendations)
        )

    def handle_help(self):
        commands = [
            "📋 Available Commands:",
            "\nBasic Commands:",
            "• status [plant_name] - Get plant status",
            "• water [plant_name] - Record watering",
            "• note [plant_name]: [text] - Add a note",
            "• list - List your plants",
            
            "\nGrowth Tracking:",
            "• stage [plant_name] [stage] - Update growth stage",
            "• data [plant_name] temp=25,humidity=60,ph=6.5,height=30 - Record measurements",
            "• recommend [plant_name] - Get care recommendations",
            
            "\nPublic Plants:",
            "• public - List all public plants",
            "• follow [plant_id] - Follow a public plant",
            "• unfollow [plant_id] - Unfollow a plant",
            "• following - List plants you follow"
        ]
        
        # Add user's plants
        plants = Plant.query.filter_by(owner_id=self.user.id, is_archived=False).all()
        if plants:
            commands.append("\nYour Plants:")
            for plant in plants:
                stage = plant.current_growth_stage()
                stage_name = stage.stage_name if stage else "No stage set"
                commands.append(f"• {plant.name} ({stage_name})")
        
        return "\n".join(commands)

    def handle_strain(self, strain_name):
        """Get information about a strain"""
        strain = Strain.query.filter(func.lower(Strain.name) == strain_name.lower()).first()
        if not strain:
            return f"❌ Strain '{strain_name}' not found"
        
        info = [
            f"🧬 {strain.name} ({strain.type})",
            f"Difficulty: {'⭐' * strain.difficulty}",
            f"Flowering Time: {strain.flowering_time} days",
            f"\n📊 Community Stats:",
            f"Rating: {strain.rating:.1f}/5 ({strain.total_ratings} ratings)",
            f"Success Rate: {strain.success_rate:.1f}%",
            f"Total Grows: {strain.total_grows}",
            f"\n🌡️ Growing Conditions:",
            f"Temperature: {strain.ideal_temp_low}-{strain.ideal_temp_high}°C",
            f"Humidity: {strain.ideal_humidity_low}-{strain.ideal_humidity_high}%",
            f"Height: {strain.height_low}-{strain.height_high}cm"
        ]
        
        # Add top tip if available
        top_tip = strain.growing_tips.order_by(GrowingTip.upvotes.desc()).first()
        if top_tip:
            info.extend([
                f"\n💡 Top Growing Tip:",
                f"{top_tip.content}",
                f"- {top_tip.author.username}"
            ])
        
        return "\n".join(info)

    def handle_rate(self, strain_name, rating, review=None):
        """Rate and review a strain"""
        strain = Strain.query.filter(func.lower(Strain.name) == strain_name.lower()).first()
        if not strain:
            return f"❌ Strain '{strain_name}' not found"
        
        try:
            rating = int(rating)
            if not 1 <= rating <= 5:
                raise ValueError
        except ValueError:
            return "❌ Rating must be between 1 and 5"
        
        # Check if user has grown this strain
        has_grown = Plant.query.filter_by(
            owner_id=self.user.id,
            strain=strain.name,
            is_archived=True
        ).first()
        
        if not has_grown:
            return "❌ You can only rate strains you have grown"
        
        # Update or create rating
        strain_rating = StrainRating.query.filter_by(
            user_id=self.user.id,
            strain_id=strain.id
        ).first()
        
        if strain_rating:
            strain_rating.rating = rating
            strain_rating.review = review
        else:
            strain_rating = StrainRating(
                user_id=self.user.id,
                strain_id=strain.id,
                rating=rating,
                review=review
            )
            db.session.add(strain_rating)
        
        db.session.commit()
        
        # Update strain statistics
        strain.rating = db.session.query(func.avg(StrainRating.rating)).\
            filter_by(strain_id=strain.id).scalar()
        strain.total_ratings = StrainRating.query.filter_by(strain_id=strain.id).count()
        db.session.commit()
        
        return f"✅ Rated {strain.name} {rating}/5" + (f"\nReview: {review}" if review else "")

    def handle_tip(self, strain_name, stage, content):
        """Add a growing tip for a strain"""
        strain = Strain.query.filter(func.lower(Strain.name) == strain_name.lower()).first()
        if not strain:
            return f"❌ Strain '{strain_name}' not found"
        
        # Verify stage is valid
        valid_stages = GrowthStage.get_default_stages().keys()
        if stage not in valid_stages:
            return f"❌ Invalid stage. Valid stages: {', '.join(valid_stages)}"
        
        # Check if user has grown this strain
        has_grown = Plant.query.filter_by(
            owner_id=self.user.id,
            strain=strain.name,
            is_archived=True,
            archive_reason='harvested'
        ).first()
        
        if not has_grown:
            return "❌ You can only add tips for strains you have successfully grown"
        
        tip = GrowingTip(
            strain_id=strain.id,
            user_id=self.user.id,
            content=content,
            growth_stage=stage
        )
        
        db.session.add(tip)
        db.session.commit()
        
        return f"✅ Added growing tip for {strain.name} ({stage} stage)"

    def handle_tips(self, strain_name, stage=None):
        """Get growing tips for a strain"""
        strain = Strain.query.filter(func.lower(Strain.name) == strain_name.lower()).first()
        if not strain:
            return f"❌ Strain '{strain_name}' not found"
        
        query = strain.growing_tips
        if stage:
            query = query.filter_by(growth_stage=stage)
        
        tips = query.order_by(GrowingTip.upvotes.desc()).limit(5).all()
        
        if not tips:
            return f"No tips found for {strain.name}" + (f" ({stage} stage)" if stage else "")
        
        response = [f"💡 Top Growing Tips for {strain.name}:"]
        for i, tip in enumerate(tips, 1):
            response.extend([
                f"\n{i}. {tip.growth_stage.title()} Stage:",
                f"{tip.content}",
                f"👍 {tip.upvotes} - by {tip.author.username}"
            ])
        
        return "\n".join(response)

    def handle_achievements(self):
        """List user's achievements"""
        achievements = UserAchievement.query.filter_by(user_id=self.user.id).all()
        
        if not achievements:
            return "You haven't earned any achievements yet. Keep growing! 🌱"
        
        response = ["🏆 Your Achievements:"]
        for ua in achievements:
            response.append(
                f"\n{ua.achievement.icon} {ua.achievement.name}"
                f"\n{ua.achievement.description}"
                f"\nEarned: {ua.earned_at.strftime('%Y-%m-%d')}"
            )
        
        # Add progress towards next achievements
        next_achievements = Achievement.query.filter(
            ~Achievement.id.in_(
                db.session.query(UserAchievement.achievement_id).\
                filter_by(user_id=self.user.id)
            )
        ).all()
        
        if next_achievements:
            response.append("\n\n🎯 Next Achievements:")
            for achievement in next_achievements[:3]:
                response.append(f"\n{achievement.icon} {achievement.name}")
        
        return "\n".join(response)

    def handle_stats(self, plant_name=None):
        """Get detailed growing statistics"""
        if plant_name:
            return self._get_plant_stats(plant_name)
        
        # Overall stats
        completed_grows = Plant.query.filter_by(
            owner_id=self.user.id,
            is_archived=True
        ).all()
        
        successful_grows = sum(1 for p in completed_grows if p.archive_reason == 'harvested')
        total_grows = len(completed_grows)
        success_rate = (successful_grows / total_grows * 100) if total_grows > 0 else 0
        
        unique_strains = db.session.query(func.count(func.distinct(Plant.strain))).\
            filter(Plant.owner_id == self.user.id).scalar()
        
        stats = [
            "📊 Your Growing Statistics",
            f"\nTotal Grows: {total_grows}",
            f"Successful Harvests: {successful_grows}",
            f"Success Rate: {success_rate:.1f}%",
            f"Unique Strains: {unique_strains}"
        ]
        
        # Add achievements count
        achievements = UserAchievement.query.filter_by(user_id=self.user.id).count()
        stats.append(f"Achievements: {achievements}")
        
        return "\n".join(stats)

    def _get_plant_stats(self, plant_name):
        """Get detailed statistics for a specific plant"""
        plant = Plant.query.filter_by(owner_id=self.user.id, name=plant_name.strip()).first()
        if not plant:
            return f"❌ Plant '{plant_name}' not found"
        
        growth_data = GrowthData.query.filter_by(plant_id=plant.id).\
            order_by(GrowthData.timestamp.desc()).all()
        
        if not growth_data:
            return f"No growth data available for {plant.name}"
        
        # Calculate statistics
        heights = [d.height for d in growth_data if d.height]
        temps = [d.temperature for d in growth_data if d.temperature]
        humidities = [d.humidity for d in growth_data if d.humidity]
        
        stats = [
            f"📊 Statistics for {plant.name}",
            f"Strain: {plant.strain}",
            f"Age: {(datetime.utcnow() - plant.start_date).days} days"
        ]
        
        if heights:
            growth_rate = (heights[0] - heights[-1]) / len(heights)
            stats.extend([
                f"\n📏 Growth:",
                f"Initial Height: {heights[-1]:.1f}cm",
                f"Current Height: {heights[0]:.1f}cm",
                f"Average Growth Rate: {growth_rate:.2f}cm/day"
            ])
        
        if temps:
            stats.extend([
                f"\n🌡️ Temperature:",
                f"Average: {sum(temps)/len(temps):.1f}°C",
                f"Range: {min(temps):.1f}-{max(temps):.1f}°C"
            ])
        
        if humidities:
            stats.extend([
                f"\n💧 Humidity:",
                f"Average: {sum(humidities)/len(humidities):.1f}%",
                f"Range: {min(humidities):.1f}-{max(humidities):.1f}%"
            ])
        
        # Add health scores
        health_scores = [d.health_score for d in growth_data if d.health_score]
        if health_scores:
            stats.extend([
                f"\n❤️ Health:",
                f"Current: {health_scores[0]}%",
                f"Average: {sum(health_scores)/len(health_scores):.1f}%",
                f"Lowest: {min(health_scores)}%"
            ])
        
        return "\n".join(stats)

class SignalService:
    def __init__(self, signal_number=None, api_url=None):
        self.signal_number = signal_number
        self.api_url = api_url
        self.command_handler = SignalCommandHandler()

    def process_incoming_message(self, sender_number, message_text):
        """Process incoming messages."""
        try:
            response = self.command_handler.handle_command(sender_number, message_text)
            return {"success": True, "message": response}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_message(self, recipient_number, message):
        """Send a message (currently just prints to console)."""
        print(f"Message to {recipient_number}: {message}")
        return True
