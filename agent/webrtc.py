from __future__ import annotations

import asyncio
import time

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
from mss import mss
from PIL import Image

PEERS: set[RTCPeerConnection] = set()


class DesktopVideoTrack(VideoStreamTrack):
    def __init__(self, fps: int = 20, quality: int = 70) -> None:
        super().__init__()
        self.fps = max(5, min(fps, 30))
        self.quality = max(30, min(quality, 90))
        self.capture = mss()
        self.monitor = self.capture.monitors[1]
        self.last_frame = 0.0

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        remaining = (1 / self.fps) - (time.monotonic() - self.last_frame)
        if remaining > 0:
            await asyncio.sleep(remaining)
        shot = self.capture.grab(self.monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        maximum_width = 1600 if self.quality >= 70 else 1280
        if image.width > maximum_width:
            scale = maximum_width / image.width
            image = image.resize(
                (maximum_width, int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )
        frame = VideoFrame.from_image(image)
        frame.pts = pts
        frame.time_base = time_base
        self.last_frame = time.monotonic()
        return frame

    def stop(self) -> None:
        try:
            self.capture.close()
        finally:
            super().stop()


async def create_answer(sdp: str, kind: str, fps: int, quality: int) -> dict[str, str]:
    peer = RTCPeerConnection()
    PEERS.add(peer)

    @peer.on("connectionstatechange")
    async def connection_state_changed() -> None:
        if peer.connectionState in {"failed", "closed", "disconnected"}:
            await peer.close()
            PEERS.discard(peer)

    await peer.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=kind))
    peer.addTrack(DesktopVideoTrack(fps, quality))
    answer = await peer.createAnswer()
    await peer.setLocalDescription(answer)
    return {"sdp": peer.localDescription.sdp, "type": peer.localDescription.type}


async def close_all() -> None:
    await asyncio.gather(*(peer.close() for peer in list(PEERS)), return_exceptions=True)
    PEERS.clear()
