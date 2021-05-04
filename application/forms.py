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
        fields = ('meshFile', 'meshUnit', 'kernelType', 'scoredVolumeRegionID', 'packetCount', 'totalEnergy', 'energyUnit' )
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
        initial['totalEnergy'] = 10
        kwargs['initial'] = initial
        super(tclInputForm, self).__init__(*args, **kwargs)
        # if CUDA == True:
        #     CUDA_kernel_choices = (('TetraCUDASVKernel','TetraCUDASVKernel'),
        #                  ('TetraCUDASurfaceKernel','TetraCUDASurfaceKernel'),
        #                  ('TetraCUDAVolumeKernel','TetraCUDAVolumeKernel'),
        #                  ('TetraCUDAInternalKernel','TetraCUDAInternalKernel'))
        #     self.fields['kernelType'].widget = forms.CheckboxSelectMultiple(choices=CUDA_kernel_choices)
        # else:
            # kernel_choices = (('TetraSVKernel','TetraSVKernel'),
            #              ('TetraSurfaceKernel','TetraSurfaceKernel'),
            #              ('TetraVolumeKernel','TetraVolumeKernel'),
            #              ('TetraInternalKernel','TetraInternalKernel'))
        kernel_choices = (('Absorbed','Energy Absorbed by Mesh'),
                        ('Leaving','Energy Leaving Mesh'),
                        ('Internal','Energy Entering/Exiting Internal Boundaries of Mesh'))
        self.fields['kernelType'].widget = forms.CheckboxSelectMultiple(choices=kernel_choices)
        self.fields['meshFile'].required = False
        mesh_unit_choices = (('mm','milimeters (mm)'),
                         ('cm','centimeters (cm)'))
        self.fields['meshUnit'].widget = forms.RadioSelect(choices=mesh_unit_choices)
        energy_unit_choices = (('J','Joules (J)'),
                         ('W','Watts (W)'))
        self.fields['energyUnit'].widget = forms.RadioSelect(choices=energy_unit_choices)

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
        fields = ('material_name', 'material_unit', 'scattering_coeff', 'absorption_coeff', 'refractive_index', 'anisotropy' )
    
    def __init__(self, *args, **kwargs):
        super(materialForm, self).__init__(*args, **kwargs)
        unit_choices = (('mm','milimeters (mm)'),
                         ('cm','centimeters (cm)'))
        self.fields['material_unit'].widget = forms.RadioSelect(choices=unit_choices)

class pdtForm(forms.Form):
    opt = forms.ChoiceField(label="Optical File", 
                            help_text="Available optical files.")
    mesh = forms.ChoiceField(label="Mesh File", 
                            help_text="Available mesh files.")
    total_energy = forms.CharField( label='PNF', required = True, max_length=255, 
                                    help_text="Stands for 'Pruning Normalization Factor. Used by the simulator to scale the light dose thresholds to match the unit of the light-simulator output. <br />Typically in the range of 1e6 to 4e11.")
    num_packets = forms.CharField(label='Num Packets', required = True, max_length=255, 
                                    help_text="The number of photon packets to launch in the light simulator FullMonte. Typically it is around 1e5 to 1e6.")
    wave_length = forms.CharField(label='Wave Length', required = True, max_length=255, 
                                    help_text="Activation wavelength of the Photosensitizer.")
    tumor_weight = forms.CharField(label='Tumor Weight', required = True, max_length=255, 
                                    help_text="An importance weight given to the tumor tissue to give it a priority in the optimization.")
    
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
    # placement_type = forms.ChoiceField(label='Placement Type', choices=(('fixed_point','fixed_point'),
    #                                                                     ('fixed_line','fixed_line'),
    #                                                                     ('virtual_point', 'virtual_point'),),
    #                                     help_text="Specifies the type of placement for the sources. <br />If it is fixed point and line, please place sources at fixed position in placement file(below). <br />If it is virtual point source, the tool will fill the mesh with candidate point sources.")
    placement_type = forms.ChoiceField(label='Placement Type', choices=(('fixed_point','fixed_point'),
                                                                        ('fixed_line','fixed_line'),),
                                        help_text="Specifies the type of placement for the sources. <br />If it is fixed point and line, please place sources at fixed position in placement file(below).")                                    
    light_placement_file = forms.FileField(
        label='Placement File',
        help_text="Placement of intial light sources."
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
                                                          ('Cylinder','Cylinder'),
                                                          ('SurfaceSourceBuilder','SurfaceSourceBuilder'),
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

    # for SurfaceSourceBuilder
    volumeRegion = forms.IntegerField(label='volumeRegion', required=False, initial=1)
    emitHemiSphere = forms.ChoiceField(label='emitHemiSphere', required=False, choices=(('false','false'),
                                                                         ('true','true')), initial='false')
    hemiSphereEmitDistribution = forms.ChoiceField(label='hemiSphereEmitDistribution', required=False,
        choices=(('UNIFORM', 'UNIFORM'), ('CUSTOM', 'CUSTOM'), ('LAMBERT', 'LAMBERT')), initial='LAMBERT')
    numericalAperture = forms.FloatField(label='numericalAperture', required=False)
    checkDirection = forms.ChoiceField(label='checkDirection', required=False, choices=(('false','false'),
                                                                         ('true','true')), initial='false')
    xDir1 = forms.FloatField(label='X Direction', widget=forms.TextInput(attrs={'placeholder': 'x'}), required=False)
    yDir1 = forms.FloatField(label='Y Direction', widget=forms.TextInput(attrs={'placeholder': 'y'}), required=False)
    zDir1 = forms.FloatField(label='Z Direction', widget=forms.TextInput(attrs={'placeholder': 'z'}), required=False)

    # for cylinder
    xPos0 = forms.FloatField(label='X Position1', widget=forms.TextInput(attrs={'placeholder': 'x'}), required=False)
    yPos0 = forms.FloatField(label='Y Position1', widget=forms.TextInput(attrs={'placeholder': 'y'}), required=False)
    zPos0 = forms.FloatField(label='Z Position1', widget=forms.TextInput(attrs={'placeholder': 'z'}), required=False)
    xPos1 = forms.FloatField(label='X Position1', widget=forms.TextInput(attrs={'placeholder': 'x'}), required=False)
    yPos1 = forms.FloatField(label='Y Position1', widget=forms.TextInput(attrs={'placeholder': 'y'}), required=False)
    zPos1 = forms.FloatField(label='Z Position1', widget=forms.TextInput(attrs={'placeholder': 'z'}), required=False)
    emitVolume = forms.ChoiceField(label='emitVolume', required=False, choices=(('false','false'),
                                                                         ('true','true')), initial='true')


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
