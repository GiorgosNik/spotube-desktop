import utils
from interface import interface
from downloader import downloader

if __name__ == "__main__":
    # Perform first time setup checks
    utils.first_time_setup()

    # Create and start the UI
    ui = interface()
    ui.run()