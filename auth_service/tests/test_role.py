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
    assert response.status_code == 200
    access_token = response.json()['access_token']
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_role_crud_lifecycle(async_client, access_token):
    """Проверяет полный жизненный цикл роли: создание, обновление, получение и удаление"""
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

    # изменение
    edit_role_data = dict(role_data)
    edit_role_data["name"] = (new_name := "first_user")
    response_put = await async_client.put(f"{BASE_URL}/roles/{role_id}", json=edit_role_data, headers=access_token)
    assert response_put.status_code == status.HTTP_200_OK
    assert response_put.json()["name"] == new_name

    # получение
    response_get = await async_client.get(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    get_role_name = response_get.json()["name"]
    assert response_get.status_code == status.HTTP_200_OK
    assert get_role_name == new_name

    # удаление
    response_delite = await async_client.delete(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    assert response_delite.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_create_role_success(async_client, access_token):
    """Проверяет успешное создание роли с корректными данными"""
    role_data = {
        "name": "moderator",
        "description": "Can moderate content",
        "permissions": ["edit", "delete"]
    }
    response = await async_client.post(
        f"{BASE_URL}/roles/",
        json=role_data,
        headers=access_token
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == role_data["name"]

    # удаление
    role_id = response.json()["id"]
    response_delite = await async_client.delete(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    assert response_delite.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_create_duplicate_role_fails(async_client, access_token):
    """Проверяет, что при попытке повторного создания роли с тем же именем возвращается 409"""
    # создание
    role_data = {
        "name": "user",
        "description": "",
        "permissions": [
            "watch"
        ]
    }
    response = await async_client.post(f"{BASE_URL}/roles/", json=role_data, headers=access_token)
    role_id = response.json()["id"]
    assert response.status_code == status.HTTP_201_CREATED

    # попытка повторного создания
    response = await async_client.post(f"{BASE_URL}/roles/", json=role_data, headers=access_token)
    assert response.status_code == status.HTTP_409_CONFLICT

    # удаление
    response_delite = await async_client.delete(f"{BASE_URL}/roles/{role_id}", headers=access_token)
    assert response_delite.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_get_all_roles(async_client, access_token):
    """Проверяет, что эндпоинт получения всех ролей возвращает список"""
    response = await async_client.get(
        f"{BASE_URL}/roles/",
        headers=access_token
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_nonexistent_role_returns_404(async_client, access_token):
    """Проверяет, что при попытке получить несуществующую роль возвращается 404"""
    response = await async_client.get(f"{BASE_URL}/roles/3fa85f64-5718-4562-b3fc-2c963f66afa6", headers=access_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_nonexistent_role_returns_404(async_client, access_token):
    """Проверяет, что удаление несуществующей роли возвращает 404"""
    response = await async_client.delete(f"{BASE_URL}/roles/3fa85f64-5718-4562-b3fc-2c963f66afa6", headers=access_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND