from enum import Enum

from authlib.integrations.starlette_client import OAuth
from app.settings import settings

class OAuthProvider(str, Enum):
    yandex = "yandex"
    google = "google"
    vk = "vk"

oauth = OAuth()

oauth.register(
    'vk',
    client_id=settings.vk_client_id,
    client_secret=settings.vk_client_secret,
    api_base_url="https://api.vk.com/method/",
    authorize_url='https://oauth.vk.com/authorize',
    access_token_url='https://oauth.vk.com/access_token',
    userinfo_endpoint='https://api.vk.com/method/users.get',
    client_kwargs={'scope': 'email', 'token_placement': 'query'}
)

oauth.register(
    'yandex',
    client_id=settings.yandex_client_id,
    client_secret=settings.yandex_client_secret,
    authorize_url='https://oauth.yandex.ru/authorize',
    access_token_url='https://oauth.yandex.ru/token',
    userinfo_endpoint='https://login.yandex.ru/info',
)

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)
