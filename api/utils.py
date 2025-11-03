import os

def get_minio_url(object_key, for_backend=True):
    if for_backend:
        #host = "minio:9000"  # Docker service name for internal use
        host = "192.168.1.222:9000"
    else:
        #host = "localhost:9000"  # For browser access
        host = "192.168.1.222:9000"
    bucket = os.environ.get("AWS_STORAGE_BUCKET_NAME", "stylescope-bucket")
    return f"http://{host}/{bucket}/{object_key}"