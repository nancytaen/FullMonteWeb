from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings 
from application.serverless.cos_storage import cos_presigned_url

MESH_BUCKET = 'mesh_bucket'
TCL_BUCKET = 'tcl_bucket'
GENERATED_TCL_BUCKET = 'generated_tcl_bucket'
OUTPUT_BUCKET = 'output_bucket'
BUCKET_MAPPING = {
    MESH_BUCKET: settings.IBM_COS_MESH_BUCKET_NAME,
    GENERATED_TCL_BUCKET: settings.IBM_COS_GENERATED_TCL_BUCKET_NAME,
    TCL_BUCKET: settings.IBM_COS_TCL_BUCKET_NAME,
    OUTPUT_BUCKET: settings.IBM_COS_OUTPUT_BUCKET_NAME,
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
