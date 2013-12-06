"""Collect Markov Chain"""

from __future__ import division as _div
import numpy as _np
from .._tools._doc import _inherit_docstring
from .._tools._chain import _Chain

class MarkovChain(_Chain):
    """MarkovChain(target, proposal, start, indicator = None,
    rng = numpy.random.mtrand)\n
    A Markov chain

    :param target:

        The target density. Must be a function which recieves a 1d numpy
        array and returns a float, namely log(P(x)) the log of the target.

    :param proposal:

        The proposal density.
        Should be of type :py:class:`pypmc.mcprerun.proposal.ProposalDensity`.

        .. hint::
            When your proposal density is symmetric, define the member
            variable ``proposal.symmetric = True``. This will omit calls
            to proposal.evaluate

    :param start:

        The starting point of the Markov chain. (numpy array)

    :param indicator:

        A function wich recieves a numpy array and returns bool.
        The target is only called if indicator(proposed_point)
        returns True, otherwise the proposed point is rejected
        without call to target.
        Use this function to specify the support of the target.

        .. seealso::
            :py:mod:`pypmc.mcprerun.indicator_factory`

    :param rng:

        The rng passed to the proposal when calling proposal.propose

        .. important::
            ``rng`` must return a numpy array of N samples from the
            uniform distribution [0,1) when calling **rng.rand(N)**

        .. seealso::
            ``rng`` must also fulfill the requirements of your proposal
            :py:meth:`pypmc.mcprerun.proposal.ProposalDensity.propose`

    """
    def __init__(self, target, proposal, start, indicator = None, rng = _np.random.mtrand):
        # store input into instance
        super(MarkovChain, self).__init__(start = start)
        self.proposal  = proposal
        self.rng       = rng
        self._merge_target_with_indicator(target, indicator)

    def _merge_target_with_indicator(self, target, indicator):
        '''Private function. Prevents call to ``target`` if ``indicator(x) = False``'''
        if indicator == None:
            self.target = target
        else:
            def merged_target(x):
                if indicator(x):
                    return target(x)
                else:
                    return 0.
            self.target = merged_target

    @_inherit_docstring(_Chain)
    def run(self, N = 1):
        # set the accept function
        if self.proposal.symmetric:
            get_log_rho = self._get_log_rho_metropolis
        else:
            get_log_rho = self._get_log_rho_metropolis_hasting

        # allocate an empty numpy array to temporary store this run
        this_run     = _np.empty((N,len(self.current)))
        accept_count = 0

        for i_N in range(N):
            # propose new point
            proposed_point = self.proposal.propose(self.current, self.rng)

            # log_rho := log(probability to accept point), where log_rho > 0 is meant to imply rho = 1
            log_rho = get_log_rho(proposed_point)

            # check for NaN
            if _np.isnan(log_rho): raise ValueError('encountered NaN')


            # accept if rho = 1
            if log_rho >=0:
                accept_count += 1
                this_run[i_N] = proposed_point
                self.current  = proposed_point

            # accept with probability rho
            elif log_rho >= _np.log(self.rng.rand()):
                accept_count += 1
                this_run[i_N] = proposed_point
                self.current  = proposed_point

            # reject if not accepted
            else:
                this_run[i_N] = self.current
                #do not need to update self.current
                #self.current = self.current
        # ---------------------- end for --------------------------------

        # store the run in history
        self.hist.append(this_run,accept_count)

    def _get_log_rho_metropolis(self, proposed_point):
        """calculate the log of the metropolis ratio"""
        return self.target(proposed_point) - self.target(self.current)

    def _get_log_rho_metropolis_hasting(self, proposed_point):
        """calculate log(metropolis ratio times hastings factor)"""
        return self._get_log_rho_metropolis(proposed_point, self.points[-1])\
             - self.proposal.evaluate      (proposed_point, self.points[-1])\
             + self.proposal.evaluate      (self.points[-1], proposed_point)

