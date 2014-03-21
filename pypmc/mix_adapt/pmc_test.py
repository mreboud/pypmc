'''Unit tests for the Population Monte Carlo.

'''

from .pmc import *
from .. import density
import numpy as np
import unittest
#TODO: compare with pmclib (Kilbinger et. al.)

class TestPMCNoOverlap(unittest.TestCase):
    # proposal density
    mu1 = np.array( [ 10., -1.0, 8.0] )
    mu2 = np.array( [-10.,  7.4, 0.5] )

    cov1 = np.array([[1.15 , 0.875, 0.0],
                     [0.875, 0.75 ,-0.2],
                     [0.0  ,-0.2  , 1.1]])

    cov2 = np.array([[1.0  , 0.01 , 0.1],
                     [0.01 , 0.75 , 0.0],
                     [0.1  , 0.0  , 2.1]])

    inv_cov1 = np.linalg.inv(cov1)
    inv_cov2 = np.linalg.inv(cov2)

    gauss1 = density.gauss.Gauss(mu1+.001, cov1+.001)
    gauss2 = density.gauss.Gauss(mu2-.005, cov2-.005)
    component_weights = np.array( (.7, .3) )
    prop = density.mixture.MixtureDensity((gauss1,gauss2), component_weights)

    # samples, weights and latent variables
    latent = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1])
    weights = np.array([12.89295915,  12.89372694,  12.89781423,  12.79548829,
                        12.89397248,  12.88642498,  12.89875608,  12.8977244 ,
                        12.8834032 ,  12.81344527,  12.8966767 ,  12.89319812,
                        20.02787201,  19.89550322,  19.81661548,  19.9733172 ,
                        19.81867511,  19.81555008,  19.83955669,  19.83352245])
    samples = np.array([[  9.7070033 ,  -1.14093259,   7.79492513],
                        [  9.56875908,  -1.3205348 ,   7.3705522 ],
                        [ 10.53728461,  -0.93171182,   8.76279014],
                        [  9.80289836,  -1.15107748,   9.27682257],
                        [  8.91717444,  -1.62000575,   7.60676764],
                        [  9.55705421,  -1.65785994,   9.4330834 ],
                        [ 10.90155376,  -0.42097835,   7.64481752],
                        [ 11.06838483,  -0.65188323,   8.69936008],
                        [  8.50673184,  -2.45559049,   8.62152455],
                        [ 10.8097935 ,  -0.33471831,   8.60497435],
                        [ 10.46129646,  -1.04132199,   9.04460811],
                        [ 10.23040728,  -0.63621386,   6.48880065],
                        [-10.76972316,   8.23669361,   2.06283074],
                        [-11.26019812,   7.03488615,  -0.87321151],
                        [ -9.99070915,   6.83422119,   0.28846651],
                        [ -9.39271812,   7.08741571,   1.91672609],
                        [-10.98814859,   7.55372701,   0.48618477],
                        [ -9.60983136,   6.24723833,   1.06241101],
                        [-10.61752466,   7.39052825,   1.17726011],
                        [-10.4898097 ,   7.48668861,  -2.41443733]])

    def test_invalid_usage(self):
        self.assertRaisesRegexp(ValueError, r'["\'` ]*rb["\'` ]*must.*["\' `]*True["\'` ]* if["\'` ]*latent["\'` ]*.*not',
                                gaussian_pmc, self.samples, self.prop, self.weights, rb=False)
        self.assertRaisesRegexp(ValueError, r'["\'` ]*mincount["\'` ]*must.*["\' `]*[0(zero)]["\'` ]* if["\'` ]*latent["\'` ]*.*not',
                                gaussian_pmc, self.samples, self.prop, self.weights, mincount=10)
        self.assertRaisesRegexp(ValueError, r'(["\'` ]*mincount["\'` ]*must.*["\' `]*[0(zero)]["\'` ]* if["\'` ]*latent["\'` ]*.*not)' + \
                                            r'|' + \
                                            r'(["\'` ]*rb["\'` ]*must.*["\' `]*True["\'` ]* if["\'` ]*latent["\'` ]*.*not)',
                                gaussian_pmc, self.samples, self.prop, self.weights, mincount=10, rb=False)

    def test_mincount_and_copy(self):
        self.prop_weights = self.prop.weights.copy()
        self.prop_mu0     = self.prop.components[0].mu.copy()
        self.prop_mu1     = self.prop.components[1].mu.copy()
        self.prop_cov0    = self.prop.components[0].sigma.copy()
        self.prop_cov1    = self.prop.components[1].sigma.copy()

        adapted_prop_no_die_rb     = gaussian_pmc(self.samples, self.prop, self.weights, self.latent, mincount=8, rb=True )
        adapted_prop_die_rb        = gaussian_pmc(self.samples, self.prop, self.weights, self.latent, mincount=9, rb=True )
        adapted_prop_no_die_no_rb  = gaussian_pmc(self.samples, self.prop, self.weights, self.latent, mincount=8, rb=False)
        adapted_prop_die_no_rb     = gaussian_pmc(self.samples, self.prop, self.weights, self.latent, mincount=9, rb=False)

        self.assertNotEqual(adapted_prop_no_die_rb.weights[1]   , 0.)
        self.assertEqual   (adapted_prop_die_rb.weights[1]      , 0.)
        self.assertNotEqual(adapted_prop_no_die_no_rb.weights[1], 0.)
        self.assertEqual   (adapted_prop_die_no_rb.weights[1]   , 0.)

        # the self.proposal should not have been touched --> expect exact equality
        np.testing.assert_equal(self.prop.weights            , self.prop_weights)
        np.testing.assert_equal(self.prop.components[0].mu   , self.prop_mu0    )
        np.testing.assert_equal(self.prop.components[1].mu   , self.prop_mu1    )
        np.testing.assert_equal(self.prop.components[0].sigma, self.prop_cov0   )
        np.testing.assert_equal(self.prop.components[1].sigma, self.prop_cov1   )

    def test_gaussian_pmc_with_origin(self):
        adapted_prop = gaussian_pmc(self.samples, self.prop, self.weights, self.latent)

        adapted_comp_weights = adapted_prop.weights
        adapted_mu1          = adapted_prop.components[0].mu
        adapted_mu2          = adapted_prop.components[1].mu
        adapted_sigma1       = adapted_prop.components[0].sigma
        adapted_sigma2       = adapted_prop.components[1].sigma

        # the values that should be obtained by the pmc algorithm
        pmc_comp_weights = np.array( (154.54358983999998, 159.02061223999999) ) / 313.56420207999997
        pmc_mu1          = np.array([ 1546.302278  ,  -172.1300429 ,  1279.34733595]) / 154.54358983999998
        pmc_mu2          = np.array([-1652.19922509,  1150.52591727,    74.098254  ]) / 159.02061223999999
        pmc_sigma1       = np.array([[91.13245238,  62.95055712,   4.96175291],
                                     [62.95055712,  51.04895641, -16.59026473],
                                     [ 4.96175291, -16.59026473, 111.63047879]]) / 154.54358983999998
        pmc_sigma2       = np.array([[ 61.35426434, -30.51320283,  50.0064872 ],
                                     [-30.51320283,  47.59366671,  10.77061072],
                                     [ 50.0064872 ,  10.77061072, 311.06169561]]) / 159.02061223999999

        np.testing.assert_allclose(adapted_comp_weights, pmc_comp_weights)
        np.testing.assert_allclose(adapted_mu1         , pmc_mu1         )
        np.testing.assert_allclose(adapted_mu2         , pmc_mu2         )
        np.testing.assert_allclose(adapted_sigma1      , pmc_sigma1      )
        np.testing.assert_allclose(adapted_sigma2      , pmc_sigma2      )

    def test_gaussian_pmc_without_origin(self):
        adapted_prop = gaussian_pmc(self.samples, self.prop, self.weights)

        adapted_comp_weights = adapted_prop.weights
        adapted_mu1          = adapted_prop.components[0].mu
        adapted_mu2          = adapted_prop.components[1].mu
        adapted_sigma1       = adapted_prop.components[0].sigma
        adapted_sigma2       = adapted_prop.components[1].sigma

        # the values that should be obtained by the pmc algorithm
        pmc_comp_weights = np.array( (154.54358983999998, 159.02061223999999) ) / 313.56420207999997
        pmc_mu1          = np.array([1546.302278, -172.1300429, 1279.34733595]) / 154.54358983999998
        pmc_mu2          = np.array([-1652.19922509, 1150.52591727, 74.098254]) / 159.02061223999999
        pmc_sigma1       = np.array([[91.13245238,  62.95055712,   4.96175291],
                                     [62.95055712,  51.04895641, -16.59026473],
                                     [ 4.96175291, -16.59026473, 111.63047879]]) / 154.54358983999998
        pmc_sigma2       = np.array([[ 61.35426434, -30.51320283,  50.0064872 ],
                                     [-30.51320283,  47.59366671,  10.77061072],
                                     [ 50.0064872 ,  10.77061072, 311.06169561]]) / 159.02061223999999

        np.testing.assert_allclose(adapted_comp_weights, pmc_comp_weights)
        np.testing.assert_allclose(adapted_mu1         , pmc_mu1         )
        np.testing.assert_allclose(adapted_mu2         , pmc_mu2         )
        np.testing.assert_allclose(adapted_sigma1      , pmc_sigma1      )
        np.testing.assert_allclose(adapted_sigma2      , pmc_sigma2      )

    def test_unweighted(self):
        adapted_prop = gaussian_pmc(self.samples, self.prop, weights=None)

        adapted_comp_weights = adapted_prop.weights
        adapted_mu1          = adapted_prop.components[0].mu
        adapted_mu2          = adapted_prop.components[1].mu
        adapted_sigma1       = adapted_prop.components[0].sigma
        adapted_sigma2       = adapted_prop.components[1].sigma

        # the values that should be obtained by the pmc algorithm
        pmc_comp_weights = np.array(( .6, .4 ))
        pmc_mu1          = np.array([ 10.00569514,  -1.11356905,   8.27908553])
        pmc_mu2          = np.array([-10.38983286,   7.23392486,   0.4632788 ])
        pmc_sigma1       = np.array([[ 0.58945043,  0.40729425,  0.03200882],
                                     [ 0.40729425,  0.33036221, -0.10717408],
                                     [ 0.03200882, -0.10717408,  0.72221294]])
        pmc_sigma2       = np.array([[ 0.38545161, -0.19190136,  0.31422734],
                                     [-0.19190136,  0.29882842,  0.06594038],
                                     [ 0.31422734,  0.06594038,  1.95479308]])

        np.testing.assert_allclose(adapted_comp_weights, pmc_comp_weights)
        np.testing.assert_allclose(adapted_mu1         , pmc_mu1         )
        np.testing.assert_allclose(adapted_mu2         , pmc_mu2         )
        np.testing.assert_allclose(adapted_sigma1      , pmc_sigma1      )
        np.testing.assert_allclose(adapted_sigma2      , pmc_sigma2      )

