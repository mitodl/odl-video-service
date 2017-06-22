"""
Forms for ui app
"""

from django.forms.widgets import TextInput
from django.forms.fields import Field, EmailField
from django.forms import ModelForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from ui.models import MoiraList, Video


class SeparatedMultiTextInput(TextInput):
    """
    Separated Multi Text Input Widget
    """
    def __init__(self, separator=" ", attrs=None):
        super().__init__(attrs=attrs)
        self.separator = separator

    def format_value(self, value):
        return self.separator.join(value)

    def value_from_datadict(self, data, files, name):
        text = data.get(name)
        return text.split(self.separator)


class DynamicModelMultipleChoiceField(Field):
    """
    Dynamic Model Multiple Choice Field
    """
    # pylint: disable=too-many-arguments, missing-docstring, arguments-differ
    widget = SeparatedMultiTextInput

    def __init__(self, model, field="pk", required=True, widget=None, label=None,
                 initial=None, help_text='', *args, **kwargs):
        Field.__init__(self, required, widget, label, initial, help_text,
                       *args, **kwargs)
        self.model = model
        self.field = field

    def prepare_value(self, values):
        return [getattr(value, self.field) for value in values]

    def to_model(self, value):
        kwargs = {self.field: value.strip()}
        instance, _ = self.model.get_or_create(**kwargs)
        return instance

    def to_python(self, values):
        return [self.to_model(value) for value in values]


class VideoForm(ModelForm):
    """
    Video Form
    """
    moira_lists = DynamicModelMultipleChoiceField(
        model=MoiraList, field="name",
    )

    class Meta:
        model = Video
        fields = ('title', 'description', 'moira_lists')


class UserCreationForm(BaseUserCreationForm):
    """
    User Creation Form
    """
    email = EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
