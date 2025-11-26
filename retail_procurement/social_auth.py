from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from social_django.utils import load_strategy
from social_core.backends.oauth import BaseOAuth2
from django.contrib.auth import login
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer
class SocialAuthView(APIView):
    """
    Представление для завершения соц. аутентификации и выдачи токена.
    """
    permission_classes = []  # Разрешено без аутентификации

    def get(self, request, backend):
        """
        Обработка callback от соц. сети.
        """
        strategy = load_strategy(request)
        backend_instance = getattr(strategy, f'get_backend')(backend)
        
        try:
            user = backend_instance.auth_complete()
            if user:
                login(request, user)
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key,
                    'message': f'Вход через {backend} успешен'
                })
            else:
                return Response({'error': 'Аутентификация не удалась'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)