"""
Photo Mosaic Platform - Flask Backend API
Handles mosaic generation, user uploads, order management, and print integration.
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import requests
from functools import wraps

from flask import Flask, request, jsonify, send_file, render_template, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt

from PIL import Image
import numpy as np
from datetime import timedelta

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///mosaic_platform.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MOSAIC_FOLDER = 'mosaics'
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
    
    # Print-on-demand API keys (set in environment)
    PRINTFUL_API_KEY = os.environ.get('PRINTFUL_API_KEY')
    PRINTFUL_API_URL = 'https://api.printful.com'
    
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    
    # Session config
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, supports_credentials=True)

# Create upload directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MOSAIC_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON 401 instead of redirecting for API calls."""
    return jsonify({'error': 'Authentication required'}), 401

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(UserMixin, db.Model):
    """User model for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    mosaics = db.relationship('Mosaic', backref='creator', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='customer', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class Mosaic(db.Model):
    """Mosaic artwork model."""
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Metadata
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    visibility = db.Column(db.String(20), default='private')  # private, public, unlisted
    
    # Image information
    target_image_path = db.Column(db.String(512), nullable=False)
    mosaic_image_path = db.Column(db.String(512), nullable=False)
    tile_folder_path = db.Column(db.String(512), nullable=False)
    
    # Generation parameters
    width = db.Column(db.Integer, default=4320)
    height = db.Column(db.Integer, default=2880)
    tile_size = db.Column(db.Integer, default=120)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    # File size
    file_size = db.Column(db.Integer)  # bytes
    
    # Relationships
    orders = db.relationship('Order', backref='mosaic', lazy=True)
    
    def to_dict(self, include_path=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'visibility': self.visibility,
            'created_at': self.created_at.isoformat(),
            'width': self.width,
            'height': self.height,
            'tile_size': self.tile_size,
            'download_count': self.download_count,
            'file_size': self.file_size,
        }
        if include_path:
            data['mosaic_image_path'] = self.mosaic_image_path
        return data


class PrintProduct(db.Model):
    """Available print products."""
    id = db.Column(db.Integer, primary_key=True)
    
    # Product info
    name = db.Column(db.String(255), nullable=False)  # "Poster 24x36"
    category = db.Column(db.String(50), nullable=False)  # poster, canvas, framed
    size = db.Column(db.String(50), nullable=False)  # "24x36"
    
    # Pricing
    base_price = db.Column(db.Float, nullable=False)  # Cost to print
    retail_price = db.Column(db.Float, nullable=False)  # Sell price
    
    # Printful integration
    printful_product_id = db.Column(db.String(50))  # Printful variant ID
    printful_data = db.Column(db.JSON)  # Store full Printful product data
    
    # Metadata
    description = db.Column(db.Text)
    image_url = db.Column(db.String(512))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'size': self.size,
            'base_price': self.base_price,
            'retail_price': self.retail_price,
            'description': self.description,
            'image_url': self.image_url,
        }


class Order(db.Model):
    """Customer order."""
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mosaic_id = db.Column(db.String(36), db.ForeignKey('mosaic.id'), nullable=False)
    
    # Order status
    status = db.Column(db.String(50), default='pending')  # pending, payment_pending, processing, shipped, completed
    
    # Pricing
    subtotal = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, default=0)
    shipping = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    
    # Payment info
    stripe_payment_intent_id = db.Column(db.String(255))
    payment_status = db.Column(db.String(50), default='pending')  # pending, succeeded, failed
    
    # Shipping info
    shipping_address = db.Column(db.JSON)
    tracking_number = db.Column(db.String(255))
    
    # Printful integration
    printful_order_id = db.Column(db.String(50))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    shipped_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'mosaic_id': self.mosaic_id,
            'status': self.status,
            'subtotal': self.subtotal,
            'tax': self.tax,
            'shipping': self.shipping,
            'total': self.total,
            'created_at': self.created_at.isoformat(),
            'items': [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    """Item in an order."""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('print_product.id'), nullable=False)
    
    # Quantity and pricing
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # Customization options
    options = db.Column(db.JSON)  # {frame_color: "black", mat: true, etc}
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'options': self.options,
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user."""
    import re
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate username (3-30 chars, alphanumeric and underscores only)
    username = data['username'].strip()
    if len(username) < 3 or len(username) > 30:
        return jsonify({'error': 'Username must be 3-30 characters'}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400

    # Validate email format
    email = data['email'].strip().lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate password (minimum 8 chars)
    password = data['password']
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user."""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    login_user(user)
    return jsonify({'user': user.to_dict()}), 200


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout user."""
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200


@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info."""
    return jsonify({'user': current_user.to_dict()}), 200


# ============================================================================
# MOSAIC ROUTES
# ============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/api/mosaic/create', methods=['POST'])
@login_required
def create_mosaic():
    """Create a new mosaic from uploaded images."""
    if 'target_image' not in request.files:
        return jsonify({'error': 'No target image provided'}), 400
    
    if 'tiles' not in request.files:
        return jsonify({'error': 'No tile images provided'}), 400
    
    target_file = request.files['target_image']
    tile_files = request.files.getlist('tiles')
    
    if not target_file or not target_file.filename:
        return jsonify({'error': 'Invalid target image'}), 400
    
    if not tile_files or len(tile_files) == 0:
        return jsonify({'error': 'No tile images provided'}), 400
    
    # Validate files
    if not allowed_file(target_file.filename):
        return jsonify({'error': 'Invalid target image format'}), 400
    
    for tile in tile_files:
        if not allowed_file(tile.filename):
            return jsonify({'error': f'Invalid tile image format: {tile.filename}'}), 400
    
    try:
        # Create directory for this mosaic
        mosaic_id = str(uuid.uuid4())
        mosaic_dir = os.path.join(app.config['UPLOAD_FOLDER'], mosaic_id)
        os.makedirs(mosaic_dir, exist_ok=True)
        
        # Save target image
        target_filename = secure_filename(f'target_{target_file.filename}')
        target_path = os.path.join(mosaic_dir, target_filename)
        target_file.save(target_path)
        
        # Save tile images
        tiles_dir = os.path.join(mosaic_dir, 'tiles')
        os.makedirs(tiles_dir, exist_ok=True)
        
        for i, tile in enumerate(tile_files):
            tile_filename = secure_filename(f'{i}_{tile.filename}')
            tile_path = os.path.join(tiles_dir, tile_filename)
            tile.save(tile_path)
        
        # Get parameters from request
        width = min(request.form.get('width', 4320, type=int), 10000)  # Cap dimensions
        height = min(request.form.get('height', 2880, type=int), 10000)
        tile_size = max(min(request.form.get('tile_size', 120, type=int), 300), 30)  # 30-300 range
        title = request.form.get('title', 'Untitled')[:255]  # Cap title length
        
        # Generate mosaic (async in production)
        mosaic_path = generate_mosaic_image(target_path, tiles_dir, width, height, tile_size)
        
        # Get file size
        file_size = os.path.getsize(mosaic_path)
        
        # Create database record
        mosaic = Mosaic(
            id=mosaic_id,
            user_id=current_user.id,
            title=title,
            visibility='private',
            target_image_path=target_path,
            mosaic_image_path=mosaic_path,
            tile_folder_path=tiles_dir,
            width=width,
            height=height,
            tile_size=tile_size,
            file_size=file_size
        )
        
        db.session.add(mosaic)
        db.session.commit()
        
        return jsonify({
            'mosaic': mosaic.to_dict(),
            'download_url': f'/api/mosaic/{mosaic.id}/download'
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Failed to create mosaic: {str(e)}'}), 500


@app.route('/api/mosaic/<mosaic_id>', methods=['GET'])
def get_mosaic(mosaic_id):
    """Get mosaic details."""
    mosaic = Mosaic.query.get(mosaic_id)
    
    if not mosaic:
        return jsonify({'error': 'Mosaic not found'}), 404
    
    if mosaic.visibility == 'private' and (not current_user or mosaic.user_id != current_user.id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({'mosaic': mosaic.to_dict()}), 200


@app.route('/api/mosaic/<mosaic_id>/download', methods=['GET'])
def download_mosaic(mosaic_id):
    """Download mosaic image."""
    mosaic = Mosaic.query.get(mosaic_id)
    
    if not mosaic:
        return jsonify({'error': 'Mosaic not found'}), 404
    
    if mosaic.visibility == 'private' and (not current_user or mosaic.user_id != current_user.id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Update download count
        mosaic.download_count += 1
        db.session.commit()
        
        return send_file(
            mosaic.mosaic_image_path,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=f'{mosaic.title.replace(" ", "_")}.jpg'
        )
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/api/mosaic', methods=['GET'])
@login_required
def list_mosaics():
    """List user's mosaics."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)  # Cap at 100

    mosaics = Mosaic.query.filter_by(user_id=current_user.id).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'mosaics': [m.to_dict() for m in mosaics.items],
        'total': mosaics.total,
        'pages': mosaics.pages,
        'page': page
    }), 200


