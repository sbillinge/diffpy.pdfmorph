#!/usr/bin/env python
##############################################################################
#
# diffpy.pdfmorph   by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2010 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Chris Farrow
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
##############################################################################

"""refine -- Refine a morph or morph chain
"""

from numpy import concatenate, dot, exp, ones_like
from scipy.optimize import leastsq
from scipy.stats import pearsonr

# Map of scipy minimizer names to the method that uses them


class Refiner(object):
    """Class for refining a Morph or MorphChain.

    This is provided to allow for custom residuals and refinement algorithms.

    Attributes
    ----------
    chain
        The Morph or MorphChain to refine.
    x_morph, y_morph
        Morphed arrays.
    x_target, y_target
        Target arrays.
    pars
        List of names of parameters to be refined.
    residual
        The residual function to optimize. Default _residual. Can be assigned to other functions.
    """

    def __init__(self, chain, x_morph, y_morph, x_target, y_target):
        self.chain = chain
        self.x_morph = x_morph
        self.y_morph = y_morph
        self.x_target = x_target
        self.y_target = y_target
        self.pars = []
        self.residual = self._residual
        return

    def _update_chain(self, pvals):
        """Update the parameters in the chain."""
        pairs = zip(self.pars, pvals)
        self.chain.config.update(pairs)
        return

    def _residual(self, pvals):
        """Standard vector residual."""
        self._update_chain(pvals)
        _x_morph, _y_morph, _x_target, _y_target = self.chain(
            self.x_morph, self.y_morph, self.x_target, self.y_target
        )
        rvec = _y_target - _y_morph
        return rvec

    def _pearson(self, pvals):
        """Pearson correlation function.

        This gives e**-p (vector), where p is the pearson correlation function.
        We seek to minimize this, which occurrs when the correlation is the largest.
        """
        self._update_chain(pvals)
        _x_morph, _y_morph, _x_target, _y_target = self.chain(
            self.x_morph, self.y_morph, self.x_target, self.y_target
        )
        pcc, pval = pearsonr(_y_morph, _y_target)
        return ones_like(_x_morph) * exp(-pcc)

    def _add_pearson(self, pvals):
        """Refine both the pearson and residual."""
        res1 = self._residual(pvals)
        res2 = self._pearson(pvals)
        res = concatenate([res1, res2])
        return res

    def refine(self, *args, **kw):
        """Refine the chain.

        Additional arguments are used to specify which parameters are to be refined.
        If no arguments are passed, then all parameters will be refined.
        Keywords pass initial values to the parameters, whether or not they are refined.

        This uses the leastsq algorithm from scipy.optimize.

        This returns the final scalar residual value.
        The parameters from the fit can be retrieved from the config dictionary of the morph or morph chain.

        Raises
        ------
        ValueError
            Exception raised if a minimum cannot be found.
        """

        self.pars = args or self.chain.config.keys()

        config = self.chain.config
        config.update(kw)

        if not self.pars:
            return 0.0

        initial = [config[p] for p in self.pars]
        sol, cov_sol, infodict, emesg, ier = leastsq(self.residual, initial, full_output=1)
        fvec = infodict["fvec"]
        if ier not in (1, 2, 3, 4):
            emesg
            raise ValueError(emesg)

        # Place the fit parameters in config
        vals = sol
        if not hasattr(vals, "__iter__"):
            vals = [vals]
        self.chain.config.update(zip(self.pars, vals))

        return dot(fvec, fvec)


# End class Refiner
