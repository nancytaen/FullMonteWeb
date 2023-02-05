from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from .models import *
from .forms import *
from django.core.files.base import ContentFile
import sys
from django.db import models, connections
from multiprocessing import Process, Event
import ibm_boto3
from ibm_botocore.client import Config, ClientError

# FullMonte Serverless Simulator start page
def fmServerlessSimulator(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        print(request.POST)
        sys.stdout.flush()
        form = serverlessForm(data=request.POST, files=request.FILES)
        # check whether it's valid:
        if form.is_valid():
            form.save()     
            p = Process(target=transfer_files_and_run_serverless_simulation, args=(request, ))
            p.start()
            return HttpResponseRedirect('/application/serverless_running')

    # If this is a GET (or any other method) create the default form.
    else:
        form = serverlessForm(data=request.GET)

    context = {
        'form': form,
    }

    return render(request, "serverless_simulator.html", context)

# FullMonte serverless simulation running page
def serverless_running(request):
    context = {

    }
    return render(request, 'serverless_running.html', context)

def transfer_files_and_run_serverless_simulation(request):
    tcl_script = serverlessInput.objects.latest('id').script.name
    meshFilePath = serverlessInput.objects.latest('id').meshFile.name
    
    # test uploading all files to janelle's test tcl bucket
    upload_large_file(settings.COS_TCL_BUCKET_NAME, meshFilePath, meshFilePath)
    upload_large_file(settings.COS_TCL_BUCKET_NAME, tcl_script, tcl_script)
    # TODO upload yaml config file with instance specs

def upload_large_file(bucket_name, item_name, file_path):
    print("Starting large file upload for {0} to bucket: {1}".format(item_name, bucket_name))

    # set the chunk size to 5 MB
    part_size = 1024 * 1024 * 5

    # set threadhold to 5 MB
    file_threshold = 1024 * 1024 * 5

    # Create client connection
    cos_cli = ibm_boto3.client("s3",
        ibm_api_key_id=settings.COS_API_KEY_ID,
        ibm_service_instance_id=settings.COS_SERVICE_INSTANCE_CRN,
        ibm_auth_endpoint=settings.COS_AUTH_ENDPOINT,
        config=Config(signature_version="oauth"),
        endpoint_url=settings.COS_ENDPOINT
    )

    # set the transfer threshold and chunk size in config settings
    transfer_config = ibm_boto3.s3.transfer.TransferConfig(
        multipart_threshold=file_threshold,
        multipart_chunksize=part_size
    )

    # create transfer manager
    transfer_mgr = ibm_boto3.s3.transfer.TransferManager(cos_cli, config=transfer_config)

    try:
        # initiate file upload
        future = transfer_mgr.upload(file_path, bucket_name, item_name)

        # wait for upload to complete
        future.result()

        print ("File upload complete!")
    except Exception as e:
        print("Unable to complete large file upload: {0}".format(e))
    finally:
        transfer_mgr.shutdown()
