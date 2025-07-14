import smtplib
from email.message import EmailMessage
from typing import List, Tuple

def send_car_email(
    send_from: str,
    send_to: str | List[str],
    recipiant_name: str,
    found_cars: List[Tuple[str, str]],
    *,
    smtp_host: str = "smtp.example.com",
    smtp_port: int = 587,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    use_tls: bool = True,
) -> None:
    """
    Send a car‑results email via SMTP.

    :param send_from: sender email
    :param send_to: recipient address(es)
    :param recipiant_name: name in greeting
    :param found_cars: list of (url, query)
    :param smtp_host: SMTP host
    :param smtp_port: SMTP port
    :param smtp_user: SMTP username
    :param smtp_password: SMTP password
    :param use_tls: start TLS or not
    :raises smtplib.SMTPException: on send failure
    """
    cars_section = "\n".join(f"{url} — {query}" for url, query in found_cars)

    body = f"""Hello {recipiant_name},

We have found you cars you might be interested in on your given search queries:

{cars_section}

With best Regards
your ML Tool"""

    msg = EmailMessage()
    msg["Subject"] = "Your car search results"
    msg["From"] = send_from
    msg["To"] = ", ".join(send_to) if isinstance(send_to, list) else send_to
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if use_tls:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
