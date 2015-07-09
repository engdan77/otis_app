import re
from functools import partial
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.network.urlrequest import UrlRequest
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.config import ConfigParser
from kivy.uix.settings import (Settings, SettingsWithSidebar,
                               SettingsWithSpinner,
                               SettingsWithTabbedPanel)

from garden import Graph, MeshLinePlot
import json


from kivy.support import install_twisted_reactor
install_twisted_reactor()
from twisted.internet import reactor, protocol

__version__ = "$Revision: 20150709.826 $"


def show_url_result(req, results):
    ''' Show result of url request '''
    print "req: %s" % (str(req),)
    print "results: %s" % (str(results),)

class InitialScreen(Screen):
    version = StringProperty(__version__.replace('$', ''))

class ConnectingServerScreen(Screen):
    _app = ObjectProperty(None)
    connection_status = StringProperty('None')
    json_sensors = StringProperty('........')

    def change_screen(self, *args):
        screen_name = args[0]
        sm = self._app.root
        sm.current = screen_name

    def create_button_view(self, json_sensors):
        import json
        import time

        # Check that JSON been recieved
        # if self.json_sensors.find('{') >= 0:
        if re.match(r'^\{.*\}$', self.json_sensors):
            try:
                j = json.loads(self.json_sensors)
            except Exception as e:
                self.json_sensors = 'Error in JSON'
            else:
                sm = self._app.root
                all_devices_boxlayout = BoxLayout(orientation='vertical')
                l = Label(text='Devices', font_size=30)
                all_devices_boxlayout.add_widget(l)
                all_devices_screen = Screen(name='all_devices_buttons')
                all_devices_screen.add_widget(all_devices_boxlayout)
                sm.add_widget(all_devices_screen)

                # Bulding new screens for list of devices and sensors based on json

                # For each device create its own Screen
                for device in j.keys():
                    print "Creating screen for device %s" % (device,)
                    screen_device = Screen(name=device)
                    box_device = BoxLayout(orientation='vertical')
                    l = Label(text=device, font_size=30)
                    box_device.add_widget(l)

                    # Add button for device on all_devices_boxlayout
                    b = Button(text=device)
                    # This will call the function with 'device' as argument to switch Screen
                    b.bind(on_press=partial(self.change_screen, device))
                    all_devices_boxlayout.add_widget(b)

                    # Create Device Screen with sensors
                    box_device = BoxLayout(orientation='vertical')
                    box_device.add_widget(Label(text=device, font_size=30))

                    # Create Sensor Screen and button on device screen
                    for sensor in j[device]:
                        sensor_name = sensor.keys()[0]
                        sensor_data = sensor[sensor_name]
                        sensor_values = sensor_data['last_records']
                        last_date, last_value = sensor_values[0]

                        sensor = device + '_' + sensor_name
                        print sensor
                        print "Last data %s %s" % (last_date, last_value)
                        # Create sensor screen
                        screen_sensor = Screen(name=device + "_" + sensor_name)
                        box_sensor = BoxLayout(orientation='vertical')
                        box_sensor.add_widget(Label(text=sensor_name, font_size=30))
                        # Add sensor value
                        box_sensor.add_widget(Label(text=last_value, font_size=40))
                        # Add sensor date
                        box_sensor.add_widget(Label(text=last_date, font_size=20))

                        # Add Back button
                        back_button = Button(text='Back')
                        back_button.bind(on_press=partial(self.change_screen, device))
                        box_sensor.add_widget(back_button)

                        screen_sensor.add_widget(box_sensor)
                        sm.add_widget(screen_sensor)

                        # Create button on device screen
                        button_sensor = Button(text=sensor_name)
                        button_sensor.bind(on_press=partial(self.change_screen, sensor))
                        box_device.add_widget(button_sensor)

                    # Add Device Screen with all sensor buttons to ScreenManager
                    back_button = Button(text='Back')
                    back_button.bind(on_press=partial(self.change_screen, 'all_devices_buttons'))
                    box_device.add_widget(back_button)
                    screen_device.add_widget(box_device)
                    sm.add_widget(screen_device)

                # Adding Back button to Devices screen
                back_button = Button(text='Back')
                back_button.bind(on_press=partial(self.change_screen, 'initial_screen'))
                all_devices_boxlayout.add_widget(back_button)

                # Unschedule timer
                Clock.unschedule(self.create_button_view)
                # Return to buttons of all devices
                sm.current = 'all_devices_buttons'


    def call_connect_sensor_status(self, *args):
        ''' Function that connects and retrieves json '''
        self.port = self._app.config.get('network', 'port')
        self.server = self._app.config.get('network', 'ip')
        # Initiate connection
        print "Connecting to %s:%s" % (self.server, self.port)
        print  str(self._app.connect_to_server())

        Clock.schedule_interval(self.create_button_view, 1)

        # self._app.root.current = 'about_screen'

