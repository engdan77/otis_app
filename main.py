# otis_app.py - This project is a frontend to otis_service
# URL: https://github.com/engdan77/otis_app
# Author: Daniel Engvall (daniel@engvalls.eu)

import kivy
kivy.require('1.9.0')

import re
from functools import partial
from collections import namedtuple
import webbrowser
from kivy.app import App
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.factory import Factory
from kivy.animation import Animation
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.listview import ListView
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from kivy.core.image import Image
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.properties import StringProperty, ObjectProperty, ListProperty, DictProperty, NumericProperty
from kivy.clock import Clock
from kivy.network.urlrequest import UrlRequest
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.config import ConfigParser
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.uix.settings import (Settings, SettingsWithSidebar,
                               SettingsWithSpinner,
                               SettingsWithTabbedPanel)

from garden import Graph, MeshLinePlot
import json

from kivy.support import install_twisted_reactor
install_twisted_reactor()
from twisted.internet import reactor, protocol

__version__ = "$Revision: 20150730.1573 $"

# ---------- Generic functions ----------

def get_date(msg):
    import time
    if not msg:
        return time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return '%s: %s' % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)

def show_url_result(req, results):
    ''' Show result of url request '''
    Logger.info("req: %s" % (str(req),))
    Logger.info("results: %s" % (str(results),))

def updates_to_plots(last_records):
    ''' Convert last records to graph plots '''
    from datetime import datetime
    last_records.reverse()
    last_records = sorted(last_records)
    Logger.info('='*30)
    Logger.info(str(last_records))
    Logger.info('='*30)
    result = []

    d_fmt = '%Y-%m-%d %H:%M:%S'
    now = datetime.now()
    prev_value = None
    for value_tuple in last_records:
        d, v = value_tuple
        d = datetime.strptime(d, d_fmt)
        # Divide timediff in seconds by one day to get how many days diff
        timediff = float(int(now.strftime('%s')) - int(d.strftime('%s'))) / 86400
        timediff = 0 - float(format(timediff, '.4f'))

        # Change value if required
        next_zero = None
        prev_zero = None
        prev_one = None
        if re.match(r'.*Motion.*', v, re.IGNORECASE):
            v = 1
            prev_zero = True
            next_zero = True
        elif re.match(r'.*Door Open.*', v, re.IGNORECASE):
            if prev_value == 1:
                prev_one = True
            if prev_value == 0:
                prev_zero = True
            v = 1
        elif re.match(r'.*Door Close.*', v, re.IGNORECASE):
            if prev_value == 1:
                prev_one = True
            v = 0
        else:
            v = float(v)

        # Add one where required
        if prev_one is True:
            result.append((timediff-0.0001, 1))
        if prev_zero is True:
            result.append((timediff-0.0001, 0))

        # Adding value
        result.append((timediff, v))

        # Correct issue with Motion/Door
        if next_zero is True:
            result.append((timediff+0.0001, 0))

        # Store previous value
        prev_value = v

    # Append last value to result
    if re.match(r'.*Motion.*', value_tuple[1], re.IGNORECASE):
        result.append((0-0.0001, 0))
        result.append((0, v))
    else:
        result.append((0, v))

    # Determina min/max values
    # result = sorted(result)
    all_x_values, all_y_values = zip(*result)
    min_x_value = float(min(*all_x_values))
    min_y_value = float(min(*all_y_values))
    max_y_value = float(max(*all_y_values))

    # Return result as dict
    return {'plots': result, 'min_y': min_y_value, 'max_y': max_y_value, 'min_x': min_x_value}


# ---------- ScreenManager and Screens ----------

