# Generated by Django 3.2.18 on 2023-03-09 21:12

import application.storage_backends
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Material',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('material_name', models.CharField(max_length=50)),
                ('material_unit', models.CharField(max_length=50)),
                ('scattering_coeff', models.FloatField(validators=[django.core.validators.MinValueValidator(0)])),
                ('absorption_coeff', models.FloatField(validators=[django.core.validators.MinValueValidator(0)])),
                ('refractive_index', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('anisotropy', models.FloatField(validators=[django.core.validators.MinValueValidator(-1), django.core.validators.MaxValueValidator(1)])),
            ],
        ),
        migrations.CreateModel(
            name='meshFiles',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meshFile', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('originalMeshFileName', models.CharField(blank=True, max_length=255)),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='preset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('presetMesh', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('layerDesc', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='visualizeMesh',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('outputMeshFile', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='tclScript',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('script', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='tclInput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meshFile', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('originalMeshFileName', models.CharField(blank=True, max_length=255)),
                ('meshUnit', models.CharField(max_length=255)),
                ('kernelType', models.CharField(max_length=255)),
                ('packetCount', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('totalEnergy', models.FloatField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('energyUnit', models.CharField(max_length=255)),
                ('meshFileID', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='application.meshfiles')),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='simulationHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('simulation_type', models.CharField(max_length=250)),
                ('tcl_script_path', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('mesh_file_path', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('originalMeshFileName', models.CharField(blank=True, max_length=255)),
                ('output_vtk_path', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('output_txt_path', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('output_dvh_csv_path', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('output_dvh_fig_path', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('simulation_time', models.DateTimeField(auto_now=True)),
                ('meshFileID', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='application.meshfiles')),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='serverlessInput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meshFile', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('script', models.FileField(null=True, storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='processRunning',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('running', models.BooleanField(default=False)),
                ('pid', models.IntegerField(default=0)),
                ('start_time', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='pdtPresetData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('opt_list', models.CharField(max_length=10240)),
                ('mesh_list', models.CharField(max_length=10240)),
                ('opt_addr', models.CharField(max_length=10240)),
                ('mesh_addr', models.CharField(max_length=10240)),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='pdtOuputLogFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdt_space_log', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='opFileInput',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_energy', models.CharField(max_length=64)),
                ('num_packets', models.CharField(max_length=64)),
                ('wave_length', models.CharField(max_length=64)),
                ('data_dir', models.CharField(blank=True, max_length=255, null=True)),
                ('data_name', models.CharField(blank=True, max_length=255, null=True)),
                ('source_type', models.CharField(max_length=64)),
                ('tumor_weight', models.CharField(max_length=64)),
                ('placement_type', models.CharField(max_length=64)),
                ('opt_file', models.CharField(blank=True, max_length=255, null=True)),
                ('opt_file_storage', models.FileField(blank=True, null=True, storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('mesh_file_storage', models.FileField(blank=True, null=True, storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('tissue_property_file_storage', models.FileField(blank=True, null=True, storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('tissue_types_file_storage', models.FileField(blank=True, null=True, storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('light_source_file', models.CharField(max_length=255)),
                ('placement_file', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='meshFileInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fileName', models.CharField(max_length=255)),
                ('remoteFileExists', models.BooleanField(default=False)),
                ('dvhFig', models.TextField(blank=True, null=True)),
                ('powerAndScaling', models.TextField(blank=True, null=True)),
                ('thresholdFluence', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='awsFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('DNS', models.CharField(max_length=250)),
                ('pemfile', models.FileField(storage=application.storage_backends.PublicMediaStorage(), upload_to='')),
                ('TCP_port', models.IntegerField(validators=[django.core.validators.MinValueValidator(8000), django.core.validators.MaxValueValidator(8999)])),
                ('user', models.ForeignKey(default=0, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
