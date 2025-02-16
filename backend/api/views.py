from django.contrib.auth import get_user_model, authenticate
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .authentication import NoAuthenticationOnly
from django.http import HttpResponseRedirect, HttpResponse
import requests
import random
import string
import environ
from django.urls import reverse
from django.utils import timezone
from .utils import (
    generate_jwt, unset_cookie_header, get_free_username,
    get_free_game_nickname, reset_password_for_user, find_user_id_by_reset_token,
    createRelativeRelation, RelativeRelationshipType
    )
from .serializers import (
    RegisterSerializer, LoginSerializer, RequestResetPasswordSerializer,
    ResetPasswordSerializer, UserUpdateSerializer, UserSearchSerializer
    )
from .tasks import send_registration_email
from .models import IntraConnection
import pyotp
import pyqrcode
import io
from django.utils.crypto import get_random_string
from .models import UserRelationship, RelationshipType
from django.db.models import Q
import base64
import uuid
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
from .xp_manager import XPManager

User = get_user_model()

env = environ.Env()
environ.Env.read_env()

class UnprotectedView(APIView):
    # ugh, currently refuse authenticated requests? empty array to accept all requests.
    authentication_classes = [NoAuthenticationOnly]

class OAuth2StartView(UnprotectedView):

    def get(self, request, *args, **kwargs):
        state = ''.join(random.choices(string.ascii_letters + string.digits, k=30))
        authorization_url = f'{os.getenv("42_AUTHORIZE_URL")}?client_id={os.getenv("CLIENT_ID")}&redirect_uri={os.getenv("BACKEND_URL")}{reverse("oauth2-callback")}&response_type=code'
        response = HttpResponseRedirect(authorization_url)
        # response.set_cookie('oauth2_state', jwt.encode({"state": state}, settings.SECRET_KEY, algorithm='HS256'))
        return response


class OAuth2CallbackView(UnprotectedView):
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        code = request.GET.get('code')
        # state = request.GET.get('state')
        # saved_state = request.COOKIES.get('oauth2_state')
        # if not saved_state or state != jwt.decode(saved_state, settings.SECRET_KEY, algorithms=['HS256'])["state"]:
        #     return Response({"message": "Invalid state parameter"}, status=status.HTTP_400_BAD_REQUEST, headers=unset_cookie_header("oauth2_state"))

        data = {
            'grant_type': 'authorization_code',
            'client_id': os.getenv("CLIENT_ID"),
            'client_secret': os.getenv("CLIENT_SECRET"),
            'redirect_uri': f"{os.getenv('BACKEND_URL')}{reverse('oauth2-callback')}",
            'code': code,
        }

        response = requests.post(os.getenv("42_TOKEN_URL"), data=data)
        if response.status_code != status.HTTP_200_OK:
            return Response({"message": "Failed to get access token"}, status=status.HTTP_400_BAD_REQUEST, headers=unset_cookie_header("oauth2_state"))

        access_token = response.json().get('access_token')
        if not access_token:
            return Response({"message": "No access token found"}, status=status.HTTP_400_BAD_REQUEST, headers=unset_cookie_header("oauth2_state"))

        user_info_url = os.getenv("42_API_ME_URL")
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info_response = requests.get(user_info_url, headers=headers)

        if user_info_response.status_code != status.HTTP_200_OK:
            return Response({"message": "Failed to fetch user info from 42"}, status=status.HTTP_400_BAD_REQUEST, headers=unset_cookie_header("oauth2_state"))

        user_data = user_info_response.json()
        intra_uid = user_data.get('id')
        username = user_data.get('login')
        email = user_data.get('email')
        avatar_url = user_data.get('image', {}).get('link')

        user = User.objects.filter(intra_connection__uid=intra_uid).first()

        message = "successfully logged in."

        # if user:
        #     if not user.intra_user:
        #         # user.username = username
        #         # user.avatar_url = avatar_url
        #         user.intra_user = True
        #         user.email_verified = True
        #         user.set_password("")
        #         user.save()
        #         message = f"We have found an existing account for you, you can update your username is settings."
        # else:
        #     user = User.objects.create_user(
        #         username=get_free_username(User, username),
        #         email=email,
        #         avatar_url=avatar_url,
        #         intra_user=True,
        #         online=True,
        #         email_verified=True
        #     )
        #     message = f"registration successful!{' your username has already been claimed, we generated a new one for you.' if user.username != username else '' }"

        if not user:
            free_username = get_free_username(username)
            user = User.objects.create_user(
                email=None,
                username=free_username,
                intra_user=True,
                tournament_alias=get_free_game_nickname(free_username),
                avatar_url=avatar_url,
                email_token=get_random_string(32)
            )
            intra_connection = IntraConnection.objects.create(
                user=user,
                uid=intra_uid,
                email=email,
                avatar_url=avatar_url
            )
            message = f"registration successful!{' your username has already been claimed, we generated a new one for you.' if user.username != username else '' }"

        access_token = generate_jwt(user, mfa_required=user.mfa_enabled)

        # //Response({
        #     "access_token": str(access_token),
        #     "message": message,
        #     "user_id": user.id,
        #     "mfa_required": user.mfa_enabled
        # }, status=status.HTTP_200_OK, headers=unset_cookie_header("oauth2_state"))
        return HttpResponseRedirect(f'{os.getenv("FRONT_END_REDIRECT_URL")}?accessToken={str(access_token)}&mfa_required={user.mfa_enabled}')


