# -*- coding: utf-8 -*-
"""把她打包/解包到新机：代码是身体，状态才是她。

用法：
  导出：python -m her2.migrate export her2_state.json her.zip
  导入：python -m her2.migrate import her.zip ./新目录

原则：
- 只打包状态（存档、willing、人设、地图），不打包测试生成的 _*.json；
- 带 sha256 清单，导入先校验；
- 解包不覆盖已存在文件（可加 --force）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

MANIFEST = "manifest.json"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def export_bundle(state: Path, out: Path, persona: Path | None = None,
                  extra: list[Path] | None = None) -> Path:
    files = [state]
    if persona and persona.exists():
        files.append(persona)
    for p in extra or []:
        if p.exists() and p.is_file():
            files.append(p)
    manifest = {"version": 1, "files": []}
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            arc = p.name
            z.write(p, arc)
            manifest["files"].append({"name": arc, "sha256": _sha(p),
                                      "size": p.stat().st_size})
        z.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=1))
    return out


def import_bundle(bundle: Path, dest: Path, force: bool = False) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle) as z:
        manifest = json.loads(z.read(MANIFEST).decode("utf-8"))
        written = []
        for item in manifest.get("files", []):
            name = item["name"]
            data = z.read(name)
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"校验失败：{name}")
            target = dest / name
            if target.exists() and not force:
                raise FileExistsError(f"已存在：{target}（加 --force 覆盖）")
            target.write_bytes(data)
            written.append(target)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("export", "import"))
    ap.add_argument("state")
    ap.add_argument("target")
    ap.add_argument("--persona", default="")
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.action == "export":
        extra = [Path(x) for x in a.extra]
        out = export_bundle(Path(a.state), Path(a.target),
                            Path(a.persona) if a.persona else None, extra)
        print("exported", out)
    else:
        written = import_bundle(Path(a.state), Path(a.target), a.force)
        print("imported", len(written), "files")
        for p in written:
            print(" ", p)


if __name__ == "__main__":
    main()
