from django.conf import settings
from django.db import models

user_model = settings.AUTH_USER_MODEL


class ServerlessRequest(models.Model):
    request_id = models.CharField(primary_key=True, max_length=255)
    mesh_name = models.CharField(max_length=255, null=False)
    tcl_name = models.CharField(max_length=255, null=False)
    completed = models.BooleanField(default=False)
    datetime = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        user_model,
        default=0,
        null=True,
        on_delete=models.CASCADE
    )


class ServerlessOutput(models.Model):
    request = models.OneToOneField(
        ServerlessRequest,
        null=False,
        default=0,
        on_delete=models.PROTECT,
        primary_key=True,
    )
    output_vtk_name = models.CharField(max_length=255, null=True)
    output_txt_name = models.CharField(max_length=255, null=True)
    log_name = models.CharField(max_length=255, null=True)
    datetime = models.DateTimeField(auto_now=True)
