# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Optional, List, Union, Sequence

import libcst as cst

from .config import Config
from .types import (
    ImportComments,
    ImportItemComments,
    SortableImport,
    SortableImportItem,
)
from .util import split_relative, split_inline_comment, with_dots


def render_node(node: cst.CSTNode, module: Optional[cst.Module] = None) -> str:
    if module is None:
        module = cst.Module(body=[])
    code = module.code_for_node(node.with_changes(leading_lines=()))
    return code


def name_to_node(name: str) -> Union[cst.Name, cst.Attribute]:
    if "." not in name:
        return cst.Name(name)

    base, name = name.rsplit(".", 1)
    return cst.Attribute(value=name_to_node(base), attr=cst.Name(name))


def import_comments_from_node(node: cst.SimpleStatementLine) -> ImportComments:
    comments = ImportComments()

    assert len(node.body) == 1
    assert isinstance(node.body[0], (cst.Import, cst.ImportFrom))
    imp: Union[cst.Import, cst.ImportFrom] = node.body[0]

    for line in node.leading_lines:
        if line.comment:
            comments.before.append(line.comment.value)
        else:
            comments.before.append("")

    if isinstance(imp, cst.ImportFrom):
        if imp.lpar:
            ws = cst.ensure_type(imp.lpar.whitespace_after, cst.ParenthesizedWhitespace)
            if ws.first_line.comment:
                comments.first_inline.extend(
                    split_inline_comment(ws.first_line.comment.value)
                )

            comments.initial.extend(
                line.comment.value for line in ws.empty_lines if line.comment
            )

            assert imp.rpar is not None
            if isinstance(imp.rpar.whitespace_before, cst.ParenthesizedWhitespace):
                comments.final.extend(
                    line.comment.value
                    for line in imp.rpar.whitespace_before.empty_lines
                    if line.comment
                )

                if imp.rpar.whitespace_before.first_line.comment:
                    comments.inline.extend(
                        split_inline_comment(
                            imp.rpar.whitespace_before.first_line.comment.value
                        )
                    )

            if node.trailing_whitespace and node.trailing_whitespace.comment:
                comments.last_inline.extend(
                    split_inline_comment(node.trailing_whitespace.comment.value)
                )

        elif node.trailing_whitespace and node.trailing_whitespace.comment:
            comments.first_inline.extend(
                split_inline_comment(node.trailing_whitespace.comment.value)
            )

    elif isinstance(imp, cst.Import):
        if node.trailing_whitespace and node.trailing_whitespace.comment:
            comments.first_inline.extend(
                split_inline_comment(node.trailing_whitespace.comment.value)
            )

    else:
        raise TypeError

    return comments


def item_comments_from_node(imp: cst.ImportAlias) -> ImportItemComments:
    comments = ImportItemComments()

    if isinstance(imp.comma, cst.Comma):
        if (
            isinstance(imp.comma.whitespace_before, cst.ParenthesizedWhitespace)
            and imp.comma.whitespace_before.first_line.comment
        ):
            # from a import (
            #   b  # THIS PART
            #   ,
            # )
            comments.inline.extend(
                split_inline_comment(
                    imp.comma.whitespace_before.first_line.comment.value
                )
            )

        ws = cst.ensure_type(imp.comma.whitespace_after, cst.ParenthesizedWhitespace)
        if ws.first_line.comment:
            # from a import (
            #   b,  # THIS PART
            # )
            comments.inline.extend(split_inline_comment(ws.first_line.comment.value))

        # from a import (
        #   b,
        #   # THIS PART
        #   c,  # (but only if it's not the last item)
        # )
        comments.following.extend(
            line.comment.value for line in ws.empty_lines if line.comment
        )

    return comments


def item_from_node(
    node: cst.ImportAlias, directive_comments: Sequence[str] = ()
) -> SortableImportItem:
    name = with_dots(node.name)
    asname = with_dots(node.asname.name) if node.asname else ""

    comments = ImportItemComments()

    if (
        isinstance(node.comma, cst.Comma)
        and isinstance(node.comma.whitespace_after, cst.ParenthesizedWhitespace)
        and node.comma.whitespace_after.first_line.comment
    ):
        comments.inline.extend(
            split_inline_comment(node.comma.whitespace_after.first_line.comment.value)
        )

    return SortableImportItem(name=name, asname=asname, comments=comments)