class MFATOTPView(APIView):

    def post(self, request):
        current_user = request.user

        if not current_user.mfa_enabled:
            return Response({
                "error": "MFA is not enabled for this user."
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        data = request.data
        if not data.get("code") or not isinstance(data.get("code"), str) or not data.get("code").isnumeric():
            return Response({
                "error": "Invalid code."
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        if not pyotp.totp.TOTP(current_user.mfa_totp_secret).verify(data.get("code")):
            return Response({
                "error": "Invalid code."
            }, status=status.HTTP_401_UNAUTHORIZED)
        access_token = generate_jwt(current_user, mfa_required=False)
        return Response({
            "access_token": str(access_token),
            "user_id": current_user.id,
            "mfa_required": False
        }, status=status.HTTP_200_OK)

class SecurityMFATOTP(APIView):

    def get(self, request):
        current_user = request.user
        if current_user.mfa_enabled:
            return Response({"error": "this user has 2FA enabled."}, status=status.HTTP_400_BAD_REQUEST)
        secret_totp = current_user.mfa_totp_secret
        url_qr = pyotp.totp.TOTP(secret_totp).provisioning_uri(current_user.username, issuer_name='TranDanDan')
        svg_buffer = io.BytesIO()
        pyqrcode.create(url_qr).svg(svg_buffer, scale=8)
        svg_buffer.seek(0)
        return HttpResponse(svg_buffer.read(), content_type='image/svg+xml')

    def put(self, request):
        current_user = request.user
        data = request.data
        if current_user.mfa_enabled:
            return Response({
                "error": "MFA is already enabled for this user."
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        secret_totp = current_user.mfa_totp_secret
        if not data.get("code") or not isinstance(data.get("code"), str) or not data.get("code").isnumeric() or not pyotp.totp.TOTP(secret_totp).verify(data.get("code")):
            return Response({
                "error": "Invalid code."
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        current_user.mfa_enabled = True
        current_user.save()
        return Response({
            "user_id": current_user.id,
            "mfa_enabled": current_user.mfa_enabled
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        current_user = request.user

        if not current_user.mfa_enabled:
            return Response({
                "error": "MFA is not enabled for this user."
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        current_user.mfa_enabled = False
        current_user.mfa_totp_secret = None
        current_user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class RegisterView(UnprotectedView):

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            token = user.email_token
            confirmation_link = f"{os.getenv('FRONT_END_VERIFY_ACC_URL')}/{token}"
            send_registration_email(confirmation_link, user.email, schedule=timezone.now())
            return Response({
                "message": "User registered successfully, please verify your email.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    'avatar': '/default_profile.webp'
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(UnprotectedView):

    def post(self, request, token):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user_id = find_user_id_by_reset_token(token)
            if not user_id:
                return Response({"error": "invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
            password = serializer.validated_data['password']
            user = User.objects.get(id=user_id) # if this raises DoesNotExist then smtg is fucked up, since we dont even support account deletion?
            user.set_password(password)
            user.save()
            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RequestResetPasswordView(UnprotectedView):

    def post(self, request):
        serializer = RequestResetPasswordSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']

            user = User.objects.filter(email=email).first()
            if user:
                if not user.email_verified:
                    token = user.email_token
                    confirmation_link = f"{os.getenv('FRONT_END_VERIFY_ACC_URL')}/{token}"
                    send_registration_email(confirmation_link, user.email, schedule=timezone.now())
                token = get_random_string(32)
                reset_password_for_user(user.id, user.email, f"{os.getenv('RESET_PASS_FRONTEND_URL')}/{token}", token)
            return Response({
                "message": "if a user exists with a verified email that you specified, you will receive a reset password token in your inbox.",
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailView(UnprotectedView):

    def get(self, _, token):
        try:
            user = User.objects.get(email_token=token)
            user.email_token = get_random_string(32) # set the token for the next verification.
            user.email_verified = True
            user.save()
            return Response({"message": "email verified."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "token not valid."}, status=status.HTTP_404_NOT_FOUND)

class LoginView(UnprotectedView):

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(request, email=email, password=password)
            if user:
                access_token = generate_jwt(user, mfa_required=user.mfa_enabled)
                return Response({
                    "access_token": str(access_token),
                    "message": "logged in successfully!",
                    "user_id": user.id,
                    "mfa_required": user.mfa_enabled
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsersMeView(APIView):

    def get(self, request):
        user = request.user
        xp_manager = XPManager(user)
        user_data = {
            'id': user.id,
            'username': user.username,
            'tournament_alias': user.tournament_alias,
            'email': user.intra_connection.email if not user.email else user.email,
            'mfa_enabled': user.mfa_enabled,
            'friends': getFriendList(user.id),
            'avatar_url': user.avatar_url,
            "level": user.level,
            "current_xp": user.xp,
            "xp_to_next_level": xp_manager.xp_to_next_level(),
            "xp_progress": xp_manager.xp_progress(),
        }
        return Response(user_data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        email = user.email
        if not email:
            if 'email' in request.data or 'password' in request.data:
                if not 'email' in request.data or not 'password' in request.data:
                    return Response({"error": ["You must set a password and an email for this intra user."]}, status=status.HTTP_400_BAD_REQUEST)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if email != user.email:
                user.email_verified = False
                user.save()
                token = user.email_token
                confirmation_link = f"{os.getenv('FRONT_END_VERIFY_ACC_URL')}/{token}"
                send_registration_email(confirmation_link, user.email, schedule=timezone.now())
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

def getFriendList(user_id):
    friendList = []
    relations = UserRelationship.objects.filter(
        Q(first_user_id=user_id) |
        Q(second_user_id=user_id),
        type=RelativeRelationshipType.FRIENDS.value
    ).order_by('-updated_at')

    for relation in relations:
        friend = relation.second_user if user_id == relation.first_user_id else relation.first_user
        friendList.append({
            'id': friend.id,
            'username': friend.username,
            'avatar_url': friend.avatar_url,
            'level': friend.level
        })
    return friendList

class UserView(APIView):

    def get(self, request, username):
        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)
        current_user = request.user

        relationship = UserRelationship.objects.filter(
            Q(first_user=current_user, second_user=target_user) |
            Q(first_user=target_user, second_user=current_user)
        ).first()

        relationship_n = 0

        if relationship:
            relationship_n = createRelativeRelation(current_user, relationship)
        xp_manager = XPManager(target_user)
        user_data = {
            'id': target_user.id,
            'username': target_user.username,
            'tournament_alias': target_user.tournament_alias,
            'email': target_user.intra_connection.email if not target_user.email else target_user.email,
            'avatar_url': target_user.avatar_url,
            'relationship': relationship_n,
            'friends': getFriendList(target_user.id),
            "level": target_user.level,
            "current_xp": target_user.xp,
            "xp_to_next_level": xp_manager.xp_to_next_level(),
            "xp_progress": xp_manager.xp_progress(),
        }

        return Response(user_data, status=status.HTTP_200_OK)

class SendFriendRequest(APIView):
    def post(self, request):
        username = request.data.get('username')
        if not username or not isinstance(username, str):
            return Response({"detail": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)

        current_user = request.user

        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if current_user == target_user:
            return Response({"detail": "You cannot send a friend request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        relationship = UserRelationship.objects.filter(
            Q(first_user=current_user, second_user=target_user) |
            Q(first_user=target_user, second_user=current_user)
        ).first()
        if relationship:
            if relationship.type in [RelationshipType.PENDING_FIRST_SECOND.value, RelationshipType.PENDING_SECOND_FIRST.value]:
                return Response({"detail": "A friend request is already pending."}, status=status.HTTP_400_BAD_REQUEST)
            if relationship.type == RelationshipType.FRIENDS.value:
                return Response({"detail": "You are already friends."}, status=status.HTTP_400_BAD_REQUEST)
            if relationship.type in [RelationshipType.BLOCK_BOTH.value, RelationshipType.BLOCK_FIRST_SECOND.value, RelationshipType.BLOCK_SECOND_FIRST.value]:
                return Response({"detail": "You can't send a friend request to this user."}, status=status.HTTP_400_BAD_REQUEST)

        relationship = UserRelationship.objects.create( # get_or_create check if the releationship is already exists
            first_user=current_user,
            second_user=target_user,
            type=RelationshipType.PENDING_FIRST_SECOND.value
        )

        return Response({"detail": "Friend request sent."}, status=status.HTTP_201_CREATED)

class DeleteFriendRequest(APIView):
    def delete(self, request):
        username = request.data.get('username')
        if not username or not isinstance(username, str):
            return Response({"detail": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)

        current_user = request.user

        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if current_user == target_user:
            return Response({"detail": "You cannot delete a request with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        relationship = UserRelationship.objects.filter(
            Q(first_user=current_user, second_user=target_user) |
            Q(first_user=target_user, second_user=current_user)
        ).first()
        if relationship and relationship.type in [RelationshipType.PENDING_FIRST_SECOND.value, RelationshipType.PENDING_SECOND_FIRST.value]:
            relationship.delete()
            return Response({"detail": "Friend request deleted."}, status=status.HTTP_204_NO_CONTENT)

        return Response({"detail": "No request to delete."}, status=status.HTTP_400_BAD_REQUEST)

class AcceptFriendRequestView(APIView):

    def get(self, request, username):
        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.user == target_user:
            return Response({"detail": "You can only accept requests sent to you."}, status=status.HTTP_400_BAD_REQUEST)

        relationship = UserRelationship.objects.filter(
            Q(first_user=target_user, second_user=request.user, type=RelationshipType.PENDING_FIRST_SECOND.value) |
            Q(first_user=request.user, second_user=target_user, type=RelationshipType.PENDING_SECOND_FIRST.value)
        ).first()

        if not relationship:
            return Response({"detail": "No pending friend request to accept."}, status=status.HTTP_400_BAD_REQUEST)

        relationship.type = RelationshipType.FRIENDS.value
        relationship.save()

        return Response({"detail": "Friend request accepted."}, status=status.HTTP_200_OK)

class BlockUser(APIView):

    def post(self, request):
        username = request.data.get('username')
        if not username or not isinstance(username, str):
            return Response({"detail": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)

        current_user = request.user

        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if current_user == target_user:
            return Response({"detail": "You cannot block yourself."}, status=status.HTTP_400_BAD_REQUEST)

        relationship = UserRelationship.objects.filter(
            Q(first_user=current_user, second_user=target_user) |
            Q(first_user=target_user, second_user=current_user)
        ).first()

        if relationship:
            if relationship.first_user == current_user:
                if relationship.type in [RelationshipType.BLOCK_BOTH.value, RelationshipType.BLOCK_FIRST_SECOND.value]:
                    return Response({"detail": "Already blocked that user."}, status=status.HTTP_400_BAD_REQUEST)
                if relationship.type == RelationshipType.BLOCK_SECOND_FIRST.value:
                    relationship.type = RelationshipType.BLOCK_BOTH.value
                    relationship.save()
                else:
                    relationship.type = RelationshipType.BLOCK_FIRST_SECOND.value
                    relationship.save()
                return Response({"detail": "User blocked."}, status=status.HTTP_201_CREATED)
            else:
                if relationship.type in [RelationshipType.BLOCK_BOTH.value, RelationshipType.BLOCK_SECOND_FIRST.value]:
                    return Response({"detail": "Already blocked that user."}, status=status.HTTP_400_BAD_REQUEST)
                if relationship.type == RelationshipType.BLOCK_FIRST_SECOND.value:
                    relationship.type = RelationshipType.BLOCK_BOTH.value
                    relationship.save()
                else:
                    relationship.type = RelationshipType.BLOCK_SECOND_FIRST.value
                    relationship.save()
                return Response({"detail": "User blocked."}, status=status.HTTP_201_CREATED)

        relationship = UserRelationship.objects.create(
            first_user=current_user,
            second_user=target_user,
            type=RelationshipType.BLOCK_FIRST_SECOND.value
        )

        return Response({"detail": "User blocked."}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        username = request.data.get('username')
        if not username or not isinstance(username, str):
            return Response({"detail": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)

        current_user = request.user

        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if current_user == target_user:
            return Response({"detail": "You cannot unblock yourself."}, status=status.HTTP_400_BAD_REQUEST)

        relationship = UserRelationship.objects.filter(
            Q(first_user=current_user, second_user=target_user) |
            Q(first_user=target_user, second_user=current_user)
        ).first()

        if relationship and relationship.type in [RelationshipType.BLOCK_BOTH.value, RelationshipType.BLOCK_FIRST_SECOND.value, RelationshipType.BLOCK_SECOND_FIRST.value]:
            if relationship.first_user == current_user:
                if relationship.type == RelationshipType.BLOCK_BOTH.value:
                    relationship.type = RelationshipType.BLOCK_SECOND_FIRST.value
                    relationship.save()
                    return Response({"detail": "User unblocked."}, status=status.HTTP_204_NO_CONTENT)
                elif relationship.type == RelationshipType.BLOCK_FIRST_SECOND.value:
                    relationship.delete()
                    return Response({"detail": "User unblocked."}, status=status.HTTP_204_NO_CONTENT)
            else:
                if relationship.type == RelationshipType.BLOCK_BOTH.value:
                    relationship.type = RelationshipType.BLOCK_FIRST_SECOND.value
                    relationship.save()
                    return Response({"detail": "User unblocked."}, status=status.HTTP_204_NO_CONTENT)
                elif relationship.type == RelationshipType.BLOCK_SECOND_FIRST.value:
                    relationship.delete()
                    return Response({"detail": "User unblocked."}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "No block relationship exists."}, status=status.HTTP_400_BAD_REQUEST)

class UnfriendView(APIView):

    def delete(self, request):
        username = request.data.get('username')
        if not username or not isinstance(username, str):
            return Response({"detail": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)

        current_user = request.user

        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if current_user == target_user:
            return Response({"detail": "You cannot unfriend yourself."}, status=status.HTTP_400_BAD_REQUEST)

        relationship = UserRelationship.objects.filter(
            Q(first_user=current_user, second_user=target_user, type=RelationshipType.FRIENDS.value) |
            Q(first_user=target_user, second_user=current_user, type=RelationshipType.FRIENDS.value)
        ).first()

        if not relationship:
            return Response({"detail": "You are not friends with this user."}, status=status.HTTP_400_BAD_REQUEST)

        relationship.delete()
        return Response({"detail": "Friend removed."}, status=status.HTTP_204_NO_CONTENT)


class FriendsView(APIView):

    def get(self, request):
        rels = UserRelationship.objects.filter(
            Q(first_user=request.user) |
            Q(second_user=request.user),
            Q(type=RelationshipType.FRIENDS.value)
        ).order_by('-updated_at')

        friends_usernames = [
            rel.second_user.username if rel.first_user == request.user else rel.first_user.username
            for rel in rels
        ]
        return Response({"friends": friends_usernames}, status=status.HTTP_200_OK)

class UserSearchView(APIView):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({'results': []}, status=status.HTTP_200_OK)
        users = User.objects.filter(Q(username__icontains=query)).distinct()[:10]
        serializer = UserSearchSerializer(users, many=True)
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)

class UsersMeAvatarView(APIView):

    def put(self, request):
        data_url = request.data.get('avatar')
        if not data_url:
            return Response({'error': 'No avatar provided.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            header, base64_data = data_url.split(';base64,')
            mime_type = header.split(':')[1]
            allowed_types = ["image/png", "image/jpeg", "image/jpg"]
            if mime_type not in allowed_types:
                return Response({'error': 'Unsupported image type.'}, status=status.HTTP_400_BAD_REQUEST)
            ext = mime_type.split('/')[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            image_data = base64.b64decode(base64_data)
            file_path = default_storage.save(filename, ContentFile(image_data))
            file_url = default_storage.url(file_path)
            # if settings.DEBUG:
                # file_url = f"{os.getenv('BACKEND_URL')}{default_storage.url(file_path)}"
            request.user.avatar_url = file_url
            request.user.save()
            return Response({'url': file_url}, status=status.HTTP_200_OK)
        except (ValueError, KeyError) as e:
            return Response({'error': 'Invalid data URL format.'}, status=status.HTTP_400_BAD_REQUEST)

class UserXPLevelView(APIView):

    def get(self, request, username=None):
        try:
            user = User.objects.get(username=username)

            xp_manager = XPManager(user)
            data = {
                "username": user.username,
                "level": user.level,
                "current_xp": user.xp,
                "xp_to_next_level": xp_manager.xp_to_next_level(),
                "xp_progress": xp_manager.xp_progress(),
            }
            return Response(data, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

class UserRankingsViewSet(APIView):

    def get(self, request):
        top_users = (User.objects
                    .values('username', 'level', 'xp', 'avatar_url', 'tournament_alias')
                    .order_by('-level', '-xp')[:10])

        top_users_formatted = [{
            'username': user['username'],
            'tournament_alias': user['tournament_alias'],
            'level': user['level'],
            'xp': user['xp'],
            'avatar_url': user['avatar_url'],
        } for user in top_users]

        return Response({
            'top_users': top_users_formatted
        })
