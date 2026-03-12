from __future__ import annotations

import shutil
import subprocess
import tempfile
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

    def build_html_url(self, worksheet_id: str, base_url: str, teacher_mode: bool = False) -> str:
        html_url = f"{base_url.rstrip('/')}/api/worksheets/{quote(worksheet_id)}/html"
        if teacher_mode:
            html_url = f"{html_url}?teacher_mode=true"
        return html_url

    def _run_render_command(self, source_url: str, output_path: Path) -> None:
        command = [
            self.resolve_node(),
            str(self.script_path),
            source_url,
            str(output_path),
        ]
        subprocess.run(
            command,
            cwd=self.project_root,
            check=True,
            capture_output=True,
            text=True,
        )

    def render(self, worksheet_id: str, base_url: str, teacher_mode: bool = False) -> Path:
        output_path = self.build_output_path(worksheet_id)
        html_url = self.build_html_url(worksheet_id, base_url, teacher_mode=teacher_mode)
        self._run_render_command(html_url, output_path)
        return output_path

    def render_raw_html(self, html_content: str, output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".html",
                dir=output.parent,
                delete=False,
            ) as handle:
                handle.write(html_content)
                temp_path = Path(handle.name)

            self._run_render_command(temp_path.resolve().as_uri(), output)
            return output
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
