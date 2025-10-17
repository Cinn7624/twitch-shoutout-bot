@app.api_route("/twitch-command", methods=["GET", "POST"])
async def twitch_command(request: Request):
    if request.method == "POST":
        data = await request.json()
        command = data.get("command")
        message = data.get("message", "")
    else:
        command = request.query_params.get("command")
        message = request.query_params.get("message", "")

    # --- Clean input checks ---
    if not command:
        return "⚠️ Missing command parameter."

    if command.lower() == "!shoutout":
        if not message:
            return "⚠️ Please specify a streamer — usage: !shoutout <username>"

        streamer = message.strip().split()[0].lstrip('@')
        user_id = await get_user_id(streamer, TWITCH_ACCESS_TOKEN)

        if user_id == "unauthorized":
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
            return f"🎬 Check out **{streamer}**! Here's a recent clip: {clip_url}"
        else:
            return f"⚠️ No recent clips found for **{streamer}**."

    return f"✅ Command '{command}' received!"


