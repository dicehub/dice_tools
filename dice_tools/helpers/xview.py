
from dice_tools import DICEObject, diceCall, wizard
import lz4framed
import math
from time import perf_counter

import concurrent.futures
import io
import threading
from queue import Queue

def worker(view, sx, sy, flip, data, index):
    data = lz4framed.compress(data, level=0)
    wizard.w_send_frame(view, sx, sy, flip, [data], index)

executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

__ALL__ = ['View']

class View(DICEObject):

    def __init__(self, **kwargs):
        super().__init__(base_type='ExposedView', **kwargs)
        wizard.subscribe(self.w_send_frame, view=self)
        self.__frame_counter = 0
        self.__send_counter = 0

    def w_send_frame(self, view, sx, sy, flip, data, frame_index):
        if self.__send_counter < frame_index:
            self.__send_counter = frame_index
            self._update(sx, sy, data, flip, 'lz4')

    @diceCall
    def _update(self, sx, sy, flip, data):
        pass

    def update(self, sx, sy, flip, data):
        self.__frame_counter += 1
        executor.submit(worker, self, sx, sy, flip, data, self.__frame_counter)

    def size_changed(self, size_x, size_y):
        """
        Size changed event handler.

        :param size_x: New size x dimension.
        :param size_y: New size y dimension.
        """

    '''
    Mouse Events
    ============
    '''
    def mouse_press(self, btn, x, y, modifiers):
        """
        Mouse button press event handler.

        :param btn: Mouse button code.
        :param x: X coordinate of position where mouse pressed.
        :param y: Y coordinate of position where mouse pressed.
        :param modifiers: Keyboard modifiers, i.e. 'Alt', 'Control', 'Shift'.
        """

    def mouse_release(self, btn, x, y, modifiers):
        """
        Mouse button release event handler.

        :param btn: Mouse button code.
        :param x: X coordinate of position where mouse pressed.
        :param y: Y coordinate of position where mouse pressed.
        :param modifiers: Keyboard modifiers, i.e. 'Alt', 'Control', 'Shift'.
        """

    def mouse_move(self, x, y, modifiers):
        """
        Mouse move event handler.

        :param x: X coordinate of position mouse moved to.
        :param y: Y coordinate of position mouse moved to.
        :param modifiers: Keyboard modifiers, i.e. 'Alt', 'Control', 'Shift'.
        """

    def mouse_wheel(self, delta_x, delta_y, x, y, modifiers):
        """
        Mouse wheel event handler.

        :param delta_x: Unused.
        :param delta_y: Mouse wheel turn offset.
        :param x: X coordinate of position where mouse wheel was turned.
        :param y: Y coordinate of position where mouse wheel was turned.
        :param modifiers: Keyboard modifiers, i.e. 'Alt', 'Control', 'Shift'.
        """
