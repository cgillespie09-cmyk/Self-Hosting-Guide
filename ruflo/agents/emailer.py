import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .base import BaseAgent, AgentResult


class EmailerAgent(BaseAgent):
    name: str = "emailer"
    description: str = "Writes and sends cold outreach emails via Gmail."
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
        gmail = os.environ.get("GMAIL_ADDRESS", "")
        app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

        if not gmail or not app_password:
            return AgentResult(
                output="Gmail not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env",
                success=False,
                error="Missing Gmail credentials",
            )

        try:
            messages = self._build_messages(
                f"{task}\n\nReturn ONLY a JSON object with keys: to, subject, body.",
                context,
            )
            result = await self.provider.complete(messages, max_tokens=1024)
            raw = result.content.strip()

            # Extract JSON (handle markdown code fences)
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
                    output=f"Could not parse email fields from LLM output:\n{result.content}",
                    success=False,
                    error="Missing to or body in LLM response",
                )

            self._send(gmail, app_password, to_addr, subject, body)

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

    def _send(self, gmail: str, password: str, to: str, subject: str, body: str):
        msg = MIMEMultipart("alternative")
        msg["From"] = gmail
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, password)
            server.sendmail(gmail, to, msg.as_string())
