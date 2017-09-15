import inspect
from ._decorators import modelRole, modelMethod
from ._item import ModelItem
from abc import abstractmethod, abstractproperty, ABCMeta
from dice_tools import wizard

__all__ = [
    'AbstractModelData',
    'StandardModelData',
    'ListOfDictsModelData'
    ]

class AbstractModelData(metaclass=ABCMeta):
    
    # root item of model
    root_item = abstractproperty()

    # roles names for this model
    model_roles = abstractproperty()

    # methods names for this model
    model_methods = abstractproperty()

    @abstractmethod
    def roles(self, item):
        """Return roles of item
        
        Args:
            item: Item
        
        Returns:
            dict: Dictionary with roles
        """

    @abstractmethod
    def elements(self, item):
        """Return list of child elements for item or None
        
        Args:
            item: Item
        
        Returns:
            list: Child elements of item or None
        """

    @abstractmethod
    def set_data(self, item, role, value):
        """This method should set new value for role of item
        
        Args:
            item: Item
            role (str): Role name
            value: New value
        
        Returns:
            None
        """

    @abstractmethod
    def call(self, item, method, args, kwargs):
        """This method should call method of item
        
        Args:
            item: Item
            method (str): Method name to call
            args (list): Arguments for method call
            kwargs (dict): Keyword arguments for method call
        
        Returns:
            None
        """

    def move(self, source, source_row, count, dest, dest_row):
        """This method should move child elements from source's row
        to new parent at destination's row. Implementation
        should call method w_model_move_items of wizard.
        
        Args:
            source: Current parent of items
            source_row: Starting index in parent's elements
            count: Number of elements for move
            dest: New parent for moved items
            dest_row: Index to insert elements
        
        Returns:
            None
        """


class StandardModelData(AbstractModelData):
    """
    This provider handles items that could contains child elements.
    """

    def __init__(self, types, **kwargs):
        super().__init__(**kwargs)
        self.__types = {}
        for t in types:
            roles = {}
            methods = {}
            for (k, v) in inspect.getmembers(t):
                if isinstance(v, modelRole):
                    roles[v.name] = v
                elif isinstance(v, modelMethod):
                    methods[v.name] = v
            self.__types[t] = dict(roles=roles, methods=methods)
        self.__root = ModelItem()

    @property
    def types(self):
        return list(self.__types.keys())

    @property
    def root_item(self):
        """
        Most top item not showed in model. Use this to work with model items.
        :return: ModelItem.
        """
        return self.__root

    @property
    def model_roles(self):
        """
        List of all model item roles.
        :return: list
        """
        roles = set()
        for v in self.__types.values():
            for k in v['roles'].keys():
                roles.add(k)
        return list(roles)

    @property
    def model_methods(self):
        """
        List of all model methods.
        :return: list
        """
        methods = []
        for v in self.__types.values():
            for k in v['methods'].keys():
                methods.append(k)
        return methods

    def roles(self, item):
        item_type = type(item)
        info = self.__types[item_type]
        roles = {}
        for k, v in info['roles'].items():
            roles[k] = v.__get__(item, item_type)
        return roles

    def elements(self, item):
        if isinstance(item, ModelItem):
            return item.elements

    def set_data(self, item, role, value):
        item_type = type(item)
        info = self.__types[item_type]
        info['roles'][role].__set__(item, value)

    def call(self, item, method, args, kwargs):
        item_type = type(item)
        info = self.__types[item_type]
        return info['methods'][method].__get__(item, item_type)(*args, **kwargs)

    def move(self, source, source_row, count, dest, dest_row):
        items = source.elements.items
        source_row_end = source_row + count
        if source == dest:
            v = items[source_row:source_row_end]
            if source_row < dest_row:
                items[dest_row:dest_row] = v
                del items[source_row:source_row_end]
            else:
                del items[source_row:source_row_end]
                items[dest_row:dest_row] = v
        else:
            dest.elements.items[dest_row:dest_row] = items[
                                                     source_row:source_row_end]
            del items[source_row:source_row_end]

        wizard.w_model_move_items(self, source=source,
                                  source_row=source_row, count=count, dest=dest,
                                  dest_row=dest_row)


class ListOfDictsModelData(AbstractModelData):
    """
    This handles model items that are dicts where keys are model roles
    and values are appropriate key data.
    """

    class ListModelItem(dict):
        def __init__(self, data):
            super().__init__(data)

        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            wizard.w_model_update_item(self)

        def __hash__(self):
            return id(self)

    def __init__(self, roles, data, **kwargs):
        super().__init__(**kwargs)
        if not roles:
            for v in data:
                self.__roles = list(v.keys())
        else:
            self.__roles = roles
        self.__root = ModelItem(element_adaptor=self.adapt_element)
        if data:
            self.__root.elements += data

    def adapt_element(self, item):
        """
        Returns instance of ListModelItem with item inside suitable to handle
        by model.
        :param item: Instance of dict.
        :return: ListModelItem
        """
        return ListOfDictsModelData.ListModelItem(item)

    @property
    def root_item(self):
        return self.__root

    @property
    def model_roles(self):
        return self.__roles

    @property
    def model_methods(self):
        return []

    def roles(self, item):
        return dict(item)

    def elements(self, item):
        if isinstance(item, ModelItem):
            return item.elements

    def set_data(self, item, role, value):
        old_value = item[role]
        if value != old_value:
            item[role] = value
            wizard.w_item_updated(self, item, role, value, old_value)

    def call(self, item, method, args, kwargs):
        pass

    def move(self, source, source_row, count, dest, dest_row):
        items = source.elements.items
        source_row_end = source_row + count
        if source == dest:
            v = items[source_row:source_row_end]
            if source_row < dest_row:
                items[dest_row:dest_row] = v
                del items[source_row:source_row_end]
            else:
                del items[source_row:source_row_end]
                items[dest_row:dest_row] = v
        else:
            dest.elements.items[dest_row:dest_row] = items[
                                                     source_row:source_row_end]
            del items[source_row:source_row_end]

        wizard.w_model_move_items(self, source=source,
                                  source_row=source_row, count=count, dest=dest,
                                  dest_row=dest_row)
