# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import List, Optional, Sequence, Union

import libcst as cst

from .config import Config
from .types import (
    COMMENT_INDENT,
    ImportComments,
    ImportItemComments,
    SortableImport,
    SortableImportItem,
)
from .util import split_inline_comment, split_relative, with_dots


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

    # # THIS PART
    # import foo
    #
    # # THIS PART
    # from foo import bar
    for line in node.leading_lines:
        if line.comment:
            comments.before.append(line.comment.value)
        else:
            comments.before.append("")

    if isinstance(imp, cst.ImportFrom):
        if imp.lpar:
            if isinstance(imp.lpar.whitespace_after, cst.ParenthesizedWhitespace):
                ws = imp.lpar.whitespace_after

                # from foo import (  # THIS PART
                #     bar,
                # )
                if ws.first_line.comment:
                    comments.first_inline.extend(
                        split_inline_comment(ws.first_line.comment.value)
                    )

                # from foo import (
                #     # THIS PART
                #     bar,
                # )
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

            # from foo import (
            #     bar,
            # )  # THIS PART
            if node.trailing_whitespace and node.trailing_whitespace.comment:
                comments.last_inline.extend(
                    split_inline_comment(node.trailing_whitespace.comment.value)
                )

        # from foo import bar  # THIS PART
        elif node.trailing_whitespace and node.trailing_whitespace.comment:
            comments.first_inline.extend(
                split_inline_comment(node.trailing_whitespace.comment.value)
            )

    # import foo  # THIS PART
    elif isinstance(imp, cst.Import):
        if node.trailing_whitespace and node.trailing_whitespace.comment:
            comments.first_inline.extend(
                split_inline_comment(node.trailing_whitespace.comment.value)
            )

    else:
        raise TypeError

    return comments


def item_from_node(
    node: cst.ImportAlias, stem: Optional[str] = None, before: Sequence[str] = ()
) -> SortableImportItem:
    name = with_dots(node.name)
    asname = with_dots(node.asname.name) if node.asname else ""
    comments = ImportItemComments()
    comments.before.extend(before)

    if isinstance(node.comma, cst.Comma):
        if (
            isinstance(node.comma.whitespace_before, cst.ParenthesizedWhitespace)
            and node.comma.whitespace_before.first_line.comment
        ):
            # from foo import (
            #     bar  # THIS PART
            #     ,
            # )
            comments.inline.extend(
                split_inline_comment(
                    node.comma.whitespace_before.first_line.comment.value
                )
            )

        if isinstance(node.comma.whitespace_after, cst.ParenthesizedWhitespace):
            ws = cst.ensure_type(
                node.comma.whitespace_after, cst.ParenthesizedWhitespace
            )
            if ws.first_line.comment:
                # from foo import (
                #     baz,  # THIS PART
                # )
                comments.inline.extend(
                    split_inline_comment(ws.first_line.comment.value)
                )

            # from a import (
            #   b,
            #   # THIS PART
            #   c,  # (but only if it's not the last item)
            # )
            comments.following.extend(
                line.comment.value for line in ws.empty_lines if line.comment
            )

    return SortableImportItem(name=name, asname=asname, comments=comments, stem=stem)


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
            items.append(item_from_node(name, stem, comments.initial))
            comments.initial = []

    else:
        raise TypeError

    # assume that "following" comments are actually meant for an item after that
    prev: Optional[SortableImportItem] = None
    for item in items:
        if prev is not None and prev.comments.following:
            item.comments.before.extend(prev.comments.following)
            prev.comments.following.clear()
        prev = item
    # following comments on the last item should maybe be on the import itself
    if prev is not None and prev.comments.following:
        comments.final.extend(prev.comments.following)
        prev.comments.following.clear()

    imp = SortableImport(
        stem=stem,
        items=items,
        comments=comments,
        config=config,
        node=node,
        indent="",
    )
    return imp


def import_to_node(
    imp: SortableImport, module: cst.Module, indent: str, config: Config
) -> cst.BaseStatement:
    node = import_to_node_single(imp, module)
    content = indent + render_node(node, module).rstrip()
    # basic imports can't be reflowed, so only deal with from-imports
    if imp.stem and len(content) > config.line_length:
        node = import_to_node_multi(imp, module)
    return node


