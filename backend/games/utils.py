from django.contrib.auth import get_user_model
import threading

class PlayersManager:
    _players = []
    _lock = threading.Lock()

    @classmethod
    def add_player(cls, username):
        with cls._lock:
            cls._players.append(username)

    @classmethod
    def remove_player(cls, username):
        with cls._lock:
            cls._players.remove(username)

    @classmethod
    def player_exists(cls, username):
        with cls._lock:
            return username in cls._players

class XPManager:
    def __init__(self, user, base_xp=100, growth_factor=1.5):
        self.user = user
        self.base_xp = base_xp
        self.growth_factor = growth_factor
        user.save()

    def xp_to_next_level(self):
        return int(self.base_xp * (self.growth_factor ** (self.user.level - 1)))

    def add_xp(self, amount):
        self.user.xp += amount
        self.check_level_up()

    def check_level_up(self):
        while self.user.xp >= self.xp_to_next_level():
            self.user.xp -= self.xp_to_next_level()
            self.user.level += 1

    def xp_progress(self):
        return int((self.user.xp / self.xp_to_next_level()) * 100)
