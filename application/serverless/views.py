from django.http import HttpResponse, HttpResponseRedirect

from application.serverless.cos_storage import cos_presigned_url

MESH_BUCKET = 'mesh_bucket'
TCL_BUCKET = 'tcl_bucket'
OUTPUT_BUCKET = 'output_bucket'
BUCKET_MAPPING = {
    MESH_BUCKET: 'ece496-fullmontesw-bucket-mesh',
    TCL_BUCKET: 'ece496-fullmontesw-bucket-tcl',
    OUTPUT_BUCKET: 'ece496-fullmontesw-bucket-outputs'
}


def cos_download_view(request, filename, bucket):
    if request.method != 'GET':
        return HttpResponse(status=405)
    if filename is None:
        raise ValueError("Found empty filename")
    try:
        response = cos_presigned_url(
            bucket_name=BUCKET_MAPPING[bucket],
            key_name=filename
        )
    except:
        return HttpResponse("The file you are requesting does not exist on the server.")

    return HttpResponseRedirect(response)
