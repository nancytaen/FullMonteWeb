from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.db import IntegrityError
from django.db.models import Model
from django.shortcuts import redirect

from application.serverless.cos_storage import cos_presigned_url, insert_id_to_filename
from application.serverless.models import ServerlessRequest, ServerlessOutput

BUCKET_NAME_MAPPING = {
    'mesh': 'IBM_COS_MESH_BUCKET_NAME',
    'tcl': 'IBM_COS_TCL_BUCKET_NAM',
    'output': 'IBM_COS_OUTPUT_BUCKET_NAME',
}

# def query_serverless_status(request):
#     if request.method != 'POST':
#         return HttpResponse(status=405)
#     try:
#         r = ServerlessRequest.objects.get(request_id=request.get('id'), user=request.user)
#     except Model.DoesNotExist:
#         return HttpResponse(status=404)
#     if r.completed:
#         return redirect('simulation_finish')
#     return HttpResponse(status=200)


def serverless_finish(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    try:
        r = ServerlessRequest.objects.get(request_id=request.get('id'))
    except Model.DoesNotExist:
        return HttpResponse(status=404)

    try:
        ServerlessOutput.objects.create(
            request=r,
            output_vtk_name=f'{r.mesh_name}.out.zip',
            output_txt_name=f'{r.mesh_name}.txt',
            log_name=f'{r.mesh_name}.log',
        )
        # ServerlessOutput.objects.create(
        #     request=r,
        #     output_vtk_name=request.get('output_vtk'),
        #     output_txt_name=request.get('output_txt'),
        #     log_name=request.get('log'),
        # )
    except IntegrityError:
        return HttpResponse(status=403)

    r.completed = True
    r.save()

    # TODO email user
    print(r.user.email)

    return HttpResponse(status=200)


def cos_download_view(request, filename, bucket):
    """
        return presigned url to objects in IBM COS
        TODO authentication - do we want to grant access to
            * users who are not logged in
            * users who did not request the associated simulation
    """
    if request.method != 'GET':
        return HttpResponse(status=405)
    if filename is None:
        raise ValueError("Found empty filename")
    try:
        response = cos_presigned_url(
            bucket_name=settings[BUCKET_NAME_MAPPING[bucket]],
            key_name=filename
        )
    except:
        return HttpResponse("The file you are requesting does not exist on the server.")

    return HttpResponseRedirect(response)
