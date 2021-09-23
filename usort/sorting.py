# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict, List, Optional, Sequence, Tuple

import libcst as cst

from .config import Config
from .translate import import_from_node, import_to_node
from .types import SortableBlock, SortableImport


def name_overlap(a: Dict[str, str], b: Dict[str, str]) -> bool:
    for k, v in b.items():
        if k in a and a[k] != v:
            return True
    return False


def is_sortable_import(stmt: cst.CSTNode, config: Config) -> bool:
    """
    Determine if any individual statement is sortable or should be a barrier.

    Handles skip directives, configured side effect modules, and star imports.
    """
    if isinstance(stmt, cst.SimpleStatementLine):
        com = stmt.trailing_whitespace.comment
        if com:
            com_str = com.value.replace(" ", "")
            if com_str.startswith("#usort:skip") or com_str.startswith("#isort:skip"):
                return False

        # N.b. `body` is a list, because the SimpleStatementLine might have
        # semicolons.  We only look at the first, which is probably the most
        # dangerous thing in here.
        #
        # If black is run, it will put the semicolon pieces on different lines,
        # but we don't want to do that until we reflow and handle directives
        # like noqa.  TODO do that before calling is_sortable_import, and assert
        # that it's not a compound statement line.
        if isinstance(stmt.body[0], cst.ImportFrom):
            # `from x import *` is a barrier
            if isinstance(stmt.body[0].names, cst.ImportStar):
                return False
            # check for side effect modules, but ignore local (from .) imports (TODO?)
            elif stmt.body[0].module is not None:
                base = cst.helpers.get_full_name_for_node_or_raise(stmt.body[0].module)
                names = [name.evaluated_name for name in stmt.body[0].names]
                if config.is_side_effect_import(base, names):
                    return False
            return True
        elif isinstance(stmt.body[0], cst.Import):
            base = ""
            names = [name.evaluated_name for name in stmt.body[0].names]
            if config.is_side_effect_import(base, names):
                return False
            return True
        else:
            return False
    else:
        return False


def sortable_blocks(
    body: Sequence[cst.BaseStatement], config: Config
) -> List[SortableBlock]:
    """
    Finds blocks of imports separated by barriers (non-import statements, or
    dangerous imports).  We will only sort within a block, and only when there
    are no duplicate names.
    """
    blocks: List[SortableBlock] = []
    current: Optional[SortableBlock] = None
    for i, stmt in enumerate(body):
        if is_sortable_import(stmt, config):
            assert isinstance(stmt, cst.SimpleStatementLine)
            imp = import_from_node(stmt, config)
            if current is None:
                current = SortableBlock(i, i + 1)
                blocks.append(current)

            if name_overlap(current.imported_names, imp.imported_names):
                # This overwrites an earlier name
                current = SortableBlock(i, i + 1)
                blocks.append(current)

            current.end_idx = i + 1
            current.imports.append(imp)
            current.imported_names.update(imp.imported_names)
        else:
            if current:
                current = None
    return blocks


def partition_leading_lines(
    lines: List[str],
) -> Tuple[List[str], List[str]]:
    """
    Returns a tuple of the initial blank lines, and the comment lines.
    """
    for j in range(len(lines)):
        if lines[j].startswith("#"):
            break
    else:
        j = len(lines)

    return lines[:j], lines[j:]


def fixup_whitespace(
    initial_blank: Sequence[str], imports: List[SortableImport]
) -> List[SortableImport]:
    """
    Normalize whitespace/comments on a block of imports before transforming back to CST.
    """
    cur_category = None
    # TODO if they've already been reshuffled, there may have been a blank
    # (separator) line between a non-block and the first import, that's now in
    # the middle.
    for imp in imports:
        _old_blanks, old_comments = partition_leading_lines(imp.comments.before)

        if cur_category is None:
            blanks = initial_blank
        elif imp.sort_key.category_index != cur_category:
            blanks = ("",)
        else:
            blanks = _old_blanks[:1]

        imp.comments.before = [*blanks, *old_comments]

        cur_category = imp.sort_key.category_index
    return imports


def find_and_sort_blocks(
    body: Sequence[cst.BaseStatement], module: cst.Module, config: Config
) -> Sequence[cst.BaseStatement]:
    """
    Find all sortable blocks in a module, sort them, and return updated module content.
    """
    sorted_body: List[cst.BaseStatement] = list(body)
    blocks = list(sortable_blocks(body, config=config))

    for block in blocks:
        initial_blank, initial_comment = partition_leading_lines(
            block.imports[0].comments.before
        )
        block.imports[0].comments.before = initial_comment
        block.imports = fixup_whitespace(initial_blank, sorted(block.imports))

    for block in blocks:
        sorted_body[block.start_idx : block.end_idx] = [
            import_to_node(imp, module, config) for imp in block.imports
        ]

    return sorted_body


class ImportSortingTransformer(cst.CSTTransformer):
    def __init__(self, config: Config, module: cst.Module) -> None:
        self.config = config
        self.module = module

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        sorted_body = find_and_sort_blocks(
            updated_node.body, module=self.module, config=self.config
        )
        return updated_node.with_changes(body=sorted_body)

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.BaseSuite:
        sorted_body = find_and_sort_blocks(
            updated_node.body, module=self.module, config=self.config
        )
        return updated_node.with_changes(body=sorted_body)
