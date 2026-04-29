import re
from pathlib import Path
from typing import Any


class PromptRenderer:
    def __init__(self, prompt_dir: Path | str) -> None:
        self.prompt_dir = Path(prompt_dir)

    def render(self, name: str, context: dict[str, Any]) -> str:
        template_path = self.prompt_dir / f"{name}.md"
        template = template_path.read_text(encoding="utf-8")
        return re.sub(
            r"{{\s*([a-zA-Z0-9_]+)\s*}}",
            lambda match: str(context.get(match.group(1), "")),
            template,
        )
