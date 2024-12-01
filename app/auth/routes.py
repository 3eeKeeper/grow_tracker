from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.urls import url_parse
import random
import string
from datetime import datetime
from app import db
from app.auth import bp
from app.models import User, Plant
from app.auth.forms import ChangePasswordForm

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@bp.route('/manage_users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('main.index'))
    
    users = User.query.all()
    for user in users:
        user.plant_count = Plant.query.filter_by(owner_id=user.id).count()
    
    return render_template('auth/manage_users.html', users=users)

@bp.route('/delete_user/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('main.index'))
    
    if id == current_user.id:
        flash('Cannot delete your own account')
        return redirect(url_for('auth.manage_users'))
    
    user = User.query.get_or_404(id)
    plants = Plant.query.filter_by(owner_id=user.id).all()
    
    for plant in plants:
        db.session.delete(plant)
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted')
    return redirect(url_for('auth.manage_users'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Your password has been updated.')
        return redirect(url_for('main.index'))
    return render_template('auth/change_password.html', form=form)
