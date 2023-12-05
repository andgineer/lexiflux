from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class CustomUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        print("CustomUserBackend", username, password)
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(username=username)
            if user.check_password(password) and (user.is_approved or user.is_superuser):
                print("CustomUserBackend", user.is_approved, user.is_superuser)
                return user
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
        return None
