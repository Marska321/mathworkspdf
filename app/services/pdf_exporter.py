from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote


class WorksheetPdfExporter:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.output_dir = project_root / "output" / "pdf"
        self.script_path = project_root / "scripts" / "render_pdf.mjs"

    def build_output_path(self, worksheet_id: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / f"{worksheet_id}.pdf"

    def resolve_node(self) -> str:
        for candidate in ("node.exe", "node", r"C:\Program Files\nodejs\node.exe"):
            resolved = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
            if resolved:
                return resolved
        raise FileNotFoundError("node is not available for PDF export.")

    def render(self, worksheet_id: str, base_url: str) -> Path:
        output_path = self.build_output_path(worksheet_id)
        html_url = f"{base_url.rstrip('/')}/api/worksheets/{quote(worksheet_id)}/html"
        command = [
            self.resolve_node(),
            str(self.script_path),
            html_url,
            str(output_path),
        ]
        subprocess.run(
            command,
            cwd=self.project_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return output_path
