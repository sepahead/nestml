# -*- coding: utf-8 -*-
#
# test_inline_expression_conversion_factors.py
#
# This file is part of NEST.
#
# Copyright (C) 2004 The NEST Initiative
#
# NEST is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# NEST is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NEST.  If not, see <http://www.gnu.org/licenses/>.

import os

import nest
import numpy as np

from pynestml.frontend.pynestml_frontend import generate_nest_target


class TestInlineExpressionConversionFactors:
    r"""
    Test that the ODEs and the inline expressions of an equations block keep their implicit conversion factors when the inline expressions are expanded.
    """

    def test_inline_expression_conversion_factors(self):
        input_path = os.path.join(os.path.realpath(os.path.join(os.path.dirname(__file__), "resources", "inline_expression_conversion_factors_neuron.nestml")))
        generate_nest_target(input_path,
                             target_path="target",
                             logging_level="INFO",
                             module_name="nestmlmodule",
                             suffix="_nestml")

        nest.ResetKernel()
        nest.resolution = 0.1
        nest.Install("nestmlmodule")
        neuron = nest.Create("inline_expression_conversion_factors_neuron_nestml")
        nest.Simulate(1.)

        # each ODE has the form r' = (r_inf - r) / tau with r(0) = 0 and tau = 1 ms, so that r(1 ms) = r_inf * (1 - exp(-1))
        np.testing.assert_allclose(neuron.get("r_ode"), 1001. * (1. - np.exp(-1.)))
        np.testing.assert_allclose(neuron.get("r_sum"), 1001. * (1. - np.exp(-1.)))
        np.testing.assert_allclose(neuron.get("r_khz"), 1000. * (1. - np.exp(-1.)))
        np.testing.assert_allclose(neuron.get("r_sum_out"), 1001.)