class ViewSensorScreen(Screen):
    pass

class AboutScreen(Screen):
    pass

class LogScreen(Screen):
    pass

class SettingScreen(Screen):
    pass

class GraphScreen(Screen):
    def draw_graph(self):
        print "Running graph"
        # Draw graph
        plot = MeshLinePlot(mode='line_strip', color=[1, 0, 0, 1])
        plot.points = [(0, 0), (5, 5), (10, 10), (50, 50)]
        self.my_graph.add_plot(plot)

class MyScrollView(ScrollView):
    def __init__(self, **kwargs):
        super(MyScrollView, self).__init__(**kwargs)

class MyScrollScreen(Screen):
    def __init__(self, **kwargs):
        kwargs['cols'] = 1
        super(MyScrollScreen, self).__init__(**kwargs)
        self.add_widget(MyScrollView())

# MyScrollWidget = MyScrollScreen()

config_ini = '''
[network]
enable = false
'''

Builder.load_string('''
#:import FadeTransition kivy.uix.screenmanager.FadeTransition
#:import Clock kivy.clock.Clock
#:import partial functools

<InitialScreen>
    name: 'initial_screen'
    BoxLayout:
        orientation: 'horizontal'
        BoxLayout:
            orientation: 'vertical'
            Button:
                text: 'Settings'
                on_press: app.open_settings()
            Button:
                text: 'View Sensors'
                on_press: app.root.current = 'connecting_server_screen'
            Button:
                text: 'Log screen'
                on_press: app.root.current = 'log_screen'
            Button:
                text: 'Graph screen'
                on_press: app.root.current = 'graph_screen'
            Button:
                text: 'About'
                on_press: app.root.current = 'about_screen'
            Button:
                text: 'Scroll View'
                on_press: app.root.current = 'scroll_screen'
        BoxLayout:
            orientation: 'vertical'
            Image:
                source: 'logo.png'
                allow_stretch: False
                keep_ratio: True
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
    on_enter: Clock.schedule_once(self.call_connect_sensor_status, 3)
    BoxLayout:
        orientation: 'vertical'
        Label:
            font_size: 30
            text: root.connection_status
        Image:
            source: 'spinning.gif'
            allow_stretch: False
            keep_ratio: True
        Label:
            font_size: 20
            text: root.json_sensors[:40]

<ViewSensorScreen>
    name: 'view_sensor_screen'
    BoxLayout:
        orientation: 'horizontal'
        Label:
            text: 'test'

<AboutScreen>
    name: 'about_screen'
    BoxLayout:
        orientation: 'vertical'
        Image:
            source: 'daniel_engvall.png'
            allow_stretch: False
            keep_ratio: True
        Label:
            text: 'EdoAutoHome - daniel@engvalls.eu'
            size_hint: None, None
            font_size: self.width / 4
            pos_hint: {'center_x': .5, 'top': .5}

<LogScreen>
    name: 'log_screen'
    BoxLayout:
        TextInput:
            text: 'app.data'

<GraphScreen>
    name: 'graph_screen'
    my_graph: my_graph
    BoxLayout:
        Button:
            text: 'Draw Graph'
            on_press: root.draw_graph()
        Graph:
            id: my_graph
            pos: 0,0
            size: 50, 50
            x_grid_label:True
            y_grid_label:True
            x_grid:True
            y_grid:True
''')

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
        self.app.print_message("connection lost")

    def clientConnectionFailed(self, conn, reason):
        self.app.print_message("connection failed")