def import_to_node_single(imp: SortableImport, module: cst.Module) -> cst.BaseStatement:
    leading_lines = [
        cst.EmptyLine(indent=True, comment=cst.Comment(line))
        if line.startswith("#")
        else cst.EmptyLine(indent=False)
        for line in imp.comments.before
    ]

    trailing_whitespace = cst.TrailingWhitespace()
    trailing_comments = list(imp.comments.first_inline)

    names: List[cst.ImportAlias] = []
    for item in imp.items:
        name = name_to_node(item.name)
        asname = cst.AsName(name=cst.Name(item.asname)) if item.asname else None
        node = cst.ImportAlias(name=name, asname=asname)
        names.append(node)
        trailing_comments += item.comments.before
        trailing_comments += item.comments.inline
        trailing_comments += item.comments.following

    trailing_comments += imp.comments.final
    trailing_comments += imp.comments.last_inline
    if trailing_comments:
        text = COMMENT_INDENT.join(trailing_comments)
        trailing_whitespace = cst.TrailingWhitespace(
            whitespace=cst.SimpleWhitespace(COMMENT_INDENT), comment=cst.Comment(text)
        )

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
    body: List[cst.BaseSmallStatement] = []
    names: List[cst.ImportAlias] = []
    prev: Optional[cst.ImportAlias] = None
    following: List[str] = []
    lpar_lines: List[cst.EmptyLine] = []
    lpar_inline: cst.TrailingWhitespace = cst.TrailingWhitespace()

    item_count = len(imp.items)
    for idx, item in enumerate(imp.items):
        name = name_to_node(item.name)
        asname = cst.AsName(name=cst.Name(item.asname)) if item.asname else None

        # Leading comments actually have to be trailing comments on the previous node.
        # That means putting them on the lpar node for the first item
        if item.comments.before:
            lines = [
                cst.EmptyLine(
                    indent=True,
                    comment=cst.Comment(c),
                    whitespace=cst.SimpleWhitespace(module.default_indent),
                )
                for c in item.comments.before
            ]
            if prev is None:
                lpar_lines.extend(lines)
            else:
                prev.comma.whitespace_after.empty_lines.extend(lines)  # type: ignore

        # all items except the last needs whitespace to indent the *next* line/item
        indent = idx != (len(imp.items) - 1)

        first_line = cst.TrailingWhitespace()
        inline = COMMENT_INDENT.join(item.comments.inline)
        if inline:
            first_line = cst.TrailingWhitespace(
                whitespace=cst.SimpleWhitespace(COMMENT_INDENT),
                comment=cst.Comment(inline),
            )

        if idx == item_count - 1:
            following = item.comments.following + imp.comments.final
        else:
            following = item.comments.following

        after = cst.ParenthesizedWhitespace(
            indent=True,
            first_line=first_line,
            empty_lines=[
                cst.EmptyLine(
                    indent=True,
                    comment=cst.Comment(c),
                    whitespace=cst.SimpleWhitespace(module.default_indent),
                )
                for c in following
            ],
            last_line=cst.SimpleWhitespace(module.default_indent if indent else ""),
        )

        node = cst.ImportAlias(
            name=name,
            asname=asname,
            comma=cst.Comma(whitespace_after=after),
        )
        names.append(node)
        prev = node

    # from foo import (
    #     bar
    # )
    if imp.stem:
        stem, ndots = split_relative(imp.stem)
        if not stem:
            module_name = None
        else:
            module_name = name_to_node(stem)
        relative = (cst.Dot(),) * ndots

        # inline comment following lparen
        if imp.comments.first_inline:
            inline = COMMENT_INDENT.join(imp.comments.first_inline)
            lpar_inline = cst.TrailingWhitespace(
                whitespace=cst.SimpleWhitespace(COMMENT_INDENT),
                comment=cst.Comment(inline),
            )

        body = [
            cst.ImportFrom(
                module=module_name,
                names=names,
                relative=relative,
                lpar=cst.LeftParen(
                    whitespace_after=cst.ParenthesizedWhitespace(
                        indent=True,
                        first_line=lpar_inline,
                        empty_lines=lpar_lines,
                        last_line=cst.SimpleWhitespace(module.default_indent),
                    ),
                ),
                rpar=cst.RightParen(),
            )
        ]

    # import foo
    else:
        raise ValueError("can't render basic imports on multiple lines")

    # comment lines above import
    leading_lines = [
        cst.EmptyLine(indent=True, comment=cst.Comment(line))
        if line.startswith("#")
        else cst.EmptyLine(indent=False)
        for line in imp.comments.before
    ]

    # inline comments following import/rparen
    if imp.comments.last_inline:
        inline = COMMENT_INDENT.join(imp.comments.last_inline)
        trailing = cst.TrailingWhitespace(
            whitespace=cst.SimpleWhitespace(COMMENT_INDENT), comment=cst.Comment(inline)
        )
    else:
        trailing = cst.TrailingWhitespace()

    return cst.SimpleStatementLine(
        body=body,
        leading_lines=leading_lines,
        trailing_whitespace=trailing,
    )
