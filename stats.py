from sqlalchemy import text

class StreakCalculator:
    def __init__(self, db_session):
        self.db = db_session

    def get_current_and_best(self, player_id, games=None):
        """Return (current_streak, best_win_streak, worst_loss_streak) for player_id.
        Current streak is positive for wins, negative for losses.
        If `games` (list of Game ORM objects) is provided, fallback to Python scan only.
        Otherwise try SQL window-function queries first, falling back to Python if not supported.
        """
        # If games provided, use Python-only calculation
        if games is not None:
            # current streak (positive for wins, negative for losses)
            current = 0
            for g in games:
                # Safely check winner_id (backward compatibility)
                if hasattr(g, 'winner_id') and g.winner_id == player_id:
                    current += 1
                elif hasattr(g, 'winner_id'):
                    current -= 1
                else:
                    break

            # best win streak and worst loss streak
            best_win = 0
            worst_loss = 0
            win_run = 0
            loss_run = 0
            for g in reversed(games):
                # Safely check winner_id (backward compatibility)
                if hasattr(g, 'winner_id') and g.winner_id == player_id:
                    win_run += 1
                    loss_run = 0
                    if win_run > best_win:
                        best_win = win_run
                elif hasattr(g, 'winner_id'):
                    loss_run += 1
                    win_run = 0
                    if loss_run > worst_loss:
                        worst_loss = loss_run
                else:
                    win_run = 0
                    loss_run = 0
            return current, best_win, worst_loss

        # Otherwise, try SQL (window functions) for performance
        try:
            # Current streak (positive for wins, negative for losses)
            sql_current = text("""
            WITH player_games AS (
                SELECT id, winner_id, played_at,
                       CASE WHEN winner_id = :pid THEN 1 ELSE -1 END AS result
                FROM game
                WHERE player1_id = :pid OR player2_id = :pid
                ORDER BY played_at DESC
            ), streak_flags AS (
                SELECT *,
                       SUM(CASE WHEN result != LAG(result, 1, result) OVER (ORDER BY played_at DESC) THEN 1 ELSE 0 END) 
                       OVER (ORDER BY played_at DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS streak_group
                FROM player_games
            )
            SELECT COALESCE(SUM(result), 0) AS current_streak 
            FROM streak_flags 
            WHERE streak_group = 0;
            """)

            res = self.db.execute(sql_current, {"pid": player_id}).scalar()
            current = int(res or 0)

            # Best win streak
            sql_best_win = text("""
            WITH player_games AS (
                SELECT id, winner_id, played_at,
                       CASE WHEN winner_id = :pid THEN 1 ELSE 0 END AS is_win
                FROM game
                WHERE player1_id = :pid OR player2_id = :pid
                ORDER BY played_at ASC
            ), numbered AS (
                SELECT *, ROW_NUMBER() OVER (ORDER BY played_at) AS rn,
                       SUM(is_win) OVER (ORDER BY played_at) AS win_cum
                FROM player_games
            ), grouped AS (
                SELECT *, (rn - win_cum) AS grp
                FROM numbered
            )
            SELECT COALESCE(MAX(win_count), 0) FROM (
                SELECT grp, SUM(is_win) AS win_count
                FROM grouped
                GROUP BY grp
            );
            """)

            res_best_win = self.db.execute(sql_best_win, {"pid": player_id}).scalar()
            best_win = int(res_best_win or 0)

            # Worst loss streak
            sql_worst_loss = text("""
            WITH player_games AS (
                SELECT id, winner_id, played_at,
                       CASE WHEN winner_id != :pid THEN 1 ELSE 0 END AS is_loss
                FROM game
                WHERE player1_id = :pid OR player2_id = :pid
                ORDER BY played_at ASC
            ), numbered AS (
                SELECT *, ROW_NUMBER() OVER (ORDER BY played_at) AS rn,
                       SUM(is_loss) OVER (ORDER BY played_at) AS loss_cum
                FROM player_games
            ), grouped AS (
                SELECT *, (rn - loss_cum) AS grp
                FROM numbered
            )
            SELECT COALESCE(MAX(loss_count), 0) FROM (
                SELECT grp, SUM(is_loss) AS loss_count
                FROM grouped
                GROUP BY grp
            );
            """)

            res_worst_loss = self.db.execute(sql_worst_loss, {"pid": player_id}).scalar()
            worst_loss = int(res_worst_loss or 0)

            return current, best_win, worst_loss
        except Exception:
            # Fallback: Python scanning via ORM if SQL fails or DB lacks window functions
            # Load games via ORM
            from models import Game
            games = self.db.query(Game).filter((Game.player1_id == player_id) | (Game.player2_id == player_id)).order_by(Game.played_at.desc()).all()
            # reuse the games branch
            return self.get_current_and_best(player_id, games=games)
