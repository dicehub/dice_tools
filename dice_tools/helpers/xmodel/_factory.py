# DICE tools imports
# ==================
from dice_tools import instantiate

# Internal modules
# ================
from ._data import ListOfDictsModelData
from ._data import StandardModelData
from ._model import Model

__all__ = [
    'ModelElements'
    ]


def standard_model(*types, model_type_name='Model'):
    """
    Creates a model whose elements could contain child elements.

    :param types: Types of elements model should handle. Child elements types
        need to be specified too.
    :param model_type_name: Name of type of model to create (i.e class
        inherited from Model).
    :return: Model instance.
    """
    return Model(StandardModelData(types=types))

def list_of_dicts_model(*roles, data=None, model_type_name='Model'):
    """
    Creates a list model whose elements are dicts where keys are model roles
        and values are appropriate key data.

    :param roles: Data roles to handle data in views with.
    :param data: Initial model data.
    :param model_type_name: Name of type of model to create (i.e class
        inherited from Model).
    :return: Model instance.
    """
    return Model(ListOfDictsModelData(roles=roles, data=data))
