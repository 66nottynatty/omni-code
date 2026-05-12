def parse_cron(cron_str: str) -> dict:
    parts = cron_str.split()
    if len(parts) != 5:
        return {}
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4]
    }
