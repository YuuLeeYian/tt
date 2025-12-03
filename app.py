from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Player, Game
try:
    from stats import StreakCalculator
    STREAK_CALCULATOR_AVAILABLE = True
except ImportError:
    STREAK_CALCULATOR_AVAILABLE = False
    print("Warning: stats.py not found - streak features will be disabled")
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

    # Optional compare player id from query string (GET)
    compare_id = request.args.get('compare_id', type=int)

    # Provide a list of players for the compare dropdown
    players = Player.query.order_by(Player.name).all()

    # Base query: games involving this player
    base_q = Game.query.filter((Game.player1_id == player_id) | (Game.player2_id == player_id))

    compare_player = None
    if compare_id:
        compare_player = Player.query.get(compare_id)
        if compare_player:
            # further restrict to games between the two players
            base_q = base_q.filter((Game.player1_id == compare_id) | (Game.player2_id == compare_id))

    games = base_q.order_by(Game.played_at.desc()).all()

    # Compute stats based on the filtered games
    games_played = len(games)
    wins = sum(1 for g in games if hasattr(g, 'winner_id') and g.winner_id == player.id)
    losses = games_played - wins
    win_rate = (wins / games_played * 100) if games_played > 0 else 0

    # Calculate streaks
    current_streak = 0
    best_streak = 0
    worst_streak = 0
    if STREAK_CALCULATOR_AVAILABLE and games_played > 0:
        try:
            streaker = StreakCalculator(db.session)
            current_streak, best_streak, worst_streak = streaker.get_current_and_best(player_id, games=games)
        except Exception as e:
            print(f"Warning: Could not calculate streaks for player {player_id}: {e}")

    return render_template('player_history.html', player=player, games=games, players=players, compare_player=compare_player, compare_id=compare_id, games_played=games_played, wins=wins, losses=losses, win_rate=win_rate, current_streak=current_streak, best_streak=best_streak, worst_streak=worst_streak)

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
    
    # Calculate current winning streaks for all players
    players = Player.query.all()
    hottest_streak_player = None
    max_streak = 0
    coldest_streak_player = None
    min_streak = 0
    best_streak_player = None
    best_streak_all_time = 0
    
    if STREAK_CALCULATOR_AVAILABLE:
        try:
            streaker = StreakCalculator(db.session)
            for player in players:
                # Get all games for this player, ordered by most recent first
                games = Game.query.filter(
                    (Game.player1_id == player.id) | (Game.player2_id == player.id)
                ).order_by(Game.played_at.desc()).all()

                # Use the streak helper with the already-fetched games to avoid extra queries
                current_streak, best_win_streak, _ = streaker.get_current_and_best(player.id, games=games)

                # Track player with longest positive streak (current)
                if current_streak > max_streak:
                    max_streak = current_streak
                    hottest_streak_player = player
                
                # Track player with best streak of all time
                if best_win_streak > best_streak_all_time:
                    best_streak_all_time = best_win_streak
                    best_streak_player = player
                
                # Track player with longest negative streak (losing streak)
                if current_streak < min_streak:
                    min_streak = current_streak
                    coldest_streak_player = player
        except Exception as e:
            # Gracefully handle missing stats module or other errors for backward compatibility
            print(f"Warning: Could not calculate streaks: {e}")
            hottest_streak_player = None
            coldest_streak_player = None
            max_streak = 0
    
    return render_template('statistics.html', 
                         total_players=total_players,
                         total_games=total_games,
                         top_player=top_player,
                         most_active=most_active,
                         hottest_streak_player=hottest_streak_player,
                         hottest_streak=max_streak,
                         coldest_streak_player=coldest_streak_player,
                         coldest_streak=min_streak,
                         best_streak_player=best_streak_player,
                         best_streak_all_time=best_streak_all_time)

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


@app.route('/delete_game/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    """Delete a game and retract the ELO changes from the two players.

    This operation only retracts the ELO change and updates simple stats
    (games_played, wins, losses) for both players. It does not recompute
    or alter other games' stored ELO fields — history entries remain as-is
    except that this game record is removed.
    """
    game = Game.query.get_or_404(game_id)

    # Compute deltas from the stored before/after values
    delta1 = game.player1_elo_after - game.player1_elo_before
    delta2 = game.player2_elo_after - game.player2_elo_before

    # Load players (they should normally exist)
    p1 = Player.query.get(game.player1_id)
    p2 = Player.query.get(game.player2_id)

    # Retract ELO and decrement stats safely
    if p1:
        p1.elo_rating = (p1.elo_rating or 0) - delta1
        p1.games_played = max(0, (p1.games_played or 0) - 1)
        if game.winner_id == p1.id:
            p1.wins = max(0, (p1.wins or 0) - 1)
        else:
            p1.losses = max(0, (p1.losses or 0) - 1)

    if p2:
        p2.elo_rating = (p2.elo_rating or 0) - delta2
        p2.games_played = max(0, (p2.games_played or 0) - 1)
        if game.winner_id == p2.id:
            p2.wins = max(0, (p2.wins or 0) - 1)
        else:
            p2.losses = max(0, (p2.losses or 0) - 1)

    db.session.delete(game)
    db.session.commit()

    flash('Game deleted and ELO retracted from the affected players.', 'success')
    # Redirect back to the referring page or recent games if unknown
    return redirect(request.referrer or url_for('recent_games'))

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
