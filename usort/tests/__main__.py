import unittest

from .config import ConfigTest  # noqa: F401
from .functional import BasicOrderingTest, UsortStringFunctionalTest  # noqa: F401
from .sort_key import IsSortableTest, SortableImportTest  # noqa: F401

unittest.main()
