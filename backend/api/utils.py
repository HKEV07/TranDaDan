
import random
import string
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.core.cache import cache
from .tasks import send_reset_password_email
from enum import Enum
from .models import RelationshipType
import jwt
import datetime
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
# from rest_framework.views import exception_handler

User = get_user_model()

def unset_cookie_header(cookie):
    return {"Set-Cookie": f"{cookie}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Lax"}

def get_free_username(username):
    while User.objects.filter(username=username).first():
        username = f"{username}_{''.join(random.choices(string.ascii_letters + string.digits, k=5))}"
    return username

def get_free_game_nickname(nickname):
    while User.objects.filter(tournament_alias=nickname).first():
        nickname = f"{nickname}_{''.join(random.choices(string.ascii_letters + string.digits, k=5))}"
    return nickname

def get_reset_password_token_cache_key(token):
    return f"api_user_rest_password_token_{token}"

def reset_password_for_user(user_id, email, link, token):
    cache_key = get_reset_password_token_cache_key(token)
    expiration_time = timedelta(hours=1)
    cache.set(cache_key, user_id, timeout=expiration_time.total_seconds())
    send_reset_password_email(link, email)

def find_user_id_by_reset_token(token):
    cache_key = get_reset_password_token_cache_key(token)
    user_id = cache.get(cache_key)
    if not user_id:
        return None
    cache.delete(cache_key)
    return int(user_id)

def minuser(a, b):
    return min([a, b], key=lambda user: user.id)

def maxuser(a, b):
    return max([a, b], key=lambda user: user.id)


class RelativeRelationshipType(Enum):
    YOU_REQUEST = 1
    HE_REQUEST = 2
    FRIENDS = 3
    YOU_BLOCK = 4
    HE_BLOCK = 5
    BLOCK_BOTH = 6


def createRelativeRelation(uid, relationship):
    if relationship.type == RelationshipType.FRIENDS.value:
        return RelativeRelationshipType.FRIENDS.value
    if relationship.type == RelationshipType.BLOCK_BOTH.value:
        return RelativeRelationshipType.BLOCK_BOTH.value

    you_first = (relationship.first_user == uid)

    if (you_first):
        if (relationship.type == RelationshipType.PENDING_FIRST_SECOND.value):
            return RelativeRelationshipType.YOU_REQUEST.value
        elif relationship.type == RelationshipType.PENDING_SECOND_FIRST.value:
            return RelativeRelationshipType.HE_REQUEST.value
        elif relationship.type == RelationshipType.BLOCK_FIRST_SECOND.value:
            return RelativeRelationshipType.YOU_BLOCK.value
        elif relationship.type == RelationshipType.BLOCK_SECOND_FIRST.value:
            return RelativeRelationshipType.HE_BLOCK.value
    else:
        if (relationship.type == RelationshipType.PENDING_FIRST_SECOND.value):
            return RelativeRelationshipType.HE_REQUEST.value
        elif relationship.type == RelationshipType.PENDING_SECOND_FIRST.value:
            return RelativeRelationshipType.YOU_REQUEST.value
        elif relationship.type == RelationshipType.BLOCK_FIRST_SECOND.value:
            return RelativeRelationshipType.HE_BLOCK.value
        elif relationship.type == RelationshipType.BLOCK_SECOND_FIRST.value:
            return RelativeRelationshipType.YOU_BLOCK.value

    return 0

def generate_jwt(user, **kwargs):
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(hours=48)
    payload = {
        'uid': user.id,
        'exp': exp
    }
    payload.update(kwargs)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return token

def decode_jwt(token):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

def catch_em_all(exc, context):
    print(f"⚠️\nOps {exc}\n⚠️")
    return Response(f"Ops: {exc}", status=status.HTTP_422_UNPROCESSABLE_ENTITY)

