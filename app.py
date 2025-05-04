from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy import or_

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['JSON_AS_ASCII'] = False
app.config['INSTANCE_PATH'] = os.path.dirname(os.path.abspath(__file__))  # Prevent instance folder creation

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'job_portal.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print(f"Upload folder created/verified at: {UPLOAD_FOLDER}")
except Exception as e:
    print(f"Error creating upload folder: {str(e)}")

# Initialize SQLAlchemy with explicit commit on session
db = SQLAlchemy(app)

# Ensure changes are committed after each request
@app.after_request
def after_request(response):
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error committing changes: {str(e)}")
    return response

# Database Models
class User(db.Model):
    __tablename__ = 'users'  # Explicitly naming the table
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)  # New admin flag
    
    # Relationships
    jobs = db.relationship('Job', backref='employer', lazy=True)
    applications = db.relationship('Application', backref='job_seeker', lazy=True)

class Job(db.Model):
    __tablename__ = 'jobs'  # Explicitly naming the table
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    employer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='job', lazy=True)

class Application(db.Model):
    __tablename__ = 'applications'  # Explicitly naming the table
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    job_seeker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    cv_file = db.Column(db.String(255))
    cover_letter = db.Column(db.Text)
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'reviews'  # Explicitly naming the table
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

def init_db():
    """Initialize the database using schema.sql"""
    try:
        # Only create tables if they don't exist
        with app.app_context():
            if not os.path.exists('job_portal.db'):
                db.create_all()
                print("SQLAlchemy tables created successfully!")
                
                # Then apply any additional schema changes from schema.sql
                schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        schema_sql = f.read()
                    
                    statements = schema_sql.split(';')
                    for statement in statements:
                        if statement.strip():
                            try:
                                db.session.execute(statement)
                            except Exception as e:
                                print(f"Warning: Could not execute statement: {str(e)}")
                                continue
                    
                    db.session.commit()
                    print("Additional schema changes applied successfully!")
            else:
                print("Using existing database file: job_portal.db")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        db.session.rollback()

# Remove automatic initialization
# init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User functions
def create_user(name, email, password, user_type):
    try:
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            raise ValueError('Email already registered')
        
        # Create new user
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            user_type=user_type,
            created_at=datetime.utcnow()
        )
        
        # Add and commit to database
        db.session.add(user)
        db.session.commit()
        return user
    except Exception as e:
        db.session.rollback()
        raise e

def get_user_by_email(email):
    try:
        return User.query.filter_by(email=email).first()
    except Exception as e:
        print(f"Error getting user by email: {str(e)}")
        return None

def get_user_by_id(user_id):
    try:
        return User.query.get(user_id)
    except Exception as e:
        print(f"Error getting user by id: {str(e)}")
        return None

# Job functions
def create_job(title, company, description, location, deadline, employer_id):
    job = Job(title=title, company=company, description=description, location=location, deadline=deadline, employer_id=employer_id, created_at=datetime.utcnow())
    db.session.add(job)
    db.session.commit()
    return job

def get_all_jobs():
    return Job.query.all()

def get_job_by_id(job_id):
    return Job.query.get(job_id)

def get_employer_jobs(employer_id):
    return Job.query.filter_by(employer_id=employer_id).all()

# Application functions
def create_application(name, email, job_id, job_seeker_id, cv_file=None, cover_letter=None):
    application = Application(name=name, email=email, job_id=job_id, job_seeker_id=job_seeker_id, status='Pending', cv_file=cv_file, cover_letter=cover_letter, applied_date=datetime.utcnow())
    db.session.add(application)
    db.session.commit()
    return application

def get_job_applications(job_id):
    return Application.query.filter_by(job_id=job_id).all()

def get_user_applications(user_id):
    return Application.query.filter_by(job_seeker_id=user_id).all()

