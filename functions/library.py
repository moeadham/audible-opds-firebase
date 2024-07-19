import audible
from audible.aescipher import decrypt_voucher_from_licenserequest
import json

AUTHFILE = 'audible_credentials.json'
auth = audible.Authenticator.from_file(AUTHFILE)
print(auth.refresh_token)
# refresh auth token
auth.refresh_access_token(auth.refresh_token)
auth.to_file(AUTHFILE)
client = audible.Client(auth=auth)
library = client.get(
        "1.0/library",
        num_results=1000,
        response_groups="product_desc, product_attrs",
        sort_by="-PurchaseDate"
    )
for book in library["items"]:
    itemSummary = {key: value for key, value in book.items() if value is not None}
    # print(json.dumps(itemSummary, indent=4))
    print(itemSummary["title"], itemSummary["asin"])

activation_bytes = auth.get_activation_bytes()
print(activation_bytes)
