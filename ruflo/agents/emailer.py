import os
import json
import urllib.request
import urllib.error
from .base import BaseAgent, AgentResult


class EmailerAgent(BaseAgent):
    name: str = "emailer"
    description: str = "Writes and sends cold outreach emails via SendGrid."
    skills: list[str] = ["send email", "email", "outreach", "cold email", "contact", "send a message"]

    def _build_system_prompt(self) -> str:
        return (
            "You are an expert cold email copywriter and outreach specialist. "
            "When asked to send an email, you write a short, personalized, conversational cold email "
            "and return it as a JSON object with keys: to, subject, body. "
            "The body should be plain text, under 150 words, with a clear call to action. "
            "Do not add any explanation outside the JSON."
        )

    async def run(self, task: str, context: list[dict] = None) -> AgentResult:
        api_key = os.environ.get("SENDGRID_API_KEY", "")
        from_email = os.environ.get("GMAIL_ADDRESS", "")

        if not api_key or not from_email:
            return AgentResult(
                output="SendGrid not configured. Set SENDGRID_API_KEY and GMAIL_ADDRESS in .env",
                success=False,
                error="Missing SendGrid credentials",
            )

        try:
            messages = self._build_messages(
                f"{task}\n\nReturn ONLY a JSON object with keys: to, subject, body.",
                context,
            )
            result = await self.provider.complete(messages, max_tokens=1024)
            raw = result.content.strip()

            # Strip markdown code fences if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            email_data = json.loads(raw.strip())

            to_addr = email_data.get("to", "")
            subject = email_data.get("subject", "")
            body = email_data.get("body", "")

            if not to_addr or not body:
                return AgentResult(
                    output=f"Could not parse email fields:\n{result.content}",
                    success=False,
                    error="Missing to or body in LLM response",
                )

            self._send_via_sendgrid(api_key, from_email, to_addr, subject, body)

            summary = f"Email sent to {to_addr}\nSubject: {subject}\n\n{body}"
            return AgentResult(
                output=summary,
                success=True,
                tokens_used=result.input_tokens + result.output_tokens,
                metadata={"to": to_addr, "subject": subject},
            )

        except json.JSONDecodeError as e:
            return AgentResult(
                output=f"Could not parse email JSON: {e}",
                success=False,
                error=str(e),
            )
        except Exception as e:
            return AgentResult(
                output=f"Email failed: {str(e)}",
                success=False,
                error=str(e),
            )

    def _send_via_sendgrid(self, api_key: str, from_email: str, to: str, subject: str, body: str):
        payload = json.dumps({
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 202):
                raise RuntimeError(f"SendGrid returned {resp.status}")
