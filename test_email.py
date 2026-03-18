from email_service import EmailService

email_service = EmailService()

result = email_service.send_email(
    to="youremail@gmail.com",
    subject="Gmail API Test",
    body="If you received this, the Gmail API works."
)

print(result)