class AdaptiveMarkovChain(MarkovChain):
    # set the docstring --> inherit from Base class, but replace:
    # - MarkovChain(*args, **kwargs) --> AdaptiveMarkovChain(*args, **kwargs)
    # - A Markov chain --> A Markov chain with proposal covariance adaption
    # - ProposalDensity by Multivariate in description of :param propoasal:
    __doc__ = MarkovChain.__doc__\
    .replace('MarkovChain(', 'AdaptiveMarkovChain(')\
    .replace('A Markov chain', 'A Markov chain with proposal covariance adaption' , 1)\
    .replace('ProposalDensity', 'Multivariate')

    #TODO: include citation HST01 & Wra+09 into docstring

    def __init__(self, *args, **kwargs):
        # set adaption params
        self.adapt_count = 0

        self.covar_scale_multiplier = kwargs.pop('covar_scale_multiplier' ,   1.5   )

        self.covar_scale_factor     = kwargs.pop('covar_scale_factor'     ,   1.    )
        self.covar_scale_factor_max = kwargs.pop('covar_scale_factor_max' , 100.    )
        self.covar_scale_factor_min = kwargs.pop('covar_scale_factor_min' ,    .0001)

        self.force_acceptance_max   = kwargs.pop('force_acceptance_max'   ,    .35  )
        self.force_acceptance_min   = kwargs.pop('force_acceptance_min'   ,    .15  )

        self.damping                = kwargs.pop('damping'                ,    .5   )

        super(AdaptiveMarkovChain, self).__init__(*args, **kwargs)

        # initialize unscaled sigma
        self.unscaled_sigma = self.proposal.sigma / self.covar_scale_factor

    def set_adapt_params(self, *args, **kwargs):
        """Sets variables for covariance adaption

        When ``adapt`` is called, the proposal's covariance matrix is adapted
        in order to improve the chain's performance. The aim is to force the
        acceptance rate of the chain to lie in a distinc interval:

        :param force_acceptance_max:

            Float, the upper limit

        :param force_acceptance_min:

            Float, the lower limit

        That is achieved in two steps:

        The first step is updating the proposal's covariance matrix
        (unscaled_sigma) with the newly gained knowledge during the run.
        The adapt function first calculates an estimate for the covariance
        matrix (covar_estimator, temporary variable) from the samples.
        Then, the covariance matrix (unscaled_sigma) is updated
        according to

        unscaled_sigma = (1-a) * unscaled_sigma + a * covar_estimator
        where a = 1./adapt_count**damping

        which describes

        :param damping:

            Float, see formula above

        The damping is neccessary to assure convergence.

        The second step is rescaling the covariance matrix. Remember that
        the goal is to force the acceptance rate into a specific interval.
        Suppose that the chain already is in a region of significant
        probability mass (should be the case before adapting it).
        When the acceptance rate is close to zero, the chain cannot move
        at all, i.e. the proposal does not propose points in regions of
        significantly higher probability density than that of the point
        where the chain is stuck. In this case the covariance matrix could
        be divided by some number > 1 in order to increase "locality" of
        the chain.
        In the opposite case, when the acceptance rate is close to one,
        the chain most probably only explores a small feature of the mode.
        Then dividing the covariance matrix by some number > 1 decreases
        "locality".
        In this implementation, the covariance matrix is not directly
        rescaled. Instead,

        :param covar_scale_factor:

            Float, this number is multiplied to unscaled_sigma after it
            has been recalculated

        is rescaled and then multiplied to unscaled_sigma. To be precise:

        :param covar_scale_multiplier:

            Float;
            if the acceptance rate is larger than ``force_acceptance_max``,
            ``covar_scale_factor`` is multiplied by covar_scale_multiplier
            if the acceptance rate is smaller than ``force_acceptance_min``,
            ``covar_scale_factor`` is divided by covar_scale_multiplier.

        Additionally, an upper and a lower limit ``for covar_scale_factor``
        can be provided.

        :param covar_scale_factor_max:

            Float, ``covar_scale_factor`` is kept below this value

        :param covar_scale_factor_min:

            Float, ``covar_scale_factor`` is kept above this value

        """
        #TODO: include citation HST01 & Wra+09 into docstring

        if args != (): raise TypeError('keyword args only; try set_adapt_parameters(keyword = value)')

        self.covar_scale_multiplier = kwargs.pop('covar_scale_multiplier' , self.covar_scale_multiplier)

        self.covar_scale_factor     = kwargs.pop('covar_scale_factor'     , self.covar_scale_factor    )
        self.covar_scale_factor_max = kwargs.pop('covar_scale_factor_max' , self.covar_scale_factor_max)
        self.covar_scale_factor_min = kwargs.pop('covar_scale_factor_min' , self.covar_scale_factor_min)

        self.force_acceptance_max   = kwargs.pop('force_acceptance_max'   , self.force_acceptance_max  )
        self.force_acceptance_min   = kwargs.pop('force_acceptance_min'   , self.force_acceptance_min  )

        self.damping                = kwargs.pop('damping'                , self.damping               )


        if not kwargs == {}: raise TypeError('unexpected keyword(s): ' + str(kwargs.keys()))


    def adapt(self):
        """Update the proposal's covariance matrix using the points
        stored in self.points and the parameters which can be set via
        :py:mod:`pypmc.mcprerun.markov_chain.AdaptiveMarkovChain.set_adapt_params`.
        In the above referenced function's docstring, the algorithm is
        described in detail.

        .. note::

            This function only uses the points obtained during the last run.

        """
        self.adapt_count += 1

        time_dependent_damping_factor = 1./self.adapt_count**self.damping

        last_run        = self.hist.get_run_points()
        accept_rate     = float(self.hist.get_run_accept_count())/len(last_run)

        # careful with rowvar!
        # in this form it is expected that each column  of ``points``
        # represents sampling values of a variable
        # this is the case if points is a list of sampled points
        covar_estimator = _np.cov(last_run, rowvar=0)

        # update sigma
        self.unscaled_sigma = (1-time_dependent_damping_factor) * self.unscaled_sigma\
                               + time_dependent_damping_factor  * covar_estimator
        self._update_scale_factor(accept_rate)

        self.proposal.update_sigma(self.covar_scale_factor * self.unscaled_sigma)

    def _update_scale_factor(self, accept_rate):
        '''Private function.
        Updates the covariance scaling factor ``covar_scale_factor``
        according to its limits

        '''
        if accept_rate > self.force_acceptance_max and self.covar_scale_factor < self.covar_scale_factor_max:
            self.covar_scale_factor *= self.covar_scale_multiplier
        elif accept_rate < self.force_acceptance_min and self.covar_scale_factor > self.covar_scale_factor_min:
            self.covar_scale_factor /= self.covar_scale_multiplier
