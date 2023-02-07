import sys
import subprocess
import os

if __name__ == "__main__":
    if sys.platform.startswith("darwin"):
        import program_files.GUI_files.GUI as GUI
        gui = GUI.GUI()

    elif sys.platform.startswith("linux"):
        import program_files.GUI_files.GUI as GUI

        gui = GUI.GUI()
    else:
        import program_files.GUI_files.GUI as GUI

        gui = GUI.GUI()
        # subprocess.call("Scripts/python program_files/GUI_files/GUI.py")
        # command to allow streamlit run
        # subprocess.call("streamlit run {}".format(os.path.dirname(__file__) + "/GUI_streamlit.py"), shell=True)
