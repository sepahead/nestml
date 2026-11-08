# -*- coding: utf-8 -*-
#
# test_comment_escaping.py
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
import re
import shutil
import tempfile
import unittest

from pynestml.codegeneration.nest_code_generator import NESTCodeGenerator
from pynestml.frontend.frontend_configuration import FrontendConfiguration
from pynestml.symbol_table.symbol_table import SymbolTable
from pynestml.symbols.predefined_functions import PredefinedFunctions
from pynestml.symbols.predefined_types import PredefinedTypes
from pynestml.symbols.predefined_units import PredefinedUnits
from pynestml.symbols.predefined_variables import PredefinedVariables
from pynestml.utils.ast_source_location import ASTSourceLocation
from pynestml.utils.logger import Logger, LoggingLevel
from pynestml.utils.model_parser import ModelParser


class CommentEscapingTest(unittest.TestCase):
    """
    Tests that the text of NESTML comments stays inside the comments of the generated C++ code.
    """

    def setUp(self) -> None:
        PredefinedUnits.register_units()
        PredefinedTypes.register_types()
        PredefinedFunctions.register_functions()
        PredefinedVariables.register_variables()
        SymbolTable.initialize_symbol_table(ASTSourceLocation(start_line=0, start_column=0, end_line=0, end_column=0))
        Logger.init_logger(LoggingLevel.INFO)

        self.target_path = tempfile.mkdtemp()

    def test_comment_escaping(self):
        input_path = str(os.path.realpath(os.path.join(os.path.dirname(__file__), "resources", "CommentEscaping.nestml")))
        FrontendConfiguration.parse_config(["--input_path", input_path, "--target_path", self.target_path])
        compilation_unit = ModelParser.parse_file(input_path)
        NESTCodeGenerator().generate_code(compilation_unit.get_model_list(), metadata={})

        for file_name in ["comment_escaping_neuron.h", "comment_escaping_neuron.cpp"]:
            with open(os.path.join(self.target_path, file_name), "r") as reader:
                code = reader.read()

            # join the lines that end with a backslash, then remove comments and string literals
            code = re.sub(r"\\[ \t]*\n", "", code)
            code = re.sub(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", " ", code, flags=re.DOTALL)
            self.assertEqual(code.count("static_assert"), 0, file_name)

        with open(os.path.join(self.target_path, "comment_escaping_neuron.h"), "r") as reader:
            header = reader.read()

        for comment in ["model comment", "state comment", "parameter comment", "joined comment lines"]:
            self.assertIn(comment, header)

    def tearDown(self):
        shutil.rmtree(self.target_path)
