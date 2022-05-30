import os
import json
import logging
import typing as t

logger = logging.getLogger(__name__)
script = None

import multiprocessing
import time

def _compileScript():
    """
    Compiles the JXA script and caches the result.

    Resources:
     - https://stackoverflow.com/questions/44209057/how-can-i-run-jxa-from-swift
     - https://stackoverflow.com/questions/16065162/calling-applescript-from-python-without-using-osascript-or-appscript
    """

    # use a global variable to cache the compiled script for performance
    global script
    if script:
        return script

    logger.debug("compiling and caching script")

    from OSAKit import OSAScript, OSALanguage

    scriptPath = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "printAppStatus.jxa"
    )

    with open(scriptPath) as f:
        scriptContents = f.read()

        # # remove shebang line
        # if scriptContents.split("\n")[0].startswith("#"):
        #     scriptContents = "\n".join(scriptContents.split("\n")[1:])

    script = OSAScript.alloc().initWithSource_language_(
        scriptContents, OSALanguage.languageForName_("JavaScript")
    )
    success, err = script.compileAndReturnError_(None)

    # should only occur if jxa was modified incorrectly
    if not success:
        raise Exception(f"error compiling jxa script: {err['NSLocalizedDescription']}")

    return script

def wrapped_function(condition, result_queue: multiprocessing.Queue, function_reference: t.Callable) -> None:
    # this is run in a forked process, which wipes all logging configuration
    from aw_core.log import setup_logging
    setup_logging(
        name="aw-watcher-window-worker",
        # TODO can we extract these from the previous logger and pass them through?
        # testing=args.testing,
        # verbose=args.verbose,
        log_stderr=True,
        log_file=True,
    )

    first_run = True

    while True:
        with condition:
            # notify parent process that we are ready to wait for notifications
            if first_run:
                condition.notify()
                first_run = False

            condition.wait()

        try:
            logger.debug("running operation in fork")
            result_queue.put(function_reference())
        except Exception as e:
            logger.exception("error running function in fork")
            result_queue.put(None)

forked_condition = None
forked_result_queue = None
forked_process = None
forked_time = None

def _run_in_forked_process(function_reference):
    global forked_condition, forked_result_queue, forked_process, forked_time

    # terminate the process after 10m
    if forked_time and time.time() - forked_time > 60 * 10:
        assert forked_process
        logger.debug("killing forked process, 10 minutes have passed")
        forked_process.kill()
        forked_process = None

    if not forked_process:
        forked_condition = multiprocessing.Condition()

        forked_result_queue = multiprocessing.Queue()
        forked_process = multiprocessing.Process(
            target=wrapped_function,
            args=(forked_condition, forked_result_queue, function_reference)
        )
        forked_process.start()

        forked_time = time.time()

        # wait until fork is ready, if this isn't done the process seems to miss the
        # the parent process `notify()` call. My guess is `wait()` needs to be called before `notify()`
        with forked_condition:
            logger.debug("waiting for child process to indicate readiness")
            forked_condition.wait()

    # if forked_process is defined, forked_condition always should be as well
    assert forked_condition and forked_result_queue

    # signal to the process to run `getInfo` again and put the result on the queue
    with forked_condition:
        forked_condition.notify()

    logger.debug("waiting for result of child process")

    return forked_result_queue.get(block=True)

# for simple benchmarking of the `getInfo()` function
def timer_func(func):
    def function_timer(*args, **kwargs):
        start = time.time()
        value = func(*args, **kwargs)
        end = time.time()
        runtime = end - start
        msg = "{func} took {time} seconds to complete its execution."
        print(msg.format(func = func.__name__,time = runtime))
        return value

    return function_timer

# unfortunately, it's well-documented that applescript leaks memory like crazy:
#
# - https://macscripter.net/viewtopic.php?id=41564
# - https://github.com/Hammerspoon/hammerspoon/issues/1980
#
# It's not designed to be executed over and over by the same process. In our case, this
# resulted in massive memory usage over time. To work around this, we fork a process
# to run our applescript and kill it every so often to clean out it's memory usage.

@timer_func
def getInfo() -> t.Dict[str, str]:
    _compileScript()
    return _run_in_forked_process(_getInfo)

def _getInfo() -> t.Dict[str, str]:
    script = _compileScript()

    result, err = script.executeAndReturnError_(None)

    if err:
        # error structure:
        # {
        #     NSLocalizedDescription = "Error: Error: Can't get object.";
        #     NSLocalizedFailureReason = "Error: Error: Can't get object.";
        #     OSAScriptErrorBriefMessageKey = "Error: Error: Can't get object.";
        #     OSAScriptErrorMessageKey = "Error: Error: Can't get object.";
        #     OSAScriptErrorNumberKey = "-1728";
        #     OSAScriptErrorRangeKey = "NSRange: {0, 0}";
        # }

        # TODO debug `python is not allowed assistive access.`
        logger.debug(err)

        raise Exception(f"jxa error: {err['NSLocalizedDescription']}")

    return json.loads(result.stringValue())


# run this file directly to manually debug AS/JXA error
# note that logging configuration and other setup is not done
if __name__ == "__main__":
    print(getInfo())
    print("Waiting 5 seconds...")

    time.sleep(5)

    print(getInfo())
