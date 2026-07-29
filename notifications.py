from datetime import datetime
from flask import render_template
from services.email_service import send_email

users = [
    {
        "name": "arun",
        "email": "kausikskausikarun@gmail.com",
        "last_active": datetime(2026, 6, 18),
        "username": "arun"
    },
]


def check_inactive_users():
    now = datetime.now()

    for user in users:
        inactive_days = (now - user["last_active"]).days

        if inactive_days >= 5:

            html_body = render_template(
                "emails/inactivity_alert.html",
                name=user["name"],
                days=inactive_days,
                username=user["username"],
                last_active=user["last_active"].strftime("%Y-%m-%d")
            )

            subject = "⚠ GitPulse: Inactivity Alert"

            send_email(user["email"], subject, html_body)