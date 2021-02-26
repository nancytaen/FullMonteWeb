from django import forms
from django.forms import formset_factory
from django.forms import BaseFormSet
from .models import *
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
import sys

class tclInputForm(forms.ModelForm):
    class Meta:
        model = tclInput
        fields = ('meshFile', 'kernelType', 'scoredVolumeRegionID', 'packetCount')
        """
        kernel_choices = (('TetraSVKernel','TetraSVKernel'),
                         ('TetraSurfaceKernel','TetraSurfaceKernel'),
                         ('TetraVolumeKernel','TetraVolumeKernel'),
                         ('TetraInternalKernel','TetraInternalKernel'))
        widgets = {
            'kernelType': forms.Select(choices=kernel_choices),
        }
        """

    def __init__(self, CUDA=False, *args, **kwargs):
        initial = kwargs.get('initial', {})
        initial['scoredVolumeRegionID'] = 1
        initial['packetCount'] = 1000000
        kwargs['initial'] = initial
        super(tclInputForm, self).__init__(*args, **kwargs)
        if CUDA == True:
            CUDA_kernel_choices = (('TetraCUDASVKernel','TetraCUDASVKernel'),
                         ('TetraCUDASurfaceKernel','TetraCUDASurfaceKernel'),
                         ('TetraCUDAVolumeKernel','TetraCUDAVolumeKernel'),
                         ('TetraCUDAInternalKernel','TetraCUDAInternalKernel'))
            self.fields['kernelType'].widget = forms.Select(choices=CUDA_kernel_choices)
        else:
            kernel_choices = (('TetraSVKernel','TetraSVKernel'),
                         ('TetraSurfaceKernel','TetraSurfaceKernel'),
                         ('TetraVolumeKernel','TetraVolumeKernel'),
                         ('TetraInternalKernel','TetraInternalKernel'))
            self.fields['kernelType'].widget = forms.Select(choices=kernel_choices)
        self.fields['meshFile'].required = False

class presetForm(forms.ModelForm):
    class Meta:
        model = preset
        fields = ('presetMesh', 'layerDesc')

class materialSet(forms.Form):
    layer = forms.CharField(label='Layer', required = False, max_length=255)
    custom = forms.ModelChoiceField(label='Preset', queryset=Material.objects.all(), required = False)
    material = forms.CharField(label='Material',
                               widget=forms.TextInput(attrs={
                                                      'class': 'form-control',
                                                      'placeholder': 'Enter Material Name here'
                                                      }),
                               max_length=255)
    scatteringCoeff = forms.FloatField(label='Scattering Coefficient', min_value=0)
    absorptionCoeff = forms.FloatField(label='Absorption Coefficient', min_value=0)
    refractiveIndex = forms.FloatField(label='Refractive Index', min_value=1)
    anisotropy = forms.FloatField(label='Anisotropy', min_value=-1, max_value=1)

class materialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ('material_name', 'scattering_coeff', 'absorption_coeff', 'refractive_index', 'anisotropy')

class pdtForm(forms.Form):
    opt = forms.ChoiceField(label="Optical File")
    mesh = forms.ChoiceField(label="Mesh File")
    total_energy = forms.CharField(label='Total Energy', required = True, max_length=255)
    num_packets = forms.CharField(label='Num Packets', required = True, max_length=255)
    wave_length = forms.CharField(label='Wave Length', required = True, max_length=255)
    tumor_weight = forms.CharField(label='Tumor Weight', required = True, max_length=255)
    
    # light_placement_file = forms.FileField(label='light_placement_file')

    def __init__(self, opt_list=None, mesh_list=None, *args, **kwargs):
        super(pdtForm, self).__init__(*args, **kwargs)
        choice_opt = [(opt_name, opt_name) for opt_name in opt_list]
        if opt_list:
            self.fields['opt'].choices = choice_opt
        choice_mesh = [(mesh_name, mesh_name) for mesh_name in mesh_list]
        if mesh_list:
            self.fields['mesh'].choices = choice_mesh
        
class pdtPlaceFile(forms.Form):
    placement_type = forms.ChoiceField(label='Placement Type', choices=(('fixed','fixed'),
                                                                        ('virtual', 'virtual'),))
    source_type = forms.ChoiceField(label='Source Type', choices=(('point','point'),
                                                                        ('line', 'line'),))
    light_placement_file = forms.FileField(
        label='Placement File'
    )

class mosekLicense(forms.Form):
    mosek_license = forms.FileField(
        label='Mosek license'
    )
        

class lightSource(forms.Form):
    sourceType = forms.ChoiceField(label='Type', choices=(('Point','Point'),
                                                          ('PencilBeam','PencilBeam'),
                                                          ('Volume','Volume'),
                                                          ('Ball','Ball'),
                                                          #('Line','Line'),
                                                          #('Fiber','Fiber'),
                                                          #('Tetraface','Tetraface'),
                                                          #('Composite','Composite')
                                                          ))
    # for Point
    xPos = forms.FloatField(label='X Position', widget=forms.TextInput(attrs={'placeholder': 'x'}), required=False)
    yPos = forms.FloatField(label='Y Position', widget=forms.TextInput(attrs={'placeholder': 'y'}), required=False)
    zPos = forms.FloatField(label='Z Position', widget=forms.TextInput(attrs={'placeholder': 'z'}), required=False)

    # for Pencil Beam (Position uses xyz from point)
    xDir = forms.FloatField(label='X Direction', widget=forms.TextInput(attrs={'placeholder': 'x'}), required=False)
    yDir = forms.FloatField(label='Y Direction', widget=forms.TextInput(attrs={'placeholder': 'y'}), required=False)
    zDir = forms.FloatField(label='Z Direction', widget=forms.TextInput(attrs={'placeholder': 'z'}), required=False)

    # for Volume
    vElement = forms.IntegerField(label='V Element ID', required=False)

    # for Ball (center uses xyz from point)
    rad = forms.FloatField(label='Radius', required=False)

    # for Line


    power = forms.IntegerField(label='Power', required=False, initial=1)

class RequiredFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        super(RequiredFormSet, self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False



class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, help_text='Required.')
    last_name = forms.CharField(max_length=30, help_text='Required.')
    email = forms.EmailField(max_length=254, help_text='Required.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )

class awsFiles(forms.ModelForm):
    class Meta:
        model = awsFile
        fields = ('DNS', 'pemfile', 'TCP_port')
    def __init__(self, *args, **kwargs):
        super(awsFiles, self).__init__(*args, **kwargs)

class visualizeMeshForm(forms.ModelForm):
    class Meta:
        model = visualizeMesh
        fields = ('outputMeshFile',)
    def __init__(self, *args, **kwargs):
        super(visualizeMeshForm, self).__init__(*args, **kwargs)

materialSetSet = formset_factory(materialSet, formset=RequiredFormSet)
lightSourceSet = formset_factory(lightSource, formset=RequiredFormSet)
