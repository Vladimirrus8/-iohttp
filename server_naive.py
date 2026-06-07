from aiohttp import web
from sqlalchemy import select

from db import AsyncSession, Ad, init_db, close_db

app = web.Application()


async def handle_create_ad(request):
    data = await request.json()
    async with AsyncSession() as session:
        ad = Ad(
            title=data["title"],
            description=data["description"],
            owner_id=data["owner_id"]
        )
        session.add(ad)
        await session.commit()
        return web.json_response({"id": ad.id}, status=201)


async def handle_get_ad(request):
    ad_id = int(request.match_info["ad_id"])
    async with AsyncSession() as session:
        ad = await session.get(Ad, ad_id)
        if not ad:
            return web.json_response({"error": "Not found"}, status=404)
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
    async with AsyncSession() as session:
        ad = await session.get(Ad, ad_id)
        if not ad:
            return web.json_response({"error": "Not found"}, status=404)
        if "title" in data:
            ad.title = data["title"]
        if "description" in data:
            ad.description = data["description"]
        await session.commit()
        return web.json_response({"id": ad.id})


async def handle_delete_ad(request):
    ad_id = int(request.match_info["ad_id"])
    async with AsyncSession() as session:
        ad = await session.get(Ad, ad_id)
        if not ad:
            return web.json_response({"error": "Not found"}, status=404)
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


app.router.add_post("/ads", handle_create_ad)
app.router.add_get("/ads/{ad_id}", handle_get_ad)
app.router.add_patch("/ads/{ad_id}", handle_update_ad)
app.router.add_delete("/ads/{ad_id}", handle_delete_ad)
app.router.add_get("/ads", handle_list_ads)


async def on_startup(app):
    await init_db()
    print("Naive server started on http://localhost:8080")


async def on_shutdown(app):
    await close_db()


app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)