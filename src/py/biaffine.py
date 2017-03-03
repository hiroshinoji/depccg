import math
import numpy as np

from chainer import cuda
from chainer.functions.connection import linear
from chainer import initializers
from chainer import link
from chainer import functions as F


class Biaffine(link.Link):


    def __init__(self, in_size, wscale=1,
                 initialW=None, initial_bias=None):
        super(Biaffine, self).__init__()

        self._W_initializer = initializers._get_initializer(
            initialW, math.sqrt(wscale))

        self._initialize_params(in_size)

    def _initialize_params(self, in_size):
        self.add_param('W', (in_size + 1, in_size),
                       initializer=self._W_initializer)

    def __call__(self, x1, x2):
        xp = cuda.get_array_module(x1.data)
        return F.matmul(
                F.concat([x1, xp.ones((x1.shape[0], 1), 'f')]),
                F.matmul(self.W, x2, transb=True))


class Bilinear(link.Link):

    ## chainer.links.Bilinear may have some problem with GPU
    ## and results in nan with batches with big size

    def __init__(self, in_size1, in_size2, out_size, wscale=1,
                 initialW=None, initial_bias=None, bias=0):
        super(Bilinear, self).__init__()

        self._W_initializer = initializers._get_initializer(
            initialW, math.sqrt(wscale))
        if initial_bias is None:
            initial_bias = bias
        self.bias_initializer = initializers._get_initializer(initial_bias)

        ## same parameters as chainer.links.Bilinear
        ## so that both can use serialized parameters of the other
        self.add_param('W', (in_size1, in_size2, out_size),
                       initializer=self._W_initializer)
        self.add_param('V1', (in_size1, out_size),
                       initializer=self._W_initializer)
        self.add_param('V2', (in_size2, out_size),
                       initializer=self._W_initializer)
        self.add_param('b', out_size,
                initializer=self.bias_initializer)
        self.in_size1 = in_size1
        self.in_size2 = in_size2
        self.out_size = out_size

    def __call__(self, e1, e2):
        ele2 = F.reshape(
                F.batch_matmul(e1[:,:,None], e2[:,None,:]), (-1, self.in_size1 * self.in_size2))

        res = F.matmul(ele2,
                F.reshape(self.W, (self.in_size1 * self.in_size2, self.out_size))) + \
            F.matmul(e1, self.V1) + \
            F.matmul(e2, self.V2)

        res, bias = F.broadcast(res, self.b)
        return res + bias

