import os

from clang.cindex import CompilationDatabase, CompilationDatabaseError, Config

if "CLANG_LIBRARY_PATH" in os.environ:
    Config.set_library_path(os.environ["CLANG_LIBRARY_PATH"])

import gc
import unittest
import sys
from pathlib import Path

INPUTS_DIR = os.path.join(os.path.dirname(__file__), "INPUTS")


@unittest.skipIf(sys.platform == "win32", "TODO: Fix these tests on Windows")
class TestCDB(unittest.TestCase):
    def test_create_fail(self):
        """Check we fail loading a database with an assertion"""
        path = os.path.dirname(__file__)

        # clang_CompilationDatabase_fromDirectory calls fprintf(stderr, ...)
        # Suppress its output.
        try:
            stderr = os.dup(2)
            with open(os.devnull, "wb") as null:
                os.dup2(null.fileno(), 2)
            with self.assertRaises(CompilationDatabaseError) as cm:
                CompilationDatabase.fromDirectory(path)
        # Ensures that stderr is reset even if the above code crashes
        finally:
            os.dup2(stderr, 2)
            os.close(stderr)

        e = cm.exception
        self.assertEqual(e.cdb_error, CompilationDatabaseError.ERROR_CANNOTLOADDATABASE)

    def test_create(self):
        """Check we can load a compilation database"""
        CompilationDatabase.fromDirectory(INPUTS_DIR)

    def test_lookup_succeed(self):
        """Check we get some results if the file exists in the db"""
        cdb = CompilationDatabase.fromDirectory(INPUTS_DIR)
        cmds = cdb.getCompileCommands("/home/john.doe/MyProject/project.cpp")
        self.assertNotEqual(len(cmds), 0)

    def test_lookup_succeed_pathlike(self):
        """Same as test_lookup_succeed, but with PathLikes"""
        cdb = CompilationDatabase.fromDirectory(Path(INPUTS_DIR))
        cmds = cdb.getCompileCommands(Path("/home/john.doe/MyProject/project.cpp"))
        self.assertNotEqual(len(cmds), 0)

    def test_all_compilecommand(self):
        """Check we get all results from the db"""
        cdb = CompilationDatabase.fromDirectory(INPUTS_DIR)
        cmds = cdb.getAllCompileCommands()
        self.assertEqual(len(cmds), 3)
        expected = [
            {
                "wd": "/home/john.doe/MyProject",
                "file": "/home/john.doe/MyProject/project.cpp",
                "line": [
                    "clang++",
                    "--driver-mode=g++",
                    "-o",
                    "project.o",
                    "-c",
                    "/home/john.doe/MyProject/project.cpp",
                ],
            },
            {
                "wd": "/home/john.doe/MyProjectA",
                "file": "/home/john.doe/MyProject/project2.cpp",
                "line": [
                    "clang++",
                    "--driver-mode=g++",
                    "-o",
                    "project2.o",
                    "-c",
                    "/home/john.doe/MyProject/project2.cpp",
                ],
            },
            {
                "wd": "/home/john.doe/MyProjectB",
                "file": "/home/john.doe/MyProject/project2.cpp",
                "line": [
                    "clang++",
                    "--driver-mode=g++",
                    "-DFEATURE=1",
                    "-o",
                    "project2-feature.o",
                    "-c",
                    "/home/john.doe/MyProject/project2.cpp",
                ],
            },
        ]
        for i in range(len(cmds)):
            self.assertEqual(cmds[i].directory, expected[i]["wd"])
            self.assertEqual(cmds[i].filename, expected[i]["file"])
            for arg, exp in zip(cmds[i].arguments, expected[i]["line"]):
                self.assertEqual(arg, exp)

    def test_1_compilecommand(self):
        """Check file with single compile command"""
        cdb = CompilationDatabase.fromDirectory(INPUTS_DIR)
        file = "/home/john.doe/MyProject/project.cpp"
        cmds = cdb.getCompileCommands(file)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].directory, os.path.dirname(file))
        self.assertEqual(cmds[0].filename, file)
        expected = [
            "clang++",
            "--driver-mode=g++",
            "-o",
            "project.o",
            "-c",
            "/home/john.doe/MyProject/project.cpp",
        ]
        for arg, exp in zip(cmds[0].arguments, expected):
            self.assertEqual(arg, exp)

    def test_2_compilecommand(self):
        """Check file with 2 compile commands"""
        cdb = CompilationDatabase.fromDirectory(INPUTS_DIR)
        cmds = cdb.getCompileCommands("/home/john.doe/MyProject/project2.cpp")
        self.assertEqual(len(cmds), 2)
        expected = [
            {
                "wd": "/home/john.doe/MyProjectA",
                "line": [
                    "clang++",
                    "--driver-mode=g++",
                    "-o",
                    "project2.o",
                    "-c",
                    "/home/john.doe/MyProject/project2.cpp",
                ],
            },
            {
                "wd": "/home/john.doe/MyProjectB",
                "line": [
                    "clang++",
                    "--driver-mode=g++",
                    "-DFEATURE=1",
                    "-o",
                    "project2-feature.o",
                    "-c",
                    "/home/john.doe/MyProject/project2.cpp",
                ],
            },
        ]
        for i in range(len(cmds)):
            self.assertEqual(cmds[i].directory, expected[i]["wd"])
            for arg, exp in zip(cmds[i].arguments, expected[i]["line"]):
                self.assertEqual(arg, exp)

    def test_compilecommand_iterator_stops(self):
        """Check that iterator stops after the correct number of elements"""
        cdb = CompilationDatabase.fromDirectory(INPUTS_DIR)
        count = 0
        for cmd in cdb.getCompileCommands("/home/john.doe/MyProject/project2.cpp"):
            count += 1
            self.assertLessEqual(count, 2)

    def test_compilationDB_references(self):
        """Ensure CompilationsCommands are independent of the database"""
        cdb = CompilationDatabase.fromDirectory(INPUTS_DIR)
        cmds = cdb.getCompileCommands("/home/john.doe/MyProject/project.cpp")
        del cdb
        gc.collect()
        cmds[0].directory

    def test_compilationCommands_references(self):
        """Ensure CompilationsCommand keeps a reference to CompilationCommands"""
        cdb = CompilationDatabase.fromDirectory(INPUTS_DIR)
        cmds = cdb.getCompileCommands("/home/john.doe/MyProject/project.cpp")
        del cdb
        cmd0 = cmds[0]
        del cmds
        gc.collect()
        cmd0.directory
