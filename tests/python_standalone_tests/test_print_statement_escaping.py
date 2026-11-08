# -*- coding: utf-8 -*-
#
# test_print_statement_escaping.py
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

import io
import os
import tokenize

from pynestml.frontend.pynestml_frontend import generate_python_standalone_target


class TestPythonStandalonePrintStatementEscaping:
    """
    Tests that the text of a print() statement stays in the string literals of the generated Python code.
    """

    def test_python_standalone_print_statement_escaping(self):
        input_path = os.path.join(os.path.realpath(os.path.join(os.path.dirname(__file__), "resources", "print_statement_escaping_neuron.nestml")))
        target_path = "nestmlmodule"

        generate_python_standalone_target(input_path, target_path, module_name="nestmlmodule", logging_level="INFO")

        with open(os.path.join(target_path, "print_statement_escaping_neuron.py"), "r") as reader:
            tokens = list(tokenize.generate_tokens(io.StringIO(reader.read()).readline))

        assert not [token for token in tokens if token.type == tokenize.NAME and token.string == "NESTML_PRINT_STRING_MARKER"]
        assert [token for token in tokens if token.type == tokenize.STRING and "NESTML_PRINT_STRING_MARKER" in token.string]
