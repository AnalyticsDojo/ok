import random
import readline
from grading import TestCaseAnswer
from utils import underline, maybe_strip_prompt, OkConsole

#######################
# UNLOCKING MECHANISM #
#######################

# TODO(albert): move this to locking mechanism
# def __make_hash_fn(hash_key, encoding='utf-8'):
#     def hash_fn(x):
#         return hmac.new(hash_key.encode(encoding),
#                         x.encode(encoding)).digest()
#     return hash_fn
#
# hash_key = tests['project_info']['hash_key']
# __make_hash_fn(hash_key)

def unlock(test, console):
    """Unlocks TestCases for a given Test.

    PARAMETERS:
    test    -- Test; the test to unlock.
    console -- UnlockConsole; a console for handling interactive
               unlocking sessions.

    DESCRIPTION:
    This function incrementally unlocks all TestCases in a specified
    Test. Students must answer in the order that TestCases are
    written. Once a TestCase is unlocked, it will remain unlocked.

    RETURN:
    int; the number of cases that are newly unlocked for this Test
    after going through an unlocking session.
    """
    # TODO(albert): move printing outside of this function
    if not test.suites:
        print('No tests to unlock for {}.'.format(test.name))
        return 0

    underline('Unlocking tests for {}'.format(test.name))
    print('At each "{}", type in what you would expect the output to '
          'be if you had implemented {}'.format(UnlockConsole.PROMPT,
                                                test.name))
    print('Type {} to quit'.format(UnlockConsole.EXIT_INPUTS[0]))
    print()

    cases = 0
    cases_unlocked = 0
    for suite in test.suites:
        for case in suite:
            cases += 1
            if not case.is_locked:
                continue
            underline('Case {}'.format(cases), line='-')
            if console.run(case):   # Abort unlocking.
                return cases_unlocked
            cases_unlocked += 1
    print("You are done unlocking tests for this question!")
    return cases_unlocked

class _UnlockException(BaseException):
    pass

class UnlockConsole(OkConsole):
    """Handles an interactive session for unlocking a TestCase.

    An instance of this class can be (and should be) reused for
    multiple TestCases. This class keeps an output log that is
    registered with the OutputLogger class, but is currently not
    used.

    The verification function that is passed into the constructor is
    used to verify whether or not a student's attempt to unlock a
    TestCase is correct. This function can be any arbitrary funcion
    that takes two arguments -- (1) the student input, and (2) the
    locked version of the correct TestCaseAnswer.
    """
    PROMPT = '? '       # Prompt that is used for user input.
    EXIT_INPUTS = (     # Valid user inputs for aborting the session.
        'exit()',
        'quit()',
    )
    PS1 = '>>> '
    PS2 = '... '

    def __init__(self, logger, verification_fn):
        """Constructor.

        PARAMETERS:
        logger          -- OutputLogger
        verification_fn -- function; takes as arguments
                           (student_input, locked_answer) and verifies
                           that the student_input matches the
                           locked_answer.
        """
        super().__init__(logger)
        self.verify = verification_fn

    ##################
    # Public methods #
    ##################

    def run(self, case):
        """Runs an interactive session for unlocking a single TestCase.

        PARAMETERS:
        case -- TestCase

        DESCRIPTION:
        Upon successful completion, the provided TestCase will be
        modified to contain the unlocked TestCaseAnswer, and the
        TestCase will be marked as unlocked. If the user aborts before
        successful completion, the TestCase will left untouched.

        RETURNS:
        bool; True if an error/abort occurs, False if the TestCase is
        unlocked successfully.
        """
        self._activate_logger()

        try:
            if not case.is_conceptual:
                answers = self.__run_code(case)
            else:
                answers = self.__run_concept(case)
        except _UnlockException:
            print('\nExiting unlocker...')
            return True
        else:
            case.set_outputs(answers)
            case.unlock()
            print("-- Congratulations, you unlocked this case! --")
            print()
            return False
        finally:
            self._deactivate_logger()

    #######################
    # Visible for testing #
    #######################

    def _input(self, prompt):
        """Retrieves user input from stdin."""
        return input(prompt)

    def _display_choices(self, choices):
        """Prints a mapping of numbers to choices and returns the
        mapping as a dictionary.
        """
        print("Choose the number of the correct choice:")
        choice_map = {}
        for i, choice in enumerate(random.sample(choices, len(choices))):
            i = str(i)
            print(i + ') ' + choice)
            choice_map[i] = choice
        return choice_map

    ###################
    # Private methods #
    ###################

    def __run_code(self, case):
        """Runs an unlocking session for a code TestCase."""
        outputs = iter(case.outputs)
        answers = []
        for line in case.lines:
            if line.startswith(' '):  # Line is indented.
                print(self.PS2 + line)
                continue
            print(self.PS1 + maybe_strip_prompt(line))
            if line.startswith('$ '):
                answer = self.__interact(next(outputs))
                answers.append(TestCaseAnswer(answer))
        return answers

    def __run_concept(self, case):
        """Runs an unlocking session for a conceptual TestCase."""
        print('\n'.join(case.lines))
        answer = self.__interact(case.outputs[0])
        return [TestCaseAnswer(answer)]

    def __interact(self, output):
        """Reads student input for unlocking tests until the student
        answers correctly.

        PARAMETERS:
        output  -- TestCaseAnswer; a locked test case answer.

        DESCRIPTION:
        Continually prompt the student for an answer to an unlocking
        question until one of the folliwng happens:

            1. The student supplies the correct answer, in which case
               the supplied answer is returned
            2. The student aborts abnormally (either by typing 'exit()'
               or using Ctrl-C/D. In this case, return None

        Correctness is determined by the verification function passed
        into the constructor. The verification function returns True
        if the student answer matches the locked answer. The student's
        answer is then used as the new TestCaseAnswer of the TestCase.

        RETURNS:
        str  -- the correct solution (that the student supplied)
        """
        correct = False
        while not correct:
            if output.choices:
                choice_map = self._display_choices(output.choices)

            try:
                student_input = self._input(self.PROMPT)
            except (KeyboardInterrupt, EOFError):
                try:
                    # TODO(albert): When you use Ctrl+C in Windows, it
                    # throws two exceptions, so you need to catch both
                    # of them. Find a cleaner fix for this.
                    print()
                except (KeyboardInterrupt, EOFError):
                    pass
                raise _UnlockException
            if student_input in self.EXIT_INPUTS:
                raise _UnlockException

            self.__add_line_to_history(student_input)

            if output.choices:
                student_input = choice_map[student_input]
            correct = self.verify(student_input, output.answer)
            if not correct:
                print("-- Not quite. Try again! --")
        return student_input

    @staticmethod
    def __add_line_to_history(line):
        """Adds the given line to readline history, only if the line
        is non-empty.
        """
        if line:
            readline.add_history(line)
