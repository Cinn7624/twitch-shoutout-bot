def normalize_name(raw: str) -> str:
    """
    Cleans up streamer name input from chat or URL.
    Works with:
      - @Username
      - Username
      - https://twitch.tv/Username
      - https://www.twitch.tv/Username/
      - http://twitch.tv/Username
    Returns lowercase username only.
    """
    name = raw.strip()
    # Remove leading @
    name = name.lstrip('@')

    # Remove any Twitch URL parts
    name = (
        name.replace("https://www.twitch.tv/", "")
        .replace("http://www.twitch.tv/", "")
        .replace("https://twitch.tv/", "")
        .replace("http://twitch.tv/", "")
    )

    # Remove trailing slashes or query strings
    name = name.split('?')[0].strip('/')

    return name.lower()
