from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product, Location, ProductMovement
from forms import LoginForm, ProductForm, LocationForm, MovementForm
from utils import generate_report_pdf, send_low_stock_alert, calculate_balance
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and default data
with app.app_context():
    db.create_all()
    
    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            email='admin@inventory.com',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created: username='admin', password='admin123'")

# ============= AUTHENTICATION ROUTES =============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# ============= DASHBOARD =============

@app.route('/dashboard')
@login_required
def dashboard():
    # Get statistics
    total_products = Product.query.count()
    total_locations = Location.query.count()
    total_movements = ProductMovement.query.count()
    
    # Get low stock items
    balance_data = calculate_balance()
    low_stock_items = [item for item in balance_data if item['qty'] <= app.config['LOW_STOCK_THRESHOLD']]
    
    # Recent movements
    recent_movements = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_products=total_products,
                         total_locations=total_locations,
                         total_movements=total_movements,
                         low_stock_items=low_stock_items,
                         recent_movements=recent_movements)

# ============= PRODUCT ROUTES =============

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    form = ProductForm()
    
    if form.validate_on_submit():
        # Check if product ID already exists
        existing = Product.query.get(form.product_id.data)
        if existing:
            flash('Product ID already exists!', 'danger')
        else:
            product = Product(
                product_id=form.product_id.data,
                name=form.name.data,
                category=form.category.data,
                description=form.description.data
            )
            db.session.add(product)
            db.session.commit()
            flash(f'Product {product.name} added successfully!', 'success')
            return redirect(url_for('products'))
    
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('products.html', form=form, products=all_products)

@app.route('/products/edit/<product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.category = form.category.data
        product.description = form.description.data
        db.session.commit()
        flash(f'Product {product.name} updated successfully!', 'success')
        return redirect(url_for('products'))
    
    return render_template('products.html', form=form, products=Product.query.all(), editing=product)

@app.route('/products/delete/<product_id>')
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    # Check if product has movements
    if product.movements:
        flash('Cannot delete product with existing movements!', 'danger')
    else:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    return redirect(url_for('products'))

# ============= LOCATION ROUTES =============

@app.route('/locations', methods=['GET', 'POST'])
@login_required
def locations():
    form = LocationForm()
    
    if form.validate_on_submit():
        existing = Location.query.get(form.location_id.data)
        if existing:
            flash('Location ID already exists!', 'danger')
        else:
            location = Location(
                location_id=form.location_id.data,
                name=form.name.data,
                address=form.address.data
            )
            db.session.add(location)
            db.session.commit()
            flash(f'Location {location.name} added successfully!', 'success')
            return redirect(url_for('locations'))
    
    all_locations = Location.query.order_by(Location.created_at.desc()).all()
    return render_template('locations.html', form=form, locations=all_locations)

@app.route('/locations/edit/<location_id>', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    form = LocationForm(obj=location)
    
    if form.validate_on_submit():
        location.name = form.name.data
        location.address = form.address.data
        db.session.commit()
        flash(f'Location {location.name} updated successfully!', 'success')
        return redirect(url_for('locations'))
    
    return render_template('locations.html', form=form, locations=Location.query.all(), editing=location)

@app.route('/locations/delete/<location_id>')
@login_required
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    if location.incoming_movements or location.outgoing_movements:
        flash('Cannot delete location with existing movements!', 'danger')
    else:
        db.session.delete(location)
        db.session.commit()
        flash('Location deleted successfully!', 'success')
    return redirect(url_for('locations'))

# ============= MOVEMENT ROUTES =============

@app.route('/movements', methods=['GET', 'POST'])
@login_required
def movements():
    form = MovementForm()
    
    # Populate dropdown choices
    products = Product.query.all()
    locations = Location.query.all()
    form.product_id.choices = [(p.product_id, f"{p.product_id} - {p.name}") for p in products]
    form.from_location.choices = [('', 'None (New Stock)')] + [(l.location_id, l.name) for l in locations]
    form.to_location.choices = [('', 'None (Remove Stock)')] + [(l.location_id, l.name) for l in locations]
    
    if form.validate_on_submit():
        # Validation: At least one location must be filled
        if not form.from_location.data and not form.to_location.data:
            flash('Either From Location or To Location must be selected!', 'danger')
        elif form.from_location.data == form.to_location.data and form.from_location.data != '':
            flash('From and To locations cannot be the same!', 'danger')
        else:
            movement = ProductMovement(
                product_id=form.product_id.data,
                from_location=form.from_location.data if form.from_location.data else None,
                to_location=form.to_location.data if form.to_location.data else None,
                qty=form.qty.data,
                notes=form.notes.data
            )
            db.session.add(movement)
            db.session.commit()
            
            # Check for low stock and send alert
            balance_data = calculate_balance()
            for item in balance_data:
                if item['qty'] <= app.config['LOW_STOCK_THRESHOLD']:
                    send_low_stock_alert(
                        item['product_name'],
                        item['product_id'],
                        item['location_name'],
                        item['qty'],
                        app.config['ADMIN_EMAIL'],
                        app.config
                    )
            
            flash('Movement recorded successfully!', 'success')
            return redirect(url_for('movements'))
    
    all_movements = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).all()
    return render_template('movements.html', form=form, movements=all_movements)

@app.route('/movements/delete/<int:movement_id>')
@login_required
def delete_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)
    db.session.delete(movement)
    db.session.commit()
    flash('Movement deleted successfully!', 'success')
    return redirect(url_for('movements'))

# ============= REPORT ROUTES =============

@app.route('/report')
@login_required
def report():
    balance_data = calculate_balance()
    return render_template('report.html', balance=balance_data)

@app.route('/report/pdf')
@login_required
def report_pdf():
    balance_data = calculate_balance()
    pdf_buffer = generate_report_pdf(balance_data)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'inventory_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )

# ============= API ENDPOINT FOR BALANCE UPDATE =============

@app.route('/api/update_balance', methods=['POST'])
@login_required
def update_balance():
    """Quick balance adjustment endpoint"""
    data = request.json
    product_id = data.get('product_id')
    location_id = data.get('location_id')
    new_qty = data.get('qty')
    
    # Calculate current balance
    current_balance = 0
    movements = ProductMovement.query.filter_by(product_id=product_id).all()
    
    for m in movements:
        if m.to_location == location_id:
            current_balance += m.qty
        if m.from_location == location_id:
            current_balance -= m.qty
    
    # Create adjustment movement
    adjustment = new_qty - current_balance
    if adjustment != 0:
        movement = ProductMovement(
            product_id=product_id,
            to_location=location_id if adjustment > 0 else None,
            from_location=location_id if adjustment < 0 else None,
            qty=abs(adjustment),
            notes=f"Balance adjustment to {new_qty}"
        )
        db.session.add(movement)
        db.session.commit()
    
    return {'success': True, 'new_balance': new_qty}

if __name__ == '__main__':
    app.run(debug=True)