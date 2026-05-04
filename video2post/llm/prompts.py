import re
from pathlib import Path
from typing import Any


class PromptRenderer:
    def __init__(self, prompt_dir: Path | str) -> None:
        self.prompt_dir = self._resolve_prompt_dir(prompt_dir)

    def _resolve_prompt_dir(self, prompt_dir: Path | str) -> Path:
        prompt_path = Path(prompt_dir)
        if prompt_path.is_absolute() or prompt_path.exists():
            return prompt_path

        package_prompt_path = Path(__file__).resolve().parents[1] / prompt_path
        if package_prompt_path.exists():
            return package_prompt_path

        repo_prompt_path = Path(__file__).resolve().parents[2] / prompt_path
        if repo_prompt_path.exists():
            return repo_prompt_path

        return prompt_path

    def render(self, name: str, context: dict[str, Any]) -> str:
        template_path = self.prompt_dir / f"{name}.md"
        template = template_path.read_text(encoding="utf-8")
        return re.sub(
            r"{{\s*([a-zA-Z0-9_]+)\s*}}",
            lambda match: str(context.get(match.group(1), "")),
            template,
        )