class MyScreenManager(ScreenManager):
    connect_server_status = StringProperty('Initiating connection')
    json_sensors = StringProperty('........')
    settings_dict = DictProperty()

    def __init__(self, **kwargs):
        super(MyScreenManager, self).__init__(**kwargs)
        self._app = App.get_running_app()

    def change_screen(self, *args):
        screen_name = args[0]
        sm = self._app.root
        # If changing back to Initial Screen
        if screen_name == 'initial_screen':
            Clock.unschedule(sm.update_views)
        sm.current = screen_name

    def refresh_variables(self):
        Logger.info("Refreshing variables after connecting to MyScreenManager")
        self._app.config.update_config('my.ini')
        self.port = self._app.config.get('network', 'port')
        self.server = self._app.config.get('network', 'ip')
        self.connect_server_status = "Connecting to %s:%s" % (self.server, self.port)
        self.json_sensors = '....'

    def update_views(self, dt):
        ''' Method to be scheduled for updating from server '''
        # Poll new JSON data
        Logger.info(str(self._app.connect_to_server()))

        # Clean records in log_screen if too many lines
        if len(self._app.log_list) > 100:
            self._app.log_list.append(get_date("Cleaning old records in log"))
            while len(self._app.log_list) > 100:
                self._app.log_list.pop(0)

        def return_screen_object(screen_name):
            # Iterate through all screens
            found = None
            for current_screen in self._app.sm.screens:
                if current_screen.name == screen_name:
                   found = current_screen
            return found

        # For each device update Screen
        if re.match(r'^\{.*\}$', self._app.sm.json_sensors):
            try:
                j = json.loads(self._app.sm.json_sensors)
            except Exception as e:
                self._app.sm.json_sensors = 'Error in JSON'
            else:
                for device in j.keys():
                    Logger.info("Updating screen for device %s" % (device,))
                    self._app.log_list.append(get_date("Updating screen for device %s" % (device,)))

                    # Create Device Screen with sensors
                    box_device = BoxLayout(orientation='vertical', spacing=10)
                    box_device.add_widget(Label(text=''))
                    box_device.add_widget(Label(size_hint_y=0.2, text='[color=ff3333]' + device + '[/color]', font_size=40, markup=True))
                    box_device.add_widget(Label(text=''))

                    # Create Sensor Screen and button on device screen
                    for sensor in j[device]:
                        sensor_name = sensor.keys()[0]
                        sensor_data = sensor[sensor_name]
                        sensor_values = sensor_data['last_records']

                        sensor_dict = updates_to_plots(sensor_values)
                        sensor_plots = sensor_dict['plots']
                        ymin = sensor_dict['min_y']
                        ymax = sensor_dict['max_y']
                        xmin = sensor_dict['min_x']

                        last_date, last_value = sensor_values[-1]

                        # Determine suffix
                        suffix = ' '
                        if re.match(r'.*temp.*', sensor_name, re.IGNORECASE):
                            suffix = u"\u00b0C"
                        if re.match(r'.*humid.*', sensor_name, re.IGNORECASE):
                            suffix = " %"
                        if re.match(r'.*smoke.*', sensor_name, re.IGNORECASE):
                            suffix = " %"
                        if re.match(r'.*stove.*', sensor_name, re.IGNORECASE):
                            suffix = " %"

                        sensor = device + '_' + sensor_name
                        Logger.info(str(sensor))
                        Logger.info("Last data %s %s" % (last_date, last_value))

                        # Create new history view
                        box_sensor_history = BoxLayout(orientation='vertical', spacing=10)
                        box_sensor_history.add_widget(Label(size_hint_y=0.1, text='[color=B6BAB9]' + sensor_name + ' (' + device + ')[/color]', font_size=30, markup=True))

                        # Create history text
                        text_history = []
                        for d, v in sensor_values:
                            text_history.append(str("%s    %s" % (d, v)))

                        # Create left aligned list
                        adapter = SimpleListAdapter(data=text_history, cls=MyLeftAlignedLabel)
                        list_view = ListView(adapter=adapter)
                        # Fix bug with ListView to refresh if required
                        if(hasattr(list_view, '_reset_spopulate')):
                            Logger.info("Refresh list_view")
                            list_view._reset_spopulate()
                        # Add ListView to Sensor History
                        box_sensor_history.add_widget(list_view)
                        back_button = Button(size_hint_y=0.1, font_size=20, text='Back')
                        back_button.bind(on_press=partial(self.change_screen, device + "_" + sensor_name))
                        box_sensor_history.add_widget(back_button)

                        screen_sensor_history = return_screen_object(device + "_" + sensor_name + '_history')
                        screen_sensor_history.clear_widgets()
                        screen_sensor_history.add_widget(box_sensor_history)
                        screen_sensor = return_screen_object(device + "_" + sensor_name)

                        box_sensor = BoxLayout(orientation='vertical')
                        box_sensor.add_widget(Label(size_hint_y=0.1, text='[color=B6BAB9]' + sensor_name + ' (' + device + ')[/color]', font_size=30, markup=True))
                        # Add sensor value
                        box_sensor.add_widget(Label(text=last_value + suffix, font_size=60))
                        # Add sensor date
                        box_sensor.add_widget(Label(size_hint_y=0.1, markup=True, text='[b]Sensor last updated ' + last_date[:-3] + '[/b]\nPolled ' + get_date(None)[:-3], font_size=15))
                        # Add sensor graph
                        Logger.info("Create plot for %s" % (sensor_name,))
                        Logger.info(str(sensor_plots))
                        plot = MeshLinePlot(mode='line_strip', color=[1, 0, 0, 1])
                        plot.points = sensor_plots
                        sensor_graph = Graph(id='plots_' + sensor_name, precision='%0.0f', x_grid_label=True, y_grid_label=True, xmin=xmin, xmax=0, ymin=ymin, ymax=ymax, xlabel='days ago', ylabel=suffix, x_grid=True, y_grid=False, x_ticks_major=1, y_ticks_major=1)
                        sensor_graph.add_plot(plot)
                        box_sensor.add_widget(sensor_graph)

                        # Add buttonbar for sensor
                        box_buttons = BoxLayout(orientation='horizontal')

                        # Create button for history
                        history_button = Button(size_hint_y=0.2, font_size=20, text='History')
                        history_button.bind(on_press=partial(self.change_screen, device + "_" + sensor_name + "_history"))

                        # Create Back button
                        back_button = Button(size_hint_y=0.2, font_size=20, text='Back')
                        back_button.bind(on_press=partial(self.change_screen, device))

                        # Add buttons to row
                        box_buttons.add_widget(back_button)
                        box_buttons.add_widget(history_button)

                        # Add row to screen
                        box_sensor.add_widget(box_buttons)

                        # Add all of it to screen
                        screen_sensor.clear_widgets()
                        screen_sensor.add_widget(box_sensor)


