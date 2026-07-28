from __future__ import annotations

import importlib.util
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from app.models.pack import FeaturePack


@dataclass(frozen=True)
class PackManifest:
    name: str
    className: str
    entryPath: Path
    folder: Path
    dependencies: tuple[str, ...]

    @classmethod
    def fromDir(cls, packDir: Path) -> PackManifest | None:
        manifestPath = packDir / "manifest.toml"
        if not manifestPath.exists():
            logger.warning("FeaturePack is missing manifest.toml: {}", packDir)
            return None

        try:
            raw = tomllib.loads(manifestPath.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Cannot read manifest {}: {}", manifestPath, repr(e))
            return None

        packSection = raw.get("pack")
        if not isinstance(packSection, dict):
            logger.warning("manifest missing [pack] section: {}", manifestPath)
            return None

        entry = packSection.get("entry", "pack.py")
        if not isinstance(entry, str) or not entry.strip():
            logger.warning("invalid manifest entry: {}", manifestPath)
            return None

        entryPath = packDir / entry
        if not entryPath.exists() and entry.endswith(".py"):
            entryPath = packDir / (entry[:-3] + ".pyc")
        if not entryPath.exists():
            logger.warning("Entry file does not exist: {}", packDir / entry)
            return None

        className = packSection.get("class")
        if not isinstance(className, str) or not className.strip():
            logger.warning("manifest missing class field: {}", manifestPath)
            return None

        deps = packSection.get("dependencies", [])
        if not isinstance(deps, list) or any(
            not isinstance(d, str) or not d for d in deps
        ):
            logger.warning("invalid manifest dependencies: {}", manifestPath)
            return None

        return cls(
            name=packDir.name,
            className=className,
            entryPath=entryPath,
            folder=packDir,
            dependencies=tuple(deps),
        )


def loadPacks(featuresDir: Path, services=None) -> list[FeaturePack]:
    if not featuresDir.exists():
        logger.warning("features directory does not exist: {}", featuresDir)
        return []

    manifests = [
        m for p in sorted(featuresDir.iterdir())
        if p.is_dir() and not p.name.startswith(".")
        if (m := PackManifest.fromDir(p)) is not None
    ]
    ordered = orderedByDependency(manifests)
    return [pack for m in ordered if (pack := loadManifest(m, services)) is not None]


def orderedByDependency(manifests: list[PackManifest]) -> list[PackManifest]:
    byName: dict[str, PackManifest] = {m.name: m for m in manifests}
    visiting: list[str] = []
    visited: set[str] = set()
    ordered: list[PackManifest] = []
    skipped: set[str] = set()

    def visit(name: str):
        if name in visited:
            return
        if name in skipped:
            raise ValueError(f"{name} depends on a FeaturePack that was skipped")
        if name in visiting:
            cycle = visiting[visiting.index(name):] + [name]
            raise ValueError(f"Circular dependency: {' -> '.join(cycle)}")

        visiting.append(name)
        for dep in byName[name].dependencies:
            if dep not in byName:
                raise ValueError(f"{name} depends on a FeaturePack that was not found: {dep}")
            visit(dep)
        visiting.pop()
        visited.add(name)
        ordered.append(byName[name])

    for m in manifests:
        try:
            visit(m.name)
        except Exception as e:
            skipped.add(m.name)
            visiting.clear()
            logger.opt(exception=e).error("Skipping FeaturePack {}", m.name)

    return [m for m in ordered if m.name not in skipped]


def loadManifest(manifest: PackManifest, services=None) -> FeaturePack | None:
    moduleName = manifest.name
    try:
        spec = importlib.util.spec_from_file_location(
            moduleName,
            manifest.entryPath,
            submodule_search_locations=[str(manifest.folder)],
        )
        if spec is None or spec.loader is None:
            logger.error("Cannot create module spec: {}", moduleName)
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[moduleName] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(moduleName, None)
            raise

        PackClass = getattr(module, manifest.className, None)
        if PackClass is None:
            logger.warning("Class not found {}: {}", manifest.className, moduleName)
            return None

        pack = PackClass(services)
        logger.success("Loading FeaturePack: {}", moduleName)
        return pack

    except Exception as e:
        sys.modules.pop(moduleName, None)
        logger.opt(exception=e).error("Failed to load FeaturePack: {}", moduleName)
        return None
