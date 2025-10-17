from fastapi import FastAPI, Request
import httpx
import os
import random
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# --- Environment variables ---
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")
TWITCH_REFRESH_TOKEN = os.getenv("TWITCH_REFRESH_TOKEN")

# --- Refresh access token ---
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


# --- Get Twitch user ID by username ---
async def get_user_id(username: str, token: str) -> str | None:
    url = f"https://api.twitch.tv/helix/users?login={username.lower()}"
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 200 and resp.json().get("data"):
        return resp.json()["data"][0]["id"]
    elif resp.status_code == 401:
        return "unauthorized"
    return None


# --- Get random clip from last 5 recent ---
async def get_recent_clip(user_id: str, token: str) -> str | None:
    url = f"https://api.twitch.tv/helix/clips?broadcaster_id={user_id}&first=5"
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 200:
        data = resp.json().get("data", [])
        if data:
            clip = random.choice(data)
            return clip["url"]
    elif resp.status_code == 401:
        return "unauthorized"
    return None


# --- Extract Twitch username (case-insensitive, from name or URL) ---
def extract_username(raw_input: str) -> str:
    raw_input = raw_input.strip().lstrip("@").lower()
    if raw_input.startswith("https://") or raw_input.startswith("http://"):
        parsed = urlparse(raw_input)
        path_parts = parsed.path.strip("/").split("/")
        if path_parts:
            return path_parts[0].lower()
    return raw_input


# --- Nightbot command handler ---
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
        return "⚠️ Missing command."

    if command.lower() == "!shoutout":
        parts = message.strip().split()
        if not parts:
            return "⚠️ Please specify a streamer name — e.g. !shoutout streamername"

        streamer = extract_username(parts[0])
        token = TWITCH_ACCESS_TOKEN

        # Get user ID
        user_id = await get_user_id(streamer, token)
        if user_id == "unauthorized":
            print("🔐 Token expired, refreshing...")
            token = await refresh_access_token()
            if not token:
                return "⚠️ Twitch authorization failed. Please try again later."
            user_id = await get_user_id(streamer, token)

        if not user_id:
            return f"⚠️ Could not find Twitch user '{streamer}'."

        # Get random recent clip
        clip_url = await get_recent_clip(user_id, token)
        if clip_url == "unauthorized":
            token = await refresh_access_token()
            if not token:
                return "⚠️ Twitch authorization failed. Please try again later."
            clip_url = await get_recent_clip(user_id, token)

        if clip_url:
            return f"📣 Go check out **{streamer}** at https://twitch.tv/{streamer}! Here's one of their recent clips: {clip_url}"
        else:
            return f"⚠️ No recent clips found for **{streamer}**."

    return f"✅ Command '{command}' received!"


@app.get("/")
async def root():
    return {"status": "ok", "message": "Twitch Shoutout Bot is live!"}

