# ui/main_window.py
import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDialog, QFormLayout, QComboBox,
    QTimeEdit, QDateEdit, QMessageBox, QInputDialog, QSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, QDate, QTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.scale import ScaleBase
from matplotlib.transforms import Transform
from matplotlib.ticker import FixedLocator, FixedFormatter
from matplotlib.patches import Rectangle
from matplotlib import scale as mscale
from datetime import date, datetime, timedelta
from database import Database

class CustomTimeTransform(Transform):
    input_dims = output_dims = 1
    is_separable = True

    def __init__(self):
        super().__init__()
        self.linearstart = 7
        self.linearend = 18
        self.ticksize1 = 0.2
        self.ticksize2 = 0.6

    def transform_non_affine(self, t):
        t = np.asarray(t)
        y = np.empty_like(t)
        # Compress 00:00-07:00
        mask = t < self.linearstart
        y[mask] = t[mask] * self.ticksize1
        # Normal scale for 07:00-18:00
        mask = (t >= self.linearstart) & (t < self.linearend)
        y[mask] = self.linearstart*self.ticksize1 + (t[mask] - self.linearstart) * self.ticksize2
        # Compress 18:00-24:00
        mask = t >= self.linearend
        y[mask] = self.linearstart*self.ticksize1 + (self.linearend-self.linearstart)*self.ticksize2 + (t[mask] - self.linearend) * self.ticksize1
        return y

    def inverted(self):
        return InvertedCustomTimeTransform(self.linearstart, self.linearend, self.ticksize1, self.ticksize2)

class InvertedCustomTimeTransform(Transform):
    input_dims = output_dims = 1
    is_separable = True

    def __init__(self, linearstart, linearend, ticksize1, ticksize2):
        super().__init__()
        self.linearstart = linearstart
        self.linearend = linearend
        self.ticksize1 = ticksize1
        self.ticksize2 = ticksize2

    def transform_non_affine(self, y):
        y = np.asarray(y)
        t = np.empty_like(y)
        # Inverse for 00:00-07:00
        mask = y < self.linearstart * self.ticksize1
        t[mask] = y[mask] / self.ticksize1
        # Inverse for 07:00-18:00
        mask = (y >= self.linearstart * self.ticksize1) & (y < self.linearstart * self.ticksize1 + (self.linearend - self.linearstart) * self.ticksize2)
        t[mask] = self.linearstart + (y[mask] - self.linearstart * self.ticksize1) / self.ticksize2
        # Inverse for 18:00-24:00
        mask = y >= self.linearstart * self.ticksize1 + (self.linearend - self.linearstart) * self.ticksize2
        t[mask] = self.linearend + (y[mask] - (self.linearstart * self.ticksize1 + (self.linearend - self.linearstart) * self.ticksize2)) / self.ticksize1
        return t

    def inverted(self):
        return CustomTimeTransform()

class CustomTimeScale(ScaleBase):
    name = 'custom_time'

    def __init__(self, axis, **kwargs):
        super().__init__(axis, **kwargs)
        self.axis = axis

    def get_transform(self):
        return CustomTimeTransform()

    def set_default_locators_and_formatters(self, axis):
        major_times = np.arange(0, 25, 2)
        axis.set_major_locator(FixedLocator(major_times))
        axis.set_major_formatter(FixedFormatter([f"{int(t):02d}:00" for t in major_times]))

# Register the custom scale
mscale.register_scale(CustomTimeScale)