@app.route('/')
def index():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if not user:
            session.clear()
    return render_template('index.html')

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    user_type = request.args.get('type', '')
    
    if request.method == 'POST':
        if 'login' in request.form:
            try:
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '').strip()
                user_type = request.form.get('user_type', '').strip()
                
                if not email or not password or not user_type:
                    flash('Please fill in all fields', 'danger')
                    return redirect(url_for('auth', type=user_type))
                
                user = get_user_by_email(email)
                
                if not user:
                    flash('No account found with this email', 'danger')
                    return redirect(url_for('auth', type=user_type))
                
                if user.user_type != user_type and not user.is_admin:
                    flash(f'This email is registered as a {user.user_type}, not a {user_type}', 'danger')
                    return redirect(url_for('auth', type=user_type))
                
                if not check_password_hash(user.password, password):
                    flash('Invalid password', 'danger')
                    return redirect(url_for('auth', type=user_type))
                
                session.clear()
                session['user_id'] = str(user.id)
                session['user_type'] = user.user_type
                session['name'] = user.name
                session['email'] = user.email
                session['is_admin'] = user.is_admin
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                print(f"Login error: {str(e)}")
                flash('An error occurred during login. Please try again.', 'danger')
                return redirect(url_for('auth', type=user_type))
        
        elif 'signup' in request.form:
            try:
                name = request.form.get('name', '').strip()
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '').strip()
                user_type = request.form.get('user_type', '').strip()
                
                if not name or not email or not password or not user_type:
                    flash('Please fill in all fields', 'danger')
                    return redirect(url_for('auth', type=user_type))
                
                if len(password) < 6:
                    flash('Password must be at least 6 characters long', 'danger')
                    return redirect(url_for('auth', type=user_type))
                
                if user_type not in ['job_seeker', 'employer']:
                    flash('Invalid user type', 'danger')
                    return redirect(url_for('auth'))
                
                # Create the user
                create_user(name, email, password, user_type)
                
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('auth', type=user_type))
                
            except ValueError as e:
                flash(str(e), 'danger')
                return redirect(url_for('auth', type=user_type))
            except Exception as e:
                print(f"Registration error: {str(e)}")
                flash('Error during registration. Please try again.', 'danger')
                return redirect(url_for('auth', type=user_type))
    
    return render_template('auth.html', user_type=user_type)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('auth'))
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        session.clear()
        flash('User not found', 'danger')
        return redirect(url_for('auth'))
    
    if user.user_type == 'employer':
        try:
            jobs = list(get_employer_jobs(user_id))
            return render_template('dashboard.html', jobs=jobs)
        except Exception as e:
            print(f"Error fetching employer jobs: {str(e)}")
            flash('Error loading dashboard', 'danger')
            return redirect(url_for('index'))
    else:  # job seeker
        try:
            # Get all available jobs
            all_jobs = Job.query.all()
            # Get user's applications
            applications = list(get_user_applications(user_id))
            # Get IDs of jobs user has already applied to
            applied_job_ids = {app.job_id for app in applications}
            # Filter jobs to show only those not applied to
            available_jobs = [job for job in all_jobs if job.id not in applied_job_ids]
            
            return render_template('dashboard.html', 
                                 applications=applications,
                                 available_jobs=available_jobs)
        except Exception as e:
            print(f"Error fetching job seeker data: {str(e)}")
            flash('Error loading dashboard', 'danger')
            return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/jobs', methods=['GET'])
def jobs():
    try:
        search_query = request.args.get('search', '').strip()
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        # Get all jobs
        if search_query:
            jobs_query = Job.query.filter(
                or_(
                    Job.title.ilike(f'%{search_query}%'),
                    Job.company.ilike(f'%{search_query}%'),
                    Job.description.ilike(f'%{search_query}%'),
                    Job.location.ilike(f'%{search_query}%')
                )
            ).order_by(Job.created_at.desc()).all()
        else:
            jobs_query = Job.query.order_by(Job.created_at.desc()).all()
        
        jobs = list(jobs_query)
        
        # Get applied jobs for the current user if they're a job seeker
        applied_jobs = set()
        if user_id and user_type == 'job_seeker':
            applications = Application.query.filter_by(job_seeker_id=user_id).all()
            applied_jobs = {str(app.job_id) for app in applications}
        
        print(f"Found {len(jobs)} jobs, {len(applied_jobs)} applied jobs")  # Debug log
        
        return render_template('jobs.html', 
                             jobs=jobs,
                             can_apply=(user_type == 'job_seeker'),
                             applied_jobs=applied_jobs,
                             search_query=search_query,
                             now=datetime.now().date())
    except Exception as e:
        print(f"Error loading jobs: {e}")  # Debug log
        flash('Error loading jobs. Please try again later.', 'error')
        return render_template('jobs.html', 
                             jobs=[], 
                             can_apply=False, 
                             applied_jobs=set(),
                             search_query='',
                             now=datetime.now().date())

