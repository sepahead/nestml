# -*- coding: utf-8 -*-
#
# inline_expression_expansion_transformer.py
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

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Mapping, Sequence

try:
    # Available in the standard library starting with Python 3.12
    from typing import override
except ImportError:
    # Fallback for Python 3.8 - 3.11
    from typing_extensions import override

from pynestml.meta_model.ast_expression import ASTExpression
from pynestml.meta_model.ast_expression_node import ASTExpressionNode
from pynestml.meta_model.ast_inline_expression import ASTInlineExpression
from pynestml.meta_model.ast_model import ASTModel
from pynestml.meta_model.ast_ode_equation import ASTOdeEquation
from pynestml.meta_model.ast_simple_expression import ASTSimpleExpression
from pynestml.transformers.transformer import Transformer
from pynestml.visitors.ast_higher_order_visitor import ASTHigherOrderVisitor
from pynestml.visitors.ast_parent_visitor import ASTParentVisitor


class InlineExpressionExpansionTransformer(Transformer):
    r"""
    Make inline expressions self contained, i.e. without any references to other inline expressions.

    Additionally, replace variable symbols referencing inline expressions in defining expressions of ODEs with the corresponding defining expressions from the inline expressions.
    """

    def __init__(self, options: Optional[Mapping[str, Any]] = None):
        super(Transformer, self).__init__(options)

    @override
    def transform(self,
                  models: Iterable[ASTModel],
                  metadata: Dict[str, Dict[str, Any]]) -> Iterable[ASTModel]:
        for model in models:
            if not model.get_equations_blocks():
                continue

            for equations_block in model.get_equations_blocks():
                self.make_inline_expressions_self_contained(equations_block.get_inline_expressions())

            for equations_block in model.get_equations_blocks():
                self.replace_inline_expressions_through_defining_expressions(equations_block.get_ode_equations(), equations_block.get_inline_expressions())

        return models

    def make_inline_expressions_self_contained(self, inline_expressions: List[ASTInlineExpression]) -> List[ASTInlineExpression]:
        r"""
        Make inline expressions self contained, i.e. without any references to other inline expressions.

        :param inline_expressions: A sorted list with entries ASTInlineExpression.
        :return: A list with ASTInlineExpressions. Defining expressions don't depend on each other.
        """
        from pynestml.visitors.ast_symbol_table_visitor import ASTSymbolTableVisitor

        for source in inline_expressions:
            if "mechanism" not in [e.namespace for e in source.get_decorators()]:
                source_position = source.get_source_position()
                for target in inline_expressions:
                    old_parent = target.expression.parent_
                    target.expression = self._replace_references(target.get_expression(), source)
                    target.expression.update_scope(source.get_scope())
                    target.expression.parent_ = old_parent
                    target.expression.accept(ASTParentVisitor())
                    target.expression.accept(ASTSymbolTableVisitor())

                    def log_set_source_position(node):
                        if node.get_source_position().is_added_source_position():
                            node.set_source_position(source_position)

                    target.expression.accept(ASTHigherOrderVisitor(visit_funcs=log_set_source_position))

        return inline_expressions

    @classmethod
    def replace_inline_expressions_through_defining_expressions(self, definitions: Sequence[ASTOdeEquation],
                                                                inline_expressions: Sequence[ASTInlineExpression]) -> Sequence[ASTOdeEquation]:
        r"""
        Replace variable symbols referencing inline expressions in defining expressions of ODEs with the corresponding defining expressions from the inline expressions.

        :param definitions: A list of ODE definitions (**updated in-place**).
        :param inline_expressions: A list of inline expression definitions.
        :return: A list of updated ODE definitions (same as the ``definitions`` parameter).
        """
        from pynestml.visitors.ast_symbol_table_visitor import ASTSymbolTableVisitor

        for m in inline_expressions:
            if "mechanism" not in [e.namespace for e in m.get_decorators()]:
                """
                exclude compartmental mechanism definitions in order to have the
                inline as a barrier inbetween odes that are meant to be solved independently
                """
                source_position = m.get_source_position()
                for target in definitions:
                    old_parent = target.rhs.parent_
                    target.rhs = self._replace_references(target.get_rhs(), m)
                    target.update_scope(m.get_scope())
                    target.rhs.parent_ = old_parent
                    target.rhs.accept(ASTParentVisitor())
                    target.accept(ASTSymbolTableVisitor())

                    def log_set_source_position(node):
                        if node.get_source_position().is_added_source_position():
                            node.set_source_position(source_position)

                    target.accept(ASTHigherOrderVisitor(visit_funcs=log_set_source_position))

        return definitions

    @classmethod
    def _replace_references(cls, node: ASTExpressionNode, inline_expression: ASTInlineExpression) -> ASTExpressionNode:
        r"""
        Replace the references to an inline expression in an expression with a copy of its defining expression in parentheses.

        The copy keeps the implicit conversion factors of the defining expression, among them the factor that converts it to the unit of the inline expression. The parentheses get the type of the inline expression and the implicit conversion factor of the reference. Thus, the expressions that contain the reference keep their values, types and implicit conversion factors.

        :param node: The expression in which to replace the references (**updated in-place**).
        :param inline_expression: The inline expression.
        :return: The updated expression; this is a new expression if ``node`` is itself a reference.
        """
        if isinstance(node, ASTSimpleExpression):
            if node.is_variable() and node.get_variable().get_name() == inline_expression.get_variable_name() \
                    and node.get_variable().get_differential_order() == 0:
                expr = ASTExpression(is_encapsulated=True, expression=inline_expression.get_expression().clone(),
                                     source_position=node.get_source_position(), scope=node.get_scope(),
                                     implicit_conversion_factor=node.get_implicit_conversion_factor())
                expr.type = inline_expression.get_data_type().get_type_symbol()
                return expr

            if node.is_function_call():
                args = node.get_function_call().get_args()
                for i, arg in enumerate(args):
                    args[i] = cls._replace_references(arg, inline_expression)

            return node

        for child_name in ["expression", "lhs", "rhs", "condition", "if_true", "if_not"]:
            child = getattr(node, child_name)
            if child is not None:
                setattr(node, child_name, cls._replace_references(child, inline_expression))

        return node
