from django.db import models
from application.storage_backends import *
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings 

user_model = settings.AUTH_USER_MODEL
def per_user_path(instance, filename):
    return '{0}/{1}'.format(instance.user, filename)
# Create your models here.

class tclInput(models.Model):
    meshFile = models.FileField(storage=PublicMediaStorage(), upload_to=per_user_path)
    kernelType = models.CharField(max_length=255)
    packetCount = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class awsFile(models.Model):
    DNS = models.CharField(max_length=250)
    pemfile = models.FileField(storage=PublicMediaStorage(), upload_to=per_user_path)
    TCP_port = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(8000), MaxValueValidator(8999)])
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class processRunning(models.Model):
    running = models.BooleanField(default = False)
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )
    pid = models.IntegerField(default=0)
    start_time = models.DateTimeField(auto_now=True)

class simulationHistory(models.Model):
    simulation_type = models.CharField(max_length=250)
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )
    tcl_script_path = models.CharField(max_length=250)
    mesh_file_path = models.CharField(max_length=250)
    output_vtk_path = models.CharField(max_length=250)
    output_txt_path = models.CharField(max_length=250)
    output_dvh_path = models.CharField(max_length=250)
    simulation_time = models.DateTimeField(auto_now=True)

class tclScript(models.Model):
    script = models.FileField(storage=PublicMediaStorage(), upload_to=per_user_path)
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class fullmonteOutput(models.Model):
    outputVtk = models.FileField(storage=PublicMediaStorage(), upload_to=per_user_path)
    outputFluence = models.FileField(storage=PublicMediaStorage(), upload_to=per_user_path)
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class preset(models.Model):
    presetMesh = models.FileField(storage=PublicMediaStorage(), upload_to=per_user_path)
    layerDesc = models.TextField(blank=True, null=True)

class Material(models.Model):
    material_name = models.CharField(max_length=50)
    scattering_coeff = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    absorption_coeff = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    refractive_index = models.FloatField(null=True, blank=True, validators=[MinValueValidator(1)])
    anisotropy = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-1), MaxValueValidator(1)])

    objects = models.Manager()

    def __str__(self):
        return self.material_name
