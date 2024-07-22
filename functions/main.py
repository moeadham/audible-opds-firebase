# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app
import json
import audible
from urllib.parse import parse_qs, urlencode
import audible.login
import audible.localization
from audible.register import register as register_device
import httpx
import base64
import subprocess
import os

initialize_app()

@https_fn.on_request(region="europe-west1")
def refresh_audible_tokens(req: https_fn.Request) -> https_fn.Response:
    try:
        # Parse the request body to get the auth data
        auth_data = req.get_json().get("auth", {})
        if not isinstance(auth_data, dict):
            auth_data = {}
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


@https_fn.on_request(region="europe-west1")
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

# Login via flask: https://github.com/mkb79/Audible/issues/76
@https_fn.on_request(region="europe-west1")
def get_login_url(req: https_fn.Request) -> https_fn.Response:
    try:
        # Parse the request body to get the country code
        country_code = req.get_json().get("country_code", "ca")
        locale = audible.localization.Locale(country_code)
        # Generate the login URL
        code_verifier = audible.login.create_code_verifier()
        oauth_url, serial = audible.login.build_oauth_url(
            country_code=locale.country_code,
            domain=locale.domain,
            market_place_id=locale.market_place_id,
            code_verifier=code_verifier,
            with_username=False
        )
        code_verifier = base64.b64encode(code_verifier).decode('utf-8')
        # Return the login URL in the response
        return https_fn.Response(json.dumps({
            "message": "Login URL generated successfully",
            "status": "success",
            "login_url": oauth_url,
            "code_verifier": code_verifier,
            "serial": serial
        }), content_type="application/json")

    except Exception as e:
        print(f"Error generating login URL: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error generating login URL: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")


class Authenticator(audible.Authenticator):
    @classmethod
    def custom_login(
        cls, code_verifier: bytes, response_url: str, serial: str, country_code = "ca"
    ):
        auth = cls()
        auth.locale = country_code

        response_url = httpx.URL(response_url)
        parsed_url = parse_qs(response_url.query.decode())
        authorization_code = parsed_url["openid.oa2.authorization_code"][0]

        registration_data = register_device(
            authorization_code=authorization_code,
            code_verifier=code_verifier,
            domain=auth.locale.domain,
            serial=serial
        )
        auth._update_attrs(**registration_data)
        return auth

@https_fn.on_request(region="europe-west1")
def do_login(req: https_fn.Request) -> https_fn.Response:
    try:
        # Parse the request body to get the country code
        code_verifier = req.get_json().get("code_verifier")
        code_verifier = base64.b64decode(code_verifier)
        response_url = req.get_json().get("response_url")
        serial = req.get_json().get("serial")
        country_code = req.get_json().get("country_code")

        auth = Authenticator.custom_login(
            code_verifier=code_verifier,
            response_url=response_url,
            serial=serial,
            country_code=country_code
        )

        # Return the auth JSON
        return https_fn.Response(json.dumps({
            "message": "Login URL generated successfully",
            "status": "success",
            "auth": auth.to_dict()
        }), content_type="application/json")

    except Exception as e:
        print(f"Processing login url: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Processing login url: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")
    

@https_fn.on_request(region="europe-west1")
def get_audible_version(req: https_fn.Request) -> https_fn.Response:
    try:
        # Execute the 'audible --version' command
        result = subprocess.run(['audible', '--version'], capture_output=True, text=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            version = result.stdout.strip()
            return https_fn.Response(json.dumps({
                "message": "Audible version retrieved successfully",
                "status": "success",
                "version": version
            }), content_type="application/json")
        else:
            error_message = result.stderr.strip()
            return https_fn.Response(json.dumps({
                "message": f"Error retrieving Audible version: {error_message}",
                "status": "error"
            }), status=500, content_type="application/json")

    except Exception as e:
        print(f"Error executing 'audible --version': {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error executing 'audible --version': {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")

# So do download the book, I think we want to:
# 1. audible manage auth-file add (file)
# 2. audible 

@https_fn.on_request(region="europe-west1")
def audible_download_file(req: https_fn.Request) -> https_fn.Response:
    try:
        country_code = req.get_json().get("country_code")
        asin = req.get_json().get("asin")
        auth_data = req.get_json().get("auth", {})
        # Write the config.toml file
        config_content = '''
title = "Audible Config File"

[APP]
primary_profile = "audible"

[profile.audible]
auth_file = "audible.json"
country_code = f"{country_code}"
'''
        config_path = 'audible-cli/config.toml'
        with open(config_path, 'w') as config_file:
            config_file.write(config_content)
        
        # Write the auth data to audible.json
        auth_path = 'audible-cli/audible.json'
        with open(auth_path, 'w') as auth_file:
            json.dump(auth_data, auth_file, indent=2)
        
        # CONFIG_DIR_ENV=audible-cli audible download --aax --asin [ASIN] -q best -f asin_ascii --output-dir audible-cli/downloads/
        print(f"Running command: CONFIG_DIR_ENV=audible-cli audible download --aax --asin {asin} -q best -f asin_ascii --output-dir audible-cli/downloads/")
        result = subprocess.run(
            ['audible', 'download', '--aax', '--asin', asin, '-q', 'best', '-f', 'asin_ascii', '--output-dir', 'audible-cli/downloads/'], 
            capture_output=True, 
            text=True, 
            env={**os.environ, 'CONFIG_DIR_ENV': 'audible-cli'})

        if result.returncode == 0:
            return https_fn.Response(json.dumps({
                "message": "Audible file downloaded successfully",
                "status": "success",
                "output": result.stdout
            }), content_type="application/json")
        else:
            return https_fn.Response(json.dumps({
                "message": f"Error downloading audible file: {result.stderr}",
                "status": "error"
            }), status=500, content_type="application/json")
    except Exception as e:
        print(f"Error downloading audible file: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error downloading audible file: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")