@app.route('/apply_job/<int:job_id>', methods=['GET', 'POST'])
def apply_job(job_id):
    if 'user_id' not in session or session.get('user_type') != 'job_seeker':
        flash('Please login as a job seeker to apply', 'danger')
        return redirect(url_for('auth'))

    # Get the job details
    job = get_job_by_id(job_id)
    print(f"Processing application for job: {job_id}")
    
    if request.method == 'GET':
        # Check if already applied
        existing_application = Application.query.filter_by(job_id=job.id, job_seeker_id=session['user_id']).first()

        if existing_application:
            flash('You have already applied for this job', 'warning')
            return redirect(url_for('jobs'))

        # Render the application form
        return render_template('apply_job.html', job=job)

    elif request.method == 'POST':
        try:
            print("Processing POST request for job application")
            # Check if already applied
            existing_application = Application.query.filter_by(job_id=job.id, job_seeker_id=session['user_id']).first()

            if existing_application:
                flash('You have already applied for this job', 'warning')
                return redirect(url_for('jobs'))

            # Get the cover letter
            cover_letter = request.form.get('cover_letter')
            if not cover_letter:
                flash('Please provide a cover letter', 'danger')
                return redirect(url_for('apply_job', job_id=job_id))

            # Handle CV file upload
            if 'cv_file' not in request.files:
                print("No cv_file in request.files")
                flash('No CV file uploaded', 'danger')
                return redirect(url_for('apply_job', job_id=job_id))

            file = request.files['cv_file']
            print(f"Received file: {file.filename}")
            
            if file.filename == '':
                flash('No CV file selected', 'danger')
                return redirect(url_for('apply_job', job_id=job_id))

            if not allowed_file(file.filename):
                flash('Invalid file type. Please upload PDF, DOC, or DOCX files only.', 'danger')
                return redirect(url_for('apply_job', job_id=job_id))

            # Secure the filename and save the file
            filename = secure_filename(f"{session['user_id']}_{job_id}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"Attempting to save file to: {file_path}")
            
            try:
                file.save(file_path)
                print(f"File saved successfully to: {file_path}")
            except Exception as e:
                print(f"Error saving file: {str(e)}")
                flash('Error saving CV file. Please try again.', 'danger')
                return redirect(url_for('apply_job', job_id=job_id))

            # Create the application
            user = get_user_by_id(session['user_id'])
            try:
                application = create_application(user.name, user.email, job.id, session['user_id'], filename, cover_letter)
                print(f"Application created successfully: {application.id}")
                db.session.commit()
                print("Database changes committed")
            except Exception as e:
                print(f"Error creating application: {str(e)}")
                db.session.rollback()
                flash('Error creating application. Please try again.', 'danger')
                return redirect(url_for('apply_job', job_id=job_id))
            
            print(f"New application submitted: {user.name} for job {job_id}")
            flash('Application submitted successfully!', 'success')
            
            # Close the window using JavaScript
            return '''
                <script>
                    alert('Application submitted successfully!');
                    window.opener.location.reload();  // Refresh the parent window
                    window.close();  // Close the application window
                </script>
            '''
            
        except Exception as e:
            print(f"Error submitting application: {str(e)}")
            flash('Error submitting application. Please try again.', 'danger')
            return redirect(url_for('apply_job', job_id=job_id))

@app.route('/add_job', methods=['POST'])
def add_job():
    if 'user_id' not in session or session.get('user_type') != 'employer':
        flash('Please login as an employer to post jobs', 'danger')
        return redirect(url_for('auth'))

    title = request.form['title']
    company = request.form['company']
    description = request.form['description']
    location = request.form['location']
    deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%d').date()
    
    try:
        create_job(title, company, description, location, deadline, session['user_id'])
        print(f"New job posted: {title} by {company}")
        flash('Job posted successfully!', 'success')
    except Exception as e:
        flash('Error posting job. Please try again.', 'danger')
        print(f"Error posting job: {str(e)}")
    
    return redirect(url_for('dashboard'))

@app.route('/update_job/<int:job_id>', methods=['GET', 'POST'])
def update_job(job_id):
    if 'user_id' not in session or session.get('user_type') != 'employer':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    try:
        job = get_job_by_id(job_id)
        
        # Verify ownership
        if str(job.employer_id) != session['user_id']:
            flash('You can only edit your own job postings', 'danger')
            return redirect(url_for('dashboard'))

        if request.method == 'GET':
            return render_template('edit_job.html', job=job)
        
        # Handle POST request
        job.title = request.form.get('title', '').strip()
        job.company = request.form.get('company', '').strip()
        job.description = request.form.get('description', '').strip()
        job.location = request.form.get('location', '').strip()
        
        # Validate required fields
        if not all([job.title, job.company, job.description, job.location]):
            flash('All fields are required', 'danger')
            return redirect(url_for('update_job', job_id=job_id))
            
        # Handle deadline
        try:
            deadline_str = request.form.get('deadline', '').strip()
            job.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(url_for('update_job', job_id=job_id))
        
        db.session.commit()
        flash('Job posting updated successfully', 'success')
        
        # Return JavaScript to close window and refresh parent
        return '''
            <script>
                alert('Job updated successfully!');
                window.opener.location.reload();  // Refresh the parent window
                window.close();  // Close the edit window
            </script>
        '''
        
    except Exception as e:
        print(f"Error updating job: {str(e)}")
        flash('Error updating job posting', 'danger')
        return redirect(url_for('update_job', job_id=job_id))

@app.route('/delete_job/<int:job_id>')
def delete_job(job_id):
    if 'user_id' not in session or session.get('user_type') != 'employer':
        flash('Please login as an employer to delete jobs', 'danger')
        return redirect(url_for('auth'))

    job = get_job_by_id(job_id)
    if str(job.employer_id) != session['user_id']:
        flash('You can only delete your own jobs', 'danger')
        return redirect(url_for('dashboard'))

    try:
        db.session.delete(job)
        db.session.commit()
        print(f"Job deleted: {job.title} by {job.company}")
        flash('Job deleted successfully!', 'success')
    except Exception as e:
        flash('Error deleting job. Please try again.', 'danger')
        print(f"Error deleting job: {str(e)}")
    
    return redirect(url_for('dashboard'))

@app.route('/view_applications/<int:job_id>')
def view_applications(job_id):
    if not session.get('user_id'):
        flash('You must be logged in to view applications.', 'error')
        return redirect(url_for('auth'))

    try:
        # Get job details
        job = get_job_by_id(job_id)
        
        if not job:
            flash('Job not found.', 'error')
            return redirect(url_for('dashboard'))

        # Check if user has permission (admin or employer of the job)
        if not (is_admin() or (session.get('user_type') == 'employer' and str(job.employer_id) == session.get('user_id'))):
            flash('You do not have permission to view these applications.', 'error')
            return redirect(url_for('dashboard'))

        # Get all applications for the job
        applications = list(get_job_applications(job.id))

        return render_template('view_applications.html', 
                             applications=applications, 
                             job=job,
                             is_admin=is_admin())

    except Exception as e:
        print(f"Error viewing applications: {e}")
        flash('An error occurred while retrieving applications.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/update_application_status/<int:application_id>', methods=['POST'])
def update_application_status(application_id):
    if not session.get('user_id'):
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('auth'))

    try:
        new_status = request.form.get('status')
        if new_status not in ['Pending', 'Accepted', 'Rejected']:
            flash('Invalid status value.', 'error')
            return redirect(request.referrer)

        # Get the application
        application = Application.query.get(application_id)
        
        if not application:
            flash('Application not found.', 'error')
            return redirect(request.referrer)
            
        # Check if user has permission (admin or employer of the job)
        job = get_job_by_id(application.job_id)
        if not (is_admin() or (session.get('user_type') == 'employer' and str(job.employer_id) == session.get('user_id'))):
            flash('You do not have permission to update this application.', 'error')
            return redirect(request.referrer)

        # Update the application status
        application.status = new_status
        db.session.commit()

        flash(f'Application status updated to {new_status}.', 'success')
        return redirect(request.referrer)

    except Exception as e:
        print(f"Error updating application status: {e}")
        flash('An error occurred while updating the application status.', 'error')
        return redirect(request.referrer)

