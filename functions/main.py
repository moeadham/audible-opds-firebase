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
import re

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
        print(f"response_url: {response_url}")
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

def upload_to_storage(bucket_name, path, sku, extension):
    bucket = storage.bucket(bucket_name)
    # Find the downloaded file
    local_file_path = f'{get_local_file_dir()}{sku}{extension}'
    
    # Create the full path in the storage bucket
    blob = bucket.blob(f'{path}{sku}{extension}')
    print(f"Uploading {local_file_path} to {blob.name}")
    blob.upload_from_filename(local_file_path)
    # Check if the blob exists after upload
    print(f"Checking if blob {blob.name} exists:")
    print(blob.exists())
    return blob

def download_ffmpeg_binary(bucket_name):
    local_ffmpeg_path = f"{get_local_file_dir()}ffmpeg"
    # Check if ffmpeg already exists locally
    if os.path.exists(local_ffmpeg_path):
        print(f"FFmpeg binary already exists at {local_ffmpeg_path}")
        return True
    bucket = storage.bucket(bucket_name)
    ffmpeg_blob = bucket.blob('bin/ffmpeg')
    if not ffmpeg_blob.exists():
        print("FFmpeg binary not found in the bucket")
        return False
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

def get_ffmpeg_info(sku):
    ffmpeg = get_ffmpeg_path()
    command = [ffmpeg, '-i', f"{get_local_file_dir()}{sku}.aaxc", '-f', 'ffmetadata', '-hide_banner']
    print(f"Running command: {command}")
    result = subprocess.run(
            command, 
        capture_output=True, 
        text=True, 
        env={**os.environ, 'CONFIG_DIR_ENV': 'audible-cli'})
    return result

