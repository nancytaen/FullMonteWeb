from django.db import models
from application.storage_backends import *
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings 

user_model = settings.AUTH_USER_MODEL

# Create your models here.

class tclInput(models.Model):
    meshFile = models.FileField(storage=PublicMediaStorage())
    kernelType = models.CharField(max_length=255)
    packetCount = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class awsFile(models.Model):
    DNS = models.CharField(max_length=250)
    pemfile = models.FileField(storage=PublicMediaStorage())
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

class pdtPresetData(models.Model):
    opt_list = models.CharField(max_length=1024)
    mesh_list = models.CharField(max_length=1024)
    opt_addr = models.CharField(max_length=1024)
    mesh_addr = models.CharField(max_length=1024)
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )
class opFileInput(models.Model):
    total_energy = models.CharField(max_length=64)
    num_packets = models.CharField(max_length=64)
    wave_length = models.CharField(max_length=64)
    data_dir = models.CharField(max_length=255)
    data_name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=64)
    tumor_weight = models.CharField(max_length=64)
    placement_type = models.CharField(max_length=64)
    opt_file = models.CharField(max_length=255)
    light_source_file = models.CharField(max_length=255)
    placement_file = models.FileField(storage=PublicMediaStorage())
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class simulationHistory(models.Model):
    simulation_type = models.CharField(max_length=250)
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )
    tcl_script_path = models.FileField(storage=PublicMediaStorage())
    mesh_file_path = models.FileField(storage=PublicMediaStorage())
    output_vtk_path = models.FileField(storage=PublicMediaStorage())
    output_txt_path = models.FileField(storage=PublicMediaStorage())
    output_dvh_path = models.FileField(storage=PublicMediaStorage())
    simulation_time = models.DateTimeField(auto_now=True)

class tclScript(models.Model):
    script = models.FileField(storage=PublicMediaStorage())
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class fullmonteOutput(models.Model):
    outputVtk = models.FileField(storage=PublicMediaStorage())
    outputFluence = models.FileField(storage=PublicMediaStorage())
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

class preset(models.Model):
    presetMesh = models.FileField(storage=PublicMediaStorage())
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

class visualizeMesh(models.Model):
    outputMeshFile = models.FileField(storage=PublicMediaStorage())
    user = models.ForeignKey(user_model,
                             default = 0,
                             null = True,
                             on_delete=models.CASCADE
                             )

