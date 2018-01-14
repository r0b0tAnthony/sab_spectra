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