def get_ffmpeg_art(sku):
    ffmpeg = get_ffmpeg_path()
    command = [ffmpeg, '-y', '-i', f"{get_local_file_dir()}{sku}.aaxc", '-an', '-vcodec', 'copy', f"{get_local_file_dir()}{sku}.jpg", '-hide_banner']
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
        bucket_name = req.get_json().get("bucket")
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
    logger.info(f"Download progress for {filename}: 0%")
    with httpx.stream("GET", url, headers=headers) as r:
        total_size = int(r.headers.get('content-length', 0))
        bytes_downloaded = 0
        last_logged_progress = 0
        with open(filename, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
                bytes_downloaded += len(chunk)
                progress = (bytes_downloaded / total_size) * 100 if total_size > 0 else 0
                if progress - last_logged_progress >= 25:
                    logger.info(f"Download progress for {filename}: {progress:.2f}%")
                    last_logged_progress = progress
    logger.info(f"Download completed for {filename}")
    return filename

@https_fn.on_request(
        region="europe-west1",
        memory=8192,
        cpu=2,
        timeout_sec=540,
        concurrency=10,
        max_instances=100
    )
@require_api_key
def audible_download_aaxc(req: https_fn.Request) -> https_fn.Response:
    logger.info(f"Starting audible_download_aaxc function")
    auth_data = req.get_json().get("auth", {})
    sku = req.get_json().get("sku")
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
    logger.info(f"Fetching library for SKU: {sku}")
    books = client.get(
        path="library",
        params={"response_groups": "product_attrs", "num_results": "999"},
    )
    book = next((book for book in books['items'] if book['sku_lite'] == sku), None)
    if not book:
        logger.error(f"Book with sku_lite {sku} not found in the library")
        return https_fn.Response(json.dumps({
            "message": f"Book with sku_lite {sku} not found in the library",
            "status": "error"
        }), status=404, content_type="application/json")
    asin = book['asin']
    logger.info(f"Getting license response for ASIN: {asin}")
    lr = get_license_response(client, asin, quality="High")
    if lr:
        logger.debug(f"License response received for ASIN: {asin}")
        dl_link = get_download_link(lr)
        filename = f"{get_local_file_dir()}{sku}.aaxc"
        logger.info(f"Downloading file from: {dl_link}")
        status = download_file(dl_link, filename)
        logger.debug(f"Downloaded file: {status}")
        logger.info(f"Decrypting voucher for ASIN: {asin}")
        decrypted_voucher = decrypt_voucher_from_licenserequest(auth, lr)
        logger.info(f"Downloading FFmpeg binary from bucket: {bucket_name}")
        download_ffmpeg_binary(bucket_name)
        logger.info(f"Decrypted voucher: {decrypted_voucher}")
        logger.info(f"Uploading aaxc file to storage")
        aaxc_blob = upload_to_storage(bucket_name, path, sku, ".aaxc")
        logger.info("Generating metadata from aaxc info and Audible details")
        ffmpeg_info_result = get_ffmpeg_info(sku)
        metadata = ffmpeg_info_to_json(ffmpeg_info_result.stderr, book)
        # Write metadata to JSON file
        try:
            with open(f"{get_local_file_dir()}{sku}.json", 'w') as metadata_file:
                json.dump(metadata, metadata_file, indent=2)
            logger.debug(f"Metadata successfully written to {sku}.json")
        except IOError as e:
            logger.error(f"Error writing metadata to file: {str(e)}")
        json_blob = upload_to_storage(bucket_name, path, sku, ".json")

        get_ffmpeg_art(sku)
        art_blob = upload_to_storage(bucket_name, path, sku, ".jpg")

        if aaxc_blob.exists() and aaxc_blob.exists() and json_blob.exists() and art_blob.exists():
            logger.info(f"Successfully processed and uploaded files for SKU: {sku}")
            return https_fn.Response(json.dumps({
                "message": "Audible file downloaded and uploaded successfully",
                "status": "success",
                "download_status": status,
                "aaxc_path": filename,
                "key": decrypted_voucher["key"],
                "iv": decrypted_voucher["iv"],
                "licence_rules": decrypted_voucher["rules"],
                "metadata": metadata
            }), content_type="application/json")
    else:
        logger.error(f"Error getting license response for SKU: {sku}")
        return https_fn.Response(json.dumps({
            "message": f"Error getting license response for {sku}",
            "status": "error"
        }), status=500, content_type="application/json")

def ffmpeg_info_to_json(ffmpeg_info, library_data):
    # Initialize the result dictionary
    result = {}

    # Extract metadata
    metadata = re.search(r'Metadata:(.*?)Duration:', ffmpeg_info, re.DOTALL)
    if metadata:
        metadata = metadata.group(1).strip().split('\n')
        for line in metadata:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key == 'title':
                # Remove "(Unabridged)" from the title and strip whitespace
                value = value.replace("(Unabridged)", "").strip()
                result['title'] = value
            elif key == 'artist':
                result['author'] = [author.strip() for author in value.split(',')]
            elif key == 'date':
                result['year'] = value

    # Get details from the audible catalogue if it is available.
    if library_data["release_date"]:
        result['year'] = library_data["release_date"].split("-")[0]
    if library_data['merchandising_summary']:
        result['description'] = library_data['merchandising_summary'].replace('<p>', '').replace('</p>', '')
    if library_data['title']:
        result['title'] = library_data['title']
    if library_data['subtitle']:
        result['subtitle'] = library_data['subtitle']
    if library_data['format_type'] == 'unabridged':
        result["abridged"] = False
    if library_data['sku_lite']:
        result['sku'] = library_data['sku_lite']
    if library_data['language']:
        result['language'] = library_data['language']
    if library_data['publication_datetime']:
        result['published'] = library_data['publication_datetime']

    
    # Extract bitrate
    bitrate = re.search(r'bitrate: (\d+) kb/s', ffmpeg_info)
    if bitrate:
        result['bitrate_kbs'] = int(bitrate.group(1))

    # Extract codec
    codec = re.search(r'Audio: (\w+)', ffmpeg_info)
    if codec:
        result['codec'] = codec.group(1)

    # Extract chapters
    chapters = re.findall(r'Chapter #0:(\d+): start (\d+\.\d+), end (\d+\.\d+)(?:\s+Metadata:\s+title\s+:\s+(.+))?', ffmpeg_info)
    result['chapters'] = {}
    for chapter in chapters:
        chapter_num, start, end, title = chapter
        result['chapters'][chapter_num] = {
            'startTime': float(start),
            'endTime': float(end),
        }
        if title:
            result['chapters'][chapter_num]['title'] = title.strip()

    # Set length to the end time of the last chapter
    if chapters:
        result['length'] = float(chapters[-1][2])

    return result

@https_fn.on_request(region="europe-west1")
@require_api_key
def audible_get_library(req: https_fn.Request) -> https_fn.Response:
    auth_data = req.get_json().get("auth", {})
    request_type = req.get_json().get("type", "opds")
    auth = audible.Authenticator.from_dict(auth_data)
    client = audible.Client(auth)
    library = client.get(
        "1.0/library",
        num_results=1000,
        response_groups="product_desc, product_attrs",
        sort_by="-PurchaseDate"
    )
    
    library_json = []

    for book in library["items"]:
        if request_type != "raw":
                print(f"ASIN: {book.get('asin', 'N/A')}, SKU: {book.get('sku', 'N/A')}, SKU Lite: {book.get('sku_lite', 'N/A')}, Title: {book.get('title', 'N/A')}")
                library_json.append(book_to_opds_publication(book))
        else:
            # Remove any null keys from the book dictionary
            book = {k: v for k, v in book.items() if v is not None}
            library_json.append(book)
    return https_fn.Response(json.dumps({
        "library": library_json,
        "status": "success"
    }), content_type="application/json")
    # now you need to make this like opds. We also need album art.
    # https://test.opds.io/2.0/home.json
    # https://readium.org/webpub-manifest/examples/Flatland/manifest.json


def book_to_opds_publication(book):
    publication = {
        "metadata": {
            "@type": "http://schema.org/Audiobook",
        },
        "links": [
            {
                "rel": "http://opds-spec.org/acquisition",
                "type": "application/audiobook+json"
            }
        ],
        # "images": [
        #     {
        #         "type": "image/jpeg",
        #         "rel": "http://opds-spec.org/image"
        #     }
        # ]
    }

    if "title" in book:
        publication["metadata"]["title"] = book["title"]
    if "authors" in book and book["authors"]:
        publication["metadata"]["author"] = {
            "name": book["authors"][0].get("name"),
            "sortAs": book["authors"][0].get("name")
        }
    if "sku_lite" in book:
        publication["metadata"]["identifier"] = book["sku_lite"]
    if "asin" in book:
        publication["metadata"]["identifier"] = book["asin"]
    if "language" in book:
        publication["metadata"]["language"] = book["language"]
    if "purchase_date" in book:
        publication["metadata"]["modified"] = book["purchase_date"]
    if "release_date" in book:
        publication["metadata"]["published"] = book["release_date"]
    if "publisher_name" in book:
        publication["metadata"]["publisher"] = book["publisher_name"]
    if "runtime_length_min" in book:
        publication["metadata"]["duration"] = f"{book['runtime_length_min']} minutes"
    if "merchandising_summary" in book:
        publication["metadata"]["description"] = book["merchandising_summary"]
    
    if "series" in book and book["series"]:
        publication["metadata"]["belongsTo"] = {
            "series": {
                "name": book["series"][0].get("title"),
                "position": book["series"][0].get("sequence")
            }
        }
    
    # Remove any None values from the metadata
    publication["metadata"] = {k: v for k, v in publication["metadata"].items() if v is not None}
    
    return publication

