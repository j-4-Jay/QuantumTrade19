from __future__ import annotations

class CursorGlowWorker:
    def css(self, accent, accent_glow):
        return f""".qt19-cursor-glow{{pointer-events:none;position:fixed;width:26px;height:26px;
border-radius:9999px;border:2px solid {accent};box-shadow:0 0 14px 4px {accent_glow};
background:radial-gradient(circle,{accent_glow}55 0%,transparent 70%);transform:translate(-50%,-50%);
z-index:9999;animation:qt19-pulse 1.6s ease-in-out infinite;}}
@keyframes qt19-pulse{{0%{{opacity:.55}}50%{{opacity:1}}100%{{opacity:.55}}}}"""
