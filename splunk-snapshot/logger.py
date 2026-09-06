import logging

# module:funcName locates a line without a full traceback -- btool:extract says
# more than [extract] once two modules define similarly named helpers. levelname
# is padded to the width of WARNING so the message column stays aligned.
FORMAT = "[%(asctime)s] [%(levelname)s] [%(module)s:%(funcName)s]  %(message)s"
DATEFMT = "%H:%M:%S"


def setup(verbose=False):
    """Configure logging for the whole program.

    Call once, from main(), before dispatch -- never at import time and never
    from a library module, otherwise two modules race to own the root handler.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=FORMAT,
        datefmt=DATEFMT,
    )


def get_logger(name):
    """Logger for one module. Pass __name__.

    No level is set here on purpose -- a fresh logger sits at NOTSET and
    delegates to root, so setup()'s verbose flag governs every module.
    """
    return logging.getLogger(name)
