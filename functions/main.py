# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn, logger
from firebase_functions.params import StringParam
from firebase_admin import initialize_app, storage
import json
import audible
from urllib.parse import parse_qs
import audible.login
import audible.localization
from audible.register import register as register_device
from audible.aescipher import decrypt_voucher_from_licenserequest
import httpx
import pathlib
import base64
import subprocess
import os
import sys
import traceback

API_KEY = StringParam("API_KEY")
ENVIRONEMENT = StringParam("ENVIRONEMENT")

initialize_app()

def require_api_key(f):
    def decorated_function(req: https_fn.Request) -> https_fn.Response:
        client_api_key = req.headers.get("Api-Key")
        server_api_key = API_KEY.value
        if client_api_key != server_api_key or server_api_key is None:
            return https_fn.Response(json.dumps({
                "message": "Invalid API key",
                "status": "error"
            }), status=401, content_type="application/json")
        
        return f(req)
    
    decorated_function.__name__ = f.__name__
    decorated_function.__doc__ = f.__doc__
    return decorated_function

@https_fn.on_request(region="europe-west1")
@require_api_key
def refresh_audible_tokens(req: https_fn.Request) -> https_fn.Response:
    try:
        logger.info("Attempting to refresh Audible tokens")
        # Parse the request body to get the auth data
        auth_data = req.get_json().get("auth", {})
        if not isinstance(auth_data, dict):
            auth_data = {}
        if not auth_data:
            logger.error("No auth data provided in the request body")
            raise ValueError("No auth data provided in the request body")
        # Create an Audible client with the provided auth
        logger.debug("Creating Audible authenticator from provided auth data")
        auth = audible.Authenticator.from_dict(auth_data)
        logger.info("Refreshing access token")
        auth.refresh_access_token(auth.refresh_token)
        updated_auth = auth.to_dict()
        logger.debug("Access token refreshed successfully")
        # Return the updated auth data in the response
        logger.info("Audible tokens refreshed successfully")
        return https_fn.Response(json.dumps({
            "message": "Audible tokens refreshed successfully",
            "status": "success",
            "updated_auth": updated_auth
        }), content_type="application/json")

    except Exception as e:
        logger.error(f"Error refreshing Audible tokens: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error refreshing Audible tokens: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")


@https_fn.on_request(region="europe-west1")
@require_api_key
def get_activation_bytes(req: https_fn.Request) -> https_fn.Response:
    try:
        logger.info("Attempting to retrieve activation bytes")
        # Parse the request body to get the auth data
        auth_data = req.get_json().get("auth", {})
        if not isinstance(auth_data, dict):
            auth_data = {}

        if not auth_data:
            logger.error("No auth data provided in the request body")
            raise ValueError("No auth data provided in the request body")

        # Create an Audible authenticator with the provided auth data
        logger.debug("Creating Audible authenticator from provided auth data")
        auth = audible.Authenticator.from_dict(auth_data)

        # Get the activation bytes
        logger.debug("Retrieving activation bytes")
        activation_bytes = auth.get_activation_bytes()

        # Return the activation bytes in the response
        logger.info("Activation bytes retrieved successfully")
        return https_fn.Response(json.dumps({
            "message": "Activation bytes retrieved successfully",
            "status": "success",
            "activation_bytes": activation_bytes
        }), content_type="application/json")

    except Exception as e:
        logger.error(f"Error retrieving activation bytes: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error retrieving activation bytes: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")

