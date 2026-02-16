"""Audio manager — infrastructure for SFX and music playback.

All methods are no-ops if pygame.mixer is unavailable or if audio files are missing.
"""
import os

import pygame

_ASSET_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, "assets"
)
_ASSET_DIR = os.path.normpath(_ASSET_DIR)


class AudioManager:
    def __init__(self):
        self._mixer_available = pygame.mixer.get_init() is not None
        self._sfx_cache: dict[str, pygame.mixer.Sound | None] = {}
        self._current_music: str | None = None
        self._sfx_volume = 1.0
        self._music_volume = 1.0

    # ------------------------------------------------------------------
    # SFX
    # ------------------------------------------------------------------

    def play_sfx(self, name: str) -> None:
        """Play a sound effect by name. Loads from assets/sounds/{name}.wav or .ogg."""
        if not self._mixer_available:
            return

        if name in self._sfx_cache:
            snd = self._sfx_cache[name]
            if snd is not None:
                snd.play()
            return

        # Try loading
        sound_dir = os.path.join(_ASSET_DIR, "sounds")
        for ext in (".wav", ".ogg"):
            path = os.path.join(sound_dir, name + ext)
            if os.path.isfile(path):
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(self._sfx_volume)
                    self._sfx_cache[name] = snd
                    snd.play()
                    return
                except pygame.error:
                    pass

        # File not found — cache None so we don't retry
        self._sfx_cache[name] = None

    def set_sfx_volume(self, volume: float) -> None:
        """Set SFX volume (0.0–1.0)."""
        self._sfx_volume = max(0.0, min(1.0, volume))
        for snd in self._sfx_cache.values():
            if snd is not None:
                snd.set_volume(self._sfx_volume)

    # ------------------------------------------------------------------
    # Music
    # ------------------------------------------------------------------

    def play_music(self, name: str, loops: int = -1) -> None:
        """Stream music from assets/music/{name}.ogg (or .wav/.mp3).

        Skips if the same track is already playing.
        """
        if not self._mixer_available:
            return

        if self._current_music == name:
            return

        music_dir = os.path.join(_ASSET_DIR, "music")
        for ext in (".ogg", ".wav", ".mp3"):
            path = os.path.join(music_dir, name + ext)
            if os.path.isfile(path):
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.set_volume(self._music_volume)
                    pygame.mixer.music.play(loops)
                    self._current_music = name
                    return
                except pygame.error:
                    pass

        # File not found — no-op
        self._current_music = None

    def stop_music(self) -> None:
        """Stop currently playing music."""
        if not self._mixer_available:
            return
        pygame.mixer.music.stop()
        self._current_music = None

    def set_music_volume(self, volume: float) -> None:
        """Set music volume (0.0–1.0)."""
        self._music_volume = max(0.0, min(1.0, volume))
        if self._mixer_available:
            pygame.mixer.music.set_volume(self._music_volume)
