from django.forms import ModelForm
from ui.models import Video


class VideoForm(ModelForm):
    class Meta:
        model = Video
        fields = ('title', 'description')
