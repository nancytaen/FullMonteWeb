from django.db import models

# Create your models here.

class tclInput(models.Model):
    meshFile = models.FileField(upload_to='application/mesh')
    kernelType = models.CharField(max_length=255)

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