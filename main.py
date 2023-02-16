import src.utils as utils
from src.ui_interface import ui_interface
from src. downloader import downloader

if __name__ == "__main__":
    # Perform first time setup checks
    utils.first_time_setup()

    # Create and start the UI
    ui = ui_interface()
    ui.run()