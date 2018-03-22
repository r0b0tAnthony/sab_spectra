from clint.textui.validators import ValidationError
import os

class PathValidator(object):
    message = 'Enter a valid path.'

    def __init__(self, message=None):
        if message is not None:
            self.message = message

    def __call__(self, value):
        """
        Validates that the input is a valid directory.
        """
        value = os.path.normpath(value)
        if os.name == 'posix':
            value = value.replace("\\", '')
        elif os.name == 'nt':
            value = value.strip(r'"')
        if not os.path.isdir(value):
            raise ValidationError(self.message)
        return value

class FloatValidator(object):
    message = 'Enter a valid float.'

    def __init__(self, message=None):
        if message is not None:
            self.message = message

    def __call__(self, value):
        """
        Validates that the input is a integer.
        """
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError(self.message)

class CommaSeparatedValidator(object):
    message = 'Enter valid options in a commad separated list. Valid options: {}'

    def __init__(self, options=[], message=None):
        if message is not None:
            self.message = message
        self.options = options

    def __call__(self, value):
        user_options = value.split(',')
        valid_choices = set(user_options).intersection(self.options)
        if len(valid_choices) < 1:
            raise ValidationError(self.message.format(','.join(self.options)))
        else:
            return valid_choices
