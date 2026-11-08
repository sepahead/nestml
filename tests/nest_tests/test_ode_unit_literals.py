# -*- coding: utf-8 -*-
#
# test_ode_unit_literals.py
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

import numpy as np
import pytest

import nest

from pynestml.codegeneration.nest_tools import NESTTools
from pynestml.frontend.pynestml_frontend import generate_nest_target


@pytest.mark.skipif(NESTTools.detect_nest_version().startswith("v2"),
                    reason="This test does not support NEST 2")
class TestODEUnitLiterals:
    r"""Test that numeric literals with a physical unit in ODEs are converted to the units that NEST uses"""

    def test_ode_unit_literals(self):
        input_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "resources", "ode_unit_literals_neuron.nestml"))
        generate_nest_target(input_path,
                             target_path="target",
                             logging_level="INFO",
                             module_name="nestml_ode_unit_literals_module",
                             suffix="_nestml")

        nest.ResetKernel()
        nest.resolution = .1    # [ms]
        nest.Install("nestml_ode_unit_literals_module")

        nrn = nest.Create("ode_unit_literals_neuron_nestml")
        nest.Simulate(10.)

        np.testing.assert_allclose(nrn.b, np.exp(-1))    # time constant 0.01 s = 10 ms
        np.testing.assert_allclose(nrn.c, 1000. * (1. - np.exp(-1)))    # c [mV] tends to 1 V = 1000 mV
        np.testing.assert_allclose(nrn.I, 1001. * (1. - np.exp(-1)))    # I [pA] tends to 1 pA + 1 nA = 1001 pA
        np.testing.assert_allclose(nrn.d, np.exp(-np.exp(1E-3)))    # 1 ms / 1 s = 1E-3
