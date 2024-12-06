import time
import pytest
import logging

mylogger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)

def test_example_test():
    for x in range(10):
        print(f"This is an example test! Log:{str(x)} ✅")
        time.sleep(0.1)
        mylogger.debug("😅😅😅" + str(x))
        mylogger.info("👹👹👹" + str(x))