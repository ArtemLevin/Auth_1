import asyncio
from sqlalchemy.future import select
from app.db.session import AsyncDBSession
import click
from app.core.security import get_password_hash
from app.db.session import AsyncDBSession
from app.models import User
from app.services.auth_service import AuthService
from sqlalchemy.future import select


@click.group()
def cli():
    pass

@cli.command()
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_superuser(username: str, password: str):
    async def _create_superuser_async():
        async with AsyncDBSession() as db:
            existing_user_query = await db.execute(
                select(User).where(User.login == username)
            )
            if existing_user_query.scalar_one_or_none():
                click.echo(f"Ошибка: Пользователь с логином '{username}' уже существует.")
                return

            pwd_hash = get_password_hash(password)
            user = User(login=username, password_hash=pwd_hash, is_superuser=True)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            click.echo(f"Суперпользователь '{username}' создан.")

    asyncio.run(_create_superuser_async())


if __name__ == "__main__":
    cli()