# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
from typing import List, Optional, Sequence, Set, Tuple

import libcst as cst
from libcst.metadata import PositionProvider

from .config import Config
from .translate import import_from_node, import_to_node
from .types import SortableBlock, SortableImport

LOG = logging.getLogger(__name__)


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


def name_overlap(block: SortableBlock, imp: SortableImport) -> Set[str]:
    """
    Find imported names that overlap existing names for a block of imports.

    Compares imports of a proposed, but not yet included, import with existing imports
    in a block. Ignores multiple imports of the same "name" that come from the same
    qualified name. Eg, `os.path` doesn't shadow `os`, but `from foo import os` does.

    Returns a set of qualified names from `imp` that shadow names from `block`.
    This set will be empty if there are no overlaps.
    """
    overlap: Set[str] = set()

    for key, value in imp.imported_names.items():
        shadowed = block.imported_names.get(key)
        if shadowed and shadowed != value:
            LOG.warning(
                f"Name {shadowed!r} shadowed by {value!r}; implicit block split"
            )
            overlap.add(shadowed)

    return overlap


def split_inplace(block: SortableBlock, overlap: Set[str]) -> SortableBlock:
    """
    Split an existing block into two blocks after the last shadowed import.

    Pre-sorts the block of imports, then finds the last import with shadowed names, and
    splits after that import. Returns a new block containing all imports after the split
    point, or empty otherwise.
    """
    # best-effort pre-sorting before we split
    for imp in block.imports:
        imp.items.sort()
    block.imports.sort()

    # find index of last shadowed import, starting from the end of the block's imports
    idx = len(block.imports)
    while idx > 0:
        idx -= 1
        imp = block.imports[idx]
        if any(item.fullname in overlap for item in imp.items):
            break

    count = idx + 1
    if count >= len(block.imports):
        # shadowed import is the last import in the block, so we can't split anything.
        # return a new, empty block following pattern from sortable_blocks()
        new = SortableBlock(block.end_idx, block.end_idx + 1)

    else:
        # Split the existing block after the shadowed import, creating a new block that
        # starts after the shadowed import, update the old block's end index, and then
        # move all the imports after that to the new block
        new = SortableBlock(block.start_idx + count, block.end_idx)
        block.end_idx = block.start_idx + count

        new.imports = block.imports[count:]
        block.imports[count:] = []

        # move imported names metadata
        for imp in new.imports:
            for key in list(imp.imported_names):
                new.imported_names[key] = block.imported_names.pop(key)

    return new


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
    for idx, stmt in enumerate(body):
        if is_sortable_import(stmt, config):
            assert isinstance(stmt, cst.SimpleStatementLine)
            imp = import_from_node(stmt, config)
            if current is None:
                current = SortableBlock(idx, idx + 1)
                blocks.append(current)

            overlap = name_overlap(current, imp)
            if overlap:
                # This overwrites an earlier name
                current = split_inplace(current, overlap)
                blocks.append(current)

            current.add_import(imp, idx)
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


def merge_and_sort_imports(
    imports: List[SortableImport], config: Config
) -> List[SortableImport]:
    if config.merge_imports:
        # Look for sequential imports with matching stems, and merge them.
        idx = 0
        while idx + 1 < len(imports):
            imp = imports[idx]
            nxt = imports[idx + 1]

            if (
                # This is a from-import and the next statement is from the same module
                (imp.stem and imp.stem == nxt.stem)
                # This is a module-import and the next statement imports the same module
                or (imp.stem is None and imp.items == nxt.items)
            ):
                # Merge them and discard the second import from the list.
                imports[idx] += nxt
                imports.pop(idx + 1)

            else:
                idx += 1

    # Sort items within each remaining statement
    for imp in imports:
        imp.items.sort()

    return imports


def find_and_sort_blocks(
    body: Sequence[cst.BaseStatement], module: cst.Module, indent: str, config: Config
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
        # Sort the imports first, so that imports from the same module line up, then
        # merge and sort imports/items, then re-sort the final set of imports again
        # in case unsorted items affected overall sorting.
        imports = sorted(block.imports)
        imports = merge_and_sort_imports(imports, config)
        imports = fixup_whitespace(initial_blank, imports)
        block.imports = sorted(imports)

    for block in blocks:
        sorted_body[block.start_idx : block.end_idx] = [
            import_to_node(imp, module, indent, config) for imp in block.imports
        ]

    return sorted_body


class ImportSortingTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, config: Config, module: cst.Module) -> None:
        self.config = config
        self.module = module

    def get_indent(self, node: cst.CSTNode) -> str:
        pos = self.get_metadata(PositionProvider, node)
        indent_level = pos.start.column
        indent = self.module.default_indent[0] * indent_level
        return indent

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        indent = self.get_indent(original_node)
        sorted_body = find_and_sort_blocks(
            updated_node.body, module=self.module, indent=indent, config=self.config
        )
        return updated_node.with_changes(body=sorted_body)

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.BaseSuite:
        indent = self.get_indent(original_node)
        sorted_body = find_and_sort_blocks(
            updated_node.body, module=self.module, indent=indent, config=self.config
        )
        return updated_node.with_changes(body=sorted_body)


def sort_module(module: cst.Module, config: Config) -> cst.Module:
    wrapper = cst.MetadataWrapper(module)
    transform = ImportSortingTransformer(config, module)
    new_module = wrapper.visit(transform)
    return new_module
