import src.utils as utils
from src.interface import interface
from src. downloader import downloader

if __name__ == "__main__":
    # Perform first time setup checks
    utils.first_time_setup()

    # Create and start the UI
    ui = interface()
    ui.run()