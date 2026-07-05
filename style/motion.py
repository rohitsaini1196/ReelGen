def build_zoompan(duration: float, fps: int, w: int, h: int, zoom_pct: float = 0.06, shake_px: float = 2.0) -> str:
    """Subtle continuous zoom-in (Ken Burns) plus a handheld micro-jitter, so stock footage doesn't feel tripod-sterile."""
    total_frames = max(1, int(duration * fps))
    target_zoom = 1.0 + zoom_pct
    increment = (target_zoom - 1.0) / total_frames
    x_expr = f"iw/2-(iw/zoom/2)+{shake_px}*sin(on/4.7)"
    y_expr = f"ih/2-(ih/zoom/2)+{shake_px}*cos(on/6.3)"
    return (
        f"zoompan=z='min(zoom+{increment:.6f},{target_zoom})':d=1:"
        f"x='{x_expr}':y='{y_expr}':s={w}x{h}:fps={fps}"
    )
