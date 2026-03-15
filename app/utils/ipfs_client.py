import requests
from app.config.settings import settings
import hashlib

def upload_to_ipfs(file_bytes: bytes, filename: str) -> str:
    """Uploads a file to IPFS via Pinata and returns the CID"""
    if not settings.PINATA_API_KEY or not settings.PINATA_SECRET_API_KEY:
        print("Warning: PINATA keys not set. Returning a mock CID for prototype.")
        h = hashlib.sha256()
        h.update(file_bytes)
        return "Qm" + h.hexdigest()

    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    
    files = {"file": (filename, file_bytes)}
    headers = {
        "pinata_api_key": settings.PINATA_API_KEY,
        "pinata_secret_api_key": settings.PINATA_SECRET_API_KEY,
    }

    try:
        response = requests.post(url, files=files, headers=headers)
        response.raise_for_status()
        return response.json()["IpfsHash"]
    except Exception as e:
        print(f"Error uploading to IPFS: {e}")
        return "Qm_fallback_" + hashlib.sha256(file_bytes).hexdigest()
