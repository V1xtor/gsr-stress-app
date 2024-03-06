import tkinter
from tkinter import ttk, StringVar
from tkinter.filedialog import askopenfilename
from client import *
from tkinter import messagebox as mb
from tkinter.scrolledtext import ScrolledText
import ctypes
import sys
import os


class GUI:

    def __init__(self, window, help_text): 
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        self.help_text = help_text
        self.str_markup = StringVar()
        self.sampling_rate = StringVar()
        self.window = window
        self.path = ''
        self.tGSR = ''
        self.markuped = 0
        self.user_mark_applied = None
        window.title("GSR Stress markup")
        window.resizable(0, 0)
        window.geometry("1200x750")
        self.value_label = ttk.Label(window)

        ttk.Button(window, text = "Select GSR File", command = lambda: self.set_path_users_field()).place(x=10,y=10) 
        ttk.Label(window, text='Enter the sampling rate of your signal: ').place(x = 10, y=41) 
        ttk.Entry(window, textvariable = self.sampling_rate, width = 7).place(x = 215, y=40) 
        # ttk.Button(window, text = "Plot GSR with labels", command = lambda: self.plot_error_window()).place(x = 120, y =40)
        ttk.Button(window, text = "Mark up the signal", command = lambda: self.markup_error_window()).place(x = 267, y =37)
        ttk.Button(window, text = "Help", command = lambda: self.help_window()).place(x = 100, y =10)
        rule_label_1 = ttk.Label(text="To use the application, you need to download a file in CSV format!", background="#FFCDD2", foreground="#B71C1C", font=("Segoe UI", 12))
        rule_label_2 = ttk.Label(text="It should contain a column that is a GSR signal with the name 'eda'!", background="#FFCDD2", foreground="#B71C1C", font=("Segoe UI", 12))
        rule_label_1.place(x=10, y=70)
        rule_label_2.place(x=10, y=95)
        self.st = ScrolledText(window, width=80, height=7)
        self.st.pack(anchor="ne")

    def help_window(self):
        help = tkinter.Toplevel(self.window, width=1000, height=330)
        help.title("Help")
        help_label = ttk.Label(help, text=self.help_text,  font=("Segoe UI", 12))
        help_label.place(x=10,y=5)
        # help.transient(help)
        help.grab_set()
        # help.focus_set()
        # help.wait_window()


    def apply_mark(self, mark):
        self.user_mark_applied = mark
        self.tGSR.viz_custom(window, correct_markup=mark)

    def submit_mark(self, mark):
        if self.user_mark_applied != None:
            self.tGSR.update_user_markup(mark)
        else:
            msg = "You didn't specify a label. Please specify label and click the apply button, then try again."
            mb.showerror("Error", msg)

    def plot_error_window(self):
        self.tGSR.viz_custom(window)
        current_value = tkinter.IntVar()
        self.value_label['text'] = str(current_value.get())
        self.value_label.place(x=145, y=710)
        ttk.Button(window, text = "Apply", command = lambda: self.apply_mark(current_value.get())).place(x=30, y =710)
        ttk.Button(window, text = "Submit label", command = lambda: self.submit_mark(self.user_mark_applied)).place(x=1100, y=710)
        slider = ttk.Scale(window,
            from_=0,
            to=self.tGSR.get_length_signal() - 1,
            orient='horizontal',
            command=lambda x: self.value_label.configure(text=str(current_value.get())),
            variable=current_value,
            length=890
        )
        slider.place(x=188, y=710)

    def markup_error_window(self):
        if self.tGSR and self.sampling_rate.get() and not self.markuped:
            self.markuped = 1
            try:
                self.tGSR.send_markup(int(self.sampling_rate.get()))
            except ConnectionRefusedError:
                msg = "The connection to the server could not be established."
                mb.showerror("Error", msg)
                return
            markup = self.tGSR.set_markup()
            self.str_markup.set(markup)
            labels = list(map(float, markup.split()))
            k = 0
            for i in range(len(labels)//2):
                self.st.insert(str(i+3)+'.0', '\nStress ' + str(i+1) + ' started at the ' + str(int(labels[i*2])//4)
                                + 'th seconds and finished at the ' + str(int(labels[i*2+1])//4) + 'th seconds.')
                k = i+1
            if len(labels) % 2 == 1:
                self.st.insert(str(k+3)+'.0', '\nStress ' + str(k+1) + ' started at the ' + str(int(labels[-1])//4) + 'th seconds.')
            self.plot_error_window()
        elif not self.tGSR:
            msg = "You have not selected a file. Please select the GSR signal file first and try again."
            mb.showerror("Error", msg)
        elif not self.sampling_rate.get():
            msg = "You have not entered a samplint rate. Please enter the samplint rate and try again."
            mb.showerror("Error", msg)
        elif self.markuped:
            msg = "You have already marked up the signal."
            mb.showwarning("Warning", msg)

    def set_path_users_field(self):
        if self.tGSR:
            self.tGSR.send_user_markup()
        self.markuped = 0
        filetypes = (
            ('csv files', '*.csv'),
            ('All files', '*.*')
        )
        self.path = askopenfilename(filetypes=filetypes, title='Open a file')
        if self.path:
            self.tGSR = TransferGSR(self.path)
            try:
                self.tGSR.open_data()
            except:
                self.tGSR = ''
                msg = "Invalid file format!"
                mb.showerror("Error", msg)
                return
            try:
                self.tGSR.send_raw_data()
            except ConnectionRefusedError:
                msg = "The connection to the server could not be established."
                mb.showerror("Error", msg)
                self.tGSR = ''
                return
            self.st.delete('1.0', tkinter.END)
            self.st.insert('2.0', 'Selected file: ' + self.get_user_path())
        else:
            msg = "You haven't selected a file. Please select the GSR signal file."
            mb.showerror("Error", msg)

    def get_user_path(self): 
        return self.path

    def on_closing(self):
        self.tGSR.send_user_markup()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


if __name__ == '__main__':
    window = tkinter.Tk()
    help_menu_path = resource_path('help_menu.txt')
    help_text = open(help_menu_path, 'r', encoding='utf-8')
    gui = GUI(window, help_text.read())
    window.mainloop()
    try:
        window.protocol("WM_DELETE_WINDOW", gui.on_closing())
    except:
        window.quit()
