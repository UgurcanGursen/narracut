from __future__ import annotations

import json

import pytest

from engine.product_io import LocalMediaStore, ProjectExporter


def test_local_media_deduplicates_without_persisting_original_path(tmp_path):
    selected = tmp_path / "source.mp4"; selected.write_bytes(b"media")
    store = LocalMediaStore(tmp_path / "managed")
    first = store.import_file(selected_path=selected, media_kind="video", license_label="CC-BY-4.0")
    second = store.import_file(selected_path=selected, media_kind="video", license_label="CC-BY-4.0")
    assert first == second
    assert str(selected) not in json.dumps(first.data())


def test_export_contains_source_license_subtitle_and_metadata_artifacts(tmp_path):
    selected = tmp_path / "source.mp4"; selected.write_bytes(b"media")
    media = LocalMediaStore(tmp_path / "media").import_file(selected_path=selected, media_kind="video", license_label="CC-BY-4.0")
    output = ProjectExporter(tmp_path / "package").export(project_id="prj_phase17", media=(media,), subtitle_srt="1\n00:00:00,000 --> 00:00:01,000\nHello\n", subtitle_vtt="WEBVTT\n", chapter_metadata={"chapters": []}, description_draft="Draft")
    assert {path.name for path in output.iterdir()} == {"source_manifest.json", "license_report.json", "chapters.json", "description_draft.txt", "subtitles.srt", "subtitles.vtt", "export_manifest.json"}
    assert json.loads((output / "source_manifest.json").read_text())["media"][0]["media_id"] == media.media_id


def test_import_requires_explicit_license_and_export_is_non_overwriting(tmp_path):
    selected = tmp_path / "source.mp4"; selected.write_bytes(b"media")
    store = LocalMediaStore(tmp_path / "media")
    with pytest.raises(ValueError, match="IMPORT_INVALID"):
        store.import_file(selected_path=selected, media_kind="video", license_label="x")
    media = store.import_file(selected_path=selected, media_kind="video", license_label="CC-BY-4.0")
    exporter = ProjectExporter(tmp_path / "package")
    kwargs = dict(project_id="prj_phase17", media=(media,), subtitle_srt=None, subtitle_vtt=None, chapter_metadata={}, description_draft="Draft")
    exporter.export(**kwargs)
    with pytest.raises(ValueError, match="ALREADY_EXISTS"):
        exporter.export(**kwargs)
