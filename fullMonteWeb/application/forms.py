from django import forms
from django.forms import formset_factory

class tclInput(forms.Form):
    class materialSet(forms.Form):
        material = forms.CharField(label='Material', required=True)
        scatteringCoeff = forms.FloatField(label='ScatteringCoeff', required=True, min_value=0)
        absorptionCoeff = forms.FloatField(label='AbsorptionCoeff', required=True, min_value=0)
        refractiveIndex = forms.FloatField(label='RefractiveIndex', required=True, min_value=0)
        anisotropy = forms.FloatField(label='Anisotropy', required=True, min_value=0)

    class lightSource(forms.Form):
        sourceType = forms.ChoiceField(label='Type', required=True, choices=(('point','Point'),
                                                        ('pencilbeam','PencilBeam'),
                                                        ('volume','Volume'),
                                                        ('ball','Ball'),
                                                        ('line','Line'),
                                                        ('fiber','Fiber'),
                                                        ('tetraface','Tetraface'),
                                                        ('cylinder','Cylinder'),
                                                        ('composite','Composite')))
        xPos = forms.FloatField(label='X Position', required=True)
        yPos = forms.FloatField(label='Y Position', required=True)
        zPos = forms.FloatField(label='Z Position', required=True)
        power = forms.IntegerField(label='Power', required=True)

    materialSetSet = formset_factory(materialSet)
    lightSourceSet = formset_factory(lightSource)
