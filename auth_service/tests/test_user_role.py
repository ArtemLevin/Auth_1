import pytest
import httpx
import pytest_asyncio
from fastapi import status


BASE_URL = "http://localhost:8000/api/v1" 


@pytest_asyncio.fixture
async def async_client():
    async with httpx.AsyncClient() as client:
        yield client
        

@pytest_asyncio.fixture()
async def access_token(async_client):
    response = await async_client.post(
        f"{BASE_URL}/auth/login", 
        # необходимо создать superuser
        json={
            "login": "superuser",
            "password": "superuser"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    access_token = response.json()['access_token']
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture()
async def user_id(async_client, access_token):
    response = await async_client.get(
        f"{BASE_URL}/auth/me", 
        headers=access_token
    )
    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()['id']
    return user_id


@pytest.mark.asyncio
async def test_assign_role(async_client, access_token, user_id):
    """"""
    # создание
    role_data = {
        "name": "user",
        "description": "",
        "permissions": [
            "watch"
        ]
    }
    response_create = await async_client.post(f"{BASE_URL}/roles/", json=role_data, headers=access_token)
    role_id = response_create.json()["id"]
    assert response_create.status_code == status.HTTP_201_CREATED

    # назначение роли пользователю
    response_assign = await async_client.post(f"{BASE_URL}/roles/{role_id}/assign/{user_id}", headers=access_token)
    response_assign.status_code == status.HTTP_200_OK

    # отзыв роли пользователя
    revoke_assign = await async_client.delete(f"{BASE_URL}/roles/{role_id}/revoke/{user_id}", headers=access_token)
    revoke_assign.status_code == status.HTTP_200_OK

    # удаление
    response_delite = await async_client.delete(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    assert response_delite.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_assign_nonexistent_role(async_client, access_token, user_id):
    """ Назначение несуществующей роли пользователю возвращает 400."""
    fake_role_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.post(f"{BASE_URL}/roles/{fake_role_id}/assign/{user_id}", headers=access_token)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_assign_role_to_nonexistent_user(async_client, access_token):
    """Назначение роли несуществующему пользователю возвращает 400"""
    # создание
    role_data = {
        "name": "user",
        "description": "",
        "permissions": [
            "watch"
        ]
    }
    response_create = await async_client.post(f"{BASE_URL}/roles/", json=role_data, headers=access_token)
    role_id = response_create.json()["id"]
    assert response_create.status_code == status.HTTP_201_CREATED

    fake_user_id = "00000000-0000-0000-0000-000000000000"
    response_assign = await async_client.post(f"{BASE_URL}/roles/{role_id}/assign/{fake_user_id}", headers=access_token)
    assert response_assign.status_code == status.HTTP_400_BAD_REQUEST

    # удаление
    response_delite = await async_client.delete(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    assert response_delite.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_revoke_unassigned_role(async_client, access_token, user_id):
    """Проверяет поведение отзыва роли, которая не назначена пользователю."""
    # создание
    role_data = {
        "name": "user",
        "description": "",
        "permissions": [
            "watch"
        ]
    }
    response_create = await async_client.post(f"{BASE_URL}/roles/", json=role_data, headers=access_token)
    role_id = response_create.json()["id"]
    assert response_create.status_code == status.HTTP_201_CREATED

    # отзыв роли
    response_revoke = await async_client.delete(f"{BASE_URL}/roles/{role_id}/revoke/{user_id}", headers=access_token)
    assert response_revoke.status_code == status.HTTP_400_BAD_REQUEST

    # удаление
    response_delite = await async_client.delete(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    assert response_delite.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_revoke_role_from_nonexistent_user(async_client, access_token):
    """ Отзыв роли у несуществующего пользователя"""
    # создание
    role_data = {
        "name": "user",
        "description": "",
        "permissions": [
            "watch"
        ]
    }
    response_create = await async_client.post(f"{BASE_URL}/roles/", json=role_data, headers=access_token)
    role_id = response_create.json()["id"]
    assert response_create.status_code == status.HTTP_201_CREATED

    fake_user_id = "00000000-0000-0000-0000-000000000000"
    response_revoke = await async_client.delete(f"{BASE_URL}/roles/{role_id}/revoke/{fake_user_id}", headers=access_token)
    assert response_revoke.status_code == status.HTTP_400_BAD_REQUEST

    # удаление
    response_delite = await async_client.delete(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    assert response_delite.status_code == status.HTTP_204_NO_CONTENT