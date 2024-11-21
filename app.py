from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///current_affairs.db'
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(500), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Create the database
with app.app_context():
    db.create_all()
    # Create default users if they don't exist
    if not User.query.filter_by(username='user1').first():
        user1 = User(
            username='user1',
            password_hash=generate_password_hash('password1')
        )
        user2 = User(
            username='user2',
            password_hash=generate_password_hash('password2')
        )
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

NEWS_API_KEY = "9cefb20616e847dd92290ae924652579"
CATEGORIES = [
    "National",
    "International",
    "Economy",
    "Science & Technology",
    "Environment",
    "Polity & Governance",
    "Sports & Culture"
]

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', categories=CATEGORIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        
        return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/api/news/<category>')
def get_news(category):
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    days = request.args.get('days', 1, type=int)
    from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    search_terms = {
        "National": "India politics government",
        "International": "international relations diplomacy",
        "Economy": "India economy finance",
        "Science & Technology": "science technology innovation India",
        "Environment": "environment climate change India",
        "Polity & Governance": "(India constitution OR India supreme court OR India parliament OR India legislation OR India governance OR India policy OR India law OR India cabinet OR India ministry)",
        "Sports & Culture": "(India sports OR India cricket OR India olympics OR Indian culture OR Indian art)"
    }
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": search_terms[category],
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": 15,
        "apiKey": NEWS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bookmarks', methods=['GET', 'POST', 'DELETE'])
def handle_bookmarks():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    if request.method == 'GET':
        bookmarks = Bookmark.query.filter_by(user_id=session['user_id']).all()
        return jsonify([{
            'id': b.id,
            'title': b.title,
            'description': b.description,
            'url': b.url,
            'date_added': b.date_added.strftime('%Y-%m-%d %H:%M:%S')
        } for b in bookmarks])
    
    elif request.method == 'POST':
        data = request.json
        bookmark = Bookmark(
            title=data['title'],
            description=data.get('description', ''),
            url=data['url'],
            user_id=session['user_id']
        )
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({"message": "Bookmark added"})
    
    elif request.method == 'DELETE':
        bookmark_id = request.args.get('id')
        bookmark = Bookmark.query.get_or_404(bookmark_id)
        if bookmark.user_id != session['user_id']:
            return jsonify({"error": "Unauthorized"}), 403
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({"message": "Bookmark deleted"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