class AddEntryDialog(QDialog):
    def __init__(self, parent=None, preset_date=None):
        super(AddEntryDialog, self).__init__(parent)
        self.setWindowTitle("Add Work Entry")
        self.setGeometry(100, 100, 300, 200)
        self.layout = QFormLayout(self)

        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        if preset_date:
            self.date_edit.setDate(QDate(preset_date.year, preset_date.month, preset_date.day))
        else:
            self.date_edit.setDate(QDate.currentDate())


        self.type_combo = QComboBox(self)
        self.type_combo.addItems(["Working", "Sick Leave", "Vacation"])

        self.check_in = QTimeEdit(self)
        self.check_in.setTime(QTime(8, 0))
        self.check_out = QTimeEdit(self)
        self.check_out.setTime(QTime(16, 00))

        self.layout.addRow("Date:", self.date_edit)
        self.layout.addRow("Type:", self.type_combo)
        self.layout.addRow("Check In:", self.check_in)
        self.layout.addRow("Check Out:", self.check_out)

        self.lunch_break_checkbox = QCheckBox("Lunch Break", self)
        self.lunch_break_checkbox.setChecked(True)
        self.layout.addRow(self.lunch_break_checkbox)

        self.buttons_layout = QHBoxLayout()
        self.submit_btn = QPushButton("Submit", self)
        self.cancel_btn = QPushButton("Cancel", self)
        self.buttons_layout.addWidget(self.submit_btn)
        self.buttons_layout.addWidget(self.cancel_btn)
        self.layout.addRow(self.buttons_layout)

        self.submit_btn.clicked.connect(self.submit)
        self.cancel_btn.clicked.connect(self.reject)

    def submit(self):
        self.accept()
