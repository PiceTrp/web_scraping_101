import requests
from urllib.parse import urlparse

# --- Configuration ---
# The list of URLs you want to check.
# Replace these with your own list of PDF links.
# URLS_TO_CHECK = [
#     "https://expired.badssl.com/",  # Example of an expired certificate
#     "https://self-signed.badssl.com/", # Example of a self-signed certificate
#     "https://wrong.host.badssl.com/", # Example of a hostname mismatch
#     "http://example.com", # Example of a non-HTTPS URL
#     "https://www.google.com", # correct URL with valid SSL
#     # Our test websites
#     "https://rtd.moe.go.th/download/manual.pdf", # Example of a privacy issue URL
#     "http://innodev.moe.go.th/document/innovation-119.pdf", # Example of a able-to-access URL
# ]

# --- Main Script ---

def check_url_privacy(urls):
    """
    Checks a list of URLs for SSL/TLS certificate issues.

    Args:
        urls: A list of URLs to check.
    """
    print("--- Starting URL Privacy Check ---")
    for url in urls:
        print(f"\n[INFO] Checking: {url}")
        
        # Check if the URL uses HTTPS
        parsed_url = urlparse(url)
        if parsed_url.scheme.lower() != 'https':
            print(f"[WARNING] The URL is not using HTTPS. Connections to this site may not be private.")
            continue

        try:
            # The 'requests' library by default verifies SSL certificates.
            # We set a timeout to avoid waiting indefinitely for a response.
            response = requests.get(url, timeout=10)
            
            # A successful request (status code 200) with no SSL error means the certificate is valid.
            if response.status_code == 200:
                print(f"[SUCCESS] Connection is secure. The SSL certificate is valid.")
            else:
                print(f"[WARNING] Connected successfully, but received an unusual status code: {response.status_code}")

        except requests.exceptions.SSLError as e:
            # This is the primary error we are looking for.
            # It indicates a problem with the SSL certificate.
            print(f"[ERROR] Privacy Error Detected! The SSL certificate is invalid. Reason: {e}")
        
        except requests.exceptions.Timeout:
            # Handle cases where the server doesn't respond in time.
            print(f"[ERROR] Connection timed out. The server did not respond.")
            
        except requests.exceptions.ConnectionError as e:
            # Handle other connection issues, like DNS failure or connection refused.
            print(f"[ERROR] Could not connect to the server. Reason: {e}")
            
        except requests.exceptions.RequestException as e:
            # A catch-all for any other 'requests' related exceptions.
            print(f"[ERROR] An unexpected error occurred: {e}")

    print("\n--- URL Privacy Check Complete ---")
