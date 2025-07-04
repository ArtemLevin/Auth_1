# Changelog

## [Unreleased]


## [1.0.1] - 2025-07-04

### Added
- Добавлена папка `infra/nginx/` с конфигурацией nginx и обновлён `docker-compose.yml`.  
  Это необходимо для работы авторизации через [VK OAuth](https://dev.vk.com/ru/api/access-token/getting-started?ref=old_portal), 
  поскольку VK требует, чтобы сервис слушал только порты 80 или 443 (другие порты не поддерживаются при регистрации приложения).
- Реализована авторизация через два внешних провайдера:  
  [Yandex](https://yandex.ru/dev/id/doc/ru/) и [Google](https://developers.google.com/identity/protocols/oauth2?hl=ru).
- Добавлена модель и таблица в БД: `UserSocialAccount` — для хранения информации о привязанных соцаккаунтах.
- Реализованы:
  - два endpoint'а для внешней авторизации (`/auth/social/{provider}`, `/auth/social/{provider}/callback`),
  - endpoint для смены пароля (`/auth/users/me/change_password`).
- Добавлены функциональные тесты для CRUD ролей. 
- Реализована настройка OAuth-клиентов через библиотеку [Authlib](https://docs.authlib.org/) в `app/core/oauth.py`.  
  Это позволяет централизованно управлять авторизацией через внешние провайдеры (Yandex, Google) с помощью единого интерфейса.

### Known issues
- Авторизация через [VK](https://dev.vk.com/ru/api/oauth) пока не реализована — из-за ошибки `Selected sign-in method 
  not available for app. Please try again later or contact the app administrator` от VK API (возможные причины: 
  неправильные настройки приложения или удаление со стороны VK).

## [1.0.0] - 2025-07-03

### Added
- Интеграция распределённой трассировки через OpenTelemetry с Jaeger  
  - добавлены зависимости: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-jaeger`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`, `opentelemetry-instrumentation-redis`, `opentelemetry-instrumentation-httpx`  
  - реализован модуль инициализации трассировки в `app/core/tracing.py`  
  - инструментирование FastAPI, SQLAlchemy, Redis и HTTPX  
  - в `docker-compose.yml` добавлен сервис `jaeger` для сбора и просмотра трассировок

- Партицирование таблицы `login_history` по полю `login_at`  
  - создана Alembic-миграция `partition_login_history`  
  - в `upgrade()`:
    1. переименование старой таблицы `login_history` в `login_history_old`  
    2. создание родительской таблицы `login_history PARTITION BY RANGE (login_at)`  
    3. создание партиций 
    4. перенос данных из `login_history_old` и удаление её  
    5. добавление индексов на новые партиции  
  - в `downgrade()` обратное преобразование к единой таблице  


### Added
- Образ Redis изменён на `redis/redis-stack:latest` для поддержки модуля RedisJSON.
- Реализация рейт-лимита через алгоритм leaky bucket в классе `RedisLeakyBucketRateLimiter`.
- Pydantic-модели:
  - `RateLimitConfig`
  - `RoleBasedLimits`
  - `RateLimitConfigDict`
- Переменная `rate_limit_config` типа `RateLimitConfigDict` с детальными настройками лимитов.
- Новая зависимость FastAPI: `rate_limit_dependency`.

### Changed
- Удалена система ограничений `slowapi`.
- Функция `get_current_user` теперь возвращает список ролей.
- Эндпоинты обновлены: добавлен статус `status.HTTP_429_TOO_MANY_REQUESTS`.
- Зависимости `Depends(require_permission(...))` и `Depends(get_current_user)` перенесены в `dependencies`.

### Removed
- Настройки `rate_limit_default`, `rate_limit_storage` из `settings.py`.
- Инициализация `SlowAPI` из `main.py`.