class MyScreenManager(ScreenManager):
    connect_server_status = StringProperty('A Initiating connection')
    def __init__(self, **kwargs):
        super(MyScreenManager, self).__init__(**kwargs)
        self._app = App.get_running_app()

'''
MyScreenManager:
    id: manager
    transition: FadeTransition()
    ViewSensorScreen:
'''

class MyApp(App):
    data = StringProperty('initial text')
    connection = None

    def __init__(self, **kwargs):
        # Superclass if we like to adjust present init
        super(MyApp, self).__init__(**kwargs)


    def build_config(self, config):
        config.setdefaults('network', {
                            'enable': False,
                            'ip': '127.0.0.1',
                            'port': '3000',
                            'refresh_time': '60'
                            })

    def build_settings(self, settings):
        import json
        self.setting_json = '''[
            {
                "type": "title",
                "title": "Server"
            },
            {
                "type": "bool",
                "title": "Enable",
                "desc": "Enable connection to server",
                "section": "network",
                "key": "enable",
                "true": "auto"
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
                "title": "Refresh Time",
                "desc": "Number of seconds before refresh",
                "section": "network",
                "key": "refresh_time"
            }

        ]'''
        settings.add_json_panel('EdoAutoHome', self.config, data=self.setting_json)


    def build(self):
        import time
        super(MyApp, self).build()

        # Configuration settings
        config = self.config
        self.settings_cls = SettingsWithSidebar

        # Clock handler
        # Clock.schedule_interval(self.timer, 20)

        # Fix ScrollView
        # container = self.root.ids.container
        # container.add_widget(MyScrollWidget)

        sm = MyScreenManager(id='manager', transition=FadeTransition())
        sm.add_widget(InitialScreen(name='initial_screen'))
        # sm.add_widget(LogScreen(name='log_screen'))
        sm.add_widget(AboutScreen(name='about_screen'))
        # sm.add_widget(GraphScreen(name='graph_screen'))

        # Test creating Scroll View
        l = Label(text=str('Really Long Text\n' * 30), font_size=30, text_size=(400, None), height=100, size_hint_y=None)
        s = MyScrollScreen(name='scroll_screen')
        s.add_widget(l)
        sm.add_widget(s)
        # sm.add_widget(MyScrollScreen(name='scroll_screen'))

        sm.add_widget(ConnectingServerScreen(name='connecting_server_screen'))

        # Add configuration to ConnectingServerScreen
        for screen in sm.screens:
            if screen.name == 'connecting_server_screen':
                screen._app = App.get_running_app()
                port = self.config.get('network', 'port')
                server = self.config.get('network', 'ip')
                self.connection_screen = screen
                screen.connection_status = "Connecting to %s:%s" % (server, port)

        # Return ScreenManager
        return sm

    def timer(self, dt):
        # self.connect_to_server()
        # self.send_message()
        pass

    def connect_to_server(self):
        server = str(self.config.get('network', 'ip'))
        port = int(self.config.get('network', 'port'))
        return reactor.connectTCP(server, port, ConnectionClass(self))

    def on_connection(self, connection):
        # self.print_message("connected succesfully!")
        self.connection_screen.connection_status = 'Connected succesfully, retrieve JSON!'
        self.connection = connection
        # Send actual command to server
        self.send_message()

    def send_message(self, *args):
        msg = '"show_status_json"'
        if msg and self.connection:
            print "Sending %s" % (msg,)
            self.connection.write(msg)

    def print_message(self, msg):
        # Successfully receieved JSON
        if str(msg).find('{') > 0 or str(msg).find('}') > 0:
            if not str(msg)[0] == '{':
                print "Appending JSON"
                self.connection_screen.json_sensors += str(msg)
            else:
                print "Found JSON"
                self.connection_screen.json_sensors = str(msg)
            print "Printing Result of JSON Sensor"
            print self.connection_screen.json_sensors
            self.connection_screen.connection_status = 'Retrieving JSON!'
            # Save to local file as debug
            with open('debug.txt', 'w') as f:
                f.write(msg)
        # Failed connection
        if msg.find("failed") > 0:
            self.connection_screen.connection_status = 'connection failed!'

MyApp().run()