@app.route('/api/mosaic/<mosaic_id>', methods=['PUT'])
@login_required
def update_mosaic(mosaic_id):
    """Update mosaic details."""
    mosaic = Mosaic.query.get(mosaic_id)
    
    if not mosaic:
        return jsonify({'error': 'Mosaic not found'}), 404
    
    if mosaic.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if 'title' in data:
        mosaic.title = data['title']
    if 'description' in data:
        mosaic.description = data['description']
    if 'visibility' in data and data['visibility'] in ['private', 'public', 'unlisted']:
        mosaic.visibility = data['visibility']
    
    db.session.commit()
    
    return jsonify({'mosaic': mosaic.to_dict()}), 200


@app.route('/api/mosaic/<mosaic_id>', methods=['DELETE'])
@login_required
def delete_mosaic(mosaic_id):
    """Delete mosaic."""
    mosaic = Mosaic.query.get(mosaic_id)
    
    if not mosaic:
        return jsonify({'error': 'Mosaic not found'}), 404
    
    if mosaic.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Delete files
        if os.path.exists(mosaic.target_image_path):
            os.remove(mosaic.target_image_path)
        if os.path.exists(mosaic.mosaic_image_path):
            os.remove(mosaic.mosaic_image_path)
        
        db.session.delete(mosaic)
        db.session.commit()
        
        return jsonify({'message': 'Mosaic deleted'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete mosaic: {str(e)}'}), 500


# ============================================================================
# PRINT PRODUCT ROUTES
# ============================================================================

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get available print products."""
    category = request.args.get('category')
    
    query = PrintProduct.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    
    products = query.all()
    return jsonify({'products': [p.to_dict() for p in products]}), 200


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get specific product."""
    product = PrintProduct.query.get(product_id)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({'product': product.to_dict()}), 200


# ============================================================================
# ORDER ROUTES
# ============================================================================

@app.route('/api/order', methods=['POST'])
@login_required
def create_order():
    """Create new order."""
    data = request.get_json()
    
    if not data or not data.get('mosaic_id') or not data.get('items'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    mosaic = Mosaic.query.get(data['mosaic_id'])
    if not mosaic:
        return jsonify({'error': 'Mosaic not found'}), 404
    
    try:
        order_id = str(uuid.uuid4())
        subtotal = 0
        
        # Validate and calculate order total
        order_items = []
        for item in data['items']:
            product = PrintProduct.query.get(item['product_id'])
            if not product:
                return jsonify({'error': f'Product {item["product_id"]} not found'}), 404
            
            quantity = item.get('quantity', 1)
            item_total = product.retail_price * quantity
            subtotal += item_total
            
            order_items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': product.retail_price,
                'total_price': item_total,
                'options': item.get('options', {})
            })
        
        # Calculate tax and shipping
        tax = subtotal * 0.08  # 8% tax (adjust based on location)
        shipping = 10.0 if subtotal > 0 else 0  # Free shipping over certain amount
        total = subtotal + tax + shipping
        
        # Create order
        order = Order(
            id=order_id,
            user_id=current_user.id,
            mosaic_id=data['mosaic_id'],
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            total=total,
            payment_status='pending'
        )
        
        db.session.add(order)
        
        # Add order items
        for item_data in order_items:
            order_item = OrderItem(
                order_id=order_id,
                product_id=item_data['product'].id,
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price'],
                options=item_data['options']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        return jsonify({
            'order': order.to_dict(),
            'payment_url': f'/api/order/{order_id}/checkout'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create order: {str(e)}'}), 500


@app.route('/api/order/<order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    """Get order details."""
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    if order.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({'order': order.to_dict()}), 200


@app.route('/api/order', methods=['GET'])
@login_required
def list_orders():
    """List user's orders."""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return jsonify({'orders': [o.to_dict() for o in orders]}), 200


# ============================================================================
# STRIPE PAYMENT ROUTES
# ============================================================================

@app.route('/api/order/<order_id>/checkout', methods=['POST'])
@login_required
def create_checkout_session(order_id):
    """Create Stripe checkout session."""
    import stripe
    stripe.api_key = app.config['STRIPE_SECRET_KEY']
    
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    if order.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Create Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(order.total * 100),  # Convert to cents
            currency='usd',
            metadata={
                'order_id': order_id,
                'mosaic_id': order.mosaic_id
            }
        )
        
        order.stripe_payment_intent_id = intent.id
        db.session.commit()
        
        return jsonify({
            'client_secret': intent.client_secret,
            'amount': order.total,
            'order_id': order_id
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Payment processing failed: {str(e)}'}), 500


@app.route('/api/webhook/stripe', methods=['POST'])
def handle_stripe_webhook():
    """Handle Stripe webhook events."""
    import stripe
    stripe.api_key = app.config['STRIPE_SECRET_KEY']
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle payment intent succeeded
    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        order_id = intent['metadata'].get('order_id')
        
        order = Order.query.get(order_id)
        if order:
            order.payment_status = 'succeeded'
            order.status = 'processing'
            
            # Send to print-on-demand service
            send_to_printful(order)
            
            db.session.commit()
    
    return jsonify({'success': True}), 200


# ============================================================================
# PRINTFUL INTEGRATION
# ============================================================================

def send_to_printful(order: Order):
    """Send order to Printful for fulfillment."""
    if not app.config['PRINTFUL_API_KEY']:
        print("Warning: Printful API key not configured")
        return
    
    headers = {
        'Authorization': f'Bearer {app.config["PRINTFUL_API_KEY"]}',
        'Content-Type': 'application/json'
    }
    
    # Get mosaic image for upload
    mosaic = order.mosaic
    
    # Upload image to Printful
    files = {'file': open(mosaic.mosaic_image_path, 'rb')}
    
    try:
        # Create order in Printful
        order_data = {
            'recipient': {
                'name': order.customer.username,
                'email': order.customer.email,
                'address1': order.shipping_address.get('address1'),
                'address2': order.shipping_address.get('address2'),
                'city': order.shipping_address.get('city'),
                'state_code': order.shipping_address.get('state'),
                'country_code': order.shipping_address.get('country'),
                'zip': order.shipping_address.get('zip')
            },
            'items': []
        }
        
        # Add items to Printful order
        for item in order.items:
            order_data['items'].append({
                'variant_id': item.product.printful_product_id,
                'quantity': item.quantity,
                'files': [{
                    'url': f'/api/mosaic/{order.mosaic_id}/image'  # Your API serving the image
                }],
                'options': item.options
            })
        
        response = requests.post(
            f'{app.config["PRINTFUL_API_URL"]}/orders',
            json=order_data,
            headers=headers
        )
        
        if response.status_code == 201:
            printful_response = response.json()
            order.printful_order_id = printful_response['result']['id']
            print(f"Order {order.id} sent to Printful: {order.printful_order_id}")
    
    except Exception as e:
        print(f"Error sending order to Printful: {e}")


# ============================================================================
# MOSAIC GENERATION (simplified - uses the photo_mosaic.py logic)
# ============================================================================

def generate_mosaic_image(target_path: str, tiles_dir: str, width: int, height: int, tile_size: int) -> str:
    """Generate mosaic image from target and tiles."""
    from photo_mosaic import TileProcessor, create_mosaic, add_title_border, find_interesting_region
    
    try:
        # Load target
        target_image = Image.open(target_path).convert('RGB')
        
        # Load tiles
        processor = TileProcessor(tile_size)
        tiles = processor.get_all_tiles(tiles_dir)
        
        if not tiles:
            raise ValueError("No valid tiles found")
        
        # Calculate grid
        mosaic_width = width // tile_size
        mosaic_height = height // tile_size
        
        # Create mosaic
        mosaic = create_mosaic(
            target_image,
            tiles,
            mosaic_width,
            mosaic_height,
            tile_size
        )
        
        # Save output
        output_path = target_path.replace('target_', 'mosaic_').replace('.jpg', '_mosaic.jpg')
        mosaic.save(output_path, quality=95, optimize=True)
        
        return output_path
    
    except Exception as e:
        raise RuntimeError(f"Mosaic generation failed: {e}")


# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# INITIALIZATION
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Initialize default products
        if PrintProduct.query.count() == 0:
            default_products = [
                PrintProduct(
                    name='Poster 24x36', category='poster', size='24x36',
                    base_price=8.00, retail_price=24.99,
                    description='High-quality poster print'
                ),
                PrintProduct(
                    name='Poster 18x24', category='poster', size='18x24',
                    base_price=5.00, retail_price=16.99,
                    description='Standard poster size'
                ),
                PrintProduct(
                    name='Canvas 16x20', category='canvas', size='16x20',
                    base_price=12.00, retail_price=39.99,
                    description='Gallery-wrapped canvas'
                ),
                PrintProduct(
                    name='Framed 11x14', category='framed', size='11x14',
                    base_price=15.00, retail_price=49.99,
                    description='Black frame included'
                ),
            ]
            for product in default_products:
                db.session.add(product)
            db.session.commit()
    
    app.run(debug=True)
