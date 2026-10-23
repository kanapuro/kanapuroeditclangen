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


def test_volume_changes_apply_to_paused_music_before_resuming(music, monkeypatch):
    monkeypatch.setitem(game.settings, "music_volume", 100)
    monkeypatch.setattr(game, "clan", SimpleNamespace(biome="Forest", current_season="Newleaf"))
    music.check_music("start screen")
    music.play_queued()
    # Restart without a fade so mixer fade-in timing cannot mask the volume check.
    pygame.mixer.music.play()
    music.mute_music()
    music.change_volume(23)
    assert pygame.mixer.music.get_volume() == pytest.approx(0.23, abs=0.01)
    assert music.unmute_music("start screen")
    assert pygame.mixer.music.get_volume() == pytest.approx(0.23, abs=0.01)


def test_next_track_uses_current_season_without_screen_navigation(music, monkeypatch):
    clan = SimpleNamespace(biome="Forest", current_season="Newleaf")
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setitem(game.switches, "cur_screen", "events screen")
    music.check_music("events screen")
    music.play_queued()
    pygame.mixer.music.stop()
    clan.current_season = "Leaf-bare"
    music.queued_track = music.playlists["newleaf_playlist"][0]
    music.play_queued()
    assert music.current_track not in music.playlists["newleaf_playlist"]
    assert set(music.playlists["leafbare_playlist"]).issubset(music.current_playlist)
    assert pygame.mixer.music.get_busy()


def test_empty_playlist_stops_previous_music(music):
    music.play_playlist(music.playlists["menu_playlist"])
    music.play_queued()
    assert pygame.mixer.music.get_busy()
    music.play_playlist([])
    assert not pygame.mixer.music.get_busy()
    assert music.current_track is None


def test_queued_playback_respects_muted_and_disabled_states(music):
    music.play_playlist(music.playlists["menu_playlist"])
    music.muted = True
    music.play_queued()
    assert not pygame.mixer.music.get_busy()
    music.muted = False
    music.audio_disabled = True
    music.play_queued()
    assert not pygame.mixer.music.get_busy()


@pytest.mark.parametrize("volume,expected", [(-10, 0), (140, 100)])
def test_volume_can_change_while_audio_device_is_disabled(music, monkeypatch, volume, expected):
    from unittest.mock import patch
    monkeypatch.setitem(game.settings, "music_volume", 100)
    music.audio_disabled = True
    with patch.object(pygame.mixer.music, "set_volume", side_effect=pygame.error("Audio device unavailable")) as set_volume:
        music.change_volume(volume)
    set_volume.assert_not_called()
    assert game.settings["music_volume"] == expected
    assert music.volume == expected / 100


def test_explicit_custom_playlist_is_not_replaced_without_screen_context(music):
    music.play_playlist(music.playlists["creation_playlist"])
    music.play_queued()
    assert music.current_track in music.playlists["creation_playlist"]


@pytest.mark.parametrize("screen", ["start screen", "settings screen", "switch clan screen", "make clan screen"])
def test_menu_audio_does_not_read_incomplete_failed_save_context(music, monkeypatch, screen):
    monkeypatch.setattr(game, "clan", SimpleNamespace(biome=None, current_season=None))
    monkeypatch.setitem(game.switches, "error_message", "A disposable save failed to load")
    music.mute_music()
    assert music.unmute_music(screen)
    pygame.mixer.music.stop()
    music.play_queued()
    playlist = "creation_playlist" if screen == "make clan screen" else "menu_playlist"
    assert music.current_track in music.playlists[playlist]
    assert pygame.mixer.music.get_busy()
    assert game.switches["error_message"] == "A disposable save failed to load"