@app.route('/view_cv/<filename>')
def view_cv(filename):
    if 'user_id' not in session:
        flash('Please login to view CV files', 'danger')
        return redirect(url_for('auth'))
    
    # Check if the user has permission to view this CV
    application = Application.query.filter_by(cv_file=filename).first()
    if not application:
        flash('CV file not found', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if the user is either the job seeker who applied or the employer who posted the job
    if session['user_type'] == 'employer':
        job = get_job_by_id(application.job_id)
        if str(job.employer_id) != session['user_id']:
            flash('You do not have permission to view this CV', 'danger')
            return redirect(url_for('dashboard'))
    elif session['user_type'] == 'job_seeker' and str(application.job_seeker_id) != session['user_id']:
        flash('You do not have permission to view this CV', 'danger')
        return redirect(url_for('dashboard'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')
            
            if not all([name, email, subject, message]):
                flash('Please fill in all fields', 'danger')
                return redirect(url_for('contact'))
            
            flash('Thank you for your message! We will get back to you soon.', 'success')
        except Exception as e:
            print(f"Error processing contact form: {str(e)}")
            flash('Error sending message. Please try again.', 'danger')
        return redirect(url_for('contact'))
    
    try:
        # Get all reviews for display, ordered by most recent first
        reviews = Review.query.order_by(Review.date.desc()).all()
        return render_template('contact.html', reviews=reviews)
    except Exception as e:
        print(f"Error fetching reviews: {str(e)}")
        return render_template('contact.html', reviews=[])

@app.route('/add_review', methods=['POST'])
def add_review():
    try:
        print("Received review submission:")
        print(f"Form data: {request.form}")
        
        name = request.form.get('name', '').strip()
        rating = request.form.get('rating')
        comment = request.form.get('comment', '').strip()

        print(f"Processed data - Name: {name}, Rating: {rating}, Comment: {comment}")

        # Validate inputs
        if not name or not comment:
            print("Validation failed: Missing name or comment")
            return jsonify({
                'status': 'error',
                'message': 'Please fill in both name and comment fields'
            }), 400

        try:
            rating = int(rating) if rating else None
            if not rating or rating < 1 or rating > 5:
                print(f"Validation failed: Invalid rating value: {rating}")
                return jsonify({
                    'status': 'error',
                    'message': 'Please select a rating between 1 and 5 stars'
                }), 400
        except (TypeError, ValueError) as e:
            print(f"Rating validation error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Please select a valid rating'
            }), 400

        # Create and save the review
        review = Review(name=name, rating=rating, comment=comment, date=datetime.utcnow())
        db.session.add(review)
        db.session.commit()
        
        print(f"Review saved successfully")
        
        # Return the new review data
        return jsonify({
            'status': 'success',
            'message': 'Thank you for your review!'
        })
        
    except Exception as e:
        print(f"Error adding review: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error submitting review. Please try again.'
        }), 500

@app.route('/database')
def view_database():
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    try:
        # Get all data from tables
        users = User.query.all()
        jobs = Job.query.all()
        applications = Application.query.all()
        reviews = Review.query.all()
        
        return render_template('database.html', 
                             users=users,
                             jobs=jobs,
                             applications=applications,
                             reviews=reviews)
    except Exception as e:
        flash('Error accessing database', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/admin/delete_job/<int:job_id>')
def admin_delete_job(job_id):
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    try:
        job = get_job_by_id(job_id)
        if job:
            # Delete associated applications first
            Application.query.filter_by(job_id=job_id).delete()
            db.session.delete(job)
            db.session.commit()
            flash('Job and associated applications deleted successfully!', 'success')
        else:
            flash('Job not found', 'danger')
    except Exception as e:
        print(f"Error deleting job: {str(e)}")
        flash('Error deleting job', 'danger')
    
    return redirect(url_for('view_database'))

@app.route('/admin/delete_user/<int:user_id>')
def admin_delete_user(user_id):
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    try:
        user = get_user_by_id(user_id)
        if user:
            if user.is_admin:
                flash('Cannot delete admin user', 'danger')
                return redirect(url_for('view_database'))
                
            # Delete associated jobs and applications
            jobs = Job.query.filter_by(employer_id=user_id).all()
            for job in jobs:
                Application.query.filter_by(job_id=job.id).delete()
            Job.query.filter_by(employer_id=user_id).delete()
            
            # Delete user's applications
            Application.query.filter_by(job_seeker_id=user_id).delete()
            
            # Finally delete the user
            db.session.delete(user)
            db.session.commit()
            flash('User and associated data deleted successfully!', 'success')
        else:
            flash('User not found', 'danger')
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        flash('Error deleting user', 'danger')
    
    return redirect(url_for('view_database'))

@app.route('/admin/delete_application/<int:application_id>')
def admin_delete_application(application_id):
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    try:
        application = Application.query.get(application_id)
        if application:
            # Delete CV file if exists
            if application.cv_file:
                try:
                    cv_path = os.path.join(app.config['UPLOAD_FOLDER'], application.cv_file)
                    if os.path.exists(cv_path):
                        os.remove(cv_path)
                except Exception as e:
                    print(f"Error deleting CV file: {str(e)}")
            
            db.session.delete(application)
            db.session.commit()
            flash('Application deleted successfully!', 'success')
        else:
            flash('Application not found', 'danger')
    except Exception as e:
        print(f"Error deleting application: {str(e)}")
        flash('Error deleting application', 'danger')
    
    return redirect(url_for('view_database'))

@app.route('/admin/edit_job/<int:job_id>', methods=['GET', 'POST'])
def admin_edit_job(job_id):
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        job = get_job_by_id(job_id)
        if not job:
            flash('Job not found', 'danger')
            return redirect(url_for('view_database'))

        if request.method == 'GET':
            return render_template('edit_job.html', job=job, is_admin=True)
        
        # Handle POST request
        job.title = request.form.get('title', '').strip()
        job.company = request.form.get('company', '').strip()
        job.description = request.form.get('description', '').strip()
        job.location = request.form.get('location', '').strip()
        
        if not all([job.title, job.company, job.description, job.location]):
            flash('All fields are required', 'danger')
            return redirect(url_for('admin_edit_job', job_id=job_id))
            
        try:
            deadline_str = request.form.get('deadline', '').strip()
            job.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(url_for('admin_edit_job', job_id=job_id))
        
        db.session.commit()
        flash('Job posting updated successfully', 'success')
        return redirect(url_for('view_database'))
        
    except Exception as e:
        print(f"Error updating job: {str(e)}")
        flash('Error updating job posting', 'danger')
        return redirect(url_for('admin_edit_job', job_id=job_id))

@app.route('/admin/delete_review/<int:review_id>')
def admin_delete_review(review_id):
    """Delete a review (admin only)"""
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        review = Review.query.get_or_404(review_id)
        db.session.delete(review)
        db.session.commit()
        flash('Review deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting review: {str(e)}', 'danger')
    
    return redirect(url_for('view_database'))

def create_admin_user():
    """Create admin user if it doesn't exist"""
    try:
        admin = get_user_by_email('admin@jobportal.com')
        if not admin:
            admin = User(
                name='Admin',
                email='admin@jobportal.com',
                password=generate_password_hash('admin123'),
                user_type='admin',
                is_admin=True,
                created_at=datetime.utcnow()
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        return admin
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        db.session.rollback()
        return None

def is_admin():
    """Check if current user is admin"""
    return session.get('user_id') and session.get('is_admin', False)

if __name__ == '__main__':
    app.run(debug=True) 



#Email: admin@jobportal.com
#Password: admin123