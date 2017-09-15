from dice_tools import wizard
from collections import MutableSequence

__all__ = [
    'ModelElements'
    ]


class ModelElements(MutableSequence):
    """
    This class provides API for work with model item`s children.
    """

    def __init__(self, parent, element_adaptor=None, **kwargs):
        self.__parent = parent
        self.__items = []
        if element_adaptor:
            self.__element_adaptor = element_adaptor

    @property
    def items(self):
        """
        Child items. You could access them also using the same API as list.
        """
        return self.__items

    @items.setter
    def items(self, value):
        self.__items = value

    def __element_adaptor(self, item):
        return item

    def __len__(self):
        return len(self.__items)

    def __getitem__(self, i):
        return self.__items[i]

    def __setitem__(self, i, item):
        item = self.__element_adaptor(item)
        if i < 0:
            i = len(self.__items) + i
        self.__items[i] = item
        wizard.w_model_update_item(
            self.__parent, row=i, count=1)

    def __delitem__(self, i):
        if i < 0:
            i = len(self.__items) + i
        del self.__items[i]
        wizard.w_model_remove_items(
            self.__parent, row=i, count=1)

    def insert(self, i, item):
        item = self.__element_adaptor(item)
        if i < 0:
            i = len(self.__items) + i
        self.__items.insert(i, item)
        wizard.w_model_insert_items(
            self.__parent, row=i, count=1)
