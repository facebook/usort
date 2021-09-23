# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict, Optional

import libcst as cst

from .config import Config
from .types import SortableImport
from .util import with_dots


def import_from_node(node: cst.SimpleStatementLine, config: Config) -> SortableImport:
    # TODO: This duplicates (differently) what's in the LibCST import
    # metadata visitor.  This is also a bit hard to read.
    first_module: Optional[str] = None
    first_dotted_import: Optional[str] = None
    names: Dict[str, str] = {}
    sort_key: Optional[str] = None

    # There are 4 basic types of import
    # Additionally some forms z can have leading dots for relative
    # imports, and there can be multiple on the right-hand side.
    #
    if isinstance(node.body[0], cst.Import):
        # import z
        # import z as y
        for name in node.body[0].names:
            if name.asname:
                names[with_dots(name.asname.name).split(".")[0]] = with_dots(name.name)
            else:
                tmp = with_dots(name.name).split(".")[0]
                names[tmp] = tmp

            if first_module is None:
                first_module = with_dots(name.name)
                first_dotted_import = first_module

    elif isinstance(node.body[0], cst.ImportFrom):
        # from z import x
        # from z import x as y

        # This is treated as a barrier and should never get this far.
        assert not isinstance(node.body[0].names, cst.ImportStar)

        if node.body[0].module is None:
            # from . import foo [as bar]
            # (won't have dots but with_dots makes the typing easier)
            sort_key = with_dots(node.body[0].names[0].name)
            name_key = sort_key
        else:
            # from x import foo [as bar]
            sort_key = with_dots(node.body[0].module)
            name_key = sort_key + "."

        if node.body[0].relative:
            first_dotted_import = sort_key
            sort_key = "." * len(node.body[0].relative)
            if node.body[0].module is not None:
                sort_key += first_dotted_import
            name_key = sort_key
            if node.body[0].module is not None:
                name_key += "."

        if first_module is None:
            first_module = sort_key
            if first_dotted_import is None:
                for alias in node.body[0].names:
                    first_dotted_import = with_dots(alias.name)
                    break

        for alias in node.body[0].names:
            if alias.asname:
                assert isinstance(alias.asname.name, cst.Name)
                names[alias.asname.name.value] = name_key + with_dots(alias.name)
            else:
                assert isinstance(alias.name, cst.Name)
                names[alias.name.value] = name_key + alias.name.value
    else:
        raise TypeError

    assert first_module is not None
    assert first_dotted_import is not None
    return SortableImport(
        node=node,
        first_module=first_module,
        first_dotted_import=first_dotted_import,
        imported_names=names,
        config=config,
    )
