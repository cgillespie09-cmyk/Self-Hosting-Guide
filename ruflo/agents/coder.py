import re
import subprocess
import sys
import tempfile
import os
from typing import Optional

from .base import BaseAgent, AgentResult

_SYSTEM_PROMPT = (
    "You are an expert software engineer. Write clean, working, well-commented code. "
    "When asked to write code, provide complete, runnable implementations. "
    "Format code blocks with proper markdown fences (```python, ```javascript, etc.). "
    "Explain what the code does briefly after providing it. "
    "Prefer simple, readable solutions over overly complex ones."
)

_EXECUTION_KEYWORDS = [
    "run", "execute", "test", "output", "print", "result of", "what does",
    "demonstrate", "show me the output", "compute", "calculate",
]


class CoderAgent(BaseAgent):
    name: str = "coder"
    description: str = "Expert software engineer that writes and optionally executes code."
    skills: list[str] = ["code", "programming", "debug", "script", "python", "javascript"]

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def _should_execute(self, task: str) -> bool:
        task_lower = task.lower()
        return any(kw in task_lower for kw in _EXECUTION_KEYWORDS)

    def _extract_python_code(self, text: str) -> Optional[str]:
        # Try to find ```python ... ``` blocks
        pattern = r"```python\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return "\n\n".join(matches)
        # Try generic ``` blocks
        pattern2 = r"```\s*\n(.*?)```"
        matches2 = re.findall(pattern2, text, re.DOTALL)
        if matches2:
            return "\n\n".join(matches2)
        return None

    def _run_python(self, code: str) -> tuple[str, bool]:
        """Execute Python code in a subprocess with a 10 second timeout."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            if proc.returncode == 0:
                output = stdout if stdout else "(no output)"
                return output, True
            else:
                output = f"Error (exit {proc.returncode}):\n{stderr}" if stderr else f"Exit code: {proc.returncode}"
                return output, False

        except subprocess.TimeoutExpired:
            return "Execution timed out after 10 seconds.", False
        except Exception as e:
            return f"Could not execute code: {str(e)}", False

    async def run(self, task: str, context: list[dict] = None) -> AgentResult:
        try:
            messages = self._build_messages(task, context)
            result = await self.provider.complete(messages, max_tokens=3000)
            generated = result.content
            tokens = result.input_tokens + result.output_tokens

            output_parts = [generated]
            exec_metadata = {}

            if self._should_execute(task):
                code = self._extract_python_code(generated)
                if code:
                    exec_output, exec_success = self._run_python(code)
                    output_parts.append(
                        f"\n---\n**Execution Output:**\n```\n{exec_output}\n```"
                    )
                    exec_metadata["executed"] = True
                    exec_metadata["execution_success"] = exec_success

            return AgentResult(
                output="\n".join(output_parts),
                success=True,
                tokens_used=tokens,
                metadata=exec_metadata,
            )

        except Exception as e:
            return AgentResult(
                output=f"Coding task failed: {str(e)}",
                success=False,
                error=str(e),
            )