class InitialScreen(Screen):
    version = StringProperty(__version__.replace('$', ''))
    logo_image = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(InitialScreen, self).__init__(**kwargs)
        self.logo_image = Image('logo.png')

    def move_logo(self, *args):
        screen = self._app.sm.get_screen('initial_screen')
        logo_object = screen.ids['logo']
        window_x, window_y = Window.size
        anim = Animation(y=window_y-(window_y/1.5), duration=6, t='in_bounce') + Animation(y=0, duration=6, t='out_bounce')
        anim.repeat = True
        anim.start(logo_object)

    def stop_logo(self, *args):
        screen = self._app.sm.get_screen('initial_screen')
        logo_object = screen.ids['logo']
        Animation.cancel_all(logo_object)


class ConnectingServerScreen(Screen):
    slideshow_all_sensors_counter = NumericProperty(0)
    slideshow_all_sensors_screens = ListProperty([])
    slideshow_all_sensors_index = NumericProperty(0)

    def change_screen(self, *args):
        screen_name = args[0]
        sm = self._app.root
        # If changing back to Initial Screen
        if screen_name == 'initial_screen':
            Clock.unschedule(sm.update_views)
        sm.current = screen_name

    def control_slideshow_all_sensors(self, button, *args):
        Logger.info('Slideshow for all sensors button is %s' % (button.state,))
        self._app.log_list.append(get_date('Slideshow for all sensors button is %s' % (button.state,)))

        if button.state == 'down':
            # Create list of screens to switch between
            for screen in self._app.sm.screens:
                if re.match(r'[^-]+-[^_]+_[^_]+$', screen.name):
                    self.slideshow_all_sensors_screens.append(screen)
            self.timeout = int(self._app.sm.settings_dict['slideshow_refresh_time'])
            self.slideshow_all_sensors_counter = self.timeout
            device_screen = self._app.sm.get_screen('all_devices_buttons')
            # Search for button object
            for widget in device_screen.walk():
                button = widget
                if widget.id == 'slide_all_button':
                    button.text = 'Slideshow All Sensors (' + str(self.slideshow_all_sensors_counter) + ')'
            Clock.schedule_interval(self.slideshow_all_sensors, 1)
        if button.state == 'normal':
            button.text = 'Slideshow All Sensors'
            Clock.unschedule(self.slideshow_all_sensors)

    def slideshow_all_sensors(self, dt):
        self.slideshow_all_sensors_counter -= 1
        device_screen = self._app.sm.get_screen('all_devices_buttons')
        for widget in device_screen.walk():
            button = widget
            if widget.id == 'slide_all_button':
                button.text = 'Slideshow All Sensors (' + str(self.slideshow_all_sensors_counter) + ')'
        if self.slideshow_all_sensors_counter == 0:
            self.slideshow_all_sensors_counter = self.timeout
            if self.slideshow_all_sensors_index < len(self.slideshow_all_sensors_screens)-1:
                self.slideshow_all_sensors_index += 1
            else:
                 self.slideshow_all_sensors_index = 0
            # Switch to next sensor screen
            self.change_screen(self.slideshow_all_sensors_screens[self.slideshow_all_sensors_index].name)

    def create_button_view(self, dt):
        import json
        import time

        # Make reference to app root widget
        sm = self._app.root

        # Check that JSON been recieved
        if re.match(r'^\{.*\}$', self._app.sm.json_sensors):
            try:
                j = json.loads(self._app.sm.json_sensors)
            except Exception as e:
                self._app.sm.json_sensors = 'Error in JSON'
            else:
                all_devices_boxlayout = BoxLayout(orientation='vertical', spacing=10)
                all_devices_boxlayout.add_widget(Label(text=''))
                all_devices_boxlayout.add_widget(Label(size_hint_y=0.2, text='[color=ff3333]Devices[/color]', font_size=40, markup=True))
                all_devices_boxlayout.add_widget(Label(text=''))
                all_devices_screen = Screen(id='all_devices_buttons', name='all_devices_buttons')
                all_devices_screen.add_widget(all_devices_boxlayout)
                sm.add_widget(all_devices_screen)

                # Bulding new screens for list of devices and sensors based on json
                # For each device create its own Screen
                for device in j.keys():
                    Logger.info("Creating screen for device %s" % (device,))
                    self._app.log_list.append(get_date("Creating screen for device %s" % (device,)))
                    screen_device = Screen(name=device)

                    # Add button for device on all_devices_boxlayout
                    b = Button(text=device)
                    # This will call the function with 'device' as argument to switch Screen
                    b.bind(on_press=partial(self.change_screen, device))
                    all_devices_boxlayout.add_widget(b)

                    # Create Device Screen with sensors
                    box_device = BoxLayout(orientation='vertical', spacing=10)
                    box_device.add_widget(Label(text=''))
                    box_device.add_widget(Label(size_hint_y=0.2, text='[color=ff3333]' + device + '[/color]', font_size=40, markup=True))
                    box_device.add_widget(Label(text=''))

                    # Create Sensor Screen and button on device screen
                    for sensor in j[device]:
                        sensor_name = sensor.keys()[0]
                        sensor_data = sensor[sensor_name]
                        sensor_values = sensor_data['last_records']

                        sensor_dict = updates_to_plots(sensor_values)
                        sensor_plots = sensor_dict['plots']
                        ymin = sensor_dict['min_y']
                        ymax = sensor_dict['max_y']
                        xmin = sensor_dict['min_x']

                        last_date, last_value = sensor_values[-1]

                        # Determine suffix
                        suffix = ' '
                        if re.match(r'.*temp.*', sensor_name, re.IGNORECASE):
                            suffix = u"\u00b0C"
                        if re.match(r'.*humid.*', sensor_name, re.IGNORECASE):
                            suffix = " %"
                        if re.match(r'.*smoke.*', sensor_name, re.IGNORECASE):
                            suffix = " %"
                        if re.match(r'.*stove.*', sensor_name, re.IGNORECASE):
                            suffix = " %"

                        sensor = device + '_' + sensor_name
                        Logger.info(str(sensor))
                        Logger.info("Last data %s %s" % (last_date, last_value))

                        # Create history view
                        screen_sensor_history = Screen(name=device + "_" + sensor_name + "_history")
                        box_sensor_history = BoxLayout(orientation='vertical', spacing=10)
                        box_sensor_history.add_widget(Label(size_hint_y=0.1, text='[color=B6BAB9]' + sensor_name + ' (' + device + ')[/color]', font_size=30, markup=True))

                        # Create history text
                        text_history = []
                        for d, v in sensor_values:
                            text_history.append(str("%s    %s" % (d, v)))

                        # Create left aligned list
                        adapter = SimpleListAdapter(data=text_history, cls=MyLeftAlignedLabel)
                        list_view = ListView(adapter=adapter)
                        # Fix bug with ListView to refresh if required
                        if(hasattr(list_view, '_reset_spopulate')):
                            Logger.info("Refresh list_view")
                            list_view._reset_spopulate()
                        # Add ListView to Sensor History
                        box_sensor_history.add_widget(list_view)
                        back_button = Button(size_hint_y=0.1, font_size=20, text='Back')
                        back_button.bind(on_press=partial(self.change_screen, device + "_" + sensor_name))
                        box_sensor_history.add_widget(back_button)
                        screen_sensor_history.add_widget(box_sensor_history)
                        sm.add_widget(screen_sensor_history)

                        # Create sensor screen
                        screen_sensor = Screen(name=device + "_" + sensor_name)
                        box_sensor = BoxLayout(orientation='vertical')
                        box_sensor.add_widget(Label(size_hint_y=0.1, text='[color=B6BAB9]' + sensor_name + ' (' + device + ')[/color]', font_size=30, markup=True))
                        # Add sensor value
                        box_sensor.add_widget(Label(text=last_value + suffix, font_size=60))
                        # Add sensor date
                        box_sensor.add_widget(Label(size_hint_y=0.1, markup=True, text='[b]Sensor last updated ' + last_date[:-3] + '[/b]\nPolled ' + get_date(None)[:-3], font_size=15))
                        # Add sensor graph
                        Logger.info("Create plot for %s" % (sensor_name,))
                        Logger.info(str(sensor_plots))
                        plot = MeshLinePlot(mode='line_strip', color=[1, 0, 0, 1])
                        plot.points = sensor_plots
                        sensor_graph = Graph(id='plots_' + sensor_name, precision='%0.0f', x_grid_label=True, y_grid_label=True, xmin=xmin, xmax=0, ymin=ymin, ymax=ymax, xlabel='days ago', ylabel=suffix, x_grid=True, y_grid=False, x_ticks_major=1, y_ticks_major=1)
                        sensor_graph.add_plot(plot)
                        box_sensor.add_widget(sensor_graph)

                        # Add buttonbar for sensor
                        box_buttons = BoxLayout(orientation='horizontal')

                        # Create button for history
                        history_button = Button(size_hint_y=0.2, font_size=20, text='History')
                        history_button.bind(on_press=partial(self.change_screen, device + "_" + sensor_name + "_history"))

                        # Create Back button
                        back_button = Button(size_hint_y=0.2, font_size=20, text='Back')
                        back_button.bind(on_press=partial(self.change_screen, device))

                        # Add buttons to row
                        box_buttons.add_widget(back_button)
                        box_buttons.add_widget(history_button)

                        # Add row to screen
                        box_sensor.add_widget(box_buttons)

                        # Add all of it to screen
                        screen_sensor.add_widget(box_sensor)
                        sm.add_widget(screen_sensor)

                        # Create button on device screen
                        button_sensor = Button(text=sensor_name)
                        button_sensor.bind(on_press=partial(self.change_screen, sensor))
                        box_device.add_widget(button_sensor)

                    # Add Device Screen with all sensor buttons to ScreenManager
                    back_button = Button(font_size=20, text='[b]Back[/b]', markup=True)
                    back_button.bind(on_press=partial(self.change_screen, 'all_devices_buttons'))
                    box_device.add_widget(back_button)
                    screen_device.add_widget(box_device)
                    sm.add_widget(screen_device)

                # Adding Back button to Devices screen
                back_button = Button(font_size=20, text='[b]Back[/b]', markup=True)
                back_button.bind(on_press=partial(self.change_screen, 'initial_screen'))
                all_devices_buttonrow = BoxLayout(orientation='horizontal')
                all_devices_buttonrow.add_widget(back_button)
                slide_all_button = ToggleButton(id='slide_all_button', font_size=20, text='Slideshow All Sensors')
                slide_all_button.bind(on_press=partial(self.control_slideshow_all_sensors, slide_all_button))
                all_devices_buttonrow.add_widget(slide_all_button)
                all_devices_boxlayout.add_widget(all_devices_buttonrow)

                # Unschedule timer
                Clock.unschedule(self.create_button_view)
                # Return to buttons of all devices
                sm.current = 'all_devices_buttons'
                # Schedule updates from server
                Clock.schedule_interval(sm.update_views, int(self._app.sm.settings_dict['refresh_time']))

        # Check if failed pause for error before return
        if re.match(r'.*fail.*', self._app.sm.connect_server_status) or re.match(r'.*error.*', self._app.sm.json_sensors):
            Clock.unschedule(self.create_button_view)
            time.sleep(2)
            self.port = self._app.config.get('network', 'port')
            self.server = self._app.config.get('network', 'ip')
            self._app.sm.connect_server_status = "Connecting to %s:%s" % (self.server, self.port)
            sm.current = 'initial_screen'

    def call_connect_sensor_status(self, dt):
        ''' Function that connects and retrieves json '''
        self._app.config.update_config('my.ini')
        port = self._app.config.get('network', 'port')
        server = self._app.config.get('network', 'ip')
        refresh_time = self._app.config.get('network', 'refresh_time')
        slideshow_refresh_time = self._app.config.get('other', 'slideshow_refresh_time')
        self._app.sm.settings_dict['ip'] = server
        self._app.sm.settings_dict['port'] = port
        self._app.sm.settings_dict['refresh_time'] = refresh_time
        self._app.sm.settings_dict['slideshow_refresh_time'] = slideshow_refresh_time

        # Initiate connection
        Logger.info("Connecting to %s:%s" % (server, port))
        self._app.log_list.append(get_date("Connecting to %s:%s" % (server, port)))
        Logger.info(str(self._app.connect_to_server()))
        Clock.schedule_interval(self.create_button_view, 1)


