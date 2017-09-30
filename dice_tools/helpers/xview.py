
from dice_tools import DICEObject, diceCall
import lz4framed
import math
from time import perf_counter

import concurrent.futures

WORKERS = 4

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS)

def chunks(data):
    n = math.ceil(len(data) / WORKERS)
    for i in range(0, len(data), n):
        yield data[i:i + n]

__ALL__ = ['View']

class View(DICEObject):

    def __init__(self, **kwargs):
        super().__init__(base_type='ExposedView', **kwargs)

    @diceCall
    def _update(self, sx, sy, flip, data):
        pass

    def update(self, sx, sy, flip, data):
        start = perf_counter()
        gg = list(chunks(data))
        # print('zz11', perf_counter()-start, len(gg))
        futures = [
            _executor.submit(lz4framed.compress, v, level=2)
            for v in gg]
        # print('zz', perf_counter()-start)
        data = [v.result() for v in futures]
        # data = [lz4framed.compress(data, level=lz4framed.LZ4F_COMPRESSION_MIN)]
        self._update(sx, sy, data, flip, 'lz4')
        print(perf_counter()-start)

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
