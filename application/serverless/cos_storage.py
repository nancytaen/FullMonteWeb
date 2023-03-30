import shortuuid

from django.conf import settings
import ibm_boto3


def generate_unique_request_id():
    return shortuuid.uuid()


def insert_id_to_filename(filename, request_id):
    # split filename into basename and extension
    # basename-<request_id>.ext
    partitions = filename.rsplit('.', 1)
    return f'{partitions[0]}-{request_id}.{partitions[1]}'


def extract_id_from_filename(filename):
    # use - and . as delimiters to extract the request id from filename
    base = filename.rsplit('.', 1)[0]
    return base.rsplit('-', 1)[1]


def cos_presigned_url(bucket_name, key_name, http_method='get_object', expiration=600):
    """
    https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-presign-url
    """
    access_key = settings.COS_HMAC_ACCESS_KEY_ID
    secret_key = settings.COS_HMAC_SECRET_ACCESS_KEY
    cos = ibm_boto3.client("s3",
                           aws_access_key_id=access_key,
                           aws_secret_access_key=secret_key,
                           endpoint_url=settings.IBM_COS_ENDPOINT_URL
                           )
    signed_url = cos.generate_presigned_url(http_method, Params={
                                           'Bucket': bucket_name, 'Key': key_name}, ExpiresIn=expiration)
    print("presigned download URL =>" + signed_url)
    return signed_url