class TestPMCWithOverlap(unittest.TestCase):
    # proposal density
    mu1 = np.array([ 10.5,   1.1,   8.0])
    mu2 = np.array([ 10.3,   1.4,   7.8])

    cov1 = np.array([[1.15 , 0.875, 0.0],
                     [0.875, 0.75 ,-0.2],
                     [0.0  ,-0.2  , 1.1]])

    cov2 = np.array([[1.0  , 0.01 , 0.1],
                     [0.01 , 0.75 , 0.0],
                     [0.1  , 0.0  , 2.1]])

    inv_cov1 = np.linalg.inv(cov1)
    inv_cov2 = np.linalg.inv(cov2)

    gauss1 = density.gauss.Gauss(mu1+.001, cov1+.001)
    gauss2 = density.gauss.Gauss(mu2-.005, cov2-.005)
    component_weights = np.array( (.7, .3) )
    prop = density.mixture.MixtureDensity((gauss1,gauss2), component_weights)

    # samples and latent variables (no weights here)
    latent = np.array([0, 1, 1, 0, 0, 1, 0, 0, 1, 0])
    samples = np.array([[  8.25176666,  -0.46218162,   6.38766958],
                        [ 10.30030254,   0.7211386 ,   8.75618216],
                        [  9.80807539,   2.0664736 ,   8.3028291 ],
                        [ 11.38801874,   1.90190379,   7.76177193],
                        [ 11.06700609,   1.52600855,   8.82273509],
                        [ 10.97130581,   0.23669273,   6.89884423],
                        [ 10.2306073 ,   0.76789268,   8.30328072],
                        [ 10.55012467,   1.26067336,   6.83958086],
                        [  9.44298062,   1.47722829,   8.32750139],
                        [ 11.74685298,   2.17160491,   6.83467116]])


    def test_with_rb(self):
        adapted_prop = gaussian_pmc(self.samples, self.prop, latent=self.latent, rb=True)

        adapted_comp_weights = adapted_prop.weights
        adapted_mu1          = adapted_prop.components[0].mu
        adapted_mu2          = adapted_prop.components[1].mu
        adapted_sigma1       = adapted_prop.components[0].sigma
        adapted_sigma2       = adapted_prop.components[1].sigma

        # the values that should be obtained by the pmc algorithm
        pmc_comp_weights = np.array( [  6.52555056,  3.47444944]) / 10.
        pmc_mu1          = np.array( [ 10.4920552 ,   1.11735768,   7.66532057])
        pmc_mu2          = np.array( [ 10.15717878,   1.25949764,   7.83278897])
        pmc_sigma1       = np.array([[ 11.54562717,   8.79011745,   3.21516184],
                                     [  8.79011745,   6.8816927 ,   1.41711901],
                                     [  3.21516184,   1.41711901,   8.52875733]]) / 10.
        pmc_sigma2       = np.array([[  4.92021176,  -3.00590244,  -3.60721614],
                                     [ -3.00590244,   5.56509117,   4.1113181 ],
                                     [ -3.60721614,   4.1113181 ,   4.9491569 ]]) / 10.

        np.testing.assert_allclose(adapted_comp_weights, pmc_comp_weights)
        np.testing.assert_allclose(adapted_mu1         , pmc_mu1         )
        np.testing.assert_allclose(adapted_mu2         , pmc_mu2         )
        np.testing.assert_allclose(adapted_sigma1      , pmc_sigma1      )
        np.testing.assert_allclose(adapted_sigma2      , pmc_sigma2      )

    def test_non_rb(self):
        adapted_prop = gaussian_pmc(self.samples, self.prop, latent=self.latent, rb=False)

        adapted_comp_weights = adapted_prop.weights
        adapted_mu1          = adapted_prop.components[0].mu
        adapted_mu2          = adapted_prop.components[1].mu
        adapted_sigma1       = adapted_prop.components[0].sigma
        adapted_sigma2       = adapted_prop.components[1].sigma

        # the values that should be obtained by the pmc algorithm
        pmc_comp_weights = np.array([0.6, 0.4])
        pmc_mu1          = np.array( [ 10.53906274,   1.19431695,   7.49161822])
        pmc_mu2          = np.array( [ 10.13066609,   1.12538331,   8.07133922])
        pmc_sigma1       = np.array([[ 12.97533036,   9.79558822,   4.01021926],
                                     [  9.79558822,   7.49336426,   2.38326823],
                                     [  4.01021926,   2.38326823,   7.63180987]]) / 10.
        pmc_sigma2       = np.array([[  3.28106932,  -3.40297223,  -2.80076755],
                                     [ -3.40297223,   4.90657639,   2.68280842],
                                     [ -2.80076755,   2.68280842,   4.90740244]]) / 10.

        np.testing.assert_allclose(adapted_comp_weights, pmc_comp_weights)
        np.testing.assert_allclose(adapted_mu1         , pmc_mu1         )
        np.testing.assert_allclose(adapted_mu2         , pmc_mu2         )
        np.testing.assert_allclose(adapted_sigma1      , pmc_sigma1      )
        np.testing.assert_allclose(adapted_sigma2      , pmc_sigma2      )

    def test_mincount_with_rb(self):
        adapted_prop = gaussian_pmc(self.samples, self.prop, latent=self.latent, rb=True, mincount=5)

        adapted_comp_weights = adapted_prop.weights
        adapted_mu1          = adapted_prop.components[0].mu
        adapted_mu2          = adapted_prop.components[1].mu
        adapted_sigma1       = adapted_prop.components[0].sigma
        adapted_sigma2       = adapted_prop.components[1].sigma

        # the values that should be obtained by the pmc algorithm
        pmc_comp_weights = np.array( [  1., 0.])
        pmc_mu1          = np.array( [ 10.4920552 ,   1.11735768,   7.66532057])
        pmc_mu2          = self.prop.components[1].mu
        pmc_sigma1       = np.array([[ 11.54562717,   8.79011745,   3.21516184],
                                     [  8.79011745,   6.8816927 ,   1.41711901],
                                     [  3.21516184,   1.41711901,   8.52875733]]) / 10.
        pmc_sigma2       = self.prop.components[1].sigma

        np.testing.assert_allclose(adapted_comp_weights, pmc_comp_weights)
        np.testing.assert_allclose(adapted_mu1         , pmc_mu1         )
        np.testing.assert_allclose(adapted_mu2         , pmc_mu2         )
        np.testing.assert_allclose(adapted_sigma1      , pmc_sigma1      )
        np.testing.assert_allclose(adapted_sigma2      , pmc_sigma2      )


    def test_mincount_no_rb(self):
        adapted_prop = gaussian_pmc(self.samples, self.prop, latent=self.latent, rb=False, mincount=5)

        adapted_comp_weights = adapted_prop.weights
        adapted_mu1          = adapted_prop.components[0].mu
        adapted_mu2          = adapted_prop.components[1].mu
        adapted_sigma1       = adapted_prop.components[0].sigma
        adapted_sigma2       = adapted_prop.components[1].sigma

        # the values that should be obtained by the pmc algorithm
        pmc_comp_weights = np.array([1., 0.])
        pmc_mu1          = np.array( [ 10.53906274,   1.19431695,   7.49161822])
        pmc_mu2          = self.prop.components[1].mu
        pmc_sigma1       = np.array([[ 12.97533036,   9.79558822,   4.01021926],
                                     [  9.79558822,   7.49336426,   2.38326823],
                                     [  4.01021926,   2.38326823,   7.63180987]]) / 10.
        pmc_sigma2       = self.prop.components[1].sigma

        np.testing.assert_allclose(adapted_comp_weights, pmc_comp_weights)
        np.testing.assert_allclose(adapted_mu1         , pmc_mu1         )
        np.testing.assert_allclose(adapted_mu2         , pmc_mu2         )
        np.testing.assert_allclose(adapted_sigma1      , pmc_sigma1      )
        np.testing.assert_allclose(adapted_sigma2      , pmc_sigma2      )

    def test_invalid_cov(self):
        # cannot build covariance from only one sample
        latent = np.zeros(len(self.samples))
        latent[-1] = 1

        adapted_prop = gaussian_pmc(self.samples, self.prop, latent=latent, rb=False)
        self.assertEqual(adapted_prop.weights[0], 1.)
        self.assertEqual(adapted_prop.weights[1], 0.)

        # samples are shared with RB, so all components should survive
        adapted_prop = gaussian_pmc(self.samples, self.prop, latent=latent, rb=True)
        self.assertLess(adapted_prop.weights[0], 1.)
        self.assertGreater(adapted_prop.weights[0], 0.)
        self.assertLess(adapted_prop.weights[1], 1.)
        self.assertGreater(adapted_prop.weights[1], 0.)