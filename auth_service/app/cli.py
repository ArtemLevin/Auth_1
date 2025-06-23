import click
import asyncio
from sqlalchemy.future import select
from auth_service.app.db.session import db_helper
from auth_service.app.core.security import get_password_hash
from auth_service.app.models import User

@click.group()
def cli():
    pass

@cli.command()
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_superuser(username: str, password: str):
    async def _create_superuser_async():
        async with db_helper.session_factory() as db:
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