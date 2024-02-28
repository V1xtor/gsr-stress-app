import numpy as np
import scipy
from tslearn.preprocessing import TimeSeriesScalerMeanVariance
from tslearn.piecewise import SymbolicAggregateApproximation
import plotly.graph_objects as go


class gsrHandler:

    def __init__(self, sub_name, bio2_signal, sampling_rate, shift_const=0.5):
        self.sub_name = sub_name

        # Resampling to 4 Hz
        bio2_signal_resampled = []
        for j in range(0, len(bio2_signal), sampling_rate // 4):
            bio2_signal_resampled.append(bio2_signal[j])

        self.bio2_signal = bio2_signal_resampled
        self.bio2_signal_f = []
        self.sampling_rate = sampling_rate
        self.aggregate_period = 60 * 4
        self.shift_const = shift_const
        self.sax_data = []
        self.x_stress_sax = []  # все точки изменения
        self.y_stress_sax = []
        self.x_stress_concat = []  # все точки изменения, кроме «начал» и «концов», которые находятся на близком расстоянии друг от друга
        self.y_stress_concat = []
        self.x_stress = []  # итоговая разметка из x_stress_sax
        self.y_stress = []
        self.x_stress_full = []  # итоговая разметка из x_stress_concat
        self.y_stress_full = []
        self.signal_var = 0

    def sax_preprocessing(self):
        # Filter the data, and plot both the original and filtered signals.
        self.bio2_signal_f = scipy.signal.medfilt(self.bio2_signal, 101)

        self.signal_var = np.var(np.array(self.bio2_signal_f))

        # Aggregate
        bio2_signal_fg = []
        for j in range(0, len(self.bio2_signal_f), self.aggregate_period):
            bio2_signal_fg.append(
                sum(self.bio2_signal_f[j:j + self.aggregate_period]) / len(self.bio2_signal_f[j:j + self.aggregate_period]))

        # SAX
        bio2_signal_fg = np.array(bio2_signal_fg)
        bio2_signal_fg_rs = bio2_signal_fg.reshape(1, len(bio2_signal_fg))
        scaler = TimeSeriesScalerMeanVariance(mu=0., std=1.)
        bio2_signal_fg_norm = scaler.fit_transform(bio2_signal_fg_rs)
        sax = SymbolicAggregateApproximation(n_segments=len(bio2_signal_fg), alphabet_size_avg=5)
        sax_dataset = sax.fit_transform(bio2_signal_fg_norm)

        self.sax_data = list(sax_dataset[0].ravel())

    def adwin(self):
        adwin_list = []

        delta = 0.002

        stress = False

        for i, val in enumerate(self.sax_data):
            adwin_list.append(val)
            w0 = []
            w1 = []
            n = len(adwin_list)
            for j in range(len(adwin_list) - 1):
                n0 = j + 1  # длина одной подпоследовательности
                n1 = n - (j + 1)  # длина второй подпоследовательности
                m = 1 / ((1 / n0) + (1 / n1))  # harmonic mean
                w0 = adwin_list[:(j + 1)]  # первая подпоследовательность
                w1 = adwin_list[(j + 1):]  # вторая подпоследовательность
                mean_w0 = np.array(w0).mean()  # среднее значение первой подпоследовательности
                mean_w1 = np.array(w1).mean()  # среднее значение второй подпоследовательности
                if self.signal_var >= 0.01:
                    eps_cut = np.sqrt((1 / (2 * m)) * np.log((4 * n) / delta))  # threshold
                else:
                    eps_cut = np.sqrt(
                        (2 / m) * ((np.array(adwin_list).var()) ** 2) * np.log((2 * np.log(n)) / delta)) + (
                                      2 / (3 * m)) * np.log((2 * np.log(n)) / delta)

                # если пройден порог на повышение
                if abs(mean_w0 - mean_w1) >= eps_cut and not stress and mean_w0 - mean_w1 < 0:
                    stress = True
                    adwin_list = w1

                    print(f"Change detected at SAX index {i}")
                    self.x_stress_sax.append(i - len(w1))
                    self.y_stress_sax.append(self.sax_data[i - len(w1)])
                    break
                # если пройден порог на понижение
                elif abs(mean_w0 - mean_w1) >= eps_cut and stress and mean_w0 - mean_w1 > 0:
                    stress = False
                    adwin_list = w1

                    print(f"Change detected at SAX index {i}")
                    self.x_stress_sax.append(i)
                    self.y_stress_sax.append(val)
                # если пройден порог на понижение, но уже ставили метку конца стресса, но сигнал стал ещё ниже
                elif abs(mean_w0 - mean_w1) >= eps_cut and not stress and mean_w0 - mean_w1 > 0 and self.x_stress_sax:
                    stress = False
                    adwin_list = w1

                    print(f"Change detected at SAX index {i}")
                    self.x_stress_sax[-1] = i
                    self.y_stress_sax[-1] = val
                # если пройден порог на понижение, но до этого стресса «не было» — значит сигнал начался со стресса
                elif abs(mean_w0 - mean_w1) >= eps_cut and not stress and mean_w0 - mean_w1 > 0:
                    stress = False
                    adwin_list = w1

                    self.x_stress_sax.append(0)
                    self.y_stress_sax.append(self.sax_data[0])
                    print(f"Change detected at SAX index {i}")
                    self.x_stress_sax.append(i)
                    self.y_stress_sax.append(val)

        # объединение стрессов, если пауза между ними не больше 2-х минут
        if self.x_stress_sax:
            self.x_stress_concat = [self.x_stress_sax[0]]
            self.y_stress_concat = [self.y_stress_sax[0]]
            for i, x in enumerate(self.x_stress_sax[2:]):
                if abs(x - self.x_stress_sax[i + 1]) > 2 and i % 2 == 0:
                    self.x_stress_concat.append(self.x_stress_sax[i + 1])
                    self.x_stress_concat.append(x)
                    self.y_stress_concat.append(self.y_stress_sax[i + 1])
                    self.y_stress_concat.append(self.y_stress_sax[i + 2])
        else:
            self.x_stress_concat = self.x_stress_sax
            self.x_stress_concat = self.y_stress_sax

        if len(self.x_stress_sax) % 2 == 0 and self.x_stress_sax:
            self.x_stress_concat.append(self.x_stress_sax[-1])
            self.y_stress_concat.append(self.y_stress_sax[-1])

    def convert_markup(self):
        bio2_signal_f = scipy.signal.medfilt(self.bio2_signal, 101)
        for i, x in enumerate(self.x_stress_concat):
            if (x + 1) * self.aggregate_period < len(bio2_signal_f) and x != 0:
                self.x_stress.append((x + self.shift_const) * self.aggregate_period)
                self.y_stress.append(bio2_signal_f[int((x + self.shift_const) * self.aggregate_period)])
            elif x == 0:
                self.x_stress.append((x) * self.aggregate_period)
                self.y_stress.append(bio2_signal_f[(x) * self.aggregate_period])
            else:
                self.x_stress.append(len(bio2_signal_f) - 1)
                self.y_stress.append(bio2_signal_f[-1])

            # проверяем, нет ли впереди ямки
            if (x + 1) * self.aggregate_period < len(bio2_signal_f) and x != 0:
                list_for_check = list(
                    bio2_signal_f[int((x + 0.5) * self.aggregate_period):(x + 2) * self.aggregate_period])
                potential_extremum = min(list_for_check)
                if potential_extremum <= bio2_signal_f[int((x + self.shift_const) * self.aggregate_period)]:
                    self.x_stress[-1] += len(list_for_check) - 1 - list_for_check[::-1].index(potential_extremum)
                    self.y_stress[-1] = bio2_signal_f[int(self.x_stress[-1])]

            # проверяем, нет ли сзади ямки
            if (x + 1) * self.aggregate_period < len(bio2_signal_f) and x != 0:
                list_for_check = list(
                    bio2_signal_f[(x - 1) * self.aggregate_period:int((x + 0.5) * self.aggregate_period)])
                potential_extremum = min(list_for_check)
                if potential_extremum <= self.y_stress[-1]:
                    self.x_stress[-1] = int((x + self.shift_const) * self.aggregate_period) - (
                            list_for_check[::-1].index(potential_extremum) + 1)
                    self.y_stress[-1] = bio2_signal_f[int(self.x_stress[-1])]

        for i, x in enumerate(self.x_stress_sax):
            if (x + 1) * self.aggregate_period < len(bio2_signal_f) and x != 0:
                self.x_stress_full.append((x + self.shift_const) * self.aggregate_period)
                self.y_stress_full.append(bio2_signal_f[int((x + self.shift_const) * self.aggregate_period)])
            elif x == 0:
                self.x_stress_full.append((x) * self.aggregate_period)
                self.y_stress_full.append(bio2_signal_f[(x) * self.aggregate_period])
            else:
                self.x_stress_full.append(len(bio2_signal_f) - 1)
                self.y_stress_full.append(bio2_signal_f[-1])

            # проверяем, нет ли впереди ямки
            if (x + 1) * self.aggregate_period < len(bio2_signal_f) and x != 0:
                list_for_check = list(bio2_signal_f[int((x + 0.5) * self.aggregate_period):(x + 2) * self.aggregate_period])
            # if list_for_check:
                potential_extremum = min(list_for_check)
                if (x + 1) * self.aggregate_period < len(bio2_signal_f) and x != 0:
                    if potential_extremum <= bio2_signal_f[int((x + self.shift_const) * self.aggregate_period)]:
                        self.x_stress_full[-1] += len(list_for_check) - 1 - list_for_check[::-1].index(potential_extremum)
                        self.y_stress_full[-1] = bio2_signal_f[int(self.x_stress_full[-1])]

            # проверяем, нет ли сзади ямки
            if (x + 1) * self.aggregate_period < len(bio2_signal_f) and x != 0:
                list_for_check = list(
                    bio2_signal_f[(x - 1) * self.aggregate_period:int((x + 0.5) * self.aggregate_period)])
                potential_extremum = min(list_for_check)
                if potential_extremum <= self.y_stress_full[-1]:
                    self.x_stress_full[-1] = int((x + self.shift_const) * self.aggregate_period) - (
                            list_for_check[::-1].index(potential_extremum) + 1)
                    self.y_stress_full[-1] = bio2_signal_f[int(self.x_stress_full[-1])]

    def sax_viz(self):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=self.sax_data,
            line=dict(shape='spline'),
            name=self.sub_name
        ))
        fig.add_trace(go.Scatter(
            x=self.x_stress_sax,
            y=self.y_stress_sax,
            mode='markers',
            marker_size=10,
            name='change points'
        ))
        fig.show()

    def orig_viz(self):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=self.bio2_signal_f,
            line=dict(shape='spline'),
            name=self.sub_name,
        ))
        fig.add_trace(go.Scatter(
            x=self.x_stress,
            y=self.y_stress,
            mode='markers',
            marker_color='red',
            marker_size=10,
            name='change points',
        ))
        x_stress_only_concat = []
        y_stress_only_concat = []
        for i, x in enumerate(self.x_stress_full):
            if x not in self.x_stress:
                x_stress_only_concat.append(x)
                y_stress_only_concat.append(self.bio2_signal_f[int(x)])
        if x_stress_only_concat:
            fig.add_trace(go.Scatter(
                x=x_stress_only_concat,
                y=y_stress_only_concat,
                mode='markers',
                marker_color='purple',
                marker_size=10,
                name='combined points',
            ))
        fig.show()
