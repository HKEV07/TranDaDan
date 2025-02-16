import json
from channels.db import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from ..utils import PlayersManager
from ..models import Match
import time
from channels.db import database_sync_to_async
from api.models import UserRelationship, RelationshipType
from django.db import models

class InviteConsumer(AsyncJsonWebsocketConsumer):
    active_connections = {}
    pending_invites = {}

    async def connect(self):
        try:
            user = self.user = self.scope.get('user', None)
            if self.user is None:
                await self.close()
                return
            self.username = user.username
            ingame_status = PlayersManager.player_exists(user.username)
            if ingame_status:
                await self.close()
                print(f"jhh ingame_status: {ingame_status}")
                return


            InviteConsumer.active_connections[self.username] = self

            await self.accept()

            pending = InviteConsumer.pending_invites.get(self.username, [])
            for invite in pending:
                await self.send_json(invite)
        except Exception:
            pass

    async def disconnect(self, code):
        if hasattr(self, 'username') and self.username in InviteConsumer.active_connections:
            del InviteConsumer.active_connections[self.username]

        if hasattr(self, 'username') and self.username in InviteConsumer.pending_invites:
            del InviteConsumer.pending_invites[self.username]

    async def receive_json(self, content):
        try:
            msg_type = content.get('type')

            if msg_type == 'send_invite':
                await self.handle_send_invite(content)
            elif msg_type == 'accept_invite':
                await self.handle_accept_invite(content)
            elif msg_type == 'decline_invite':
                await self.handle_decline_invite(content)
        except Exception:
            pass

    async def handle_send_invite(self, content):
        target_username = content.get('target_username')
        game_type = content.get('game_type', 'pong')

        if target_username == self.username:
            await self.send_json({
                'type': 'invite_error',
                'message': 'Cannot invite yourself'
            })
            return

        target_connection = InviteConsumer.active_connections.get(target_username)

        invite_data = {
            'type': 'game_invite',
            'from_username': self.username,
            'game_type': game_type,
            'timestamp': time.time()
        }

        if target_connection:
            await target_connection.send_json(invite_data)
        else:
            if target_username not in InviteConsumer.pending_invites:
                InviteConsumer.pending_invites[target_username] = []
            InviteConsumer.pending_invites[target_username].append(invite_data)

        await self.send_json({
            'type': 'invite_sent',
            'target_username': target_username
        })

    async def handle_accept_invite(self, content):
        from_username = content.get('from_username')
        inviter_connection = InviteConsumer.active_connections.get(from_username)


        if not inviter_connection:
            await self.send_json({
                'type': 'invite_error',
                'message': 'Inviter is no longer online'
            })
            return

        player1 = self.scope['user']
        player2 = inviter_connection.scope['user']

        if player1 == player2:
            await self.send_json({
                'type': 'invite_error',
                'message': 'Cannot invite yourself'
            })
            return
        if not await self.is_friend(player1, player2):
            await self.send_json({
                'type': 'invite_error',
                'message': 'You guys are not friends.'
            })
            return
        match = await sync_to_async(Match.objects.create)(
            player1=self.scope['user'],
            player2=inviter_connection.scope['user'],
            game_type=content.get('game_type', 'pong'),
            status="ongoing"
        )

        match_data = {
            'type': 'invite_accepted',
            'game_id': match.id,
            'opponent': self.username,
            "player1" : player1.username,
            'game_type': match.game_type
        }
        await inviter_connection.send_json(match_data)

        await self.send_json({
            **match_data,
            'opponent': from_username
        })

    async def handle_decline_invite(self, content):
        from_username = content.get('from_username')
        inviter_connection = InviteConsumer.active_connections.get(from_username)

        if inviter_connection:
            await inviter_connection.send_json({
                'type': 'invite_declined',
                'by_username': self.username
            })

    @database_sync_to_async
    def is_friend(self, user, target_user):
        try:
            relationship = UserRelationship.objects.get(
                (models.Q(first_user=user) & models.Q(second_user=target_user)) |
                (models.Q(first_user=target_user) & models.Q(second_user=user))
            )
            if relationship.type == RelationshipType.FRIENDS.value:
                return True
            return False
        except UserRelationship.DoesNotExist:
            return False
