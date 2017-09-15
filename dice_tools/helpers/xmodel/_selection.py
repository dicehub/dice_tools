from collections import MutableSet
from dice_tools import wizard
from weakref import WeakSet

__all__ = [
    'ModelSelection'
    ]

class ModelSelection(MutableSet):
    def __init__(self, model):
        self.__model = model
        self.__items = WeakSet()

    def __hash__(self):
        return id(self)

    def __iter__(self):
        return iter(self.__items)

    def __len__(self):
        return len(self.__items)

    def __contains__(self, key):
        return key in self.__items

    def add(self, key):
        if key not in self.__items:
            self.__items.add(key)
            wizard.w_model_select_item(self, item = key)

    def discard(self, key):
        if key in self.__items:
            self.__items.discard(key)
            wizard.w_model_deselect_item(self, item = key)
