"""Phase 17 local media ingress and deterministic, provenance-first exports."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes

_PROJECT = re.compile(r"^prj_[a-z0-9][a-z0-9_-]{2,63}$")
_LICENSE = re.compile(r"^[A-Za-z0-9 ._+:/()-]{3,160}$")


def _hash(content: bytes | object) -> str:
    value = content if type(content) is bytes else encode_canonical_json_bytes(content)
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / ("." + path.name + "." + uuid.uuid4().hex)
    with temp.open("xb") as stream:
        stream.write(content); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)


@dataclass(frozen=True)
class LocalMediaRecord:
    media_id: str
    content_hash: str
    byte_length: int
    filename: str
    media_kind: str
    license_label: str
    provenance: str

    def data(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in self.__dataclass_fields__}


class LocalMediaStore:
    """Imports only a user-selected local file; the original path is never persisted."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def import_file(self, *, selected_path: Path, media_kind: str, license_label: str) -> LocalMediaRecord:
        path = Path(selected_path).resolve(strict=True)
        if not path.is_file() or not re.fullmatch(r"[a-z][a-z0-9_]{2,31}", media_kind) or _LICENSE.fullmatch(license_label) is None:
            raise ValueError("LOCAL_MEDIA_IMPORT_INVALID")
        content = path.read_bytes()
        if not content or len(content) > 2**31:
            raise ValueError("LOCAL_MEDIA_IMPORT_INVALID")
        digest = _hash(content)
        target = self.root / "objects" / digest.removeprefix("sha256:")
        if target.exists() and target.read_bytes() != content:
            raise ValueError("LOCAL_MEDIA_HASH_COLLISION")
        if not target.exists():
            _atomic(target, content)
        body = {"content_hash": digest, "byte_length": len(content), "filename": path.name, "media_kind": media_kind, "license_label": license_label, "provenance": "user_selected_local"}
        record_hash = _hash(body)
        return LocalMediaRecord("lmed_" + record_hash[7:31], **body)


class ProjectExporter:
    """Writes a local package without media rendering or cloud/object-storage behavior."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def export(self, *, project_id: str, media: tuple[LocalMediaRecord, ...], subtitle_srt: str | None, subtitle_vtt: str | None, chapter_metadata: Mapping[str, object], description_draft: str) -> Path:
        if _PROJECT.fullmatch(project_id) is None or type(media) is not tuple or any(type(item) is not LocalMediaRecord for item in media) or type(chapter_metadata) is not dict or type(description_draft) is not str:
            raise ValueError("PROJECT_EXPORT_INVALID")
        if (subtitle_srt is not None and type(subtitle_srt) is not str) or (subtitle_vtt is not None and type(subtitle_vtt) is not str):
            raise ValueError("PROJECT_EXPORT_INVALID")
        output = self.root / "exports" / project_id
        stage = self.root / ".staging" / ("export_" + uuid.uuid4().hex)
        stage.mkdir(parents=True)
        try:
            source_manifest = {"schema_version": "P17-SOURCE-MANIFEST-V1", "project_id": project_id, "media": [item.data() for item in sorted(media, key=lambda value: value.media_id)]}
            licenses = {"schema_version": "P17-LICENSE-REPORT-V1", "project_id": project_id, "licenses": [{"media_id": item.media_id, "license_label": item.license_label, "content_hash": item.content_hash} for item in sorted(media, key=lambda value: value.media_id)]}
            _atomic(stage / "source_manifest.json", encode_canonical_json_bytes(source_manifest))
            _atomic(stage / "license_report.json", encode_canonical_json_bytes(licenses))
            _atomic(stage / "chapters.json", encode_canonical_json_bytes(dict(chapter_metadata)))
            _atomic(stage / "description_draft.txt", description_draft.encode("utf-8"))
            if subtitle_srt is not None: _atomic(stage / "subtitles.srt", subtitle_srt.encode("utf-8"))
            if subtitle_vtt is not None: _atomic(stage / "subtitles.vtt", subtitle_vtt.encode("utf-8"))
            manifest_files = []
            for path in sorted(stage.iterdir(), key=lambda value: value.name):
                content = path.read_bytes()
                manifest_files.append({"path": path.name, "content_hash": _hash(content), "size_bytes": len(content)})
            archive = {"schema_version": "P17-PROJECT-EXPORT-MANIFEST-V1", "project_id": project_id, "files": manifest_files}
            _atomic(stage / "export_manifest.json", encode_canonical_json_bytes(archive))
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                raise ValueError("PROJECT_EXPORT_ALREADY_EXISTS")
            os.replace(stage, output)
            return output
        except BaseException:
            raise


class ProjectArchive:
    """Creates and restores a checked local package; restore never overwrites."""

    def create(self, *, source_directory: Path, archive_path: Path) -> Path:
        source = Path(source_directory).resolve(strict=True)
        target = Path(archive_path).resolve()
        if not source.is_dir() or target.exists() or target.suffix.lower() != ".zip":
            raise ValueError("PROJECT_ARCHIVE_INPUT_INVALID")
        rows: list[dict[str, object]] = []
        for file in sorted((item for item in source.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
            relative = file.relative_to(source).as_posix(); content = file.read_bytes()
            rows.append({"path": relative, "content_hash": _hash(content), "size_bytes": len(content)})
        if not rows: raise ValueError("PROJECT_ARCHIVE_INPUT_INVALID")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for row in rows: archive.write(source / row["path"], row["path"])
            archive.writestr("archive_manifest.json", encode_canonical_json_bytes({"schema_version": "P17-PROJECT-ARCHIVE-V1", "files": rows}))
        return target

    def restore(self, *, archive_path: Path, destination: Path) -> Path:
        archive_path = Path(archive_path).resolve(strict=True); target = Path(destination).resolve()
        if target.exists() or archive_path.suffix.lower() != ".zip": raise ValueError("PROJECT_RESTORE_INPUT_INVALID")
        try:
            with zipfile.ZipFile(archive_path) as archive:
                manifest = json.loads(archive.read("archive_manifest.json").decode("utf-8")); rows = manifest.get("files") if type(manifest) is dict else None
                if manifest.get("schema_version") != "P17-PROJECT-ARCHIVE-V1" or type(rows) is not list: raise ValueError
                target.mkdir(parents=True)
                for row in rows:
                    if type(row) is not dict or set(row) != {"path", "content_hash", "size_bytes"}: raise ValueError
                    relative = Path(row["path"])
                    if relative.is_absolute() or ".." in relative.parts or row["path"] == "archive_manifest.json": raise ValueError
                    content = archive.read(row["path"])
                    if len(content) != row["size_bytes"] or _hash(content) != row["content_hash"]: raise ValueError
                    _atomic(target / relative, content)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
            if target.exists(): shutil.rmtree(target)
            raise ValueError("PROJECT_RESTORE_INVALID") from exc
        return target
