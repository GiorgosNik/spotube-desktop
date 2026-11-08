import os
import sys

from src import app_support


def self_test():
    from spotube import exportify

    import src.ui_interface  # noqa: F401

    checks = {
        "cover image bundled": os.path.isfile(app_support.resource_path("images", "cover_art.jpg")),
        "ffmpeg available": app_support.setup_ffmpeg(),
        "exportify available": exportify.is_available(),
    }
    for name, passed in checks.items():
        print(f"{'ok' if passed else 'FAILED'}: {name}")
    return 0 if all(checks.values()) else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--self-test" in argv:
        return self_test()
    from src.ui_interface import ui_interface

    ui_interface().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
