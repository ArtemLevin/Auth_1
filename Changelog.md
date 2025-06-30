# Changelog


## [Unreleased]

## [1.0.0] - 2025-04-05

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

