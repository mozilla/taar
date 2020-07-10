
import hashlib

def hasher(client_id):
    return hashlib.new("sha256", client_id.encode("utf8")).hexdigest()
