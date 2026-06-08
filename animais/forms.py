from django import forms
from .models import Animal, AnimalImages, Adoptante

class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = '__all__' 
        exclude = ['adoptante']

        
class AnimalFotosForm(forms.ModelForm):
    class Meta:
        model = AnimalImages
        fields = ('image_url',)
        

class AdoptanteForm(forms.ModelForm):
    animals = forms.ModelMultipleChoiceField(
        queryset=Animal.objects.filter(adoptante__isnull=True),  
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),  
        required=False,
        label="Available Animals",
    )
    
    class Meta:
        model = Adoptante
        fields = '__all__'  
        exclude = ['has_animal']
        
    def save(self, commit=True):
        adoptante = super().save(commit=False)
        if commit:
            adoptante.save()
            if self.cleaned_data['animals']:
                self.cleaned_data['animals'].update(adoptante=adoptante)
                adoptante.has_animal = True
                adoptante.save()
        return adoptante
