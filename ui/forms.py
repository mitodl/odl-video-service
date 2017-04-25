from django.forms.widgets import TextInput
from django.forms.fields import Field
from django.forms.models import ModelMultipleChoiceField
from django.forms import ModelForm
from ui.models import MoiraList, Video

## Widget

class SeparatedMultiTextInput(TextInput):
    def __init__(self, separator=" ", attrs=None):
        super().__init__(attrs=attrs)
        self.separator = separator

    def format_value(self, value):
        return self.separator.join(value)

    def value_from_datadict(self, data, files, name):
        text = data.get(name)
        return text.split(self.separator)


## Field

class DynamicModelMultipleChoiceField(Field):
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
        instance, created = self.model.get_or_create(**kwargs)
        return instance

    def to_python(self, values):
        return [self.to_model(value) for value in values]


## Forms

class VideoForm(ModelForm):
    moira_lists = DynamicModelMultipleChoiceField(
        model=MoiraList, field="name",
    )
    class Meta:
        model = Video
        fields = ('title', 'description', 'moira_lists')