# Login via flask: https://github.com/mkb79/Audible/issues/76
@https_fn.on_request(region="europe-west1")
@require_api_key
def get_login_url(req: https_fn.Request) -> https_fn.Response:
    try:
        logger.info("Attempting to generate Audible login URL")
        # Parse the request body to get the country code
        country_code = req.get_json().get("country_code", "ca")
        logger.debug(f"Using country code: {country_code}")
        locale = audible.localization.Locale(country_code)
        # Generate the login URL
        logger.debug("Generating code verifier and building OAuth URL")
        code_verifier = audible.login.create_code_verifier()
        oauth_url, serial = audible.login.build_oauth_url(
            country_code=locale.country_code,
            domain=locale.domain,
            market_place_id=locale.market_place_id,
            code_verifier=code_verifier,
            with_username=False
        )
        code_verifier = base64.b64encode(code_verifier).decode('utf-8')
        logger.debug("OAuth URL and code verifier generated successfully")
        # Return the login URL in the response
        logger.info("Login URL generated successfully")
        return https_fn.Response(json.dumps({
            "message": "Login URL generated successfully",
            "status": "success",
            "login_url": oauth_url,
            "code_verifier": code_verifier,
            "serial": serial
        }), content_type="application/json")

    except Exception as e:
        logger.error(f"Error generating login URL: {str(e)}")
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
@require_api_key
def do_login(req: https_fn.Request) -> https_fn.Response:
    try:
        logger.info("Starting login process")
        # Parse the request body to get the country code
        logger.debug("Parsing request body")
        code_verifier = req.get_json().get("code_verifier")
        code_verifier = base64.b64decode(code_verifier)
        response_url = req.get_json().get("response_url")
        serial = req.get_json().get("serial")
        country_code = req.get_json().get("country_code")

        logger.debug(f"Attempting custom login with country_code: {country_code}")
        auth = Authenticator.custom_login(
            code_verifier=code_verifier,
            response_url=response_url,
            serial=serial,
            country_code=country_code
        )
        logger.info("Custom login successful")

        logger.debug("Getting activation bytes")
        activation_bytes = auth.get_activation_bytes()
        logger.debug("Activation bytes retrieved successfully")

        # Return the auth JSON
        logger.info("Login process completed successfully")
        return https_fn.Response(json.dumps({
            "message": "Login process completed successfully",
            "status": "success",
            "auth": auth.to_dict(),
        }), content_type="application/json")

    except Exception as e:
        logger.error(f"Error processing login: {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return https_fn.Response(json.dumps({
            "message": f"Error processing login: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")

def get_local_file_dir():
    os.makedirs('bin/downloads/', exist_ok=True)
    return "bin/downloads/"

def upload_to_storage(bucket_name, path, asin, extension):
    bucket = storage.bucket(bucket_name)
    # Find the downloaded file
    local_file_path = f'{get_local_file_dir()}{asin}{extension}'
    
    # Create the full path in the storage bucket
    blob = bucket.blob(f'{path}{asin}{extension}')
    print(f"Uploading {local_file_path} to {blob.name}")
    blob.upload_from_filename(local_file_path)
    # Check if the blob exists after upload
    print(f"Checking if blob {blob.name} exists:")
    print(blob.exists())
    return blob

def download_ffmpeg_binary(bucket_name):
    bucket = storage.bucket(bucket_name)
    ffmpeg_blob = bucket.blob('bin/ffmpeg')
    if not ffmpeg_blob.exists():
        print("FFmpeg binary not found in the bucket")
        return False
    local_ffmpeg_path = f"{get_local_file_dir()}ffmpeg"
    ffmpeg_blob.download_to_filename(local_ffmpeg_path)
    # Make the downloaded file executable
    os.chmod(local_ffmpeg_path, 0o755)
    print(f"FFmpeg binary downloaded to {local_ffmpeg_path}")
    return True

def get_ffmpeg_path():
    if ENVIRONEMENT.value == "dev":
        return "ffmpeg"
    else:
        return f"{get_local_file_dir()}ffmpeg"

def convert_aaxc_to_m4b(asin, key, iv):
    # ffmpeg -y -activation_bytes [activation_bytes] -i  './[filename].aax' -codec copy '[filename].m4b'
    ffmpeg = get_ffmpeg_path()
    command = [ffmpeg, '-y', '-audible_key', key, '-audible_iv', iv, '-i', f"{get_local_file_dir()}{asin}.aaxc", '-codec', 'copy', f"{get_local_file_dir()}{asin}.m4b"]
    print(f"Running command: {command}")
    result = subprocess.run(
            command, 
        capture_output=True, 
        text=True, 
        env={**os.environ, 'CONFIG_DIR_ENV': 'audible-cli'})
    return result



@https_fn.on_request(region="europe-west1")
@require_api_key
def dev_upload_ffmpeg(req: https_fn.Request) -> https_fn.Response:
    if ENVIRONEMENT.value != "dev":
        return https_fn.Response(json.dumps({
            "message": "This function is only available in the dev environment",
            "status": "error"
        }), status=403, content_type="application/json")

    try:
        bucket_name = "visibl-dev-ali"
        local_ffmpeg_path = "../test/bin/ffmpeg"
        destination_blob_name = "bin/ffmpeg"

        bucket = storage.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(local_ffmpeg_path)

        return https_fn.Response(json.dumps({
            "message": "FFmpeg binary uploaded successfully",
            "status": "success",
            "destination": f"gs://{bucket_name}/{destination_blob_name}"
        }), content_type="application/json")

    except Exception as e:
        print(f"Error uploading FFmpeg binary: {str(e)}")
        return https_fn.Response(json.dumps({
            "message": f"Error uploading FFmpeg binary: {str(e)}",
            "status": "error"
        }), status=500, content_type="application/json")


