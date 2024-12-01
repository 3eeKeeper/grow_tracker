from flask import jsonify, request
from flask_login import login_required, current_user
from app import db
from app.plants import bp
from app.models import Plant, PlantPermission

@bp.route('/api/plants/permissions/<int:plant_id>', methods=['POST'])
@login_required
def update_permissions(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    if plant.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    user_id = request.form.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    permission = PlantPermission.query.filter_by(
        plant_id=plant_id,
        user_id=user_id
    ).first()
    
    if not permission:
        permission = PlantPermission(plant_id=plant_id, user_id=user_id)
        db.session.add(permission)
    
    permission.can_edit = 'can_edit' in request.form
    permission.can_water = 'can_water' in request.form
    permission.can_add_notes = 'can_add_notes' in request.form
    
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/plants/permissions/<int:plant_id>/<int:user_id>', methods=['DELETE'])
@login_required
def remove_permissions(plant_id, user_id):
    plant = Plant.query.get_or_404(plant_id)
    if plant.owner_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    permission = PlantPermission.query.filter_by(
        plant_id=plant_id,
        user_id=user_id
    ).first()
    
    if permission:
        db.session.delete(permission)
        db.session.commit()
    
    return jsonify({'success': True})
