from ._elements import ModelElements

__all__ = [
    'ModelItem'
    ]

class ModelItem(object):
    """
    This is base class for implementing model items with children.
    """

    def __init__(self, element_adaptor=None, **kwargs):
        super().__init__(**kwargs)
        self.__elements = ModelElements(self, element_adaptor, **kwargs)

    @property
    def elements(self):
        """
        Children of this model item.
        :return: Instance of ModelElements.
        """
        return self.__elements