class AboutScreen(Screen):
    def move_text(self, *args):
        screen = self._app.sm.get_screen('about_screen')
        text_object = screen.ids['moving_text']
        window_x, window_y = Window.size
        center_x = window_x/2
        center_x = 10
        center_y = window_y/2
        center_y = 10
        dia = 200
        dur = 3
        t = 'in_out_circ'
        anim = Animation(x=center_x, y=center_y-dia, duration=dur, t=t) + Animation(x=center_x+dia, y=center_y, duration=dur, t=t) + Animation(x=center_x, y=center_y+dia, duration=dur, t=t) + Animation(x=center_x-dia, y=center_y, duration=dur, t=t)
        anim.repeat = True
        anim.start(text_object)

    def stop_text(self, *args):
        screen = self._app.sm.get_screen('about_screen')
        text_object = screen.ids['moving_text']
        Animation.cancel_all(text_object)

    def open_browser(self, *args):
        url = 'https://github.com/engdan77'
        webbrowser.open(url)


class MyLeftAlignedLabel(Label):
    pass


class LogScreen(Screen):
    left_label = ObjectProperty(MyLeftAlignedLabel)


class SettingScreen(Screen):
    pass


Builder.load_string('''
#:import FadeTransition kivy.uix.screenmanager.FadeTransition
#:import Clock kivy.clock.Clock
#:import partial functools
#:import sla kivy.adapters.simplelistadapter
#:import label kivy.uix.label
#:import window kivy.core.window

<InitialScreen>
    name: 'initial_screen'
    _app: app
    on_enter: self.move_logo(self)
    on_leave: self.stop_logo(self)
    BoxLayout:
        orientation: 'horizontal'
        BoxLayout:
            orientation: 'vertical'
            Button:
                text: 'View Sensors'
                on_press: root._app.sm.refresh_variables(); app.root.current = 'connecting_server_screen'
            Button:
                text: 'View App Log'
                on_press: app.root.current = 'log_screen'
            Button:
                text: 'Settings'
                on_press: app.open_settings()
            Button:
                text: 'About This App'
                on_press: app.root.current = 'about_screen'
            Button:
                text: '[b]Exit[/b]'
                font_size: 20
                on_press: app.stop()
                markup: True
        BoxLayout:
            orientation: 'vertical'
            id: right_pane
            Image:
                id: logo
                source: 'logo.png'
                allow_stretch: False
                keep_ratio: True
                pos_hint: {'center_x': .5, 'top': .9}
            Label:
                text: root.version
                size_hint: None, None
                pos_hint: {'center_x': .5, 'top': .8}
                font_size: self.width / 7
                valign: 'middle'
                halign: 'center'

<ConnectingServerScreen>
    name: 'connecting_server_screen'
    id: 'connecting_server_screen'
    on_enter: Clock.schedule_once(self.call_connect_sensor_status)
    _app: app
    BoxLayout:
        orientation: 'vertical'
        Label:
            font_size: 30
            text: app.sm.connect_server_status
        Image:
            source: 'RingGreen.zip'
            allow_stretch: False
            keep_ratio: True
            anim_delay: 0.02
        Label:
            font_size: 20
            text: app.sm.json_sensors[:40]
        Button:
            font_size: 20
            text: 'Abort'
            size_hint_y: 0.2
            on_press: Clock.unschedule(root.create_button_view); app.sm.current = 'initial_screen'

<AboutScreen>
    name: 'about_screen'
    _app: app
    on_enter: self.move_text(self)
    on_leave: self.stop_text(self)
    FloatLayout:
        orientation: 'vertical'
        Scatter:
            auto_bring_to_front: False
            Image:
                center: self.parent.center
                source: 'daniel_engvall.png'
                size: root.width-400, root.height-400
        Label:
            text: "[color=ff3333][b]AutoHomeMobile[/b][/color]\\nDeveloped by daniel@engvalls.eu\\n[color=0000ff][ref=url]https://github.com/engdan77[/ref][/font]"
            markup: True
            on_ref_press: root.open_browser(self)
            size_hint: None, None
            font_size: self.width / 5
            pos_hint: {'center_x': .5, 'top': .2}
        Label:
            id: moving_text
            text: '[color=A31B00]Try to pinch/rotate me...[/color]'
            markup: True
            pos: 50, 50
        Button:
            text: 'Back'
            on_press: app.root.current = 'initial_screen'
            size_hint: None, None

<MyLeftAlignedLabel>
    font_size: 15
    halign: 'left'
    size_hint_y: None
    text_size: self.size

<LogScreen>:
    name: 'log_screen'
    BoxLayout:
        orientation: 'vertical'
        ListView:
            adapter:
                sla.SimpleListAdapter(data=app.log_list, cls=root.left_label)
        Button:
            size_hint_y: 0.1
            text: 'Back'
            on_press: app.root.current = 'initial_screen'
''')