class EditEntryDialog(QDialog):
    def __init__(self, parent=None, date=None, start_time=None, end_time=None):
        super(EditEntryDialog, self).__init__(parent)
        self.setWindowTitle("Edit Work Entry")
        self.setGeometry(100, 100, 300, 200)
        self.layout = QFormLayout(self)

        self.date_edit = QDateEdit(self)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate(date.year, date.month, date.day))

        self.check_in = QTimeEdit(self)
        self.check_in.setTime(QTime(int(start_time), int((start_time % 1) * 60)))
        self.check_out = QTimeEdit(self)
        self.check_out.setTime(QTime(int(end_time), int((end_time % 1) * 60)))

        self.layout.addRow("Date:", self.date_edit)
        self.layout.addRow("Check In:", self.check_in)
        self.layout.addRow("Check Out:", self.check_out)

        self.buttons_layout = QHBoxLayout()
        self.update_btn = QPushButton("Update", self)
        self.delete_btn = QPushButton("Delete", self)
        self.cancel_btn = QPushButton("Cancel", self)
        self.buttons_layout.addWidget(self.update_btn)
        self.buttons_layout.addWidget(self.delete_btn)
        self.buttons_layout.addWidget(self.cancel_btn)
        self.layout.addRow(self.buttons_layout)

        self.update_btn.clicked.connect(self.update)
        self.delete_btn.clicked.connect(self.delete)
        self.cancel_btn.clicked.connect(self.reject)

        self.delete_entry = False

    def update(self):
        self.accept()

    def delete(self):
        self.delete_entry = True
        self.accept()
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.db = Database()
        self.setWindowTitle("Work Hours Tracker")
        self.setGeometry(100, 100, 1000, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        # Top Buttons
        self.top_layout = QHBoxLayout()
        self.add_entry_btn = QPushButton("Add Entry")
        self.set_start_date_btn = QPushButton("Set Start Date")
        self.top_layout.addWidget(self.add_entry_btn)
        self.top_layout.addWidget(self.set_start_date_btn)
        self.main_layout.addLayout(self.top_layout)

        self.add_entry_btn.clicked.connect(self.open_add_entry_dialog)
        self.set_start_date_btn.clicked.connect(self.set_start_date)

        # Week navigation
        self.week_layout = QHBoxLayout()
        self.prev_week_btn = QPushButton("Previous Week")
        self.next_week_btn = QPushButton("Next Week")
        self.week_spinbox = QSpinBox()
        self.week_spinbox.setRange(1, 53)
        self.week_spinbox.setValue(date.today().isocalendar()[1])
        self.week_label = QLabel(f"Week {self.week_spinbox.value()}")
        
        self.week_layout.addWidget(self.prev_week_btn)
        self.week_layout.addWidget(self.week_label)
        self.week_layout.addWidget(self.week_spinbox)
        self.week_layout.addWidget(self.next_week_btn)
        
        self.main_layout.insertLayout(1, self.week_layout)  # Insert after top buttons

        self.prev_week_btn.clicked.connect(self.previous_week)
        self.next_week_btn.clicked.connect(self.next_week)
        self.week_spinbox.valueChanged.connect(self.week_changed)

        # Matplotlib Figure
        self.figure, self.ax = plt.subplots(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        #self.toolbar = NavigationToolbar(self.canvas, self)
        #self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.canvas)

        # Connect the click event
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)

        # Extra Hours Display
        self.extra_hours_label = QLabel("Extra Hours: 0")
        self.extra_hours_label.setAlignment(Qt.AlignCenter)
        self.extra_hours_label.setStyleSheet("font-size: 16px;")
        self.main_layout.addWidget(self.extra_hours_label)

        self.set_current_week()
        self.load_data()

    def set_current_week(self):
        today = date.today()
        current_week = today.isocalendar()[1]
        self.week_spinbox.setValue(current_week)
        start_of_week = today - timedelta(days=today.weekday())
        self.db.set_setting("start_date", start_of_week.strftime("%Y-%m-%d"))

    def on_plot_click(self, event):
        if event.inaxes == self.ax:
            day_index = int(event.xdata + 0.5)  # Round to nearest integer
            if 0 <= day_index < 7:
                start_date = datetime.strptime(self.db.get_setting("start_date"), "%Y-%m-%d").date()
                clicked_date = start_date + timedelta(days=day_index)
                
                # Check if we clicked on an existing bar
                for artist in self.ax.get_children():
                    if isinstance(artist, Rectangle) and artist.get_x() == day_index - 0.3:  # -0.3 because bar width is 0.6
                        if artist.contains(event)[0]:
                            # We clicked on an existing bar
                            start_time = artist.get_y()
                            end_time = start_time + artist.get_height()
                            self.open_edit_entry_dialog(clicked_date, start_time, end_time)
                            return

                # If we didn't click on a bar, open the add entry dialog
                self.open_add_entry_dialog(clicked_date)

    def open_edit_entry_dialog(self, date, start_time, end_time):
        dialog = EditEntryDialog(self, date, start_time, end_time)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.delete_entry:
                print("main_window says delete")
                self.db.delete_entry(
                    date.strftime("%Y-%m-%d"),
                    f"{int(start_time):02d}:{int((start_time % 1) * 60):02d}",
                    f"{int(end_time):02d}:{int((end_time % 1) * 60):02d}"
                )
            else:
                new_date = dialog.date_edit.date().toString("yyyy-MM-dd")
                new_check_in = dialog.check_in.time().toString("HH:mm")
                new_check_out = dialog.check_out.time().toString("HH:mm")
                new_hours = (dialog.check_out.time().hour() - dialog.check_in.time().hour()) + \
                            (dialog.check_out.time().minute() - dialog.check_in.time().minute()) / 60
                self.db.update_entry(
                    date.strftime("%Y-%m-%d"),
                    f"{int(start_time):02d}:{int((start_time % 1) * 60):02d}",
                    f"{int(end_time):02d}:{int((end_time % 1) * 60):02d}",
                    new_date, new_check_in, new_check_out, new_hours
                )
            self.load_data()

    def open_add_entry_dialog(self, preset_date=None):
        dialog = AddEntryDialog(self)
        if preset_date:
            dialog.date_edit.setDate(QDate(preset_date.year, preset_date.month, preset_date.day))
        if dialog.exec_() == QDialog.Accepted:
            date = dialog.date_edit.date().toString("yyyy-MM-dd")
            entry_type = dialog.type_combo.currentText()
            check_in = dialog.check_in.time().toString("HH:mm")
            check_out = dialog.check_out.time().toString("HH:mm")
            fmt = "%H:%M"
            lunch_break = dialog.lunch_break_checkbox.isChecked()
            try:
                t_in = datetime.strptime(check_in, fmt)
                t_out = datetime.strptime(check_out, fmt)
                if t_out <= t_in:
                    QMessageBox.warning(self, "Invalid Time", "Check-out time must be after check-in time.")
                    return
                hours = (t_out - t_in).seconds / 3600
            except ValueError:
                QMessageBox.warning(self, "Invalid Time", "Please enter valid check-in and check-out times.")
                return
            
            # Automatically set lunch_break to True for working sessions over 5 hours
            if entry_type == "Working" and hours > 5:
                lunch_break = True
            else:
                lunch_break = False
            
            self.db.add_entry(date, check_in, check_out, entry_type, hours, lunch_break)
            self.load_data()

    def set_start_date(self):
        date, ok = QInputDialog.getText(self, 'Set Start Date', 'Enter start date (YYYY-MM-DD):')
        if ok:
            try:
                datetime.strptime(date, "%Y-%m-%d")
                self.db.set_setting("start_date", date)
                self.load_data()
            except ValueError:
                QMessageBox.warning(self, "Invalid Date", "Please enter a valid date in YYYY-MM-DD format.")

    def previous_week(self):
        self.week_spinbox.setValue(self.week_spinbox.value() - 1)

    def next_week(self):
        self.week_spinbox.setValue(self.week_spinbox.value() + 1)

    def week_changed(self, value):
        self.week_label.setText(f"Week {value}")
        self.update_displayed_week(value)

    def update_displayed_week(self, week_number):
        year = date.today().year
        start_date = date.fromisocalendar(year, week_number, 1)
        self.db.set_setting("start_date", start_date.strftime("%Y-%m-%d"))
        self.load_data()

    def load_data(self):
        start_date = self.db.get_setting("start_date")
        if not start_date:
            today = date.today()
            start_date = today - timedelta(days=today.weekday())
        else:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        end_date = start_date + timedelta(days=6)
        
        # Update week number display
        self.week_spinbox.setValue(start_date.isocalendar()[1])
        self.week_label.setText(f"Week {self.week_spinbox.value()}")       
        
        entries = self.db.get_entries(start_date, end_date)

        # Process data
        data = {}
        for entry in entries:
            date2 = entry[1]
            entry_type = entry[4]
            hours = entry[5]
            lunch_break = entry[6]
            if entry[2] and entry[3]:
                check_in = datetime.strptime(entry[2], "%H:%M")
                check_out = datetime.strptime(entry[3], "%H:%M")
                start_time = check_in.hour + check_in.minute / 60
                end_time = check_out.hour + check_out.minute / 60
                data[date2] = data.get(date2, []) + [(start_time, end_time, entry_type, lunch_break)]
            else:
                data[date2] = data.get(date2, []) + [(8.0, 16.0, entry_type, lunch_break)]

        # Ensure all days are present
        dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        
        # Reorder dates to make Sunday the last day
        if datetime.strptime(dates[0], "%Y-%m-%d").weekday() == 6:  # If the first day is Sunday
            dates = dates[1:] + [dates[0]]

        # Calculate extra hours
        total_extra = 0
        for day in data:
            for period in data[day]:
                hours = period[1] - period[0]
                if hours > 7.5:
                    total_extra += (hours - 7.5)
        self.extra_hours_label.setText(f"Extra Hours: {total_extra}")

        # Plot data
        self.ax.clear()
        self.ax.set_yscale('custom_time')
        self.ax.set_ylim(24, 0)  # Reverse y-axis so 0 at top
        self.ax.set_xlim(-0.5, len(dates) - 0.5)

        x_positions = np.arange(len(dates))

        # Plot each work period as a vertical bar
        for i, day in enumerate(dates):
            if day in data:
                periods = data[day]
                for period in periods:
                    start, end, entry_type, lunch_break = period
                    color = 'skyblue' if entry_type == 'Working' else 'green' if entry_type == 'Vacation' else 'yellow'
                    self.ax.bar(
                        i,
                        end - start,
                        bottom=start,
                        width=0.6,
                        color=color,
                        edgecolor='black'
                    )
                    # Add white dot for lunch break
                    if lunch_break:
                        mid_time = (start + end) / 2
                        self.ax.scatter(i, mid_time, color='white', s=70, zorder=3, edgecolors='black')
        
        # Add vertical lines to separate days
        for i in range(1, len(dates)):
            self.ax.axvline(x=i-0.5, color='gray', linestyle='--', alpha=0.5)

        self.ax.set_xticks(x_positions)
        self.ax.set_xticklabels([
            f"{datetime.strptime(d, '%Y-%m-%d').strftime('%A')}\n{datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m.%Y')}"
            for d in dates
        ])
        # Bottom margin:
        self.figure.subplots_adjust(bottom=0.2)

        #self.ax.set_xlabel("Day of Week")
        #self.ax.set_ylabel("Time of Day")
        #self.ax.set_title("Weekly Work Schedule")

        self.figure.tight_layout()
        self.canvas.draw()

    def closeEvent(self, event):
        self.db.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
