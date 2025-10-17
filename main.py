from fastapi import FastAPI, Request
import httpx
import os
import random
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Twitch credentials
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")
TWITCH_REFRESH_TOKEN = os.getenv("TWITCH_REFRESH_TOKEN")


# --- Helper: Refresh access token ---
async def refresh_access_token() -> str | None:
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "grant_type": "refresh_token",
        "refresh_token": TWITCH_REFRESH_TOKEN,
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, params=params)

    if resp.status_code == 200:
        data = resp.json()
        new_token = data["access_token"]
        os.environ["TWITCH_ACCESS_TOKEN"] = new_token
        print("🔄 Access token refreshed successfully!")
        return new_token
    else:
        print(f"⚠️ Failed to refresh token: {resp.text}")
        return None


# --- Get user ID by username ---
async def get_user_id(username: str, token: str) -> str | None:
    url = f"https://api.twitch.tv/helix/users?login={username}"
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code == 200 and resp.json().get("data"):
        return resp.json()["data"][0]["id"]
    elif resp.status_code == 401:
        return "unauthorized"
    return None


# --- Get a random recent clip (from up to last 5) ---
async def get_recent_clip(user_id: str, token: str) -> str | None:
    url = f"https://api.twitch.tv/helix/clips?broadcaster_id={user_id}&first=5"
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 200:
        data = resp.json().get("data", [])
        if data:
            clip = random.choice(data)  # Pick a random one from recent 5
            return clip["url"]
    elif resp.status_code == 401:
        return "unauthorized"
    return None


# --- Normalize streamer name ---
def normalize_name(raw: str) -> str:
    name = raw.strip()
    name = name.lstrip('@')
    name = (
        name.replace("https://www.twitch.tv/", "")
        .replace("http://www.twitch.tv/", "")
        .replace("https://twitch.tv/", "")
        .replace("http://twitch.tv/", "")
    )
    name = name.split('?')[0].strip('/')
    normalized = name.lower()
    print(f"🧩 Normalized streamer name: {raw} → {normalized}")
    return normalized


# --- Handle Nightbot command ---
@app.api_route("/twitch-command", methods=["GET", "POST"])
async def twitch_command(request: Request):
    if request.method == "POST":
        data = await request.json()
        command = data.get("command")
        message = data.get("message", "")
    else:
        command = request.query_params.get("command")
        message = request.query_params.get("message", "")

    if not command:
        return {"error": "Missing command"}

    if command.lower() in ["!shoutout", "!so"]:
        parts = message.strip().split()
        if not parts:
            return "⚠️ Please specify a streamer name — e.g. !shoutout streamername"

        streamer = normalize_name(parts[0])

        user_id = await get_user_id(streamer, TWITCH_ACCESS_TOKEN)

        if user_id == "unauthorized":
            print("🔐 Access token expired. Refreshing...")
            new_token = await refresh_access_token()
            if not new_token:
                return "⚠️ Twitch authorization failed. Please try again later."
            user_id = await get_user_id(streamer, new_token)

        if not user_id:
            return f"⚠️ Could not find Twitch user '{streamer}'."

        clip_url = await get_recent_clip(user_id, TWITCH_ACCESS_TOKEN)

        if clip_url == "unauthorized":
            new_token = await refresh_access_token()
            if not new_token:
                return "⚠️ Twitch authorization failed. Please try again later."
            clip_url = await get_recent_clip(user_id, new_token)

        if clip_url:
            message = f"📣 Go follow {streamer} at https://twitch.tv/{streamer}! Here's a recent clip: {clip_url}"
        else:
            message = f"📣 Go follow {streamer} at https://twitch.tv/{streamer}! (No recent clips found yet.)"

        return message.strip()

    return f"✅ Command '{command}' received!"


@app.get("/")
async def root():
    return {"status": "ok", "message": "Twitch Shoutout Bot is live!"}
