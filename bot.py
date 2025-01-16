# Project: WhatsApp Bot with Payment Integration

# Backend Code (Python Flask):

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client
import os
import time
import threading
from werkzeug.utils import secure_filename
import csv

# Initialize Flask App
app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///whatsapp_bot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Twilio Configuration
TWILIO_SID = 'your_twilio_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
WHATSAPP_NUMBER = 'your_twilio_whatsapp_number'
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    api_key = db.Column(db.String(100), unique=True, nullable=False)
    contacts = db.relationship('Contact', backref='user', lazy=True)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    phone = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Database Initialization
db.create_all()

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    incoming_msg = data.get('Body', '').strip()
    sender = data.get('From', '')

    # Logic to handle commands
    if incoming_msg.lower().startswith('save contacts'):
        group_name = incoming_msg.split(' ')[2]
        contacts = [{'name': 'John Doe', 'phone': '+1234567890'}]  # Example data
        user = User.query.filter_by(phone=sender).first()
        if user:
            for contact in contacts:
                new_contact = Contact(name=contact['name'], phone=contact['phone'], user_id=user.id)
                db.session.add(new_contact)
            db.session.commit()
            return jsonify({"message": "All Saved"})
        else:
            return jsonify({"message": "User not found."})

    elif incoming_msg.lower() == 'send':
        user = User.query.filter_by(phone=sender).first()
        if user:
            threading.Thread(target=send_messages, args=(user,)).start()
            return jsonify({"message": "Sending messages..."})
        else:
            return jsonify({"message": "User not found."})

    return jsonify({"message": "Command not recognized"})

def send_messages(user):
    user_contacts = Contact.query.filter_by(user_id=user.id).all()
    for contact in user_contacts:
        client.messages.create(
            from_=f'whatsapp:{WHATSAPP_NUMBER}',
            body=f"Hello {contact.name}, this is a test message.",
            to=f'whatsapp:{contact.phone}'
        )
        time.sleep(60)  # 1-minute interval

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"})

    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"})

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        save_contacts_from_file(filepath)
        return jsonify({"message": "Contacts uploaded successfully"})

def save_contacts_from_file(filepath):
    with open(filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            new_contact = Contact(name=row['name'], phone=row['phone'], user_id=1)  # Replace with dynamic user_id
            db.session.add(new_contact)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
