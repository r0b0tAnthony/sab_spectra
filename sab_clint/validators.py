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
        print os.path.normpath(value)
        if not os.path.isdir(value):
            raise ValidationError(self.message)
        return value
