from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.models import Plant, Note, Watering, PlantImage, Milestone, PlantPermission, User
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from config import Config

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@bp.route('/')
@login_required
def index():
    # Get private plants user owns (not archived and not public)
    owned_plants = Plant.query.filter_by(
        owner_id=current_user.id,
        is_group_grow=False,
        is_archived=False
    ).all()
    
    # Get plants user has permissions for (not archived)
    permitted_plants = Plant.query.join(PlantPermission).filter(
        PlantPermission.user_id == current_user.id,
        Plant.is_archived == False
    ).all()
    
    # Get public plants (not archived)
    public_plants = Plant.query.filter_by(
        is_group_grow=True,
        is_archived=False
    ).order_by(Plant.start_date.desc()).all()
    
    return render_template('main/index.html',
                         owned_plants=owned_plants,
                         permitted_plants=permitted_plants,
                         public_plants=public_plants)

@bp.route('/plant/<int:id>', methods=['GET'])
@login_required
def plant_profile(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(plant_id=plant.id, user_id=current_user.id).first()
        if not permission:
            flash('Access denied')
            return redirect(url_for('main.index'))
    
    has_edit_permission = plant.owner_id == current_user.id or (
        permission and permission.can_edit if 'permission' in locals() else False
    )
    
    return render_template('main/plant_profile.html', 
                         plant=plant,
                         has_edit_permission=has_edit_permission,
                         Watering=Watering,
                         PlantImage=PlantImage,
                         Milestone=Milestone,
                         Note=Note)

@bp.route('/plant/new', methods=['GET', 'POST'])
@login_required
def new_plant():
    if request.method == 'POST':
        name = request.form['name']
        strain = request.form['strain']
        is_group_grow = 'is_group_grow' in request.form
        
        plant = Plant(
            name=name,
            strain=strain,
            is_group_grow=is_group_grow,
            owner_id=current_user.id
        )
        db.session.add(plant)
        db.session.commit()
        
        flash(f'Plant {name} created successfully')
        return redirect(url_for('main.plant_profile', id=plant.id))
    
    return render_template('main/new_plant.html')

@bp.route('/plant/<int:id>/water', methods=['POST'])
@login_required
def water_plant(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=plant.id,
            user_id=current_user.id,
            can_water=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403
    
    amount = float(request.form['amount'])
    nutrients = request.form.get('nutrients', '')
    
    watering = Watering(
        amount=amount,
        nutrients=nutrients,
        plant_id=plant.id,
        user_id=current_user.id
    )
    db.session.add(watering)
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/plant/<int:id>/note', methods=['POST'])
@login_required
def add_note(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=plant.id,
            user_id=current_user.id,
            can_add_notes=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403
    
    content = request.form['content']
    note = Note(
        content=content,
        plant_id=plant.id,
        user_id=current_user.id
    )
    db.session.add(note)
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/plant/<int:id>/image', methods=['POST'])
@login_required
def add_image(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=plant.id,
            user_id=current_user.id,
            can_edit=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        
        image = PlantImage(
            filename=filename,
            description=request.form.get('description', ''),
            is_profile='is_profile' in request.form,
            plant_id=plant.id,
            user_id=current_user.id
        )
        db.session.add(image)
        db.session.commit()
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid file type'}), 400

@bp.route('/plant/<int:id>/milestone', methods=['POST'])
@login_required
def add_milestone(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=plant.id,
            user_id=current_user.id,
            can_edit=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403
    
    title = request.form['title']
    description = request.form.get('description', '')
    
    milestone = Milestone(
        title=title,
        description=description,
        plant_id=plant.id,
        user_id=current_user.id
    )
    db.session.add(milestone)
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/plant/<int:id>/edit', methods=['POST'])
@login_required
def edit_plant(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=plant.id,
            user_id=current_user.id,
            can_edit=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403

    try:
        if 'name' in request.form:
            plant.name = request.form['name']
        if 'strain' in request.form:
            plant.strain = request.form['strain']
        if 'start_date' in request.form:
            plant.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        plant.is_group_grow = 'is_group_grow' in request.form
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/watering/<int:id>/edit', methods=['POST'])
@login_required
def edit_watering(id):
    watering = Watering.query.get_or_404(id)
    if watering.plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=watering.plant_id,
            user_id=current_user.id,
            can_edit=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403

    try:
        watering.amount = float(request.form['amount'])
        watering.nutrients = request.form['nutrients']
        watering.timestamp = datetime.strptime(
            f"{request.form['date']} {request.form['time']}", 
            '%Y-%m-%d %H:%M'
        )
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/watering/<int:id>/delete', methods=['POST'])
@login_required
def delete_watering(id):
    watering = Watering.query.get_or_404(id)
    if watering.plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=watering.plant_id,
            user_id=current_user.id,
            can_edit=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403

    try:
        db.session.delete(watering)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/plant-image/<int:id>/delete', methods=['POST'])
@login_required
def delete_plant_image(id):
    image = PlantImage.query.get_or_404(id)
    if image.plant.owner_id != current_user.id:
        permission = PlantPermission.query.filter_by(
            plant_id=image.plant_id,
            user_id=current_user.id,
            can_edit=True
        ).first()
        if not permission:
            return jsonify({'error': 'Access denied'}), 403

    try:
        # Delete the actual file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # If this was the profile image, unset it
        if image.is_profile:
            image.plant.profile_image_id = None
            
        # Delete the database record
        db.session.delete(image)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/plant/<int:id>/archive', methods=['POST'])
@login_required
def archive_plant(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    try:
        plant.is_archived = True
        plant.archive_date = datetime.utcnow()
        plant.archive_reason = request.form['reason']  # 'harvested' or 'died'
        plant.archive_notes = request.form.get('notes', '')
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/plant/<int:id>/unarchive', methods=['POST'])
@login_required
def unarchive_plant(id):
    plant = Plant.query.get_or_404(id)
    if plant.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    try:
        plant.is_archived = False
        plant.archive_date = None
        plant.archive_reason = None
        plant.archive_notes = None
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/plant/<int:id>/delete', methods=['POST'])
@login_required
def delete_plant(id):
    plant = Plant.query.get_or_404(id)
    
    # Allow deletion if user is the owner or if it's a public archived plant
    if plant.owner_id != current_user.id and not (plant.is_group_grow and plant.is_archived):
        return jsonify({'error': 'Access denied'}), 403

    try:
        # Delete all associated images
        for image in plant.images.all():
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete the plant and all associated records (cascade delete)
        db.session.delete(plant)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/archives')
@login_required
def archives():
    search = request.args.get('search', '')
    show_public = request.args.get('show_public', '0') == '1'
    
    # Base query for archived plants
    plants_query = Plant.query.filter(Plant.is_archived == True)
    
    if show_public:
        # Show public archives
        plants_query = plants_query.filter(Plant.is_group_grow == True)
    else:
        # Show only user's private archives
        plants_query = plants_query.filter(
            Plant.owner_id == current_user.id,
            Plant.is_group_grow == False
        )
    
    if search:
        plants_query = plants_query.filter(
            db.or_(
                Plant.name.ilike(f'%{search}%'),
                Plant.strain.ilike(f'%{search}%'),
                Plant.archive_notes.ilike(f'%{search}%')
            )
        )
    
    plants = plants_query.order_by(Plant.archive_date.desc()).all()
    return render_template('main/archives.html', 
                         plants=plants, 
                         search=search,
                         show_public=show_public)