# ---------- Generic Classes ----------

class ProtocolClass(protocol.Protocol):
    def connectionMade(self):
        self.factory.app.on_connection(self.transport)

    def dataReceived(self, data):
        self.factory.app.print_message(data)


class ConnectionClass(protocol.ClientFactory):
    protocol = ProtocolClass
    def __init__(self, app):
        self.app = app

    def clientConnectionLost(self, conn, reason):
        self.app.print_message("Connection lost")
        self.app.log_list.append(get_date("Connected and disconnecting from server"))
        Logger.info('Connection lost')

    def clientConnectionFailed(self, conn, reason):
        self.app.print_message("Connection failed")
        self.app.log_list.append(get_date("Connection failed"))
        Logger.error('Connection failed')

# ---------- Main App ----------

class MyApp(App):
    sm = ObjectProperty()
    settings = DictProperty({'apa': 1})
    connection = None
    log_list = ListProperty([get_date(None) + ': Application Started'])

    def __init__(self, **kwargs):
        # Superclass if we like to adjust present init
        super(MyApp, self).__init__(**kwargs)

    def build_config(self, config):
        config.setdefaults('network', {
                            'ip': '127.0.0.1',
                            'port': '3000',
                            'refresh_time': '60'})
        config.setdefaults('other', {'slideshow_refresh_time': '60'})

    def on_config_change(self, config, section, key, value):
       pass

    def build_settings(self, settings):
        import json
        self.setting_json = '''[
            {
                "type": "title",
                "title": "Server"
            },
            {
                "type": "string",
                "title": "IP Address",
                "desc": "IP address for server",
                "section": "network",
                "key": "ip"
            },
            {
                "type": "numeric",
                "title": "Port",
                "desc": "Port for server",
                "section": "network",
                "key": "port"
            },
            {
                "type": "numeric",
                "title": "Server Refresh Time",
                "desc": "Number of seconds before refresh status from server",
                "section": "network",
                "key": "refresh_time"
            },
            {
                "type": "numeric",
                "title": "Slideshow Refresh Time",
                "desc": "Number of seconds for each slide",
                "section": "other",
                "key": "slideshow_refresh_time"
            }

        ]'''
        settings.add_json_panel('otis_service', self.config, data=self.setting_json)

    def on_stop(self):
        Logger.info("Good Bye!!")

    def connect_to_server(self):
        server = str(self.config.get('network', 'ip'))
        port = int(self.config.get('network', 'port'))
        return reactor.connectTCP(server, port, ConnectionClass(self))

    def on_connection(self, connection):
        self.sm.connect_server_status = 'Connected succesfully, retrieving JSON data!'
        self.connection = connection
        # Send actual command to server
        self.send_message()

    def send_message(self, *args):
        msg = '"show_status_json"'
        if msg and self.connection:
            Logger.info("Sending %s" % (msg,))
            self.connection.write(msg)

    def print_message(self, msg):
        import time
        # Successfully receieved JSON
        if str(msg).find('{') > 0 or str(msg).find('}') > 0:
            if not str(msg)[0] == '{':
                Logger.info("Appending JSON")
                self.sm.json_sensors += str(msg)
            else:
                Logger.info("Found JSON")
                self.sm.json_sensors = str(msg)
            Logger.info("Printing Result of JSON Sensor")
            Logger.info(str(self.sm.json_sensors))
            self.sm.connect_server_status = 'Parsing JSON!'

            # Save to local file as debug
            # with open('debug.txt', 'w') as f:
                # f.write(msg)
        # Failed connection
        if msg.find("failed") > 0:
            self.sm.connect_server_status = 'Connection failed!'

    def build(self):
        import time
        super(MyApp, self).build()

        # Set icon and name
        self.title = 'AutoHomeMobile'
        self.icon = 'icon.png'

        # Configuration settings
        config = self.config

        # self.settings_cls = SettingsWithSidebar
        self.settings_cls = SettingsWithTabbedPanel
        self.use_kivy_settings = False

        # Clock handler
        # Clock.schedule_interval(self.timer, 20)

        self.sm = MyScreenManager(id='manager', transition=FadeTransition())
        self.sm.add_widget(InitialScreen(name='initial_screen'))
        self.sm.add_widget(LogScreen(name='log_screen'))
        self.sm.add_widget(AboutScreen(name='about_screen'))
        self.sm.add_widget(ConnectingServerScreen(name='connecting_server_screen'))
        # Return ScreenManager
        return self.sm


if __name__ == '__main__':
    MyApp().run()
