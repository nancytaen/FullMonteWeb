from django.db import models
from application.storage_backends import *

# Create your models here.

class tclInput(models.Model):
    meshFile = models.FileField(storage=PublicMediaStorage())
    kernelType = models.CharField(max_length=255)

class tclScript(models.Model):
    script = models.FileField(storage=PublicMediaStorage())

class preset(models.Model):
    presetMesh = models.FileField(storage=PublicMediaStorage())
    layerDesc = models.TextField(blank=True, null=True)

class Material(models.Model):
    material_name = models.CharField(max_length=50)

    objects = models.Manager()

    def __str__(self):
        return self.material_name

class Optical(models.Model):
    property_name = models.CharField(max_length=50)
    property_value = models.FloatField()
    material = models.ForeignKey(Material, on_delete=models.CASCADE)

    objects = models.Manager()

    def __str__(self):
        return self.property_name
