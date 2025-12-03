from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    elo_rating = db.Column(db.Integer, default=1500)
    games_played = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    games_as_player1 = db.relationship('Game', foreign_keys='Game.player1_id', backref='player1', lazy=True)
    games_as_player2 = db.relationship('Game', foreign_keys='Game.player2_id', backref='player2', lazy=True)
    
    def __repr__(self):
        return f'<Player {self.name}>'

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player1_elo_before = db.Column(db.Integer, nullable=False)
    player2_elo_before = db.Column(db.Integer, nullable=False)
    player1_elo_after = db.Column(db.Integer, nullable=False)
    player2_elo_after = db.Column(db.Integer, nullable=False)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Game {self.id}: {self.player1_id} vs {self.player2_id}>'
