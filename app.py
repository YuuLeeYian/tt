from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Player, Game
from datetime import datetime, timedelta, timezone
import math
import os

app = Flask(__name__)

# Ensure instance folder exists
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "tabletennis.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

db.init_app(app)
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

# ELO calculation constants
K_FACTOR = 32  # Standard K-factor for ELO calculation

def calculate_elo_change(rating1, rating2, player1_won):
    """
    Calculate ELO rating changes for two players.
    Returns (new_rating1, new_rating2)
    """
    # Expected scores
    expected1 = 1 / (1 + math.pow(10, (rating2 - rating1) / 400))
    expected2 = 1 / (1 + math.pow(10, (rating1 - rating2) / 400))
    
    # Actual scores (1 for win, 0 for loss)
    actual1 = 1 if player1_won else 0
    actual2 = 0 if player1_won else 1
    
    # Calculate new ratings
    new_rating1 = round(rating1 + K_FACTOR * (actual1 - expected1))
    new_rating2 = round(rating2 + K_FACTOR * (actual2 - expected2))
    
    return new_rating1, new_rating2

def compute_player_elo_history(player):
    """Return complete ELO history data points (initial + after each game with metadata)."""
    games = Game.query.filter(
        (Game.player1_id == player.id) | (Game.player2_id == player.id)
    ).order_by(Game.played_at.asc()).all()
    data_points = []
    created = player.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    initial_date = created or (games[0].played_at if games else datetime.now(timezone.utc))
    if initial_date.tzinfo is None:
        initial_date = initial_date.replace(tzinfo=timezone.utc)
    data_points.append({'date': initial_date.isoformat(), 'elo': 1500, 'type': 'initial'})
    for g in games:
        is_player1 = g.player1_id == player.id
        current_elo = g.player1_elo_after if is_player1 else g.player2_elo_after
        won = g.winner_id == player.id
        opponent = g.player2 if is_player1 else g.player1
        elo_change = current_elo - (g.player1_elo_before if is_player1 else g.player2_elo_before)
        played = g.played_at
        if played.tzinfo is None:
            played = played.replace(tzinfo=timezone.utc)
        data_points.append({
            'date': played.isoformat(),
            'elo': current_elo,
            'type': 'game',
            'result': 'win' if won else 'loss',
            'opponent': opponent.name,
            'elo_change': elo_change
        })
    return data_points

@app.route('/')
def index():
    """Show rankings/leaderboard"""
    players = Player.query.order_by(Player.elo_rating.desc()).all()
    return render_template('index.html', players=players)

@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    """Add a new player"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        
        if not name:
            flash('Player name is required!', 'error')
            return redirect(url_for('add_player'))
        
        # Check if player already exists
        existing_player = Player.query.filter_by(name=name).first()
        if existing_player:
            flash(f'Player "{name}" already exists!', 'error')
            return redirect(url_for('add_player'))
        
        # Create new player with default ELO of 1500
        new_player = Player(name=name)
        db.session.add(new_player)
        db.session.commit()
        
        flash(f'Player "{name}" added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_player.html')

@app.route('/add_game', methods=['GET', 'POST'])
def add_game():
    """Add a new game result"""
    if request.method == 'POST':
        winner_id = request.form.get('winner_id', type=int)
        loser_id = request.form.get('loser_id', type=int)
        
        # Validation
        if not all([winner_id, loser_id]):
            flash('All fields are required!', 'error')
            return redirect(url_for('add_game'))
        
        if winner_id == loser_id:
            flash('Winner and loser must be different players!', 'error')
            return redirect(url_for('add_game'))
        
        # Get players
        winner = Player.query.get(winner_id)
        loser = Player.query.get(loser_id)
        
        if not winner or not loser:
            flash('Invalid players selected!', 'error')
            return redirect(url_for('add_game'))
        
        # Store ELO ratings before the game
        winner_elo_before = winner.elo_rating
        loser_elo_before = loser.elo_rating
        
        # Calculate new ELO ratings (winner is always player1 in calculation)
        new_winner_elo, new_loser_elo = calculate_elo_change(
            winner.elo_rating, 
            loser.elo_rating, 
            True  # winner won
        )
        
        # Create game record (store winner as player1, loser as player2)
        game = Game(
            player1_id=winner_id,
            player2_id=loser_id,
            winner_id=winner_id,
            player1_elo_before=winner_elo_before,
            player2_elo_before=loser_elo_before,
            player1_elo_after=new_winner_elo,
            player2_elo_after=new_loser_elo
        )
        
        # Update player stats
        winner.elo_rating = new_winner_elo
        loser.elo_rating = new_loser_elo
        winner.games_played += 1
        loser.games_played += 1
        winner.wins += 1
        loser.losses += 1
        
        db.session.add(game)
        db.session.commit()
        
        flash(f'Game recorded! {winner.name} defeated {loser.name}', 'success')
        return redirect(url_for('index'))
    
    players = Player.query.order_by(Player.name).all()
    return render_template('add_game.html', players=players)

@app.route('/player/<int:player_id>')
def player_history(player_id):
    """Show game history for a specific player"""
    player = Player.query.get_or_404(player_id)
    
    # Get all games for this player
    games = Game.query.filter(
        (Game.player1_id == player_id) | (Game.player2_id == player_id)
    ).order_by(Game.played_at.desc()).all()
    
    return render_template('player_history.html', player=player, games=games)

@app.route('/recent_games')
def recent_games():
    """Show recent games across all players"""
    games = Game.query.order_by(Game.played_at.desc()).limit(20).all()
    return render_template('recent_games.html', games=games)

@app.route('/statistics')
def statistics():
    """Show overall statistics"""
    total_players = Player.query.count()
    total_games = Game.query.count()
    
    # Get top player
    top_player = Player.query.order_by(Player.elo_rating.desc()).first()
    
    # Get most active player
    most_active = Player.query.order_by(Player.games_played.desc()).first()
    
    return render_template('statistics.html', 
                         total_players=total_players,
                         total_games=total_games,
                         top_player=top_player,
                         most_active=most_active)

@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    """Delete a player (only if they haven't played any games)"""
    player = Player.query.get_or_404(player_id)
    
    if player.games_played > 0:
        flash(f'Cannot delete {player.name} - they have played games!', 'error')
        return redirect(url_for('index'))
    
    db.session.delete(player)
    db.session.commit()
    flash(f'Player {player.name} deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/api/player/<int:player_id>/elo_history')
def elo_history(player_id):
    """Return ELO history for a player with optional period filtering.
    Query param: period=hour|day|week|month|all (default all)
    Response JSON: { player_name, current_elo, data: [{date, elo}...] }
    Includes initial rating at player creation and rating after each game.
    """
    player = Player.query.get_or_404(player_id)
    period = request.args.get('period', 'all').lower()

    now = datetime.now(timezone.utc)
    period_map = {
        'hour': timedelta(hours=1),
        'day': timedelta(days=1),
        'week': timedelta(days=7),
        'month': timedelta(days=30)
    }
    cutoff = None if period == 'all' or period not in period_map else now - period_map[period]
    if period not in period_map and period != 'all':
        period = 'all'
    data_points = compute_player_elo_history(player)
    if cutoff:
        filtered = [pt for pt in data_points if datetime.fromisoformat(pt['date']) >= cutoff]
        data_points = filtered or (data_points[-1:] if data_points else [])

    return jsonify({
        'player_name': player.name,
        'current_elo': player.elo_rating,
        'period': period,
        'data': data_points
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3456)