def import_from_node(node: cst.SimpleStatementLine, config: Config) -> SortableImport:
    # TODO: This duplicates (differently) what's in the LibCST import metadata visitor.

    stem: Optional[str] = None
    items: List[SortableImportItem] = []
    comments = import_comments_from_node(node)

    # There are 4 basic types of import
    # Additionally some forms z can have leading dots for relative
    # imports, and there can be multiple on the right-hand side.
    #
    if isinstance(node.body[0], cst.Import):
        # import z
        # import z as y
        items = [item_from_node(name) for name in node.body[0].names]

    elif isinstance(node.body[0], cst.ImportFrom):
        # from z import x
        # from z import x as y

        # This is treated as a barrier and should never get this far.
        assert not isinstance(node.body[0].names, cst.ImportStar)

        stem = with_dots(node.body[0].module) if node.body[0].module else ""

        if node.body[0].relative:
            stem = "." * len(node.body[0].relative) + stem

        for name in node.body[0].names:
            items.append(item_from_node(name, comments.initial))
            comments.initial = []

    else:
        raise TypeError

    return SortableImport(
        stem=stem,
        items=items,
        comments=comments,
        config=config,
        node=node,
    )


def import_to_node(
    imp: SortableImport, module: cst.Module, config: Config
) -> cst.BaseStatement:
    width = 88  # TODO: get width from tool.black
    node = import_to_node_single(imp, module)
    content = render_node(node, module)
    if len(content) > width:
        node = import_to_node_multi(imp, module)
    return node


def import_to_node_single(imp: SortableImport, module: cst.Module) -> cst.BaseStatement:
    trailing_whitespace = cst.TrailingWhitespace()
    leading_lines = [
        cst.EmptyLine(comment=(cst.Comment(line) if line.startswith("#") else None))
        for line in imp.comments.before
    ]

    if imp.comments.first_inline or imp.comments.last_inline:
        text = " ".join(imp.comments.first_inline + imp.comments.last_inline)
        trailing_whitespace = cst.TrailingWhitespace(
            whitespace=cst.SimpleWhitespace("  "), comment=cst.Comment(text)
        )

    names: List[cst.ImportAlias] = []
    for item in imp.items:
        name = name_to_node(item.name)
        asname = cst.AsName(name=cst.Name(item.asname)) if item.asname else None
        node = cst.ImportAlias(name=name, asname=asname)
        names.append(node)

    if imp.stem:
        stem, ndots = split_relative(imp.stem)
        if not stem:
            module_name = None
        else:
            module_name = name_to_node(stem)
        relative = (cst.Dot(),) * ndots

        line = cst.SimpleStatementLine(
            body=[cst.ImportFrom(module=module_name, names=names, relative=relative)],
            leading_lines=leading_lines,
            trailing_whitespace=trailing_whitespace,
        )

    else:
        line = cst.SimpleStatementLine(
            body=[cst.Import(names=names)],
            leading_lines=leading_lines,
            trailing_whitespace=trailing_whitespace,
        )

    return line


def import_to_node_multi(imp: SortableImport, module: cst.Module) -> cst.BaseStatement:
    leading_lines: List[cst.EmptyLine] = []

    names: List[cst.ImportAlias] = []
    for item in imp.items:
        name = name_to_node(item.name)
        asname = cst.AsName(name=cst.Name(item.asname)) if item.asname else None
        node = cst.ImportAlias(
            name=name,
            asname=asname,
            comma=cst.Comma(whitespace_after=cst.ParenthesizedWhitespace()),
        )
        names.append(node)

    if imp.stem:
        stem, ndots = split_relative(imp.stem)
        if not stem:
            module_name = None
        else:
            module_name = name_to_node(stem)
        relative = (cst.Dot(),) * ndots

        line = cst.SimpleStatementLine(
            body=[
                cst.ImportFrom(
                    module=module_name,
                    names=names,
                    relative=relative,
                    lpar=cst.LeftParen(whitespace_after=cst.ParenthesizedWhitespace()),
                    rpar=cst.RightParen(),
                )
            ],
            leading_lines=leading_lines,
        )

    else:
        line = cst.SimpleStatementLine(
            body=[cst.Import(names=names)], leading_lines=leading_lines
        )

    return line
