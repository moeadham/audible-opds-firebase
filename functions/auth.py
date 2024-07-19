import audible

import os

USERNAME = os.environ.get('AUDIBLE_USERNAME')
PASSWORD = os.environ.get('AUDIBLE_PASSWORD')
AUTHFILE = "audible_credentials.json"

def custom_cvf_callback():
    cvf = input("Please enter the CVF: ")
    return cvf

def custom_otp_callback():
    otp = input("Please enter the OTP: ")
    return otp

def custom_approval_callback():
    input("Please appove login")
    return True

auth = audible.Authenticator.from_login(
    USERNAME,
    PASSWORD,
    locale="ca",
    with_username=False,
    otp_callback=custom_otp_callback,
    cvf_callback=custom_cvf_callback,
    approval_callback=custom_approval_callback
)
auth.to_file(AUTHFILE)

