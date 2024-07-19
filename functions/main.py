# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
import json
import audible

initialize_app()


@https_fn.on_request()
def on_request_example(req: https_fn.Request) -> https_fn.Response:
    return https_fn.Response(json.dumps({"message": "Hello world!"}), content_type="application/json")


@https_fn.on_request()
def refresh_audible_tokens(req: https_fn.Request) -> https_fn.Response:
    try:
        # Parse the request body to get the auth data
        # Print the content type of the request
        print(f"Request content type: {req.content_type}")

        auth_data = req.get_json().get("auth", {})
        if not isinstance(auth_data, dict):
            auth_data = {}

        # print("Auth data received:")
        # print(json.dumps(auth_data, indent=4))

        if not auth_data:
            print("No auth data provided in the request body")
            raise ValueError("No auth data provided in the request body")
        # Create an Audible client with the provided auth

        auth = audible.Authenticator.from_dict(auth_data)
        auth.refresh_access_token(auth.refresh_token)
        updated_auth = auth.to_dict()
        # Return the updated auth data in the response
        return https_fn.Response(json.dumps({
            "message": "Audible tokens refreshed successfully",
            "status": "success",
            "updated_auth": updated_auth
        }), content_type="application/json")

    except Exception as e:
        print(f"Error refreshing Audible tokens: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error refreshing Audible tokens: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")


@https_fn.on_request()
def get_activation_bytes(req: https_fn.Request) -> https_fn.Response:
    try:
        # Parse the request body to get the auth data
        auth_data = req.get_json().get("auth", {})
        if not isinstance(auth_data, dict):
            auth_data = {}

        if not auth_data:
            print("No auth data provided in the request body")
            raise ValueError("No auth data provided in the request body")

        # Create an Audible authenticator with the provided auth data
        auth = audible.Authenticator.from_dict(auth_data)

        # Get the activation bytes
        activation_bytes = auth.get_activation_bytes()

        # Return the activation bytes in the response
        return https_fn.Response(json.dumps({
            "message": "Activation bytes retrieved successfully",
            "status": "success",
            "activation_bytes": activation_bytes
        }), content_type="application/json")

    except Exception as e:
        print(f"Error retrieving activation bytes: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error retrieving activation bytes: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")

def custom_login_url_callback(login_url):
    print(login_url)
    return ""


@https_fn.on_request()
def get_login_url(req: https_fn.Request) -> https_fn.Response:
    try:
        # Parse the request body to get the country code
        country_code = req.get_json().get("locale", "us")
        print(country_code)
        # Generate the login URL
        auth = audible.Authenticator.from_login_external(
            locale=country_code,)
            #login_url_callback=custom_login_url_callback)
        print(auth.to_dict())

        # Return the login URL in the response
        return https_fn.Response(json.dumps({
            "message": "Login URL generated successfully",
            "status": "success",
            "login_url": auth.to_dict()
        }), content_type="application/json")

    except Exception as e:
        print(f"Error generating login URL: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error generating login URL: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")

# https://github.com/mkb79/Audible/blob/5ffe1aeee3092f75f0facf9fe594a64327d8a5aa/src/audible/login.py#L569
# Likely need to do something like this to structure the URLs correctly.