from dice_tools import wizard, DICEObject, diceCall
from ._selection import ModelSelection
import weakref

__all__ = [
    'Model'
    ]


class Model(DICEObject):
    """This type exports model to DICE QML and provides several
    features like item selection, item iterators etc.

    Model can represent simple lists and data with complex tree hierarchy.
    
    Implementation notes:
        * Every item identified by python's object identity function id.
        * Items can be repeated in model, but selection and current_item
        will work with some issues: selection will select all found duplicates
        and current item moves to first found item in model.
        * Items move has some limitations now, see method comment.
        * Every action is sent to dice in asynchronous mode.
    """

    def __init__(self, model_data, **kwargs):
        """Initialization
        """
        super().__init__(base_type = 'BaseModel', **kwargs)
        self.__data = None
        self.setup(model_data)

    def connected(self):
        super().connected()
        root_item_id = id(self.__data.root_item)
        roles = self.__data.model_roles
        methods = self.__data.model_methods
        self.x_model_reset(root_item_id, roles, methods, mode=1)
        def fill(item):
            if item in self.__fetched:
                self.__model_insert_children(item, mode=1)
                for v in self.__data.elements(item):
                    fill(v)
        fill(self.__data.root_item)

    def setup(self, model_data):
        """Resets the model and initializes it to use model data passed in arguments.
        
        Args:
            model_data (ModelData): Model data, which will be exported to DICE

        Returns:
            None
        """
        if self.__data:
            wizard.unsubscribe(self, self.__data.root_item)
            wizard.unsubscribe(self, self.__data)
        self.__current = lambda: None
        self.__selection = ModelSelection(self)
        self.__data = model_data
        self.__fetched = weakref.WeakSet()
        self.__items = weakref.WeakValueDictionary()
        root_item_id = id(self.__data.root_item)
        self.__items[root_item_id] = self.__data.root_item
        wizard.subscribe(self, self.__data)
        wizard.subscribe(self, self.__data.root_item)
        wizard.subscribe(self, self.__selection)
        roles = self.__data.model_roles
        methods = self.__data.model_methods
        self.x_model_reset(root_item_id, roles, methods, callback=None)

    @property
    def root_elements(self):
        """Contains elements of root item in model. Using
        this property simplifies access to model items when
        model represents simple item list. 

        Returns:
            ModelElements: root item elements
        """
        return self.__data.elements(self.__data.root_item)

    @property
    def selection(self):
        """Current selection. Selection is set-like object of type
        ModelSelection, and it contains selected items.
       
        Returns:
            ModelSelection: current selection
        """
        return self.__selection

    @property
    def root_item(self):
        """Root item of this model

        Returns:
            Root item, type depend on model data implementation
        """
        return self.__data.root_item

    @property
    def data(self):
        """This property holds model data. Model data provides items,
        roles and methods of model items. Model data always has root
        item. Methods, related to data modifications, implemented in
        model data too.

        Returns:
            Instance of ModelData
        """
        return self.__data

    @property
    def current_item(self):
        """Current item represents current cursor in model.
        
        Returns:
            tuple: current item
        """
        
        return self.__current()

    @current_item.setter
    def current_item(self, item):
        """Sets cursor to item.

        Args:
            item: Model item
        
        Returns:
            None
        """

        # if self.__current() != item:
        if item == None:
            self.__current = lambda: None
            self.x_set_current(id(self.__data.root_item), callback=None)
        else:
            self.__current = weakref.ref(item)
            item_id = id(item)
            if item_id in self.__items:
                self.x_set_current(item_id, callback=None)

    def __iter__(self):
        def walk(p):
            items = self.__data.elements(p)
            if items:
                for v in items:
                    yield v
                    for vv in walk(v):
                        yield vv

        return walk(self.__data.root_item)

    def elements_of(self, type):
        """This method returns generator, which yields model
        items filtered by type.

        Args:
            type: Type to filter items
        
        Returns:
            generator 
        """
        for v in self:
            if isinstance(v, type):
                yield v

    # wizard handlers

    def w_model_select_item(self, selection, item):
        # print('select', item)
        self.__model_select_item(item)

    def w_model_deselect_item(self, item):
        self.__model_deselect_item(item)

    def w_model_insert_items(self, parent, row=0, count=None):
        self.__model_insert_children(parent, row, count)

    def w_model_remove_items(self, parent, row=0, count=None):
        self.__model_remove_children(parent, row, count)

    def w_model_update_item(self, item):
        self.__model_update_item(item)

    def w_model_move_items(self, model_data, source, source_row, count, dest,
                           dest_row):
        self.__model_move_items(source, source_row, count, dest, dest_row)

    def w_model_set_current(self, item):
        self.current_item = item

    # private methods

    def __model_move_items(self, source, source_row, count, dest, dest_row):
        # model items move allowed only if items exists in DICE

        source_fetched = source in self.__fetched
        dest_fetched = dest in self.__fetched

        if not source_fetched and not dest_fetched:
            return

        if not source_fetched:
            self.__model_insert_children(dest, dest_row, count)
        elif not dest_fetched:
            self.__model_remove_children(source, source_row, count)
        else:
            self.x_model_move_items(id(source), source_row, count,
                                    id(dest), dest_row, callback=None)

    def __model_insert_children(self, item, row=0, count=None, mode=0):
        # do not send data if item is not expanded and has no children in DICE
        if item in self.__fetched:
            children = self.__data.elements(item)
            count = count if count != None else len(children) - row
            data = []
            for i in range(row, row + count):

                child = children[i]
                # subscribe on new item to get wizard events about it
                wizard.subscribe(self, child)

                child_id = id(child)
                # remember item for future identification by ID
                self.__items[child_id] = child

                params = dict(row=i,
                              roles=self.__data.roles(child),
                              item_id=child_id)

                # query model data for child items
                if self.__data.elements(child) != None:
                    params['has_children'] = True

                # is item in selection
                if child in self.__selection:
                    params['selected'] = True

                # is item is current
                if self.__current() == child:
                    params['current'] = True

                data.append(params)

            # send data about new items
            self.x_model_insert_items(id(item), data, mode=mode)

    def __model_remove_children(self, item, row=0, count=None):
        # send data only if items exists in DICE (item's parent expanded)
        if item in self.__fetched:
            children = self.__data.elements(item)
            count = count if count != None else len(children) - row
            if count > 0:
                self.x_model_remove_items(id(item), row, count)

    def __model_update_item(self, item, row=None, count=1):
        item_id = id(item)
        # update only if item exists in DICE (item's parent expanded)
        if item_id in self.__items:
            self.x_model_update_item(item_id, self.__data.roles(item))

    def __model_select_item(self, item):
        item_id = id(item)
        # select only if item exists in DICE (item's parent expanded)
        if item_id in self.__items:
            self.x_model_select([item_id], True, False)
        wizard.w_model_selection_changed(self, [item], [])

    def __model_deselect_item(self, item):
        item_id = id(item)
        # select only if item exists in DICE (item's parent expanded)
        if item_id in self.__items:
            self.x_model_select([item_id], False, False)
        wizard.w_model_selection_changed(self, [], [item])

    # notifications

    def n_model_fetch_items(self, item_id):
        """Model items fetched dynamically when model item
        expanded in view. Root item expanded when model
        view becomes visible.
        
        Args:
            item_id: ID of item to fetch
        
        Returns:
            None
        """
        item = self.__items.get(item_id)
        if item and item not in self.__fetched:
            self.__fetched.add(item)
            self.__model_insert_children(item)

    def n_model_current_changed(self, cur_item_id, prev_item_id, modifiers):
        """Callback on cursor move. In QML cursor can be moved
        by selection model, which can be accessed by 'selection'
        property of model in QML.
        
        Args:
            cur_item_id: ID of item under cursor.
            prev_item_id: ID of previous item ID.
            modifiers: Keyboard modifiers
        
        Returns:
            TYPE: Description
        """
        current = self.__items.get(cur_item_id)
        prev = self.__items.get(prev_item_id)

        if current == None:
            self.__current = lambda: None
        else:
            self.__current = weakref.ref(current)

        wizard.w_model_current_changed(self, current, prev)

    def n_model_change_selection(self, selected, deselected):
        """Selection change notification
        
        Args:
            selected (list): IDs of selected items
            deselected (list): IDs of deselected items
        
        Returns:
            None
        """
        selected_items = []
        deselected_items = []

        # unsubscribe from selection to skip selection notification
        wizard.unsubscribe(self, self.__selection)

        for item_id in selected:
            item = self.__items.get(item_id)
            if item and item not in self.__selection:
                selected_items.append(item)
                self.__selection.add(item)

        for item_id in deselected:
            item = self.__items.get(item_id)
            if item and item in self.__selection:
                deselected_items.append(item)
                self.__selection.discard(item)

        # subscribe back
        wizard.subscribe(self, self.__selection)
        
        wizard.w_model_selection_changed(self, selected_items, deselected_items)

    def n_model_set_item_data(self, item_id, role, value):
        """Called when item role was modified
        
        Args:
            item_id: ID of item
            role (str): Role name
            value: New value
        
        Returns:
            None
        """
        item = self.__items.get(item_id)
        if item:
            self.__data.set_data(item, role, value)

    def n_model_call_item_method(self, item_id, method, args, kwargs):
        """Called when model wants call item's method
        
        Args:
            item_id: ID of item
            method (str): Method name to call
            args (list): Arguments for method call
            kwargs (dict): Keyword arguments for method call
        
        Returns:
            None
        """
        item = self.__items.get(item_id)
        if item:
            return self.__data.call(item, method, args, kwargs)

    def n_model_move_items(self, source_id, source_row, count, dest_id,
                           dest_row):
        """Called when model queries for items move
        
        Args:
            source_id: ID of parent
            source_row: Starting index in parent's elements
            count: Number of elements for move
            dest_id: ID of new parent for elements
            dest_row: Index to insert elements
        
        Returns:
            None
        """
        source = self.__items.get(source_id)
        dest = self.__items.get(dest_id)
        if source and dest:
            self.__data.move(source, source_row, count, dest, dest_row)

    @diceCall
    def x_model_reset(self):
        pass

    @diceCall
    def x_set_current(self):
        pass

    @diceCall
    def x_model_move_items(self):
        pass

    @diceCall
    def x_model_insert_items(self):
        pass

    @diceCall
    def x_model_remove_items(self):
        pass

    @diceCall
    def x_model_update_item(self):
        pass

    @diceCall
    def x_model_select(self):
        pass