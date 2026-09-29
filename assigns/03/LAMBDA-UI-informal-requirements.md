# Stakeholder Brief: A Web-Based Environment for Testing LAMBDA

*From the course instructor to the project team*

I would like a small web-based environment that students can use to try out
programs and test the compiler for LAMBDA, the programming language we are
working with in this course. At present, trying examples involves working
directly with the language tools. I would like a more convenient way to do
this from a browser.

The main users would be students in the course. Some will be interested in
writing LAMBDA programs; others will be changing the compiler and checking
whether it still works correctly. I would also like to use the environment
in lectures. It should be easy to get started, including for someone who has
not used the compiler before.

## Trying a program

I imagine opening the page, typing or pasting a short program, and asking the
system to compile or run it. Having a few examples to start from would help.
For instance, I might select a factorial example during a lecture, change its
input, and show the new result. Students should be able to modify an example
without losing access to the original.

Sometimes I only want to check whether a program compiles. At other times,
I want to run it and see the answer. For teaching, it would also be useful to
inspect information the compiler produces, such as an abstract syntax tree
or generated code, when that information is available. I do not want all of
that detail to get in the way when someone just wants to run a simple example.

Students may already have programs saved in files, and they should not have
to retype them. They should also be able to keep a program they have written
and return to it later.

## Understanding what happened

The result should be easy to understand. If there is a mistake in the program,
I want the student to see a useful explanation. When the compiler reports where
the problem occurred, the environment should help the student find that place
in the source. A compilation error and a failure while running the program
should not look like the same thing.

The environment itself may have problems too. If it cannot reach the compiler,
I do not want students to think their program is wrong. They should be able to
keep their work and try again when the problem is resolved.

Some examples may run for a long time, and a recursive program might never
finish. There should be a way to stop it and move on. The page should remain
usable while work is in progress. If I change a program while an earlier run
is still working, I need to know which version produced the result I am seeing.

## Keeping examples as tests

Running one program at a time is useful, but I would also like students to
keep a collection of named tests. Each test would contain a program and some
record of what should happen. After changing the compiler, a student could
run the collection again to check whether anything has broken.

Some tests would expect an answer, such as an integer or a Boolean value.
Others would intentionally contain an error and expect the compiler to reject
the program. I would like a quick summary of which tests worked as expected,
with enough detail to investigate the ones that did not. One troublesome test
should not make the rest of the collection useless.

I would be frustrated if refreshing the page meant losing the examples I had
prepared. Students will also want to come back to their work in another session.
Sharing a collection of examples with the class would be useful, although I
could live without that in the first version.

## The compiler is still evolving

The LAMBDA tools are not finished. The current course interpreter works with
abstract syntax trees constructed in Python, and the notation for source
programs is still being discussed. The team developing this environment will
need to coordinate with whoever provides the compiler interface.

I would like work on the interface to proceed even before the compiler is
ready. Using sample compiler responses for a demonstration would be acceptable
at that stage, as long as nobody mistakes them for actual compilation results.
Eventually, we should be able to connect the real compiler without starting
the interface over again. Developing the compiler itself is a separate project.

## Keeping the project manageable

For the first version, running locally on a student's or instructor's computer
is enough. I am not asking for a public website, user accounts, or several
people editing the same program together. It should work in a browser students
normally use, and the setup should be straightforward enough that another
person can follow the instructions and get it running.

During lectures, I need to move between examples without spending much time
on the interface. Students should be able to perform the main tasks with a
keyboard, and messages should make sense without depending only on colors.
The environment should respond promptly to ordinary actions, even when the
compiler takes longer to finish.

Reliable editing, understandable results, and repeatable tests are more
important to me than sophisticated visual effects or features found in a full
development environment. Please tell me where choices need to be made and
which features you think should wait. I would rather agree on a useful small
version than discover late in the project that we had different expectations.
