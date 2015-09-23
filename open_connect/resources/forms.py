"""Forms for resources."""
from autocomplete_light.contrib.taggit_field import TaggitWidget
from django import forms

from open_connect.resources.models import Resource


class ResourceForm(forms.ModelForm):
    """Form for Resource model."""
    class Meta(object):
        """Meta options."""
        model = Resource
        widgets = {
            'tags': TaggitWidget(
                'TagAutocomplete', attrs={'placeholder': "type tags here"})
        }
        attachment = forms.FileField(widget=forms.FileInput)
        fields = ['attachment', 'name', 'groups', 'tags']

    def clean(self):
        """Limit the length of the filename."""
        attachment = self.cleaned_data.get('attachment')
        # Limits filename to 200 characters to leave room for upload_path.
        if attachment and len(attachment.name) > 200:
            self._errors['attachment'] = self.error_class([
                'Filename cannot exceed 200 characters.'])
        return self.cleaned_data
