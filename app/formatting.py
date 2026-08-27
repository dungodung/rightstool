def format_timestamp(ts) -> str:
    """MediaWiki's 14-digit YYYYMMDDHHMMSS -> 'YYYY/MM/DD HH:MM:SS'.
    None (no activity at all) renders as '×'; anything not exactly 14
    characters is returned unchanged rather than sliced incorrectly.
    """
    if not ts:
        return "×"
    text = ts.decode() if isinstance(ts, bytes) else str(ts)
    if len(text) != 14:
        return text
    return f"{text[:4]}/{text[4:6]}/{text[6:8]} {text[8:10]}:{text[10:12]}:{text[12:]}"
