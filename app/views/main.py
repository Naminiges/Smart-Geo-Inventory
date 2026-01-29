"""
Main routes for landing page
"""
from flask import Blueprint, render_template

bp = Blueprint('main', __name__)


@bp.route('/')
def landing():
    """Landing page for LOKASET"""
    return render_template('landing.html')


@bp.route('/home')
def home():
    """Alternative route to landing page"""
    return render_template('landing.html')