# Okay maybe give up on using the CLI and just get the URls
# from https://github.com/mkb79/Audible/issues/3
# or https://github.com/mkb79/Audible/blob/master/examples/download_books_aax.py


# From examples:
# https://github.com/mkb79/Audible/blob/master/examples/download_books_aax.py
def get_license_response(client, asin, quality):
    try:
        response = client.post(
            f"content/{asin}/licenserequest",
            body={
                "drm_type": "Adrm",
                "consumption_type": "Download",
                "quality": quality,
            },
        )
        return response
    except Exception as e:
        print(f"Error: {e}")
        return


def get_download_link(license_response):
    return license_response["content_license"]["content_metadata"]["content_url"][
        "offline_url"
    ]


def download_file(url, filename):
    headers = {"User-Agent": "Audible/671 CFNetwork/1240.0.4 Darwin/20.6.0"}
    with httpx.stream("GET", url, headers=headers) as r:
        with open(filename, "wb") as f:
            for chunck in r.iter_bytes():
                f.write(chunck)
    return filename

@https_fn.on_request(region="europe-west1", memory=4096, timeout_sec=540)
@require_api_key
def audible_download_aaxc(req: https_fn.Request) -> https_fn.Response:
    logger.info(f"Starting audible_download_aaxc function")
    auth_data = req.get_json().get("auth", {})
    asin = req.get_json().get("asin")
    bucket_name = req.get_json().get("bucket")
    path = req.get_json().get("path")

    if not isinstance(auth_data, dict):
        auth_data = {}
    if not auth_data:
        logger.error("No auth data provided in the request body")
        raise ValueError("No auth data provided in the request body")
    
    logger.debug(f"Creating Audible client with provided auth data")
    auth = audible.Authenticator.from_dict(auth_data)
    client = audible.Client(auth)
    logger.info(f"Fetching library for ASIN: {asin}")
    books = client.get(
        path="library",
        params={"response_groups": "product_attrs", "num_results": "999"},
    )
    book = next((book for book in books['items'] if book['asin'] == asin), None)
    if not book:
        logger.error(f"Book with ASIN {asin} not found in the library")
        return https_fn.Response(json.dumps({
            "message": f"Book with ASIN {asin} not found in the library",
            "status": "error"
        }), status=404, content_type="application/json")
    logger.info(f"Getting license response for ASIN: {asin}")
    lr = get_license_response(client, asin, quality="High")
    if lr:
        logger.debug(f"License response received for ASIN: {asin}")
        dl_link = get_download_link(lr)
        filename = f"{get_local_file_dir()}{asin}.aaxc"
        logger.info(f"Downloading file from: {dl_link}")
        status = download_file(dl_link, filename)
        logger.debug(f"Downloaded file: {status}")
        logger.info(f"Decrypting voucher for ASIN: {asin}")
        decrypted_voucher = decrypt_voucher_from_licenserequest(auth, lr)
        logger.info(f"Downloading FFmpeg binary from bucket: {bucket_name}")
        download_ffmpeg_binary(bucket_name)
        logger.info(f"Converting aaxc to m4b for ASIN: {asin}")
        convert_result = convert_aaxc_to_m4b(asin, decrypted_voucher["key"], decrypted_voucher["iv"])
        if convert_result.returncode != 0:
            logger.error(f"Error converting aaxc to m4b: {convert_result.stderr}")
            return https_fn.Response(json.dumps({
                "message": f"Error converting aaxc to m4b: {convert_result.stderr}",
                "status": "error"
            }), status=500, content_type="application/json")
        logger.info(f"Uploading m4b file to storage")
        m4b_blob = upload_to_storage(bucket_name, path, asin, ".m4b")
        logger.info(f"Uploading aaxc file to storage")
        aaxc_blob = upload_to_storage(bucket_name, path, asin, ".aaxc")
        if m4b_blob.exists() and aaxc_blob.exists():
            logger.info(f"Successfully processed and uploaded files for ASIN: {asin}")
            return https_fn.Response(json.dumps({
                "message": "Audible file downloaded and uploaded successfully",
                "status": "success",
                "download_status": status,
                "aaxc_path": filename,
                "licence": decrypted_voucher,
                "m4b_path": m4b_blob.name
            }), content_type="application/json")
    else:
        logger.error(f"Error getting license response for ASIN: {asin}")
        return https_fn.Response(json.dumps({
            "message": f"Error getting license response for {asin}",
            "status": "error"
        }), status=500, content_type="application/json")