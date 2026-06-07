import json
import bcrypt
from aiohttp import web
from sqlalchemy import select

from db import AsyncSession, User, Ad, init_db, close_db

app = web.Application()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def error_middleware(app, handler):
    async def middleware(request):
        try:
            return await handler(request)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    return middleware


app.middlewares.append(error_middleware)


def auth_required(handler):
    async def wrapper(request):
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            return web.json_response({"error": "X-User-Id required"}, status=401)
        async with AsyncSession() as session:
            user = await session.get(User, int(user_id))
            if not user:
                return web.json_response({"error": "Invalid user"}, status=401)
            request["user"] = user
            return await handler(request)
    return wrapper


async def handle_create_user(request):
    data = await request.json()
    async with AsyncSession() as session:
        user = User(name=data["name"], password=hash_password(data["password"]))
        session.add(user)
        await session.commit()
        return web.json_response({"id": user.id}, status=201)


async def handle_get_user(request):
    user_id = int(request.match_info["user_id"])
    async with AsyncSession() as session:
        user = await session.get(User, user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)
        return web.json_response({
            "id": user.id,
            "name": user.name,
            "created_at": user.created_at.isoformat()
        })


async def handle_update_user(request):
    user_id = int(request.match_info["user_id"])
    data = await request.json()
    async with AsyncSession() as session:
        user = await session.get(User, user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)
        if "name" in data:
            user.name = data["name"]
        if "password" in data:
            user.password = hash_password(data["password"])
        await session.commit()
        return web.json_response({"id": user.id})


async def handle_delete_user(request):
    user_id = int(request.match_info["user_id"])
    async with AsyncSession() as session:
        user = await session.get(User, user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)
        await session.delete(user)
        await session.commit()
        return web.json_response({"status": "deleted"})


async def handle_login(request):
    data = await request.json()
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.name == data["name"]))
        user = result.scalar_one_or_none()
        if not user or not check_password(data["password"], user.password):
            return web.json_response({"error": "Invalid credentials"}, status=401)
        return web.json_response({"user_id": user.id})


async def handle_create_ad(request):
    data = await request.json()
    user = request["user"]
    async with AsyncSession() as session:
        ad = Ad(title=data["title"], description=data["description"], owner_id=user.id)
        session.add(ad)
        await session.commit()
        return web.json_response({
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "owner_id": ad.owner_id,
            "created_at": ad.created_at.isoformat()
        }, status=201)


async def handle_get_ad(request):
    ad_id = int(request.match_info["ad_id"])
    async with AsyncSession() as session:
        ad = await session.get(Ad, ad_id)
        if not ad:
            return web.json_response({"error": "Ad not found"}, status=404)
        return web.json_response({
            "id": ad.id,
            "title": ad.title,
            "description": ad.description,
            "owner_id": ad.owner_id,
            "created_at": ad.created_at.isoformat()
        })


async def handle_update_ad(request):
    ad_id = int(request.match_info["ad_id"])
    data = await request.json()
    user = request["user"]
    async with AsyncSession() as session:
        ad = await session.get(Ad, ad_id)
        if not ad:
            return web.json_response({"error": "Ad not found"}, status=404)
        if ad.owner_id != user.id:
            return web.json_response({"error": "Forbidden"}, status=403)
        if "title" in data:
            ad.title = data["title"]
        if "description" in data:
            ad.description = data["description"]
        await session.commit()
        return web.json_response({"id": ad.id})


async def handle_delete_ad(request):
    ad_id = int(request.match_info["ad_id"])
    user = request["user"]
    async with AsyncSession() as session:
        ad = await session.get(Ad, ad_id)
        if not ad:
            return web.json_response({"error": "Ad not found"}, status=404)
        if ad.owner_id != user.id:
            return web.json_response({"error": "Forbidden"}, status=403)
        await session.delete(ad)
        await session.commit()
        return web.json_response({"status": "deleted"})


async def handle_list_ads(request):
    async with AsyncSession() as session:
        result = await session.execute(select(Ad))
        ads = result.scalars().all()
        return web.json_response({
            "ads": [{
                "id": ad.id,
                "title": ad.title,
                "description": ad.description,
                "owner_id": ad.owner_id,
                "created_at": ad.created_at.isoformat()
            } for ad in ads],
            "count": len(ads)
        })


app.router.add_post("/users", handle_create_user)
app.router.add_get("/users/{user_id}", handle_get_user)
app.router.add_patch("/users/{user_id}", handle_update_user)
app.router.add_delete("/users/{user_id}", handle_delete_user)
app.router.add_post("/login", handle_login)
app.router.add_post("/ads", auth_required(handle_create_ad))
app.router.add_get("/ads/{ad_id}", handle_get_ad)
app.router.add_patch("/ads/{ad_id}", auth_required(handle_update_ad))
app.router.add_delete("/ads/{ad_id}", auth_required(handle_delete_ad))
app.router.add_get("/ads", handle_list_ads)


async def on_startup(app):
    await init_db()
    print("Server started on http://localhost:8080")


async def on_shutdown(app):
    await close_db()


app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)