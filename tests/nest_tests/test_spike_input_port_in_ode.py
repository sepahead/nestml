# -*- coding: utf-8 -*-
#
# test_spike_input_port_in_ode.py
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


class TestSpikeInputPortInODE:
    r"""
    Test that a spike input port that is used in an ODE, as in ``y' = -y / tau_m + unit_psp * spikes_in``, increases ``y`` by ``unit_psp`` times the weight of the spike.
    """

    def test_spike_input_port_in_ode(self):
        input_path = os.path.join(os.path.realpath(os.path.join(os.path.dirname(__file__), "resources", "spike_input_port_in_ode_neuron.nestml")))
        generate_nest_target(input_path,
                             target_path="target",
                             logging_level="INFO",
                             module_name="nestmlmodule",
                             suffix="_nestml")

        nest.ResetKernel()
        nest.resolution = 0.1
        nest.Install("nestmlmodule")
        neuron = nest.Create("spike_input_port_in_ode_neuron_nestml")
        sg = nest.Create("spike_generator", params={"spike_times": [1.]})
        nest.Connect(sg, neuron, syn_spec={"weight": 1000., "delay": 0.1})
        mm = nest.Create("multimeter", params={"record_from": ["y"], "interval": nest.resolution})
        nest.Connect(mm, neuron)
        nest.Simulate(5.)

        np.testing.assert_allclose(np.amax(mm.get("events")["y"]), 1000.)    # 1 mV times the weight 1000
