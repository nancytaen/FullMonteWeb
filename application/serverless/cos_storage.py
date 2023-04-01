from django.conf import settings
import ibm_boto3
from ibm_botocore.client import Config


def handle_uploaded_file(request_f, dest_f):
    with open(dest_f, 'wb+') as destination:
        for chunk in request_f.chunks():
            destination.write(chunk)


def cos_search_prefix(bucket_name, prefix):
    client = ibm_boto3.client(
        "s3",
        ibm_api_key_id=settings.IBM_COS_API_KEY_ID,
        ibm_service_instance_id=settings.IBM_COS_SERVICE_INSTANCE_CRN,
        ibm_auth_endpoint=settings.IBM_COS_AUTH_ENDPOINT,
        config=Config(signature_version="oauth"),
        endpoint_url=settings.IBM_COS_ENDPOINT_URL
    )
    response = client.list_objects_v2(
        Bucket=bucket_name,
        EncodingType='url',
        MaxKeys=123,
        Prefix=prefix,
        FetchOwner=True | False,
    )

    return [filename['Key'] for filename in response.get('Contents', [])]


def cos_upload_file(bucket_name, item_name, file_path):
    print("Starting large file upload for {0} to bucket: {1}".format(item_name, bucket_name))

    # Create client connection
    cos_cli = ibm_boto3.client(
        "s3",
        ibm_api_key_id=settings.IBM_COS_API_KEY_ID,
        ibm_service_instance_id=settings.IBM_COS_SERVICE_INSTANCE_CRN,
        ibm_auth_endpoint=settings.IBM_COS_AUTH_ENDPOINT,
        config=Config(signature_version="oauth"),
        endpoint_url=settings.IBM_COS_ENDPOINT_URL
    )

    try:
        # initiate file upload
        cos_cli.upload_file(file_path, bucket_name, item_name)

        print("File upload complete!")
    except Exception as e:
        print("Unable to complete large file upload: {0}".format(e))
    finally:
        print("completed file transfer")


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
