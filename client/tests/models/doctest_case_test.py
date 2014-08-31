"""Tests the DoctestCase model."""

from models import core
from models import doctest_case
from unittest import mock
from utils import utils
import exceptions
import ok
import sys
import unittest

class OnGradeTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'

    def setUp(self):
        # This logger captures output and is used by the unittest,
        # it is wired to stdout.
        self.log = []
        self.capture = sys.stdout = utils.OutputLogger()
        self.capture.register_log(self.log)
        self.capture.on = mock.Mock()
        self.capture.off = mock.Mock()

        # This logger is used by on_grade.
        self.logger = utils.OutputLogger()

        self.assignment = core.Assignment.deserialize({
            'name': self.ASSIGN_NAME,
            'version': '1.0',
        })
        self.test = core.Test.deserialize({
            'names': ['q1'],
            'points': 1,
        }, self.assignment, {})

    def tearDown(self):
        self.stdout = sys.__stdout__

    def makeTestCase(self, case_json):
        case_json['type'] = doctest_case.DoctestCase.type
        if 'locked' not in case_json:
            case_json['locked'] = False
        return doctest_case.DoctestCase.deserialize(case_json,
                self.assignment, self.test)

    def calls_onGrade(self, case_json, errors=False, verbose=False,
            interact=False):
        case = self.makeTestCase(case_json)
        error = case.on_grade(self.logger, verbose, interact)
        if errors:
            self.assertTrue(error)
        else:
            self.assertFalse(error)

    def assertCorrectLog(self, expected_log):
        expected_log = '\n'.join(expected_log).strip('\n')
        log = ''.join(self.capture.log).strip('\n')
        self.assertEqual(expected_log, log)

    def testPass_equals(self):
        self.calls_onGrade({
            'test': """
            >>> 3 + 4
            7
            """,
        })

    def testPass_expectException(self):
        self.calls_onGrade({
            'test': """
            >>> 1 / 0
            ZeroDivisionError
            """,
        })

    def testPass_multilineSinglePrompt(self):
        self.calls_onGrade({
            'test': """
            >>> x = 5
            >>> x + 4
            9
            """,
        })

    def testPass_multiplePrompts(self):
        self.calls_onGrade({
            'test': """
            >>> x = 5
            >>> x + 4
            9
            >>> 1 / 0
            ZeroDivisionError
            """,
        })

    def testPass_multilineWithIndentation(self):
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(4)
            16
            """,
        })

    def testPass_teardown(self):
        # TODO(albert)
        pass

    def testError_notEqualError(self):
        self.calls_onGrade({
            'test': """
            >>> 2 + 4
            7
            """,
        }, errors=True)

    def testError_expectedException(self):
        self.calls_onGrade({
            'test': """
            >>> 1 + 2
            ZeroDivisionError
            """,
        }, errors=True)

    def testError_wrongException(self):
        self.calls_onGrade({
            'test': """
            >>> 1 / 0
            TypeError
            """,
        }, errors=True)

    def testError_runtimeError(self):
        self.calls_onGrade({
            'test': """
            >>> f = lambda: f()
            >>> f()
            4
            """,
        }, errors=True)

    def testError_timeoutError(self):
        # TODO(albert): test timeout errors without actually waiting
        # for timeouts.
        pass

    def testError_teardown(self):
        # TODO(albert):
        pass

    def testOutput_singleLine(self):
        self.calls_onGrade({
            'test': """
            >>> 1 + 2
            3
            """
        })
        self.assertCorrectLog([
            '>>> 1 + 2',
            '3'
        ])

    def testOutput_multiLineIndentNoNewline(self):
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(4)
            16
            """,
        })
        self.assertCorrectLog([
            '>>> def square(x):',
            '...     return x * x',
            '>>> square(4)',
            '16',
        ])

    def testOutput_multiLineIndentWithNewLine(self):
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x

            >>> square(4)
            16
            """,
        })
        self.assertCorrectLog([
            '>>> def square(x):',
            '...     return x * x',
            '>>> square(4)',
            '16',
        ])

    def testOutput_forLoop(self):
        self.calls_onGrade({
            'test': """
            >>> for i in range(3):
            ...     print(i)
            >>> 3 + 4
            7
            """
        })
        self.assertCorrectLog([
            '>>> for i in range(3):',
            '...     print(i)',
            '0',
            '1',
            '2',
            '>>> 3 + 4',
            '7',
        ])

    def testOutput_errorNotEqual(self):
        self.calls_onGrade({
            'test': """
            >>> 3 + 4
            1
            """,
        }, errors=True)
        self.assertCorrectLog([
            '>>> 3 + 4',
            '7',
            '# Error: expected 1 got 7'
        ])

    def testOutput_errorOnNonPrompt(self):
        self.calls_onGrade({
            'test': """
            >>> x = 1 / 0
            >>> 3 + 4
            7
            """,
        }, errors=True)
        self.assertCorrectLog([
            '>>> 1 / 0',
            'ZeroDivisionError: division by zero'
        ])

    def testOutput_errorOnPromptWithException(self):
        self.calls_onGrade({
            'test': """
            >>> 1/ 0
            1
            """,
        }, errors=True)
        self.assertCorrectLog([
            '>>> 1 / 0',
            'ZeroDivisionError: division by zero',
            '# Error: expected 1 got ZeroDivisionError'
        ])

class OnUnlockTest(unittest.TestCase):
    # TODO(albert):
    pass

class SerializationTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'

    def setUp(self):
        self.assignment = core.Assignment.deserialize({
            'name': self.ASSIGN_NAME,
            'version': '1.0',
        })
        self.test = core.Test.deserialize({
            'names': ['q1'],
            'points': 1,
        }, self.assignment, {})

    def assertSerialize(self, json):
        case = doctest_case.DoctestCase.deserialize(
                json, self.assignment, self.test)
        self.assertEqual(json, case.serialize())

    def testIncorrectType(self):
        case_json = {'type': 'foo'}
        self.assertRaises(exceptions.DeserializeError,
                          doctest_case.DoctestCase.deserialize,
                          case_json, self.assignment, self.test)

    def testSimplePrompt(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            """),
        })

    def testExplanation(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            # explanation: Squares a negative number
            """),
        })

    def testMultipleChoice(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            # choice: 0
            # choice: 2
            # choice: -4
            """),
        })

    def testLocked(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            5
            # locked
            """),
        })

    def testMultiplePrompts(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            >>> x = 4
            >>> square(x)
            16
            """),
        })
