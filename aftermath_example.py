"""Example: crash on purpose and write a dump under the 'debug' folder."""

from aftermath import Aftermath


def sub_test():
    x = 2  # noqa: F841 - captured in the dump
    raise ValueError("boom")


@Aftermath.guard("debug")
def test():
    y = 2  # noqa: F841
    sub_test()


if __name__ == "__main__":
    test()
