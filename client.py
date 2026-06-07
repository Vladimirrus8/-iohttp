import asyncio
import aiohttp


async def main():
    async with aiohttp.ClientSession() as session:
        print("=== USERS ===")
        resp = await session.post("http://127.0.0.1:8080/users", json={
            "name": "user_1", "password": "1234"
        })
        user = await resp.json()
        print(f"POST /users: {resp.status} {user}")

        resp = await session.post("http://127.0.0.1:8080/login", json={
            "name": "user_1", "password": "1234"
        })
        login_data = await resp.json()
        print(f"POST /login: {resp.status} {login_data}")

        print("\n=== ADS ===")
        headers = {"X-User-Id": str(login_data["user_id"])}
        resp = await session.post("http://127.0.0.1:8080/ads", json={
            "title": "Test Ad", "description": "Test Description"
        }, headers=headers)
        ad = await resp.json()
        print(f"POST /ads: {resp.status} {ad}")

        resp = await session.get(f"http://127.0.0.1:8080/ads/{ad['id']}")
        print(f"GET /ads/{ad['id']}: {resp.status} {await resp.json()}")

        resp = await session.get("http://127.0.0.1:8080/ads")
        print(f"GET /ads: {resp.status} {await resp.json()}")

        resp = await session.delete(f"http://127.0.0.1:8080/users/{user['id']}")
        print(f"DELETE /users/{user['id']}: {resp.status} {await resp.json()}")


asyncio.run(main())