from django import forms
from django.forms import formset_factory
from django.forms import BaseFormSet
from .models import *
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class tclInputForm(forms.ModelForm):
    class Meta:
        model = tclInput
        fields = ('meshFile', 'kernelType')
        kernel_choices = (('TetraSVKernal','TetraSVKernel'),
                         ('TetraSurfaceKernal','TetraSurfaceKernel'),
                         ('TetraVolumeKernal','TetraVolumeKernel'),
                         ('TetraInternalKernal','TetraInternalKernel'))
        widgets = {
            'kernelType': forms.Select(choices=kernel_choices),
        }

class presetForm(forms.ModelForm):
    class Meta:
        model = preset
        fields = ('presetMesh', 'layerDesc')

class materialSet(forms.Form):
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

class lightSource(forms.Form):
    sourceType = forms.ChoiceField(label='Type', choices=(('Point','Point'),
                                                            ('PencilBeam','PencilBeam'),
                                                            ('Volume','Volume'),
                                                            ('Ball','Ball'),
                                                            ('Line','Line'),
                                                            ('Fiber','Fiber'),
                                                            ('Tetraface','Tetraface'),
                                                            ('Composite','Composite')))
    # for Point
    xPos = forms.FloatField(label='X Position')
    yPos = forms.FloatField(label='Y Position')
    zPos = forms.FloatField(label='Z Position')
    
    power = forms.IntegerField(label='Power')

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

materialSetSet = formset_factory(materialSet, formset=RequiredFormSet)
lightSourceSet = formset_factory(lightSource, formset=RequiredFormSet)
