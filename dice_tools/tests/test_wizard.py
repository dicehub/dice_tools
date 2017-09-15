
from dice_tools import wizard
from pprint import pprint
from unittest.mock import Mock
import pytest
import gc

wizard.setup(lambda: None)

class SomeClass(object):
    def __init__(self):
        self.mock = Mock()

    def method(self, *args, **kwargs):
        self.mock(*args, **kwargs)

def test_subscribe():
    sub = SomeClass() 
    wizard.subscribe('method', sub)
    wizard.method()
    sub.mock.assert_called_with()

def test_unsubscribe():
    sub = SomeClass() 
    wizard.subscribe('method', sub)
    wizard.unsubscribe('method', sub)
    wizard.method()
    assert sub.mock.called == False

def test_unsubscribe_all():
    sub = SomeClass() 
    wizard.subscribe('method', sub)
    wizard.unsubscribe(sub)
    wizard.method()
    assert sub.mock.called == False

def test_subscribe_method():
    sub = SomeClass() 
    wizard.subscribe('othermethod', sub.method)
    wizard.othermethod()
    sub.mock.assert_called_with()

def test_subscribe_method_multi():
    sub = SomeClass() 
    wizard.subscribe('othermethod1', sub.method)
    wizard.subscribe('othermethod2', sub.method)
    wizard.othermethod1()
    sub.mock.assert_called_with()
    sub.mock.reset_mock()
    wizard.othermethod2()
    sub.mock.assert_called_with()

def test_unsubscribe_method():
    sub = SomeClass() 
    wizard.subscribe('othermethod', sub.method)
    wizard.unsubscribe('othermethod', sub.method)
    wizard.othermethod()
    assert sub.mock.called == False

def test_unsubscribe_all_method():
    sub = SomeClass() 
    wizard.subscribe('othermethod1', sub.method)
    wizard.subscribe('othermethod2', sub.method)
    wizard.unsubscribe(sub.method)
    wizard.othermethod1()
    wizard.othermethod2()
    assert sub.mock.called == False

def test_unsubscribe_all_method_self():
    sub = SomeClass() 
    wizard.subscribe('othermethod1', sub.method)
    wizard.subscribe('othermethod2', sub.method)
    wizard.unsubscribe(sub)
    wizard.othermethod1()
    wizard.othermethod2()
    assert sub.mock.called == False

def test_parameters():
    sub = SomeClass() 
    wizard.subscribe('method', sub)
    wizard.method(1, 2, 3, test='wow')
    sub.mock.assert_called_with(1, 2, 3, test='wow')

def test_condition():
    sub = SomeClass() 
    wizard.subscribe('method', sub, 'red')
    wizard.method(1, 2, 3, test='wow')
    wizard.method(1, 2, 3, 'blue', test='wow')
    wizard.method(1, 2, 3, 'red', test='wow')
    sub.mock.assert_called_once_with(1, 2, 3, 'red', test='wow')


def test_condition_unsubscribe():
    sub = SomeClass() 
    wizard.subscribe('method', sub, 'red')
    wizard.unsubscribe('method', sub, 'red')
    wizard.method(1, 2, 3, 'red', test='wow')
    assert sub.mock.called == False

def test_condition_replace():
    sub = SomeClass() 
    wizard.subscribe('method', sub, 'red')
    wizard.method('red')
    wizard.method(1, 2, 3, 'red', test='wow')
    wizard.method('red', 1, 2, 3, test='wow')
    sub.mock.assert_any_call('red')
    sub.mock.assert_any_call(1, 2, 3, 'red', test='wow')
    sub.mock.assert_any_call('red', 1, 2, 3, test='wow')


def test_condition_method():
    sub = SomeClass() 
    wizard.subscribe('othermethod', sub.method, 'red')
    wizard.othermethod(1, 2, 3, test='wow')
    wizard.othermethod(1, 2, 3, 'blue', test='wow')
    wizard.othermethod(1, 2, 3, 'red', test='wow')
    sub.mock.assert_called_once_with(1, 2, 3, 'red', test='wow')

def test_condition_method_unsubscribe():
    sub = SomeClass() 
    wizard.subscribe('othermethod', sub.method, 'red')
    wizard.unsubscribe('othermethod', sub.method, 'red')
    wizard.othermethod('red')
    assert sub.mock.called == False

def test_condition_method_unsubscribe_all():
    sub = SomeClass() 
    wizard.subscribe('othermethod',sub.method, 'red')
    wizard.subscribe('othermethod',sub.method, 'blue')
    wizard.unsubscribe(sub.method)
    wizard.othermethod('red')
    wizard.othermethod('blue')
    assert sub.mock.called == False

def test_condition_method_unsubscribe_all_self():
    sub = SomeClass() 
    wizard.subscribe('othermethod', sub.method, 'red')
    wizard.subscribe('othermethod', sub.method, 'blue')
    wizard.unsubscribe(sub)
    wizard.othermethod('red')
    wizard.othermethod('blue')
    assert sub.mock.called == False

def test_condition_replace_method():
    sub = SomeClass() 
    wizard.subscribe('othermethod', sub.method, 'red')
    wizard.othermethod('red')
    wizard.othermethod(1, 2, 3, 'red', test='wow')
    wizard.othermethod('red', 1, 2, 3, test='wow')
    sub.mock.assert_any_call('red')
    sub.mock.assert_any_call(1, 2, 3, 'red', test='wow')
    sub.mock.assert_any_call('red', 1, 2, 3, test='wow')

def test_wizard_gc_info():
    gc.collect()
    assert not wizard.info()

def test_wizard_gc_r():
    gc.collect()
    assert not wizard.subs

def test_wizard_gc_w():
    gc.collect()
    assert not wizard.refs

def test_condition_destroy():
    sub = SomeClass()
    obj1 = SomeClass()
    obj2 = SomeClass()
    wizard.subscribe(sub, 'method', obj1, obj2)
    obj1 = None
    assert not wizard.subs[sub]

def test_unhashable():
    sub = SomeClass()
    wizard.subscribe(sub, 'method')
    wizard.method({})
