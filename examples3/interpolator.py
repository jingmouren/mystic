#!/usr/bin/env python
#
# Author: Mike McKerns (mmckerns @uqfoundation)
# Copyright (c) 2019 The Uncertainty Quantification Foundation.
# License: 3-clause BSD.  The full license text is available at:
#  - https://github.com/uqfoundation/mystic/blob/master/LICENSE
"""
an interpolator
  - initalize with x (and z)
  - can downsample and/or add noise
  - interpolates with "interp.interp"
  - converts f(*x) <-> f(x)
  - plot data and interpolated surface
"""

class Interpolator(object):
   #surface has:
   #    args - interpolation configuration (method, ...)
   #    maxpts - a maximum number of sampling points
   #    noise - a noise coefficient
   #    function - interpolated function [F(*x)]
   #    model - interpolated function [F(x)]
   #    x,y,z - sampled points(*)
   #
   #surface can:
   #    Interpolate - build interpolated function from sampled points
   #    Plot - plot sampled points and interpolated surface
   #
   #surface (or sampler) can:
   #    _noise - remove duplicate sampled points (x) by adding noise to x
   #    _downsample - skip sampled points at a regular interval (for speed)

    def __init__(self, x, z=None, **kwds):
        """interpolator for data (x,z)

        Input:
          x: an array of shape (npts, dim) or (npts,)
          z: an array of shape (npts,)

        Additional Inputs:
          maxpts: int, maximum number of points to use from (x,z)
          noise: float, amplitude of gaussian noise to remove duplicate x
          method: string for kind of interpolator

        NOTE:
          if scipy is not installed, will use np.interp for 1D (non-rbf),
          or mystic's rbf otherwise. default method is 'nearest' for
          1D and 'linear' otherwise. method can be one of ('rbf','linear',
          'nearest','cubic','inverse','gaussian','quintic','thin_plate').
        """
        # basic configuration
        self.maxpts = kwds.pop('maxpts', None)  # N = 1000
        self.noise = kwds.pop('noise', 1e-8)
        # parameter trajectories (from arrays or monitor)
        self.x = getattr(x, '_x', x)  # params (x)
        self.z = x._y if z is None else z # cost (f(x))
        import numpy as np
        self.x = np.asarray(self.x); self.z = np.asarray(self.z)
        # point generator(s) and interpolated function(s) #XXX: better names?
        self.function = None # interpolated F(*x)
        # interpolator configuration
        self.args = {}#dict(method='thin_plate')
        self.args.update(kwds)
        return


    def _noise(self, scale=None, x=None):
        """inject gaussian noise into x to remove duplicate points

        Input:
          scale: amplitude of gaussian noise
          x: an array of shape (npts, dim) or (npts,)

        Output:
          array x, with added noise
        """
        import numpy as np
        if x is None: x = self.x
        if scale is None: scale = self.noise
        if not scale: return x
        return x + np.random.normal(scale=scale, size=x.shape)


    def _downsample(self, maxpts=None, x=None, z=None):
        """downsample (x,z) to at most maxpts

        Input:
          maxpts: int, maximum number of points to use from (x,z)
          x: an array of shape (npts, dim) or (npts,)
          z: an array of shape (npts,)

        Output:
          x: an array of shape (npts, dim) or (npts,)
          z: an array of shape (npts,)
        """
        if maxpts is None: maxpts = self.maxpts
        if x is None: x = self.x
        if z is None: z = self.z
        if len(x) != len(z):
            raise ValueError("the input array lengths must match exactly")
        if maxpts is not None and len(z) > maxpts:
            N = max(int(round(len(z)/float(maxpts))),1)
        #   print("for speed, sampling {} down to {}".format(len(z),len(z)/N))
        #   ax.plot(x[:,0], x[:,1], z, 'ko', linewidth=2, markersize=4)
            x = x[::N]
            z = z[::N]
        #   plt.show()
        #   exit()
        return x, z


    def _interpolate(self, x, z, **kwds):
        """interpolate data (x,z) to generate response function z=f(*x)

        Input:
          x: an array of shape (npts, dim) or (npts,)
          z: an array of shape (npts,)

        Additional Inputs:
          method: string for kind of interpolator

        Output:
          interpolated response function, where z=f(*x.T)

        NOTE:
          if scipy is not installed, will use np.interp for 1D (non-rbf),
          or mystic's rbf otherwise. default method is 'nearest' for
          1D and 'linear' otherwise. method can be one of ('rbf','linear',
          'nearest','cubic','inverse','gaussian','quintic','thin_plate').
        """
        from mystic.math.interpolate import interpf
        return interpf(x, z, **kwds)


    def Interpolate(self, **kwds): #XXX: better take a strategy?
        """interpolate data (x,z) to generate response function z=f(*x)

        Input:
          maxpts: int, maximum number of points to use from (x,z)
          noise: float, amplitude of gaussian noise to remove duplicate x

        Additional Input:
          method: string for kind of interpolator

        Output:
          interpolated response function, where z=f(*x.T)

        NOTE:
          if scipy is not installed, will use np.interp for 1D (non-rbf),
          or mystic's rbf otherwise. default method is 'nearest' for
          1D and 'linear' otherwise. method can be one of ('rbf','linear',
          'nearest','cubic','inverse','gaussian','quintic','thin_plate').
        """
        maxpts = kwds.pop('maxpts', self.maxpts)
        noise = kwds.pop('noise', self.noise)
        args = self.args.copy()
        args.update(kwds)
        x, z = self._downsample(maxpts)
        #NOTE: really only need to add noise when have duplicate x,y coords
        x = self._noise(noise, x)
        # build the surrogate
        self.function = self._interpolate(x, z, **args)
        return self.function


    def Plot(self, **kwds):
        """produce a scatterplot of (x,z) and the surface z = function(*x.T)

        Input:
          step: int, plot every 'step' points on the grid [default: 200]
          scale: float, scaling factor for the z-axis [default: False]
          shift: float, additive shift for the z-axis [default: False]
          density: int, density of wireframe for the plot surface [default: 9]
          axes: tuple, indicies of the axes to plot [default: ()]
          vals: list of values (one per axis) for unplotted axes [default: ()]
          maxpts: int, maximum number of (x,z) points to use [default: None]
        """
        # get interpolted function
        fx = self.function
        # plot interpolated surface
        from plotter import Plotter
        p = Plotter(self.x, self.z, fx, **kwds)
        p.Plot()
        # if plotter interpolated the function, get the function
        self.function = fx or p.function


    def __model(self): #XXX: deal w/ selector (2D)? ExtraArgs?
        # convert to 'model' format (i.e. takes a parameter vector)
        if self.function is None: return None
        from mystic.math.interpolate import _to_objective
        _objective = _to_objective(self.function)
        def objective(x, *args, **kwds):
            return _objective(x, *args, **kwds).tolist()
        objective.__doc__ = _objective.__doc__
        return objective


    # interface
    model = property(__model )


def interpolate(monitor, method=None, **kwds):
    '''generic interface to Interpolator, returning an Interpolator instance

    Input:
      monitor: a mystic.monitor instance
      method: string for kind of interpolator

    Additional Inputs:
      maxpts: int, maximum number of points (x,z) to use from the monitor
      noise: float, amplitude of gaussian noise to remove duplicate x

    NOTE:
      if scipy is not installed, will use np.interp for 1D (non-rbf),
      or mystic's rbf otherwise. default method is 'nearest' for
      1D and 'linear' otherwise. method can be one of ('rbf','linear',
      'nearest','cubic','inverse','gaussian','quintic','thin_plate').
    '''
    d = Interpolator(monitor, method=method, **kwds)
    d.Interpolate()
    return d  #XXX: return a function instead?


# EOF
