import socket
import pandas as pd
import pickle
from kernel import *

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# HOST = (socket.gethostname(), 4000)
HOST = ('213.178.155.64', 4000)


class TransferGSR():
    def __init__(self, filename):
        self.data = []
        self.filename = filename
        self.gsr = ''
        self.user_markup_x = []
    
    def connect_to_server(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(HOST)
        print('Connected to', HOST)
        return client

    def open_data(self):
        eda_df = pd.read_csv(self.filename)
        eda_signal = eda_df['eda']
        return list(eda_signal)

    def send_raw_data(self):
        client = self.connect_to_server()

        self.data = np.array(self.open_data())
        data_dict = {'header': 'raw_data', 'data': self.data}
        data_bytes = pickle.dumps(data_dict)
        client.send(data_bytes)

    def send_markup(self, s_rate):
        client = self.connect_to_server()

        self.gsr = gsrHandler('filtered gsr', self.data, s_rate)
        self.gsr.sax_preprocessing()
        self.gsr.adwin()
        self.gsr.convert_markup()
        data_dict = {'header': 'markup', 'data': self.gsr.x_stress, 'sample_rate': s_rate}
        data_bytes = pickle.dumps(data_dict)
        client.send(data_bytes)
    
    def update_user_markup(self, x):
        if self.user_markup_x:
            if x != self.user_markup_x[-1]:
                self.user_markup_x.append(x)
        else:
            self.user_markup_x.append(x)
    
    def send_user_markup(self):
        client = self.connect_to_server()

        data_dict = {'header': 'user_markup', 'data': self.user_markup_x}
        data_bytes = pickle.dumps(data_dict)
        client.send(data_bytes)

    def viz_custom(self, root, correct_markup=None):
        if self.gsr:
            figure = Figure(figsize=(15, 7), dpi=82)
            plot = figure.add_subplot(1, 1, 1)
            faceclr = "#003366"
            figure.set_facecolor(faceclr)
            plot.set_facecolor(faceclr)
            plot_clr = "#FFFFFF"
            csfont = {'fontname': 'Segoe UI'}
            title_clr = "#F0E68C"

            plot.set_title('Marked up GSR signal', **csfont, color=title_clr, fontsize=16)

            plot.set_facecolor(faceclr)
            plot.set_xlabel('t', **csfont, color='#FFFFFF', fontsize=13)
            plot.spines['bottom'].set_color('#FFFFFF')
            plot.spines['top'].set_color('#FFFFFF')
            plot.spines['left'].set_color('#FFFFFF')
            plot.spines['right'].set_color('#FFFFFF')
            plot.tick_params(axis='x', colors='#FFFFFF')
            plot.tick_params(axis='y', colors='#FFFFFF')
            # remove spines
            plot.spines['right'].set_visible(False)
            plot.spines['top'].set_visible(False)
            # grid
            plot.set_axisbelow(True)
            plot.yaxis.grid(color='#FFFFFF', linestyle='dashed', alpha=0.3)
            plot.xaxis.grid(color='#FFFFFF', linestyle='dashed', alpha=0.3)

            plot.plot(self.gsr.bio2_signal_f, color=plot_clr, label='Filtered gsr')
            x_onsets = []
            y_onsets = []
            x_ends = []
            y_ends = []
            for i in range(len(self.gsr.x_stress)):
                if i % 2 == 0:
                    x_onsets.append(self.gsr.x_stress[i])
                    y_onsets.append(self.gsr.y_stress[i])
                else:
                    x_ends.append(self.gsr.x_stress[i])
                    y_ends.append(self.gsr.y_stress[i])
            plot.plot(x_onsets, y_onsets, color="#fa5711", marker="o", markersize=8, linestyle="", label='Onsets of stress')
            plot.plot(x_ends, y_ends, color="#15fa11", marker="o", markersize=8, linestyle="", label='Ends of stress')
            user_markup_x = []
            if correct_markup != None:
                user_markup_x.append(correct_markup)
                user_markup_x.extend(self.user_markup_x)
            if user_markup_x:
                user_markup_y = []
                for x in user_markup_x:
                    user_markup_y.append(self.gsr.bio2_signal_f[x])
                plot.plot(user_markup_x, user_markup_y, color="#c72020", marker="o", markersize=8, linestyle="", label='Your markup')
            legend = plot.legend(fontsize=14, shadow=True, frameon=False)
            legend.get_frame().set_facecolor(faceclr)
            for t in legend.get_texts():
                t.set_color(title_clr)
                t.set_fontfamily(**csfont)
            canvas = FigureCanvasTkAgg(figure, root)
            canvas.get_tk_widget().place(x = 0, y = 127)

        else:
            figure = Figure(figsize=(15, 7), dpi=82)
            plot = figure.add_subplot(1, 1, 1)
            faceclr = "#003366"
            figure.set_facecolor(faceclr)
            plot.set_facecolor(faceclr)
            plot_clr = "#FFFFFF"
            csfont = {'fontname': 'Segoe UI'}
            title_clr = "#F0E68C"
            plot.set_title("You haven't done the markup yet. Click the «Mark up the signal» button and try again", **csfont, color=title_clr, fontsize=16)
            plot.set_facecolor(faceclr)
            plot.set_xlabel('t', **csfont, color='#FFFFFF', fontsize=13)
            plot.spines['bottom'].set_color('#FFFFFF')
            plot.spines['top'].set_color('#FFFFFF')
            plot.spines['left'].set_color('#FFFFFF')
            plot.spines['right'].set_color('#FFFFFF')
            plot.tick_params(axis='x', colors='#FFFFFF')
            plot.tick_params(axis='y', colors='#FFFFFF')
            # remove spines
            plot.spines['right'].set_visible(False)
            plot.spines['top'].set_visible(False)
            # grid
            plot.set_axisbelow(True)
            plot.yaxis.grid(color='#FFFFFF', linestyle='dashed', alpha=0.3)
            plot.xaxis.grid(color='#FFFFFF', linestyle='dashed', alpha=0.3)

            canvas = FigureCanvasTkAgg(figure, root)
            canvas.get_tk_widget().place(x = 0, y = 127)
    
    def viz(self, root):
        figure = Figure(figsize=(15, 7), dpi=82)
        plot = figure.add_subplot(1, 1, 1)

        plot.plot(self.gsr.bio2_signal_f, color="blue")
        plot.plot(self.gsr.x_stress, self.gsr.y_stress, color="red", marker="o", linestyle="")

        canvas = FigureCanvasTkAgg(figure, root)
        canvas.get_tk_widget().grid(row=2, columnspan=3)

    def set_markup(self):
        sample_to_write = [str(x) for x in self.gsr.x_stress]
        sample_to_write = ' '.join(sample_to_write)
        return sample_to_write
    
    def get_length_signal(self):
        return len(self.gsr.bio2_signal_f)
