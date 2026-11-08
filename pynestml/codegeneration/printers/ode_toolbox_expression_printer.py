# -*- coding: utf-8 -*-
#
# ode_toolbox_expression_printer.py
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

import math

from pynestml.codegeneration.printers.cpp_expression_printer import CppExpressionPrinter
from pynestml.codegeneration.printers.sympy_simple_expression_printer import SympySimpleExpressionPrinter
from pynestml.meta_model.ast_arithmetic_operator import ASTArithmeticOperator
from pynestml.meta_model.ast_expression import ASTExpression
from pynestml.meta_model.ast_expression_node import ASTExpressionNode
from pynestml.meta_model.ast_node import ASTNode
from pynestml.meta_model.ast_simple_expression import ASTSimpleExpression
from pynestml.visitors.ast_power_visitor import ASTPowerVisitor


class ODEToolboxExpressionPrinter(CppExpressionPrinter):
    r"""
    Printer for ``ASTExpression`` nodes in ODE-toolbox (sympy) syntax.

    An implicit conversion factor converts a value in the units in which its numeric literals are written. If the simple expression printer prints numeric literals with a physical unit in NEST units, this printer corrects the factors for this; for example, ``1 pA + 1 nA`` is printed as ``1 + 1000.`` instead of ``1 + (1000.0000000000001 * (1000.))``.
    """

    def print(self, node: ASTNode) -> str:
        if self._prints_literals_in_nest_units() and isinstance(node, (ASTExpression, ASTSimpleExpression)):
            return self._print_with_conversion_factor(node, target_literal_factor=1.)

        return super().print(node)

    def _prints_literals_in_nest_units(self) -> bool:
        return isinstance(self._simple_expression_printer, SympySimpleExpressionPrinter) \
            and self._simple_expression_printer.print_literals_in_nest_units

    def _print_with_conversion_factor(self, node: ASTExpressionNode, target_literal_factor: float) -> str:
        r"""
        Print ``node`` with its implicit conversion factor. ``target_literal_factor`` is the factor with which this printer multiplies the value of the target of the conversion (see ``_get_unit_literal_factor()``).
        """
        if isinstance(node, ASTExpression):
            s = self.print_expression(node)
        else:
            s = self._simple_expression_printer.print_simple_expression(node)

        factor = node.get_implicit_conversion_factor()
        if not factor:
            return s

        literal_factor = self._get_unit_literal_factor(node)
        if not (literal_factor == 1 and target_literal_factor == 1):
            factor *= target_literal_factor / literal_factor
            if math.isclose(factor, 1.):
                factor = 1.

        if factor == 1:
            return s

        return "(" + str(factor) + " * (" + s + "))"

    def _get_unit_literal_factor(self, node: ASTExpressionNode) -> float:
        r"""
        Return the factor with which this printer multiplies the value of ``node``, because it prints the numeric literals with a physical unit in ``node`` in NEST units.
        """
        if isinstance(node, ASTSimpleExpression):
            return self._simple_expression_printer.get_unit_literal_factor(node)

        if node.is_compound_expression():
            op = node.get_binary_operator()
            if not isinstance(op, ASTArithmeticOperator):
                # comparison, logical or bit operator: the value has no physical unit
                return 1.

            lhs_factor = self._get_unit_literal_factor(node.get_lhs())
            if op.is_times_op:
                return lhs_factor * self._get_unit_literal_factor(node.get_rhs())

            if op.is_div_op:
                return lhs_factor / self._get_unit_literal_factor(node.get_rhs())

            if op.is_pow_op:
                if lhs_factor == 1:
                    return 1.

                try:
                    return lhs_factor ** ASTPowerVisitor().calculate_numeric_value(node.get_rhs())
                except Exception:
                    return 1.

            # sum, difference or modulo: the right-hand operand is converted to the units of the left-hand operand
            return lhs_factor

        if node.is_ternary_operator():
            return self._get_unit_literal_factor(node.get_if_true())

        if node.is_logical_not:
            return 1.

        if node.is_expression():
            # unary operator or parentheses
            return self._get_unit_literal_factor(node.get_expression())

        return 1.

    def _print_ternary_operator_expression(self, node: ASTExpression) -> str:
        """
        Prints a ternary operator using the sympy.Piecewise class.
        :return: a string representation
        """
        condition = self.print(node.get_condition())
        if_true = self.print(node.get_if_true())
        if_not = self.print(node.if_not)

        return "Piecewise((" + if_true + ", " + condition + "), (" + if_not + ", True))"

    def _print_arithmetic_operator_expression(self, node: ASTExpressionNode) -> str:
        """
        Prints an arithmetic operator.
        :param op: an arithmetic operator object
        :return: a string representation
        """
        op = node.get_binary_operator()
        lhs = self.print(node.get_lhs())
        if (op.is_plus_op or op.is_minus_op) and node.get_rhs().get_implicit_conversion_factor() and self._prints_literals_in_nest_units():
            # the implicit conversion factor converts the right-hand operand to the units of the left-hand operand
            rhs = self._print_with_conversion_factor(node.get_rhs(), target_literal_factor=self._get_unit_literal_factor(node.get_lhs()))
        else:
            rhs = self.print(node.get_rhs())

        if op.is_pow_op:
            # Check if the SimpleExpression has a variable which is the same as its unit type.
            # For example, if an expression is of the form ``x pA = 0 pA**-1``, simple expression on the lhs is ``0pA``, and the rhs is ``-1``.
            # This simple expression will have 0 stored as a numeric literal and ``pA`` as a variable.
            # In this case, the printer must only print the lhs, which is the numeric literal, as the rhs is the exponent of the unit pA.
            if isinstance(node.get_lhs(), ASTSimpleExpression) and node.get_lhs().get_variable() is not None \
                    and node.get_lhs().get_variable().get_name() == node.get_lhs().type.get_symbol_name():
                return lhs
            return "(" + lhs + ")" + "**" + rhs

        if op.is_plus_op:
            return lhs + " + " + rhs

        if op.is_minus_op:
            return lhs + " - " + rhs

        if op.is_times_op:
            return lhs + " * " + rhs

        if op.is_div_op:
            return lhs + " / " + rhs

        if op.is_modulo_op:
            return "sympy.Mod(" + lhs + ", " + rhs + ")"

        raise RuntimeError("Cannot determine arithmetic operator!")
