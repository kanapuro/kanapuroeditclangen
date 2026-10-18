from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from scripts.game_structure.audio import MusicManager
from scripts.game_structure.game_essentials import game


@pytest.fixture
def music():
    manager = MusicManager()
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    try:
        yield manager
    finally:
        pygame.mixer.music.stop()


@pytest.mark.parametrize("biome", ["Forest", "Mountainous", "Plains", "Beach"])
@pytest.mark.parametrize("season,season_key", [("Newleaf", "newleaf_playlist"), ("Leaf-bare", "leafbare_playlist")])
def test_ingame_playlists_include_general_and_matching_season(music, monkeypatch, biome, season, season_key):
    monkeypatch.setattr(game, "clan", SimpleNamespace(biome=biome, current_season=season))
    tracks = music.get_biome_music()
    assert set(music.playlists["general_playlist"]).issubset(tracks)
    assert set(music.playlists[season_key]).issubset(tracks)
    other_season = "leafbare_playlist" if season == "Newleaf" else "newleaf_playlist"
    assert set(music.playlists[other_season]).isdisjoint(tracks)
    assert all(Path(track).is_file() for track in tracks)


def test_real_menu_creation_and_ingame_audio_can_switch_and_play(music, monkeypatch):
    monkeypatch.setattr(game, "clan", SimpleNamespace(biome="Forest", current_season="Newleaf"))
    for screen in ("start screen", "make clan screen", "events screen", "start screen"):
        music.check_music(screen)
        # The frame loop plays the queue after the outgoing track finishes fading.
        pygame.mixer.music.stop()
        music.play_queued()
        assert pygame.mixer.music.get_busy()
        assert music.current_track in music.current_playlist
        assert music.queued_track in music.current_playlist
    music.mute_music()
    assert music.muted
    assert music.unmute_music("start screen")
    assert not music.muted
    assert pygame.mixer.music.get_busy()


def test_switch_from_an_unrelated_track_to_a_multitrack_playlist(music):
    music.current_track = music.playlists["creation_playlist"][0]
    music.play_playlist(music.playlists["general_playlist"])
    assert music.queued_track in music.playlists["general_playlist"]
    music.current_track = music.queued_track
    music.queue_music()
    assert music.queued_track != music.current_track


def test_empty_playlist_clears_stale_queue_and_track_count(music):
    music.play_playlist(music.playlists["general_playlist"])
    music.play_playlist([])
    assert music.number_of_tracks == 0
    assert music.queued_track is None


def test_biome_only_custom_playlist_remains_supported(music, monkeypatch):
    monkeypatch.setattr(game, "clan", SimpleNamespace(biome="Forest", current_season="Newleaf"))
    music.playlists = {"forest_playlist": ["custom.mp3"]}
    assert music.get_biome_music() == ["custom.mp3"]
