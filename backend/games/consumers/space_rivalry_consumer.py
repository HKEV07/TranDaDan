from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio
import random
import math
import time
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from ..models import Match
from ..utils import PlayersManager, XPManager
from django.utils import timezone

class SpaceRivalryConsumer(AsyncWebsocketConsumer):
    shared_games = {}
    game_loops = {}
    active_connections = {}
    connection_timestamps = {}
    disconnection_cleanup_tasks = {}

    GAME_WIDTH = 800
    GAME_HEIGHT = 600
    SHIP_WIDTH = 40
    SHIP_HEIGHT = 30
    LASER_WIDTH = 4
    LASER_HEIGHT = 15
    ASTEROID_SIZE = 30
    DEBRIS_SIZE = 20
    POWERUP_SIZE = 25
    MOVEMENT_SPEED = 10

    POWERUPS = {
        'RAPID_FIRE': {'duration': 5000, 'color': 'yellow'},
        'SHIELD': {'duration': 8000, 'color': 'cyan'},
        'DOUBLE_BULLETS': {'duration': 6000, 'color': 'magenta'},
        'SLOW_MOTION': {'duration': 4000, 'color': 'lime'}
    }

    ASTEROID_TYPES = {
        'NORMAL': {'speed': 3, 'size': ASTEROID_SIZE, 'health': 1, 'points': 100},
        'FAST': {'speed': 5, 'size': ASTEROID_SIZE * 0.7, 'health': 1, 'points': 150},
        'SPLIT': {'speed': 2, 'size': ASTEROID_SIZE * 1.2, 'health': 1, 'points': 200},
        'EXPLODING': {'speed': 2, 'size': ASTEROID_SIZE * 1.3, 'health': 1, 'points': 300}
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = None
        self.game_id = None
        self.username = None
        self.player_num = None
        self.reconnection_grace_period = 0
        self.delta_time = 1/60

    @database_sync_to_async
    def check_match_status(self):
        try:
            match = Match.objects.get(id=self.game_id)
            return match.status == "completed"
        except Match.DoesNotExist:
            return False

    # @database_sync_to_async
    # def update_user_ingame(self, username, ingame):
    #     user = get_user_model().objects.filter(username=username).first()
    #     user.ingame = ingame
    #     user.save()

    async def connect(self):
        try:
            self.user = self.scope.get('user', None)

            if self.user is None:
                await self.close()
                return

            self.game_id = self.scope['url_route']['kwargs']['game_id']
            self.username = self.user.username

            # await self.update_user_ingame(self.username, True)
            PlayersManager.add_player(self.username)

            if not self.game_id or not self.username:
                await self.close()
                return

            self.room_group_name = f'space_rivalry_{self.game_id}'

            is_completed = await self.check_match_status()
            if is_completed:
                await self.close()
                return

            self.connection_timestamps[self.channel_name] = time.time()

            if self.game_id in self.disconnection_cleanup_tasks:
                self.disconnection_cleanup_tasks[self.game_id].cancel()
                del self.disconnection_cleanup_tasks[self.game_id]

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

            if self.game_id not in self.shared_games:
                self.initialize_game_state()
                if self.game_id not in self.game_loops:
                    self.game_loops[self.game_id] = asyncio.create_task(self.game_loop())

            if self.active_connections.get(self.game_id, 0) > 0:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'player_reconnected',
                        'message': 'Opponent has reconnected'
                    }
                )

            self.active_connections[self.game_id] = self.active_connections.get(self.game_id, 0) + 1
        except Exception:
            pass

    async def delayed_cleanup(self, game_id, player_number):
        try:
            await asyncio.sleep(self.reconnection_grace_period)

            if game_id in self.shared_games:
                game_state = self.shared_games[game_id]

                if not game_state.get('winner'):
                    disconnected_player = player_number
                    winning_player = 'player2' if disconnected_player == 'player1' else 'player1'

                    game_state['winner'] = game_state[winning_player]
                    game_state['gameOver'] = True
                    game_state['forfeit'] = True

                    winner_score = max(game_state['score1'], game_state['score2'])
                    game_state['score1'] = winner_score if winning_player == 'player1' else 0
                    game_state['score2'] = winner_score if winning_player == 'player2' else 0

                    await self.update_match_record(game_state)

                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'game_ended_by_forfeit',
                            'state': game_state,
                            'message': f'Game ended due to player disconnection. {game_state[winning_player]} wins by forfeit.'
                        }
                    )

                if game_id in self.game_loops:
                    self.game_loops[game_id].cancel()
                    del self.game_loops[game_id]

                if game_id in self.shared_games:
                    del self.shared_games[game_id]

                if game_id in self.active_connections:
                    del self.active_connections[game_id]

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in delayed cleanup for game {game_id}: {e}")

    async def disconnect(self, close_code):
        try:
            if not hasattr(self, 'game_id'):
                return

            disconnect_time = time.time()
            connection_time = self.connection_timestamps.get(self.channel_name, disconnect_time)
            connection_duration = disconnect_time - connection_time

            self.connection_timestamps.pop(self.channel_name, None)

            # await self.update_user_ingame(self.username, False)

            PlayersManager.remove_player(self.username)
            print(f"players: {PlayersManager._players}")
            if connection_duration < 1:
                await self.handle_unstable_connection()
                return

            cleanup_task = asyncio.create_task(
                self.delayed_cleanup(self.game_id, self.player_num)
            )
            self.disconnection_cleanup_tasks[self.game_id] = cleanup_task

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_disconnected',
                    'player': self.player_num,
                    'message': 'Opponent disconnected. Waiting for reconnection...'
                }
            )

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            if self.game_id in self.active_connections:
                self.active_connections[self.game_id] -= 1
        except Exception:
            pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            game_state = self.shared_games[self.game_id]

            if data['type'] == 'init':
                if data['isPlayer1']:
                    self.player_num = 'player1'
                    game_state['player1'] = data['username']
                    game_state['player2'] = data['opponent']
                else:
                    self.player_num = 'player2'
                    game_state['player1'] = data['opponent']
                    game_state['player2'] = data['username']

                if game_state['player1'] and game_state['player2']:
                    game_state['gameStarted'] = True

            elif data['type'] == 'player_input':
                self.handle_player_input(data['input'])

            await self.broadcast_game_state()

        except Exception as e:
            print(f"Error in receive: {e}")
            await self.send_error("An error occurred processing your input")

    async def game_ended_by_forfeit(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_ended_by_forfeit',
            'state': event['state'],
            'message': event['message']
        }))

    async def handle_unstable_connection(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'connection_warning',
                'message': 'Unstable connection detected. Please check your internet connection.'
            }
        )

    def handle_player_input(self, input_type):
        game_state = self.shared_games[self.game_id]
        player_pos_key = f'player{self.player_num[-1]}Pos'

        if input_type == 'left':
            current_pos = game_state[player_pos_key]
            min_pos = self.SHIP_WIDTH/2 if self.player_num == 'player1' else self.GAME_WIDTH/2 + self.SHIP_WIDTH/2
            game_state[player_pos_key] = max(min_pos, current_pos - self.MOVEMENT_SPEED)

        elif input_type == 'right':
            current_pos = game_state[player_pos_key]
            max_pos = self.GAME_WIDTH/2 - self.SHIP_WIDTH/2 if self.player_num == 'player1' else self.GAME_WIDTH - self.SHIP_WIDTH/2
            game_state[player_pos_key] = min(max_pos, current_pos + self.MOVEMENT_SPEED)

        elif input_type == 'shoot':
            self.handle_shooting(game_state)

    def handle_shooting(self, game_state):
        player_num = int(self.player_num[-1])
        current_time = time.time() * 1000
        last_shot_key = f'lastShot{player_num}'

        if current_time - game_state.get(last_shot_key, 0) >= self.get_shooting_cooldown(game_state, player_num):
            player_pos = game_state[f'player{player_num}Pos']
            lasers_key = f'lasers{player_num}'
            effects = game_state[f'activeEffects{player_num}']

            if effects.get('DOUBLE_BULLETS', {}).get('active'):
                game_state[lasers_key].extend([
                    {'x': player_pos - 10, 'y': self.GAME_HEIGHT - self.SHIP_HEIGHT - 10},
                    {'x': player_pos + 10, 'y': self.GAME_HEIGHT - self.SHIP_HEIGHT - 10}
                ])
            else:
                game_state[lasers_key].append({
                    'x': player_pos,
                    'y': self.GAME_HEIGHT - self.SHIP_HEIGHT - 10
                })

            game_state[last_shot_key] = current_time

    def get_shooting_cooldown(self, game_state, player_num):
        effects = game_state[f'activeEffects{player_num}']
        return 250 if effects.get('RAPID_FIRE', {}).get('active') else 500

    async def game_loop(self):
        try:
            while True:
                if self.game_id in self.shared_games:
                    game_state = self.shared_games[self.game_id]
                    current_time = time.time()
                    dt = current_time - game_state['lastUpdate']

                    if game_state['gameStarted'] and not game_state['gameOver']:
                        self.update_game_state(dt)
                        game_state['lastUpdate'] = current_time
                        await self.check_game_over()
                        await self.broadcast_game_state()

                await asyncio.sleep(self.delta_time)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in game loop: {e}")

    def initialize_game_state(self):
        self.shared_games[self.game_id] = {
            'gameStarted': False,
            'gameOver': False,
            'player1': None,
            'player2': None,
            'player1Pos': self.GAME_WIDTH / 4,
            'player2Pos': 3 * self.GAME_WIDTH / 4,
            'health1': 75,
            'health2': 75,
            'score1': 0,
            'score2': 0,
            'lasers1': [],
            'lasers2': [],
            'asteroids': [],
            'debris': [],
            'powerups': [],
            'explosions': [],
            'activeEffects1': {},
            'activeEffects2': {},
            'combo1': 0,
            'combo2': 0,
            'wave': 1,
            'difficulty': 1,
            'lastUpdate': time.time(),
            'winner': None,
            'forfeit': False
        }

    def update_game_state(self, dt):
        game_state = self.shared_games[self.game_id]

        self.update_lasers(game_state)

        slow_motion = any(
            game_state[f'activeEffects{i}'].get('SLOW_MOTION', {}).get('active')
            for i in [1, 2]
        )
        speed_multiplier = 0.5 if slow_motion else 1

        self.update_asteroids(game_state, speed_multiplier)

        self.update_powerups(game_state)

        self.update_debris(game_state)

        self.update_explosions(game_state)

        self.check_all_collisions(game_state)

        game_state['difficulty'] = min(game_state['difficulty'] + 0.1 * dt / 30, 10)

        if random.random() < 0.02 * game_state['difficulty']:
            self.spawn_asteroid(game_state)

    def update_lasers(self, game_state):
        for player in [1, 2]:
            game_state[f'lasers{player}'] = [
                {**laser, 'y': laser['y'] - 10}
                for laser in game_state[f'lasers{player}']
                if laser['y'] > 0
            ]

    def update_asteroids(self, game_state, speed_multiplier):
        game_state['asteroids'] = [
            {**asteroid, 'y': asteroid['y'] + asteroid['speed'] * speed_multiplier}
            for asteroid in game_state['asteroids']
            if asteroid['y'] < self.GAME_HEIGHT + asteroid['size']
        ]

    def update_powerups(self, game_state):
        current_time = time.time() * 1000

        game_state['powerups'] = [
            {**powerup, 'y': powerup['y'] + 2}
            for powerup in game_state['powerups']
            if powerup['y'] < self.GAME_HEIGHT
        ]

        for player in [1, 2]:
            effects_key = f'activeEffects{player}'
            for powerup_type, effect in game_state[effects_key].items():
                if effect.get('active') and current_time >= effect.get('endsAt', 0):
                    game_state[effects_key][powerup_type] = {'active': False}

    def update_debris(self, game_state):
        game_state['debris'] = [
            {**debris, 'y': debris['y'] + 3}
            for debris in game_state['debris']
            if debris['y'] < self.GAME_HEIGHT
        ]

    def update_explosions(self, game_state):
        current_time = time.time() * 1000
        game_state['explosions'] = [
            explosion for explosion in game_state['explosions']
            if current_time - explosion['created'] < 500
        ]

    def check_all_collisions(self, game_state):

        self.check_laser_collisions(game_state, 1)
        self.check_laser_collisions(game_state, 2)

        self.check_ship_collisions(game_state)

        self.check_powerup_collisions(game_state)

    def check_laser_collisions(self, game_state, player_num):
        lasers_key = f'lasers{player_num}'
        new_lasers = []
        current_time = time.time() * 1000

        for laser in game_state[lasers_key]:
            hit = False
            for asteroid in game_state['asteroids'][:]:
                if self.check_collision(
                    laser['x'], laser['y'], self.LASER_WIDTH, self.LASER_HEIGHT,
                    asteroid['x'], asteroid['y'], asteroid['size'], asteroid['size']
                ):
                    hit = True
                    game_state['asteroids'].remove(asteroid)

                    if asteroid['type'] == 'SPLIT':
                        self.split_asteroid(game_state, asteroid)
                    elif asteroid['type'] == 'EXPLODING':
                        self.create_explosion(game_state, asteroid)
                        self.damage_nearby_asteroids(game_state, asteroid)

                    self.update_score(game_state, player_num, asteroid['points'])

                    if random.random() < 0.2:
                        self.spawn_powerup(game_state, asteroid)

                    self.create_debris(game_state, asteroid, 3 - player_num)
                    break

            if not hit:
                new_lasers.append(laser)

        game_state[lasers_key] = new_lasers

    def check_ship_collisions(self, game_state):
        for player_num in [1, 2]:
            if game_state[f'activeEffects{player_num}'].get('SHIELD', {}).get('active'):
                continue

            ship_pos = game_state[f'player{player_num}Pos']

            for asteroid in game_state['asteroids'][:]:
                if self.check_collision(
                    ship_pos, self.GAME_HEIGHT - self.SHIP_HEIGHT, self.SHIP_WIDTH, self.SHIP_HEIGHT,
                    asteroid['x'], asteroid['y'], asteroid['size'], asteroid['size']
                ):
                    game_state[f'health{player_num}'] = max(0, game_state[f'health{player_num}'] - 20)
                    game_state['asteroids'].remove(asteroid)

            for debris in game_state['debris'][:]:
                if debris['targetPlayer'] == player_num and self.check_collision(
                    ship_pos, self.GAME_HEIGHT - self.SHIP_HEIGHT, self.SHIP_WIDTH, self.SHIP_HEIGHT,
                    debris['x'], debris['y'], self.DEBRIS_SIZE, self.DEBRIS_SIZE
                ):
                    game_state[f'health{player_num}'] = max(0, game_state[f'health{player_num}'] - 10)
                    game_state['debris'].remove(debris)

    def check_powerup_collisions(self, game_state):
        current_time = time.time() * 1000

        for player_num in [1, 2]:
            ship_pos = game_state[f'player{player_num}Pos']

            for powerup in game_state['powerups'][:]:
                if self.check_collision(
                    ship_pos, self.GAME_HEIGHT - self.SHIP_HEIGHT, self.SHIP_WIDTH, self.SHIP_HEIGHT,
                    powerup['x'], powerup['y'], self.POWERUP_SIZE, self.POWERUP_SIZE
                ):
                    # Activate power-up
                    effects_key = f'activeEffects{player_num}'
                    game_state[effects_key][powerup['type']] = {
                        'active': True,
                        'endsAt': current_time + self.POWERUPS[powerup['type']]['duration']
                    }
                    game_state['powerups'].remove(powerup)

    def check_collision(self, x1, y1, w1, h1, x2, y2, w2, h2):
        return (
            abs(x1 - x2) * 2 < (w1 + w2) and
            abs(y1 - y2) * 2 < (h1 + h2)
        )

    def update_score(self, game_state, player_num, points):
        combo_key = f'combo{player_num}'
        score_key = f'score{player_num}'

        game_state[combo_key] += 1
        combo_multiplier = 1 + game_state[combo_key] // 5
        game_state[score_key] += points * combo_multiplier

        game_state[f'lastHit{player_num}'] = time.time() * 1000

    def spawn_asteroid(self, game_state):
        asteroid_type = random.choice(list(self.ASTEROID_TYPES.keys()))
        asteroid_data = self.ASTEROID_TYPES[asteroid_type]

        game_state['asteroids'].append({
            'x': random.uniform(0, self.GAME_WIDTH),
            'y': -asteroid_data['size'],
            'type': asteroid_type,
            **asteroid_data
        })

    def split_asteroid(self, game_state, asteroid):
        for offset in [-20, 20]:
            game_state['asteroids'].append({
                'x': asteroid['x'] + offset,
                'y': asteroid['y'],
                'type': 'NORMAL',
                **self.ASTEROID_TYPES['NORMAL']
            })

    def create_explosion(self, game_state, asteroid):
        game_state['explosions'].append({
            'x': asteroid['x'],
            'y': asteroid['y'],
            'created': time.time() * 1000
        })

    def damage_nearby_asteroids(self, game_state, exploding_asteroid):
        explosion_radius = 100
        for asteroid in game_state['asteroids'][:]:
            dx = asteroid['x'] - exploding_asteroid['x']
            dy = asteroid['y'] - exploding_asteroid['y']
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < explosion_radius:
                game_state['asteroids'].remove(asteroid)

    def spawn_powerup(self, game_state, asteroid):
        powerup_type = random.choice(list(self.POWERUPS.keys()))
        game_state['powerups'].append({
            'x': asteroid['x'],
            'y': asteroid['y'],
            'type': powerup_type,
            **self.POWERUPS[powerup_type]
        })

    def create_debris(self, game_state, asteroid, target_player):
        game_state['debris'].append({
            'x': asteroid['x'],
            'y': asteroid['y'],
            'targetPlayer': target_player
        })

    async def check_game_over(self):
        game_state = self.shared_games[self.game_id]

        if game_state['health1'] <= 0 or game_state['health2'] <= 0:
            game_state['gameOver'] = True
            winner = game_state['player2'] if game_state['health1'] <= 0 else game_state['player1']
            game_state['winner'] = winner

            await self.update_match_record(game_state)
            await self.broadcast_game_end(winner)

    @database_sync_to_async
    def update_match_record(self, game_state):
        try:
            match = Match.objects.get(id=self.game_id)
            winner_username = game_state['winner']
            winner_user = get_user_model().objects.get(username=winner_username)
            xp_manager = XPManager(winner_user)
            xp_manager.add_xp(50)
            winner_user.save()

            match.winner = winner_user
            match.score_player1 = game_state['score1']
            match.score_player2 = game_state['score2']
            match.forfeit = game_state['forfeit']
            match.ended_at = timezone.now()

            match.status = "completed"
            match.save()
        except Exception as e:
            print(f"Error updating match record: {e}")

    async def broadcast_game_end(self, winner):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_ended',
                'winner': winner,
                'state': self.shared_games[self.game_id]
            }
        )

    async def broadcast_game_state(self):
        if self.game_id in self.shared_games:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_state_update',
                    'state': self.shared_games[self.game_id]
                }
            )

    async def game_state_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'state': event['state']
        }))

    async def player_disconnected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_disconnected',
            'message': event['message']
        }))

    async def player_reconnected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_reconnected',
            'message': event['message']
        }))

    async def game_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_ended',
            'winner': event['winner'],
            'state': event['state']
        }))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
