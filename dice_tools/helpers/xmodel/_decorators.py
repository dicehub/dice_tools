from dice_tools import wizard

__all__ = [
    'modelRole',
    'modelMethod'
    ]

class modelRole(property):
    """
    It is for defining model element role. This decorator is, same time,
    descriptor inherited from Python property. Thus, defined role could by used
    as common property. To define editable role you need to implement setter.
    """

    def __init__(self, name, fget=None, fset=None):
        property.__init__(self, fget=self.__fget, fset=self.__fset)
        self.__name = name
        self.__getter = fget
        self.__setter = fset

    @property
    def name(self):
        return self.__name

    def __fget(self, obj):
        return self.__getter(obj)

    def __fset(self, obj, value):
        self.__setter(obj, value)
        wizard.w_model_update_item(obj)

    def __call__(self, fget):
        return self.getter(fget)

    def getter(self, fget):
        self.__getter = fget
        return self

    def setter(self, fset):
        self.__setter = fset
        return self


class modelMethod:
    def __init__(self, name):
        self.__name = name
        self.__method = None

    @property
    def name(self):
        return self.__name

    def __get__(self, obj, tp):
        if obj == None:
            return self
        return self.__method.__get__(obj, tp)

    def __call__(self, method):
        self.__method = method
        return self
