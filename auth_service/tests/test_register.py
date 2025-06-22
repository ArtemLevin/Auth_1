import pytest
import httpx
import pytest_asyncio
from fastapi import status
import logging
from datetime import datetime
# Базовый URL вашего сервера
BASE_URL = "http://localhost:8000/api/v1/auth"  # Измените, если ваш сервер работает на другом порту


@pytest_asyncio.fixture
async def async_client():
    async with httpx.AsyncClient() as client:
        yield client


@pytest.mark.asyncio
async def test_register_success(async_client):
    """Тест успешной регистрации пользователя"""
    # Используем уникальный логин и email для каждого теста
    timestamp = int(datetime.now().timestamp())
    test_data = {
        "login": f"testuser_{timestamp}",
        "password": "strongpassword123",
        "email": f"test_{timestamp}@example.com"
    }

    response = await async_client.post(f"{BASE_URL}/register", json=test_data)

    assert response.status_code == status.HTTP_201_CREATED
    assert not response.content


@pytest.mark.asyncio
async def test_register_conflict_login(async_client):
    """Тест конфликта при регистрации с существующим логином"""
    # Сначала создаем пользователя
    timestamp = int(datetime.now().timestamp())
    test_data = {
        "login": f"conflictuser_{timestamp}",
        "password": "strongpassword123",
        "email": f"conflict_{timestamp}@example.com"
    }

    # Первый запрос должен быть успешным
    response1 = await async_client.post(f"{BASE_URL}/register", json=test_data)
    assert response1.status_code == status.HTTP_201_CREATED

    # Второй запрос с теми же данными должен вернуть конфликт
    response2 = await async_client.post(f"{BASE_URL}/register", json=test_data)

    assert response2.status_code == status.HTTP_409_CONFLICT
    assert "detail" in response2.json()
    assert "already exists" in str(response2.json()["detail"]).lower()


@pytest.mark.asyncio
async def test_register_invalid_data(async_client):
    """Тест валидации входных данных"""
    test_cases = [
        ({}, ["Missing login", "Missing password"]),
        ({"login": "short", "password": "123"},
         ["Login too short", "Password too short"]),
        ({"login": "validlogin", "password": "short"}, ["Password too short"]),
        ({"login": "validlogin", "password": "validpassword",
          "email": "invalid"}, ["Invalid email"]),
    ]

    for data, error_msgs in test_cases:
        response = await async_client.post(f"{BASE_URL}/register", json=data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_register_logging(async_client, caplog):
    """Тест логирования успешной регистрации"""
    timestamp = int(datetime.now().timestamp())
    test_data = {
        "login": f"logginguser_{timestamp}",
        "password": "strongpassword123",
        "email": f"logging_{timestamp}@example.com"
    }

    with caplog.at_level(logging.INFO):
        response = await async_client.post(f"{BASE_URL}/register",
                                           json=test_data)
        assert response.status_code == status.HTTP_201_CREATED
