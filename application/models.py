from django.db import models

# Create your models here.

class tclInput(models.Model):
    meshFile = models.FileField(upload_to='mesh')
    kernelType = models.CharField(max_length=255)
